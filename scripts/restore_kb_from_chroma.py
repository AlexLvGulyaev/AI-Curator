#!/usr/bin/env python3
"""Restore a KB document from Chroma when the source file is missing.

This script reconstructs the original markdown for document_id=65
(Claude Code: быстрый старт) from its Chroma chunks, persists it to disk,
updates the database records and saves the source into the kb-content repo.
"""

import asyncio
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running both locally (src/ layout) and inside the Docker container
# where src/ is copied to the image root.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_possible_src = _repo_root / "src"
if _possible_src.exists() and str(_possible_src) not in sys.path:
    sys.path.insert(0, str(_possible_src))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from db import AsyncSessionLocal
from models.knowledge_base import (
    DifficultyLevel,
    DocumentStatus,
    DocumentType,
    KbDocument,
    KbDocumentChunk,
    KbDocumentVersion,
)
from services.document_processor import DocumentProcessor
from services.kb_git import KbGitService
from services.rag_pipeline import RagPipeline

KB_ROOT = Path(settings.doc_store_path)
KB_CONTENT_REPO = Path(__file__).resolve().parent.parent / "kb-content"


def _deduplicate_overlap(texts: list[str]) -> str:
    """Join overlapping chunks removing duplicated paragraphs.

    The heuristic is conservative: if the end of the accumulated text
    matches the start of the next chunk, drop the overlapping part.
    """
    if not texts:
        return ""
    result = texts[0]
    for next_text in texts[1:]:
        next_text = next_text.strip()
        if not next_text:
            continue
        overlap = 0
        # Try to find the longest suffix/prefix match up to 500 chars.
        max_overlap = min(500, len(result), len(next_text))
        for size in range(max_overlap, 0, -1):
            if result[-size:].strip() == next_text[:size].strip():
                overlap = size
                break
        result = result + "\n\n" + next_text[overlap:]
    return result


async def restore_document(db, document_id: int) -> KbDocument:
    """Restore a single document from Chroma chunks."""
    # Load the document and version.
    result = await db.execute(
        select(KbDocument)
        .options(selectinload(KbDocument.versions))
        .where(KbDocument.id == document_id)
    )
    document = result.scalar_one()

    version = next((v for v in document.versions if v.is_active), document.versions[0])

    # Fetch chunks from Chroma.
    rag = RagPipeline()
    chroma_result = rag.collection.get(
        where={"document_id": document_id},
        limit=100,
        include=["documents", "metadatas"],
    )

    chunks_data = sorted(
        zip(chroma_result["documents"], chroma_result["metadatas"]),
        key=lambda item: item[1].get("chunk_index", 0),
    )
    if not chunks_data:
        raise RuntimeError(f"No Chroma chunks found for document {document_id}")

    raw_text = _deduplicate_overlap([doc for doc, _ in chunks_data])

    # Normalize cleaned text.
    processor = DocumentProcessor()
    cleaned_text = processor.load_cleaned_text_from_text(raw_text)

    # Persist files.
    storage_dir = KB_ROOT / str(document_id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    raw_filename = f"v{version.version_number}_{document_id}_restored_raw.md"
    cleaned_filename = f"v{version.version_number}_{document_id}_restored_cleaned.md"
    raw_path = storage_dir / raw_filename
    cleaned_path = storage_dir / cleaned_filename

    raw_path.write_text(raw_text, encoding="utf-8")
    cleaned_path.write_text(cleaned_text, encoding="utf-8")

    # Compute sha256 of the raw file (matches original upload logic).
    sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()

    # Update version metadata.
    version.storage_path = str(raw_path.relative_to(KB_ROOT))
    version.raw_storage_path = version.storage_path
    version.cleaned_storage_path = str(cleaned_path.relative_to(KB_ROOT))
    version.sha256 = sha256
    version.status = DocumentStatus.INDEXED
    version.is_active = True
    version.indexed_at = datetime.now(timezone.utc)
    version.embedding_model = settings.openai_embedding_model
    version.chunk_count = len(chunks_data)

    # Deactivate other versions.
    for v in document.versions:
        if v.id != version.id:
            v.is_active = False

    # Update document metadata.
    document.status = DocumentStatus.INDEXED
    document.last_error = None

    # Re-create chunk traceability records.
    for old_chunk in version.chunks:
        await db.delete(old_chunk)

    for chunk_index, (chunk_text, meta) in enumerate(chunks_data):
        db_chunk = KbDocumentChunk(
            version_id=version.id,
            chunk_index=chunk_index,
            char_start=meta.get("char_start"),
            char_end=meta.get("char_end"),
            token_count=len(chunk_text) // 4,  # approximate
            content_preview=(chunk_text[:4000] if chunk_text else None),
            status=DocumentStatus.INDEXED,
        )
        db.add(db_chunk)

    await db.commit()
    await db.refresh(document)

    print(f"Restored document {document_id} from {len(chunks_data)} Chroma chunks")
    print(f"  raw: {raw_path}")
    print(f"  cleaned: {cleaned_path}")
    print(f"  sha256: {sha256}")

    return document, version


async def publish_document(db, document_id: int) -> KbDocument:
    """Publish the restored document and activate its version."""
    result = await db.execute(
        select(KbDocument)
        .options(selectinload(KbDocument.versions))
        .where(KbDocument.id == document_id)
    )
    document = result.scalar_one()

    document.is_published = True
    for v in document.versions:
        v.is_active = v.id == document.active_version.id

    await db.commit()
    await db.refresh(document)
    print(f"Published document {document_id}")
    return document


async def save_to_kb_content_repo(document: KbDocument, version: KbDocumentVersion):
    """Copy the raw source file into the kb-content Git repository."""
    safe_title = re.sub(r"[^\w\-]+", "-", document.title.lower()).strip("-")
    if document.course_id:
        dest_dir = KB_CONTENT_REPO / "courses" / str(document.course_id) / "lectures"
    else:
        dest_dir = KB_CONTENT_REPO / "courses" / "uncategorized" / "lectures"
    dest_dir.mkdir(parents=True, exist_ok=True)

    source_path = KB_ROOT / version.storage_path
    dest_path = dest_dir / f"{safe_title}.md"
    dest_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    if settings.kb_content_git_enabled:
        try:
            git = KbGitService()
            commit_result = git.add_commit_push(
                dest_path,
                message=f"chore(kb): restore {document.title} from Chroma",
            )
            print(f"Committed to kb-content: {commit_result.get('commit_hash')}")
        except Exception as exc:
            print(f"Git commit failed (git workflow may be disabled): {exc}")
    else:
        print(f"Git workflow disabled. File saved to {dest_path}")


async def main():
    async with AsyncSessionLocal() as db:
        document, version = await restore_document(db, document_id=65)
        await publish_document(db, document_id=65)
        await save_to_kb_content_repo(document, version)


if __name__ == "__main__":
    asyncio.run(main())
