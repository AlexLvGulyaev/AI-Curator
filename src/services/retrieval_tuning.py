"""Retrieval tuning settings business logic for AI Curator."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.retrieval_tuning import RetrievalTuning

DEFAULT_TOP_K = 5
DEFAULT_RAG_DISTANCE_THRESHOLD = 1.35
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 128
DEFAULT_CACHE_ENABLED = True
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_RETRIEVAL_TIMEOUT_MS = 5000
DEFAULT_EMBEDDING_TIMEOUT_MS = 30000


class RetrievalTuningService:
    """Service for managing operational retrieval parameters."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_default(self) -> RetrievalTuning:
        """Return the effective retrieval tuning row, creating defaults if needed."""
        stmt = select(RetrievalTuning).order_by(RetrievalTuning.id.asc()).limit(1)
        result = await self.db.execute(stmt)
        tuning = result.scalar_one_or_none()
        if tuning is None:
            tuning = RetrievalTuning(
                top_k=DEFAULT_TOP_K,
                rag_distance_threshold=DEFAULT_RAG_DISTANCE_THRESHOLD,
                chunk_size=DEFAULT_CHUNK_SIZE,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                cache_enabled=DEFAULT_CACHE_ENABLED,
                cache_ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
                retrieval_timeout_ms=DEFAULT_RETRIEVAL_TIMEOUT_MS,
                embedding_timeout_ms=DEFAULT_EMBEDDING_TIMEOUT_MS,
            )
            self.db.add(tuning)
            await self.db.commit()
            await self.db.refresh(tuning)
        return tuning

    async def update(
        self,
        top_k: Optional[int] = None,
        rag_distance_threshold: Optional[float] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        cache_enabled: Optional[bool] = None,
        cache_ttl_seconds: Optional[int] = None,
        retrieval_timeout_ms: Optional[int] = None,
        embedding_timeout_ms: Optional[int] = None,
    ) -> RetrievalTuning:
        """Update the effective retrieval tuning row."""
        tuning = await self.get_or_create_default()
        if top_k is not None:
            tuning.top_k = top_k
        if rag_distance_threshold is not None:
            tuning.rag_distance_threshold = rag_distance_threshold
        if chunk_size is not None:
            tuning.chunk_size = chunk_size
        if chunk_overlap is not None:
            tuning.chunk_overlap = chunk_overlap
        if cache_enabled is not None:
            tuning.cache_enabled = cache_enabled
        if cache_ttl_seconds is not None:
            tuning.cache_ttl_seconds = cache_ttl_seconds
        if retrieval_timeout_ms is not None:
            tuning.retrieval_timeout_ms = retrieval_timeout_ms
        if embedding_timeout_ms is not None:
            tuning.embedding_timeout_ms = embedding_timeout_ms
        await self.db.commit()
        await self.db.refresh(tuning)
        return tuning
