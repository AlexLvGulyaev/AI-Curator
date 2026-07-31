"""Pydantic schemas for Knowledge Base API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KbDocumentBase(BaseModel):
    """Common fields for document input/output."""

    title: str = Field(..., max_length=500)
    document_type: str = "lecture"
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    topic_id: Optional[int] = None
    difficulty: str = "beginner"
    language: str = "ru"
    description: Optional[str] = None
    source_url: Optional[str] = None


class KbDocumentCreate(KbDocumentBase):
    """Payload for creating a new document card."""

    pass


class KbDocumentUpdate(BaseModel):
    """Payload for updating document metadata."""

    title: Optional[str] = Field(None, max_length=500)
    document_type: Optional[str] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    topic_id: Optional[int] = None
    difficulty: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None


class KbDocumentEventOut(BaseModel):
    """Lifecycle event for a Knowledge Base document or version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_id: Optional[int]
    event_type: str
    status: str
    message: Optional[str]
    details: Optional[dict]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]


class KbDocumentChunkOut(BaseModel):
    """Traceability info for a document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    char_start: Optional[int]
    char_end: Optional[int]
    token_count: Optional[int]
    content_preview: Optional[str]
    status: str
    created_at: Optional[datetime]


class KbDocumentVersionOut(BaseModel):
    """Output representation of a document version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    storage_path: str
    original_filename: str
    file_size: Optional[int]
    mime_type: Optional[str]
    status: str
    chunk_count: Optional[int]
    is_active: bool
    raw_storage_path: Optional[str]
    cleaned_storage_path: Optional[str]
    sha256: Optional[str]
    indexed_at: Optional[datetime]
    embedding_model: Optional[str]
    git_commit_hash: Optional[str]
    git_blob_hash: Optional[str]
    git_author: Optional[str]
    git_commit_message: Optional[str]
    git_committed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class KbDocumentOut(KbDocumentBase):
    """Output representation of a Knowledge Base document card."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_published: bool
    status: str
    last_error: Optional[str]
    active_version_id: Optional[int] = None
    versions: List[KbDocumentVersionOut] = []
    created_at: datetime
    updated_at: datetime


class KbVersionTextOut(BaseModel):
    """Raw or cleaned text preview for a document version."""

    version_id: int
    version_number: int
    stage: str
    original_filename: str
    mime_type: Optional[str]
    total_length: int
    preview_length: int
    preview: str


class KbDocumentExecutionOut(BaseModel):
    """Technical execution metadata shown in the central console panel."""

    provider: Optional[str] = None
    model: Optional[str] = None
    backend: Optional[str] = None
    sha256: Optional[str] = None
    indexed_at: Optional[datetime] = None
    raw_size: Optional[int] = None
    cleaned_size: Optional[int] = None
    postgres_status: Optional[str] = None


class KbDocumentDetailOut(BaseModel):
    """Full operational console bundle for a Knowledge Base document."""

    document: KbDocumentOut
    active_version: Optional[KbDocumentVersionOut]
    chunks: List[KbDocumentChunkOut]
    timeline: List[KbDocumentEventOut]
    execution: KbDocumentExecutionOut


class KbStatusOut(BaseModel):
    """Aggregated status of the Knowledge Base."""

    total_documents: int
    published_documents: int
    draft_documents: int
    total_versions: int
    active_versions: int
    total_chunks: int
    indexed_chunks: int
    last_updated: Optional[datetime]


class KbReindexAllOut(BaseModel):
    """Result of a bulk reindex operation."""

    processed: int
    failed: int
    total: int
