"""Remove test KB documents (Git Workflow Test Doc, Prompt Engineering) and their Chroma chunks."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "/app/src")

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_session_factory
from models.knowledge_base import KbDocument, KbDocumentChunk, KbDocumentEvent, KbDocumentVersion
from services.rag_pipeline import RagPipeline


TEST_TITLES = {"Git Workflow Test Doc", "Prompt Engineering"}


async def cleanup() -> None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(KbDocument.id).where(KbDocument.title.in_(TEST_TITLES))
        )
        doc_ids = [row[0] for row in result.all()]
        if not doc_ids:
            print("No test documents found.")
            return

        print(f"Found test documents: {doc_ids}")

        # Get version ids for chroma cleanup
        version_result = await db.execute(
            select(KbDocumentVersion.id).where(KbDocumentVersion.document_id.in_(doc_ids))
        )
        version_ids = [row[0] for row in version_result.all()]

        # Delete Chroma chunks
        rag = RagPipeline()
        for version_id in version_ids:
            try:
                rag.delete_version_chunks(version_id)
                print(f"Deleted Chroma chunks for version {version_id}")
            except Exception as exc:
                print(f"Warning: failed to delete chunks for version {version_id}: {exc}")

        # Delete lifecycle events
        await db.execute(
            delete(KbDocumentEvent).where(KbDocumentEvent.document_id.in_(doc_ids))
        )
        # Delete chunks records via cascade through versions
        await db.execute(
            delete(KbDocumentChunk).where(KbDocumentChunk.version_id.in_(version_ids))
        )
        # Delete versions
        await db.execute(
            delete(KbDocumentVersion).where(KbDocumentVersion.document_id.in_(doc_ids))
        )
        # Delete documents
        await db.execute(
            delete(KbDocument).where(KbDocument.id.in_(doc_ids))
        )
        await db.commit()
        print(f"Removed {len(doc_ids)} test documents and related records.")

        # Delete storage files
        for doc_id in doc_ids:
            storage_dir = f"/app/storage/documents/{doc_id}"
            if os.path.exists(storage_dir):
                import shutil
                shutil.rmtree(storage_dir)
                print(f"Removed storage dir {storage_dir}")


if __name__ == "__main__":
    asyncio.run(cleanup())
