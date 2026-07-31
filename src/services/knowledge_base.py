"""Knowledge Base business logic and storage."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional
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
    KbDocumentVersion,
)
from schemas.knowledge_base import KbDocumentCreate, KbDocumentUpdate
from services.document_processor import DocumentProcessor
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

        return KbDocumentVersion(
            document_id=document_id,
            version_number=version_number,
            storage_path=str(storage_path.relative_to(self.root_path)),
            original_filename=original_filename,
            file_size=file_size,
            mime_type=mime,
            status=DocumentStatus.PENDING,
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

        version = await self._save_upload(document.id, file, version_number=1)
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(document, attribute_names=["versions"])
        return document

    async def list_documents(
        self,
        *,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[KbDocument]:
        """Return a paginated list of documents with optional filters."""
        stmt = select(KbDocument).order_by(KbDocument.created_at.desc())
        if course_id is not None:
            stmt = stmt.where(KbDocument.course_id == course_id)
        if module_id is not None:
            stmt = stmt.where(KbDocument.module_id == module_id)
        if is_published is not None:
            stmt = stmt.where(KbDocument.is_published == is_published)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique())

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
        return document

    async def delete_document(self, document_id: int) -> None:
        """Soft-delete a document by archiving it."""
        document = await self.get_document(document_id)
        document.status = DocumentStatus.ARCHIVED
        document.is_published = False
        for version in document.versions:
            version.status = DocumentStatus.ARCHIVED
            version.is_active = False
        await self.db.commit()

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
        version = await self._save_upload(document_id, file, next_version)
        version.status = DocumentStatus.PENDING
        self.db.add(version)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def toggle_publish(self, document_id: int, publish: bool) -> KbDocument:
        """Publish or unpublish a document and manage version activation."""
        document = await self.get_document(document_id)
        document.is_published = publish
        if publish:
            document.status = DocumentStatus.PENDING
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
        else:
            document.status = DocumentStatus.DRAFT
            for version in document.versions:
                version.is_active = False
        await self.db.commit()
        await self.db.refresh(document)
        return document

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

        try:
            file_path = self.root_path / active_version.storage_path
            tuning = await RetrievalTuningService(self.db).get_or_create_default()
            processor = DocumentProcessor(
                chunk_size=tuning.chunk_size,
                chunk_overlap=tuning.chunk_overlap,
            )
            rag = RagPipeline()

            chunks = processor.process(file_path, active_version.mime_type)

            # Remove any previously indexed chunks for this document.
            # Only the currently active version should remain searchable.
            try:
                rag.collection.delete(where={"document_id": document.id})
            except Exception:
                # Collection may be empty or not exist yet; safe to ignore.
                pass

            # Clean up old chunk traceability records for the active version.
            for old_chunk in active_version.chunks:
                await self.db.delete(old_chunk)

            indexed_count = await rag.index_chunks(
                chunks=chunks,
                document_id=document.id,
                version_id=active_version.id,
                course_id=document.course_id,
                module_id=document.module_id,
                topic_id=document.topic_id,
                difficulty=document.difficulty.value,
            )

            for chunk in chunks:
                db_chunk = KbDocumentChunk(
                    version_id=active_version.id,
                    chunk_index=chunk.chunk_index,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    token_count=chunk.token_count,
                    status=DocumentStatus.INDEXED,
                )
                self.db.add(db_chunk)

            active_version.chunk_count = indexed_count
            active_version.status = DocumentStatus.INDEXED
            document.status = DocumentStatus.INDEXED
            document.last_error = None
            await self.db.commit()
            await self.db.refresh(document)
            return document

        except Exception as exc:
            await self.db.rollback()
            document.status = DocumentStatus.ERROR
            active_version.status = DocumentStatus.ERROR
            document.last_error = f"{type(exc).__name__}: {exc}"
            await self.db.commit()
            await self.db.refresh(document)
            raise KnowledgeBaseError(
                f"Failed to process document {document_id}: {exc}"
            ) from exc

    async def reindex_all_published(self) -> dict:
        """Reindex all currently published documents."""
        documents = await self.list_documents(is_published=True)
        processed = 0
        failed = 0
        for document in documents:
            try:
                await self.process_document(document.id)
                processed += 1
            except Exception:
                failed += 1
        return {"processed": processed, "failed": failed, "total": len(documents)}

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
