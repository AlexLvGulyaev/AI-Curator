#!/usr/bin/env python3
"""One-off cleanup script for orphaned KB documents.

A document/version is considered orphaned when the raw file referenced by
KbDocumentVersion.storage_path no longer exists in the filesystem.
Such documents cannot be previewed or reindexed and only produce 500 errors.

The script archives (soft-deletes) every document whose active version file
is missing. It is idempotent: running it twice archives nothing new.
"""

import asyncio
import sys
from pathlib import Path

# Allow imports from the backend package when running inside the container.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from db import AsyncSessionLocal
from models.knowledge_base import KbDocument, KbDocumentVersion
from services.knowledge_base import KnowledgeBaseService
from services.rag_pipeline import RagPipeline


KB_ROOT = Path(settings.doc_store_path)


def _document_ids_in_chroma() -> set:
    """Return all document_id values currently present in the Chroma index."""
    try:
        rag = RagPipeline()
        count = rag.collection.count()
        if count == 0:
            return set()
        result = rag.collection.get(limit=count, include=["metadatas"])
        return {int(meta.get("document_id")) for meta in result["metadatas"] if meta.get("document_id") is not None}
    except Exception:
        # If Chroma is unreachable, fall back to empty set and let the
        # regular file-based check decide.
        return set()


async def main():
    async with AsyncSessionLocal() as db:
        service = KnowledgeBaseService(db)

        result = await db.execute(
            select(KbDocument)
            .options(selectinload(KbDocument.versions))
            .where(KbDocument.status != "archived")
        )
        documents = result.scalars().all()

        chroma_doc_ids = _document_ids_in_chroma()

        orphans = []
        for document in documents:
            # Skip documents that still have indexed chunks in Chroma.
            # They can be restored from the vector store even if the raw
            # source file is missing; archiving them would break RAG answers.
            if document.id in chroma_doc_ids:
                continue
            for version in document.versions:
                file_path = KB_ROOT / version.storage_path
                if not file_path.exists():
                    orphans.append((document.id, document.title, version.id, str(file_path)))
                    break  # one missing file is enough to archive the document

        if not orphans:
            print("No orphaned KB documents found.")
            return

        print(f"Found {len(orphans)} orphaned KB document(s):")
        for doc_id, title, version_id, file_path in orphans:
            print(f"  - doc_id={doc_id} title={title!r} version_id={version_id} missing_file={file_path}")

        for doc_id, *_ in orphans:
            await service.delete_document(doc_id)
            print(f"  Archived document {doc_id}")

        print(f"Cleanup complete. Archived {len(orphans)} document(s).")


if __name__ == "__main__":
    asyncio.run(main())
