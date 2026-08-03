#!/usr/bin/env python3
"""Remove Chroma chunks for archived KB documents."""

import asyncio
import os
import sys

sys.path.insert(0, "/app")

import asyncpg

from services.chroma_client import get_chroma_client
from services.rag_pipeline import RagPipeline


async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql://ai_curator:postgres@ai-curator-postgres:5432/ai_curator").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(
            "SELECT id FROM kb_documents WHERE status = 'ARCHIVED'"
        )
        archived_ids = [r["id"] for r in rows]
        print(f"Found {len(archived_ids)} archived documents: {archived_ids}")
    finally:
        await conn.close()

    if not archived_ids:
        print("No archived documents to clean up.")
        return

    pipeline = RagPipeline()
    collection = pipeline.collection

    for doc_id in archived_ids:
        print(f"Deleting chunks for document {doc_id}...")
        try:
            collection.delete(where={"document_id": doc_id})
            print(f"  -> deleted")
        except Exception as exc:
            print(f"  -> error: {exc}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
