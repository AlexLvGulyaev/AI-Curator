#!/usr/bin/env python3
"""Remove test/artifact KB documents created by automated test runs.

Documents matching known test title patterns are archived (soft-deleted).
Real course materials are preserved.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import AsyncSessionLocal
from models.knowledge_base import KbDocument
from services.knowledge_base import KnowledgeBaseService
from services.rag_pipeline import RagPipeline

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
)

# Always keep these real course document ids.
PROTECTED_IDS = {65}


async def main():
    async with AsyncSessionLocal() as db:
        service = KnowledgeBaseService(db)

        result = await db.execute(
            select(KbDocument).options(selectinload(KbDocument.versions))
        )
        documents = result.scalars().all()

        to_delete = []
        for doc in documents:
            if doc.id in PROTECTED_IDS:
                continue
            if any(doc.title == pattern or doc.title.startswith(pattern) for pattern in TEST_TITLE_PATTERNS):
                to_delete.append(doc)

        print(f"Found {len(to_delete)} test/artifact document(s) to archive:")
        for doc in to_delete[:10]:
            print(f"  - id={doc.id} title={doc.title!r}")
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")

        for doc in to_delete:
            await service.delete_document(doc.id)
            print(f"  Archived doc {doc.id}: {doc.title}")

        print(f"\nCleanup complete. Archived {len(to_delete)} document(s).")


if __name__ == "__main__":
    asyncio.run(main())
