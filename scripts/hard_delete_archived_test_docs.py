#!/usr/bin/env python3
"""Permanently delete archived test/artifact KB documents.

WARNING: This is a destructive operation. Use only after confirming that
archived documents are no longer needed and are not referenced by Chroma
or other systems.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from db import AsyncSessionLocal
from models.knowledge_base import KbDocument
from services.knowledge_base import KnowledgeBaseService

TEST_TITLE_PATTERNS = (
    "Publish Test",
    "Version Replacement Test",
    "Debug",
    "Debug V2",
    "Debug V3",
    "Test Lecture",
    "Claude Code Intro",
    "Prompt Engineering",
    "Audit Doc",
    "ASGI Test",
    "Detail Bundle Test",
    "Version Preview Test",
    "Timeline Test",
    "Activate Test",
    "Reindex All Test",
    "Cleaned Edit Test",
    "Cleaned Edit No Reindex",
    "Raw Save Rejected",
    "Archived Save Rejected",
    "Curl Test Lecture",
    "A",
)


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(KbDocument))
        documents = result.scalars().all()

        to_delete = []
        for doc in documents:
            if doc.status.value != "archived":
                continue
            if any(doc.title == pattern or doc.title.startswith(pattern) for pattern in TEST_TITLE_PATTERNS):
                to_delete.append(doc.id)

        if not to_delete:
            print("No archived test documents found.")
            return

        print(f"Deleting {len(to_delete)} archived test document(s)...")
        for doc_id in to_delete[:10]:
            print(f"  - doc_id={doc_id}")
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")

        # Delete via service to ensure storage cleanup and audit logging.
        service = KnowledgeBaseService(db)
        for doc_id in to_delete:
            await service.delete_document(doc_id)

        print(f"Deleted {len(to_delete)} archived test document(s).")


if __name__ == "__main__":
    asyncio.run(main())
