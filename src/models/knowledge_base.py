"""Knowledge Base SQLAlchemy models for AI Curator Backend."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
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
        """Return the most recent non-archived version."""
        non_archived = [v for v in self.versions if v.status != DocumentStatus.ARCHIVED]
        if not non_archived:
            return None
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
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )

    version: Mapped["KbDocumentVersion"] = relationship(back_populates="chunks")
