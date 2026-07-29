"""Admin API endpoints for Knowledge Base management."""

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.knowledge_base import KbDocument, KbDocumentVersion
from schemas.knowledge_base import (
    KbDocumentCreate,
    KbDocumentOut,
    KbDocumentUpdate,
    KbStatusOut,
)
from services.knowledge_base import (
    DocumentNotFoundError,
    KnowledgeBaseError,
    KnowledgeBaseService,
    UnsupportedFileError,
)

router = APIRouter(prefix="/kb", tags=["admin-kb"])


def get_kb_service(db: AsyncSession = Depends(get_db)) -> KnowledgeBaseService:
    """Dependency factory for Knowledge Base service."""
    return KnowledgeBaseService(db)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _document_out(document: KbDocument) -> KbDocumentOut:
    """Convert an ORM document to the output schema with active version id."""
    active_version_id = None
    if document.versions:
        for version in document.versions:
            if version.is_active:
                active_version_id = version.id
                break
        if active_version_id is None:
            active_version_id = document.versions[0].id
    data = KbDocumentOut.model_validate(document)
    data.active_version_id = active_version_id
    return data


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------


@router.post("/documents", response_model=KbDocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: str = Form(...),
    document_type: str = Form("lecture"),
    course_id: int = Form(None),
    module_id: int = Form(None),
    topic_id: int = Form(None),
    difficulty: str = Form("beginner"),
    language: str = Form("ru"),
    description: str = Form(None),
    source_url: str = Form(None),
    file: UploadFile = File(...),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Upload a new document to the Knowledge Base."""
    try:
        data = KbDocumentCreate(
            title=title,
            document_type=document_type,
            course_id=course_id,
            module_id=module_id,
            topic_id=topic_id,
            difficulty=difficulty,
            language=language,
            description=description,
            source_url=source_url,
        )
        document = await service.create_document(data, file)
        return _document_out(document)
    except UnsupportedFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except KnowledgeBaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/documents", response_model=List[KbDocumentOut])
async def list_documents(
    course_id: int = Query(None),
    module_id: int = Query(None),
    is_published: bool = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return a paginated list of Knowledge Base documents."""
    documents = await service.list_documents(
        course_id=course_id,
        module_id=module_id,
        is_published=is_published,
        limit=limit,
        offset=offset,
    )
    return [_document_out(doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=KbDocumentOut)
async def get_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return a single Knowledge Base document card."""
    try:
        document = await service.get_document(document_id)
        return _document_out(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put("/documents/{document_id}", response_model=KbDocumentOut)
async def update_document(
    document_id: int,
    data: KbDocumentUpdate,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Update document metadata."""
    try:
        document = await service.update_document(document_id, data)
        return _document_out(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Archive a Knowledge Base document."""
    try:
        await service.delete_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/documents/{document_id}/versions", response_model=KbDocumentOut)
async def add_version(
    document_id: int,
    file: UploadFile = File(...),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Upload a new version of an existing document."""
    try:
        await service.add_version(document_id, file)
        document = await service.get_document(document_id)
        return _document_out(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UnsupportedFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc


@router.post("/documents/{document_id}/publish", response_model=KbDocumentOut)
async def publish_document(
    document_id: int,
    publish: bool = Query(True),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Publish or unpublish a document."""
    try:
        document = await service.toggle_publish(document_id, publish)
        return _document_out(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except KnowledgeBaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ------------------------------------------------------------------
# Status
# ------------------------------------------------------------------


@router.get("/status", response_model=KbStatusOut)
async def get_kb_status(service: KnowledgeBaseService = Depends(get_kb_service)):
    """Return aggregated Knowledge Base status."""
    status_data = await service.get_status()
    return KbStatusOut(**status_data)
