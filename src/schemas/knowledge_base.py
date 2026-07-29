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


class KbDocumentChunkOut(BaseModel):
    """Traceability info for a document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    char_start: Optional[int]
    char_end: Optional[int]
    token_count: Optional[int]
    status: str
    created_at: datetime


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
