"""Delete Chroma chunks whose document_id is not in the active KbDocumentChunk table."""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "/app/src")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_session_factory
from models.knowledge_base import KbDocumentChunk
from services.rag_pipeline import RagPipeline


async def cleanup() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(KbDocumentChunk.id, KbDocumentChunk.version_id))
        active = {(row[0], row[1]) for row in result.all()}
        print(f"Active DB chunks: {len(active)}")

    rag = RagPipeline()
    collection = rag.collection
    data = collection.get(include=["metadatas"])
    chroma_ids = data.get("ids", [])
    metadatas = data.get("metadatas", [])

    to_delete = []
    for chroma_id, meta in zip(chroma_ids, metadatas):
        chunk_id = meta.get("chunk_id")
        version_id = meta.get("version_id")
        if chunk_id is None or (chunk_id, version_id) not in active:
            to_delete.append(chroma_id)

    print(f"Orphan Chroma chunks to delete: {len(to_delete)}")
    if to_delete:
        batch_size = 100
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i + batch_size]
            collection.delete(ids=batch)
            print(f"Deleted batch {i // batch_size + 1}: {len(batch)} chunks")


if __name__ == "__main__":
    asyncio.run(cleanup())
