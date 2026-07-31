"""Retrieval tuning settings SQLAlchemy model for AI Curator."""

from sqlalchemy import Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class RetrievalTuning(Base):
    """Singleton-ish table with operational retrieval parameters.

    Only the row with the lowest id is considered effective.
    The service auto-creates a default row if the table is empty.
    """

    __tablename__ = "retrieval_tuning"

    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    rag_distance_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=1.35)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=512)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=128)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    retrieval_timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    embedding_timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    course_boost_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    course_boost_factor: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.15,
    )
