"""Knowledge Base business logic and storage."""

from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models.knowledge_base import (
    DifficultyLevel,
    DocumentStatus,
    DocumentType,
    KbDocument,
    KbDocumentChunk,
    KbDocumentEvent,
    KbDocumentVersion,
)
from schemas.knowledge_base import KbDocumentCreate, KbDocumentUpdate
from services.document_processor import DocumentProcessor, DocumentProcessorError
from services.kb_git import KbGitService
from services.kb_lifecycle import KbLifecycleService
from services.rag_pipeline import RagPipeline
from services.retrieval_tuning import RetrievalTuningService

KB_ROOT = Path(settings.doc_store_path)
ALLOWED_MIME_TYPES = {
    "text/markdown": ".md",
    "text/plain": ".txt",
    "application/pdf": ".pdf",
}


class KnowledgeBaseError(Exception):
    """Base exception for Knowledge Base operations."""

    pass


class UnsupportedFileError(KnowledgeBaseError):
    """Raised when an unsupported file type is uploaded."""

    pass


class DocumentNotFoundError(KnowledgeBaseError):
    """Raised when a document is not found."""

    pass


class KnowledgeBaseService:
    """Service for managing Knowledge Base documents, versions and storage."""

    def __init__(self, db: AsyncSession, root_path: Path = KB_ROOT):
        self.db = db
        self.root_path = root_path
        self.root_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Storage helpers
    # ------------------------------------------------------------------

    def _storage_dir(self, document_id: int) -> Path:
        return self.root_path / str(document_id)

    async def _save_upload(
        self,
        document_id: int,
        file: UploadFile,
        version_number: int,
        *,
        document_type: str = "lecture",
        course_id: Optional[int] = None,
    ) -> KbDocumentVersion:
        """Persist an uploaded file to disk and return a version record."""
        mime = file.content_type or "application/octet-stream"
        ext = ALLOWED_MIME_TYPES.get(mime)
        if ext is None and mime.startswith("text/"):
            ext = ".txt"
        if ext is None:
            raise UnsupportedFileError(f"MIME type '{mime}' is not supported.")

        original_filename = file.filename or f"document{ext}"
        storage_filename = f"v{version_number}_{uuid4().hex}{ext}"
        storage_dir = self._storage_dir(document_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / storage_filename

        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(storage_path)
        sha256 = hashlib.sha256(storage_path.read_bytes()).hexdigest()

        # Capture Git provenance if Git workflow is enabled.
        git_info: Dict[str, Any] = {}
        if settings.kb_content_git_enabled:
            try:
                git = KbGitService()
                commit_result = git.commit_file(
                    storage_path,
                    document_type=document_type,
                    course_id=course_id,
                    filename=original_filename,
                    message=(
                        f"feat(kb): upload {original_filename} "
                        f"(doc {document_id}, v{version_number})"
                    ),
                )
                git_info["git_commit_hash"] = commit_result.get("commit_hash")
                git_info["git_blob_hash"] = commit_result.get("git_blob_hash")
                git_info["git_author"] = commit_result.get("author_name")
                git_info["git_commit_message"] = commit_result.get("message")
                committed_at = commit_result.get("committed_at")
                if committed_at:
                    if isinstance(committed_at, str):
                        git_info["git_committed_at"] = datetime.fromisoformat(
                            committed_at.replace("Z", "+00:00")
                        )
                    else:
                        git_info["git_committed_at"] = committed_at
            except Exception:
                # Git commit must not break the upload flow.
                pass

        return KbDocumentVersion(
            document_id=document_id,
            version_number=version_number,
            storage_path=str(storage_path.relative_to(self.root_path)),
            raw_storage_path=str(storage_path.relative_to(self.root_path)),
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime,
            status=DocumentStatus.PENDING,
            sha256=sha256,
            **git_info,
        )

    # ------------------------------------------------------------------
    # CRUD documents
    # ------------------------------------------------------------------

    async def create_document(
        self,
        data: KbDocumentCreate,
        file: UploadFile,
    ) -> KbDocument:
        """Create a document card and store the initial version."""
        document = KbDocument(
            title=data.title,
            document_type=DocumentType(data.document_type),
            course_id=data.course_id,
            module_id=data.module_id,
            topic_id=data.topic_id,
            difficulty=DifficultyLevel(data.difficulty),
            language=data.language,
            description=data.description,
            source_url=data.source_url,
            status=DocumentStatus.PENDING,
            is_published=False,
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)

        version = await self._save_upload(
            document.id,
            file,
            version_number=1,
            document_type=document.document_type.value,
            course_id=document.course_id,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(document, attribute_names=["versions"])

        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document.id,
            version_id=version.id,
            event_type="upload",
            status="success",
            message=f"Created document with initial version {version.version_number}",
            details={
                "version_id": version.id,
                "version_number": version.version_number,
                "original_filename": version.original_filename,
                "file_size": version.file_size,
                "mime_type": version.mime_type,
                "git_commit_hash": version.git_commit_hash,
            },
        )
        return document

    async def list_documents(
        self,
        *,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KbDocument]:
        """Return a paginated list of documents with optional filters."""
        stmt = (
            select(KbDocument)
            .options(selectinload(KbDocument.versions))
            .order_by(KbDocument.created_at.desc())
        )
        if course_id is not None:
            stmt = stmt.where(KbDocument.course_id == course_id)
        if module_id is not None:
            stmt = stmt.where(KbDocument.module_id == module_id)
        if is_published is not None:
            stmt = stmt.where(KbDocument.is_published == is_published)
        if status:
            stmt = stmt.where(KbDocument.status == DocumentStatus(status))
        if document_type:
            stmt = stmt.where(KbDocument.document_type == DocumentType(document_type))
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        documents = list(result.scalars().unique())
        # Eagerly load scalar attributes while still inside the async greenlet.
        for doc in documents:
            _ = doc.id, doc.title, doc.is_published, doc.status, doc.document_type
        return documents

    async def get_document(self, document_id: int) -> KbDocument:
        """Return a document by id or raise DocumentNotFoundError."""
        stmt = (
            select(KbDocument)
            .where(KbDocument.id == document_id)
            .options(
                selectinload(KbDocument.versions).selectinload(
                    KbDocumentVersion.chunks
                )
            )
        )
        result = await self.db.execute(stmt)
        document = result.unique().scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        return document

    async def update_document(
        self,
        document_id: int,
        data: KbDocumentUpdate,
    ) -> KbDocument:
        """Update document metadata."""
        document = await self.get_document(document_id)
        update_data = data.model_dump(exclude_unset=True)
        if "document_type" in update_data:
            update_data["document_type"] = DocumentType(update_data["document_type"])
        if "difficulty" in update_data:
            update_data["difficulty"] = DifficultyLevel(update_data["difficulty"])
        for field, value in update_data.items():
            setattr(document, field, value)
        await self.db.commit()
        await self.db.refresh(document)

        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document.id,
            event_type="metadata_update",
            status="success",
            message="Document metadata updated",
            details={"updated_fields": list(update_data.keys())},
        )
        return document

    async def delete_document(self, document_id: int) -> None:
        """Soft-delete a document by archiving it."""
        document = await self.get_document(document_id)
        previous_status = document.status.value
        was_published = document.is_published
        document.status = DocumentStatus.ARCHIVED
        document.is_published = False
        for version in document.versions:
            version.status = DocumentStatus.ARCHIVED
            version.is_active = False
        await self.db.commit()

        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document_id,
            event_type="delete",
            status="success",
            message="Document archived",
            details={
                "previous_status": previous_status,
                "was_published": was_published,
            },
        )

    # ------------------------------------------------------------------
    # Versions and publishing
    # ------------------------------------------------------------------

    async def add_version(
        self,
        document_id: int,
        file: UploadFile,
    ) -> KbDocumentVersion:
        """Upload a new version of an existing document."""
        document = await self.get_document(document_id)
        next_version = len(document.versions) + 1
        version = await self._save_upload(
            document_id,
            file,
            next_version,
            document_type=document.document_type.value,
            course_id=document.course_id,
        )
        version.status = DocumentStatus.PENDING
        self.db.add(version)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(version)

        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document_id,
            version_id=version.id,
            event_type="upload",
            status="success",
            message=f"Added version {version.version_number}",
            details={
                "version_id": version.id,
                "version_number": version.version_number,
                "original_filename": version.original_filename,
                "file_size": version.file_size,
                "mime_type": version.mime_type,
                "git_commit_hash": version.git_commit_hash,
            },
        )
        return version

    async def toggle_publish(self, document_id: int, publish: bool) -> KbDocument:
        """Publish or unpublish a document and manage version activation."""
        document = await self.get_document(document_id)
        document.is_published = publish
        if publish:
            # Activate the most recent pending/indexed version, deactivate others.
            candidates = [
                version
                for version in document.versions
                if version.status in (DocumentStatus.PENDING, DocumentStatus.INDEXED)
            ]
            if not candidates:
                raise KnowledgeBaseError(
                    f"Document {document_id} has no processable version to publish."
                )
            latest = max(candidates, key=lambda v: v.version_number)
            for version in document.versions:
                version.is_active = version.id == latest.id
            # If the activated version is already indexed, keep the document status
            # indexed. Otherwise mark it pending so it will be processed.
            if latest.status == DocumentStatus.INDEXED:
                document.status = DocumentStatus.INDEXED
            else:
                document.status = DocumentStatus.PENDING
        else:
            document.status = DocumentStatus.DRAFT
            for version in document.versions:
                version.is_active = False
        await self.db.commit()
        await self.db.refresh(document)

        active_version_id = document.active_version.id if document.active_version else None
        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document_id,
            event_type="publish" if publish else "unpublish",
            status="success",
            message="Document published" if publish else "Document unpublished",
            details={
                "is_published": document.is_published,
                "active_version_id": active_version_id,
            },
        )
        return document

    async def _index_cleaned_text(
        self,
        document: KbDocument,
        version: KbDocumentVersion,
        cleaned_text: str,
        *,
        commit: bool = True,
    ) -> int:
        """Split cleaned text into chunks, persist them and index in Chroma.

        Returns the number of indexed chunks. The caller controls the final
        transaction commit so this helper can be reused inside larger flows.
        """
        tuning = await RetrievalTuningService(self.db).get_or_create_default()
        processor = DocumentProcessor(
            chunk_size=tuning.chunk_size,
            chunk_overlap=tuning.chunk_overlap,
        )
        rag = RagPipeline()

        chunks = processor.split_text(cleaned_text)

        # Remove any previously indexed chunks for this document.
        # Only the currently active version should remain searchable.
        try:
            rag.collection.delete(where={"document_id": document.id})
        except Exception:
            # Collection may be empty or not exist yet; safe to ignore.
            pass

        # Clean up old chunk traceability records for the version.
        for old_chunk in version.chunks:
            await self.db.delete(old_chunk)

        indexed_count = await rag.index_chunks(
            chunks=chunks,
            document_id=document.id,
            version_id=version.id,
            course_id=document.course_id,
            module_id=document.module_id,
            topic_id=document.topic_id,
            difficulty=document.difficulty.value,
            embedding_timeout_ms=tuning.embedding_timeout_ms,
        )

        for chunk in chunks:
            db_chunk = KbDocumentChunk(
                version_id=version.id,
                chunk_index=chunk.chunk_index,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                token_count=chunk.token_count,
                content_preview=(chunk.content[:4000] if chunk.content else None),
                status=DocumentStatus.INDEXED,
            )
            self.db.add(db_chunk)

        version.chunk_count = indexed_count
        version.status = DocumentStatus.INDEXED
        version.indexed_at = datetime.now(timezone.utc)
        version.embedding_model = settings.openai_embedding_model
        document.status = DocumentStatus.INDEXED
        document.last_error = None

        if commit:
            await self.db.commit()
        return indexed_count

    async def process_document(self, document_id: int) -> KbDocument:
        """Process the active version of a document: chunk, embed and index in Chroma."""
        document = await self.get_document(document_id)

        active_version = document.active_version
        if active_version is None:
            raise KnowledgeBaseError(
                f"Document {document_id} has no active version to process."
            )

        document.status = DocumentStatus.PROCESSING
        active_version.status = DocumentStatus.PROCESSING
        await self.db.commit()

        lifecycle = KbLifecycleService(self.db)
        start_event = await lifecycle.start_event(
            document_id=document.id,
            version_id=active_version.id,
            event_type="index_start",
            message=f"Started indexing version {active_version.version_number}",
            details={
                "version_id": active_version.id,
                "version_number": active_version.version_number,
                "mime_type": active_version.mime_type,
            },
            commit=False,
        )

        try:
            file_path = self.root_path / active_version.storage_path
            tuning = await RetrievalTuningService(self.db).get_or_create_default()
            processor = DocumentProcessor(
                chunk_size=tuning.chunk_size,
                chunk_overlap=tuning.chunk_overlap,
            )

            # Load cleaned text. Persist the cleaned copy so the console
            # can show both RAW and cleaned previews without re-processing.
            cleaned_text = processor.load_cleaned_text(file_path, active_version.mime_type)

            storage_dir = self._storage_dir(document_id)
            cleaned_filename = f"v{active_version.version_number}_{uuid4().hex}.cleaned.md"
            cleaned_path = storage_dir / cleaned_filename
            cleaned_path.write_text(cleaned_text, encoding="utf-8")
            active_version.cleaned_storage_path = str(
                cleaned_path.relative_to(self.root_path)
            )

            await self._index_cleaned_text(
                document, active_version, cleaned_text, commit=False
            )

            await lifecycle.finish_event(
                event_id=start_event.id,
                status="success",
                message=f"Indexed {active_version.chunk_count} chunks",
                details={"chunk_count": active_version.chunk_count},
                commit=False,
            )

            await self.db.commit()
            await self.db.refresh(document)
            return document

        except Exception as exc:
            await self.db.rollback()

            # Refresh in-memory objects after rollback so we can update their status.
            document = await self.get_document(document_id)
            active_version = document.active_version
            if active_version is None:
                raise KnowledgeBaseError(
                    f"Document {document_id} has no active version after rollback."
                ) from exc

            document.status = DocumentStatus.ERROR
            active_version.status = DocumentStatus.ERROR
            document.last_error = f"{type(exc).__name__}: {exc}"

            await lifecycle.finish_event(
                event_id=start_event.id,
                status="error",
                message=str(exc),
                details={"error": f"{type(exc).__name__}: {exc}"},
                commit=False,
            )

            await self.db.commit()
            await self.db.refresh(document)
            raise KnowledgeBaseError(
                f"Failed to process document {document_id}: {exc}"
            ) from exc

    async def save_version_text(
        self,
        document_id: int,
        version_id: int,
        text: str,
        *,
        reindex: bool = True,
    ) -> KbDocument:
        """Persist edited cleaned text for a version and optionally reindex it."""
        document = await self.get_document(document_id)
        version = next(
            (v for v in document.versions if v.id == version_id),
            None,
        )
        if version is None:
            raise DocumentNotFoundError(
                f"Version {version_id} not found for document {document_id}"
            )
        if version.status == DocumentStatus.ARCHIVED:
            raise KnowledgeBaseError(f"Version {version_id} is archived")

        # Persist the edited cleaned text to disk and update provenance.
        storage_dir = self._storage_dir(document_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        cleaned_filename = f"v{version.version_number}_{uuid4().hex}.cleaned.md"
        cleaned_path = storage_dir / cleaned_filename
        cleaned_path.write_text(text, encoding="utf-8")
        version.cleaned_storage_path = str(cleaned_path.relative_to(self.root_path))
        version.sha256 = hashlib.sha256(cleaned_path.read_bytes()).hexdigest()

        # Capture Git provenance for cleaned text if Git workflow is enabled.
        if settings.kb_content_git_enabled:
            try:
                git = KbGitService()
                cleaned_filename = f"{Path(version.original_filename).stem}.cleaned.md"
                commit_result = git.commit_file(
                    cleaned_path,
                    document_type=document.document_type.value,
                    course_id=document.course_id,
                    filename=cleaned_filename,
                    message=(
                        f"feat(kb): update cleaned text for {version.original_filename} "
                        f"(doc {document_id}, v{version.version_number})"
                    ),
                )
                version.git_commit_hash = commit_result.get("commit_hash")
                version.git_blob_hash = commit_result.get("git_blob_hash")
                version.git_author = commit_result.get("author_name")
                version.git_commit_message = commit_result.get("message")
                committed_at = commit_result.get("committed_at")
                if committed_at:
                    if isinstance(committed_at, str):
                        version.git_committed_at = datetime.fromisoformat(
                            committed_at.replace("Z", "+00:00")
                        )
                    else:
                        version.git_committed_at = committed_at
            except Exception:
                # Git commit must not break the save flow.
                pass

        lifecycle = KbLifecycleService(self.db)

        if reindex:
            # Activate the edited version and index the new cleaned text.
            for v in document.versions:
                v.is_active = v.id == version_id
            version.status = DocumentStatus.PROCESSING
            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            start_event = await lifecycle.start_event(
                document_id=document.id,
                version_id=version.id,
                event_type="reindex_start",
                message=(
                    f"Started reindexing edited cleaned text for version "
                    f"{version.version_number}"
                ),
                details={
                    "version_id": version.id,
                    "version_number": version.version_number,
                    "char_count": len(text),
                },
                commit=False,
            )

            try:
                await self._index_cleaned_text(
                    document, version, text, commit=False
                )
                await lifecycle.finish_event(
                    event_id=start_event.id,
                    status="success",
                    message=(
                        f"Reindexed version {version.version_number} after "
                        f"cleaned text edit"
                    ),
                    details={"chunk_count": version.chunk_count},
                    commit=False,
                )
                await self.db.commit()
            except Exception as exc:
                await self.db.rollback()

                # Refresh objects after rollback to record the failure.
                document = await self.get_document(document_id)
                version = next(
                    (v for v in document.versions if v.id == version_id),
                    None,
                )
                if version is None:
                    raise KnowledgeBaseError(
                        f"Version {version_id} not found after rollback"
                    ) from exc

                document.status = DocumentStatus.ERROR
                version.status = DocumentStatus.ERROR
                document.last_error = f"{type(exc).__name__}: {exc}"

                await lifecycle.finish_event(
                    event_id=start_event.id,
                    status="error",
                    message=str(exc),
                    details={"error": f"{type(exc).__name__}: {exc}"},
                    commit=False,
                )
                await self.db.commit()
                await self.db.refresh(document)
                raise KnowledgeBaseError(
                    f"Failed to reindex edited cleaned text: {exc}"
                ) from exc
        else:
            version.status = DocumentStatus.PENDING
            document.status = DocumentStatus.PENDING
            await self.db.commit()
            await lifecycle.record_event(
                document_id=document.id,
                version_id=version.id,
                event_type="metadata_update",
                status="success",
                message=(
                    f"Saved cleaned text for version {version.version_number}"
                ),
                details={
                    "version_id": version.id,
                    "version_number": version.version_number,
                    "char_count": len(text),
                    "reindex": False,
                },
            )

        return await self.get_document(document_id)

    async def reindex_all_published(self) -> dict:
        """Reindex all currently published documents."""
        documents = await self.list_documents(is_published=True)
        # Snapshot scalar ids before any nested processing to avoid lazy-loading
        # expired objects outside the async greenlet context.
        document_ids = []
        for document in documents:
            document_ids.append(
                {
                    "id": document.id,
                    "title": document.title,
                }
            )
        processed = 0
        failed = 0
        lifecycle = KbLifecycleService(self.db)
        for snapshot in document_ids:
            document_id = snapshot["id"]
            document_title = snapshot["title"]
            start_event = await lifecycle.start_event(
                document_id=document_id,
                event_type="reindex_start",
                message=f"Starting reindex of document {document_id}",
                details={"document_id": document_id, "title": document_title},
            )
            # Snapshot the scalar id before process_document commits/rolls back,
            # otherwise the ORM object expires and cannot be refreshed in the
            # nested async greenlet context.
            start_event_id = start_event.id
            try:
                await self.process_document(document_id)
                processed += 1
                await lifecycle.finish_event(
                    event_id=start_event_id,
                    status="success",
                    message=f"Document {document_id} reindexed",
                    details={"document_id": document_id},
                )
            except Exception as exc:
                failed += 1
                await lifecycle.finish_event(
                    event_id=start_event_id,
                    status="error",
                    message=str(exc),
                    details={"error": f"{type(exc).__name__}: {exc}"},
                )
        return {"processed": processed, "failed": failed, "total": len(document_ids)}

    # ------------------------------------------------------------------
    # Operational console helpers
    # ------------------------------------------------------------------

    async def get_document_detail_bundle(
        self,
        document_id: int,
        timeline_limit: int = 100,
    ) -> Dict[str, Any]:
        """Return document metadata, active version, chunks, timeline and execution info."""
        document = await self.get_document(document_id)
        active_version = document.active_version

        chunks: List[Dict[str, Any]] = []
        execution: Dict[str, Any] = {}
        if active_version:
            chunks = [
                {
                    "id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "token_count": chunk.token_count,
                    "content_preview": chunk.content_preview,
                    "status": chunk.status.value,
                    "created_at": (
                        chunk.created_at.isoformat() if chunk.created_at else None
                    ),
                }
                for chunk in active_version.chunks
            ]

            # Compute file sizes for RAW and cleaned copies.
            raw_size = 0
            cleaned_size = 0
            raw_path = (
                self.root_path / active_version.storage_path
                if active_version.storage_path
                else None
            )
            cleaned_path = (
                self.root_path / active_version.cleaned_storage_path
                if active_version.cleaned_storage_path
                else None
            )
            if raw_path and raw_path.exists():
                raw_size = raw_path.stat().st_size
            if cleaned_path and cleaned_path.exists():
                cleaned_size = cleaned_path.stat().st_size

            execution = {
                "provider": "OpenAI",
                "model": active_version.embedding_model or settings.openai_embedding_model,
                "backend": "Chroma",
                "sha256": active_version.sha256,
                "indexed_at": (
                    active_version.indexed_at.isoformat()
                    if active_version.indexed_at
                    else None
                ),
                "raw_size": raw_size,
                "cleaned_size": cleaned_size,
                "postgres_status": active_version.status.value,
            }

        lifecycle = KbLifecycleService(self.db)
        timeline = await lifecycle.get_timeline(document_id, limit=timeline_limit)

        return {
            "document": document,
            "active_version": active_version,
            "chunks": chunks,
            "timeline": timeline,
            "execution": execution,
        }

    async def get_version_text_preview(
        self,
        version_id: int,
        limit: int = 262144,
        stage: str = "cleaned",
    ) -> Dict[str, Any]:
        """Return raw or cleaned text preview for a specific document version."""
        stmt = (
            select(KbDocumentVersion)
            .where(KbDocumentVersion.id == version_id)
            .options(selectinload(KbDocumentVersion.document))
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            raise DocumentNotFoundError(f"Version {version_id} not found")

        processor = DocumentProcessor()
        if stage == "raw":
            file_path = self.root_path / version.storage_path
            text = processor.load_raw_text(file_path, version.mime_type)
        elif stage == "cleaned":
            # Prefer the persisted cleaned copy when available.
            if version.cleaned_storage_path:
                file_path = self.root_path / version.cleaned_storage_path
                try:
                    text = processor.load_cleaned_text(file_path, version.mime_type)
                except DocumentProcessorError:
                    # Persisted cleaned copy missing; fall back to raw.
                    file_path = self.root_path / version.storage_path
                    text = processor.load_cleaned_text(file_path, version.mime_type)
            else:
                # Legacy fallback: clean on the fly from the original file.
                file_path = self.root_path / version.storage_path
                text = processor.load_cleaned_text(file_path, version.mime_type)
        else:
            raise KnowledgeBaseError(
                f"Unknown preview stage '{stage}'. Use 'raw' or 'cleaned'."
            )

        preview = text[:limit]

        return {
            "version_id": version.id,
            "version_number": version.version_number,
            "stage": stage,
            "original_filename": version.original_filename,
            "mime_type": version.mime_type,
            "total_length": len(text),
            "preview_length": len(preview),
            "preview": preview,
        }

    async def get_version_chunks(
        self,
        version_id: int,
    ) -> List[Dict[str, Any]]:
        """Return traceability chunks for a specific version."""
        stmt = (
            select(KbDocumentChunk)
            .where(KbDocumentChunk.version_id == version_id)
            .order_by(KbDocumentChunk.chunk_index)
        )
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()
        return [
            {
                "id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "token_count": chunk.token_count,
                "content_preview": chunk.content_preview,
                "status": chunk.status.value,
                "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
            }
            for chunk in chunks
        ]

    async def activate_version(
        self,
        document_id: int,
        version_id: int,
    ) -> KbDocument:
        """Mark a specific version as active without reindexing it."""
        document = await self.get_document(document_id)
        version = next(
            (v for v in document.versions if v.id == version_id),
            None,
        )
        if version is None:
            raise DocumentNotFoundError(
                f"Version {version_id} not found for document {document_id}"
            )
        if version.status == DocumentStatus.ARCHIVED:
            raise KnowledgeBaseError(f"Version {version_id} is archived")

        for v in document.versions:
            v.is_active = v.id == version_id
        await self.db.commit()
        await self.db.refresh(document)

        lifecycle = KbLifecycleService(self.db)
        await lifecycle.record_event(
            document_id=document.id,
            version_id=version.id,
            event_type="version_activate",
            status="success",
            message=f"Version {version.version_number} set as active",
            details={
                "version_id": version.id,
                "version_number": version.version_number,
            },
        )
        return document

    async def reindex_version(
        self,
        document_id: int,
        version_id: int,
    ) -> KbDocument:
        """Activate a specific version and reindex it."""
        document = await self.activate_version(document_id, version_id)
        active_version = document.active_version
        if active_version is None or active_version.id != version_id:
            raise KnowledgeBaseError("Failed to activate version for reindexing")

        lifecycle = KbLifecycleService(self.db)
        start_event = await lifecycle.start_event(
            document_id=document.id,
            version_id=active_version.id,
            event_type="reindex_start",
            message=f"Started reindexing version {active_version.version_number}",
            details={
                "version_id": active_version.id,
                "version_number": active_version.version_number,
            },
        )

        try:
            await self.process_document(document_id)
        except Exception as exc:
            await lifecycle.finish_event(
                event_id=start_event.id,
                status="error",
                message=str(exc),
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
            raise

        await lifecycle.finish_event(
            event_id=start_event.id,
            status="success",
            message=f"Reindexed version {active_version.version_number}",
            details={"version_id": version_id},
        )
        return await self.get_document(document_id)

    async def get_status(self) -> dict:
        """Return aggregated Knowledge Base statistics."""

        async def _scalar(stmt):
            result = await self.db.execute(stmt)
            value = result.scalar()
            result.close()
            return value

        total_documents = await _scalar(
            select(func.count(KbDocument.id)).where(KbDocument.status != DocumentStatus.ARCHIVED)
        )
        published_documents = await _scalar(
            select(func.count(KbDocument.id)).where(KbDocument.is_published == True)
        )
        draft_documents = await _scalar(
            select(func.count(KbDocument.id)).where(KbDocument.status == DocumentStatus.DRAFT)
        )
        total_versions = await _scalar(
            select(func.count(KbDocumentVersion.id)).where(
                KbDocumentVersion.status != DocumentStatus.ARCHIVED
            )
        )
        active_versions = await _scalar(
            select(func.count(KbDocumentVersion.id)).where(KbDocumentVersion.is_active == True)
        )
        from models.knowledge_base import KbDocumentChunk

        total_chunks = await _scalar(select(func.count(KbDocumentChunk.id)))
        indexed_chunks = await _scalar(
            select(func.count(KbDocumentChunk.id)).where(
                KbDocumentChunk.status == DocumentStatus.INDEXED
            )
        )
        last_updated = await _scalar(
            select(func.max(KbDocument.updated_at)).where(
                KbDocument.status != DocumentStatus.ARCHIVED
            )
        )
        return {
            "total_documents": total_documents or 0,
            "published_documents": published_documents or 0,
            "draft_documents": draft_documents or 0,
            "total_versions": total_versions or 0,
            "active_versions": active_versions or 0,
            "total_chunks": total_chunks or 0,
            "indexed_chunks": indexed_chunks or 0,
            "last_updated": last_updated,
        }
