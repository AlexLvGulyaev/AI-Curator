"""Knowledge Base SQLAlchemy models for AI Curator Backend."""

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class DifficultyLevel(str, enum.Enum):
    """Target difficulty level of a knowledge base document."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class DocumentType(str, enum.Enum):
    """Type of a knowledge base document."""

    LECTURE = "lecture"
    METHODICAL = "methodical"
    FAQ = "faq"
    INSTRUCTION = "instruction"
    GLOSSARY = "glossary"
    EXAMPLE = "example"
    EXTERNAL = "external"


class DocumentStatus(str, enum.Enum):
    """Processing/publication status of a knowledge base document."""

    DRAFT = "draft"
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"
    ARCHIVED = "archived"


class KbDocument(Base):
    """Knowledge Base document card (metadata and lifecycle)."""

    __tablename__ = "kb_documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"),
        nullable=False,
        default=DocumentType.LECTURE,
    )
    course_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    module_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"),
        nullable=False,
        default=DifficultyLevel.BEGINNER,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="ru")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    versions: Mapped[List["KbDocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def active_version(self) -> Optional["KbDocumentVersion"]:
        """Return the active version, falling back to the latest non-archived one."""
        non_archived = [v for v in self.versions if v.status != DocumentStatus.ARCHIVED]
        if not non_archived:
            return None
        active = [v for v in non_archived if v.is_active]
        if active:
            return max(active, key=lambda v: v.version_number)
        return max(non_archived, key=lambda v: v.version_number)


class KbDocumentVersion(Base):
    """A concrete version of a Knowledge Base document file."""

    __tablename__ = "kb_document_versions"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )
    chunk_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Raw and cleaned text storage paths. The uploaded original lives at
    # ``storage_path``; the cleaned/normalized copy is stored separately so the
    # operational console can show both RAW and cleaned previews.
    raw_storage_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    cleaned_storage_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Technical execution metadata exposed in the operational console.
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Git provenance for source documents.
    git_commit_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    git_blob_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    git_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    git_commit_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    git_committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["KbDocument"] = relationship(back_populates="versions")
    chunks: Mapped[List["KbDocumentChunk"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KbDocumentChunk(Base):
    """A text chunk extracted from a document version (used for traceability)."""

    __tablename__ = "kb_document_chunks"

    version_id: Mapped[int] = mapped_column(
        ForeignKey("kb_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )

    version: Mapped["KbDocumentVersion"] = relationship(back_populates="chunks")


class KbDocumentEvent(Base):
    """Lifecycle event for a Knowledge Base document or version."""

    __tablename__ = "kb_document_events"

    document_id: Mapped[int] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("kb_document_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Lifecycle timing for the operational console timeline.
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_kb_document_events_document_created", "document_id", "created_at"),
        Index("ix_kb_document_events_version_created", "version_id", "created_at"),
    )
