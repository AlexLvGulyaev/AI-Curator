"""Admin API endpoints for Knowledge Base management."""

from typing import Any, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.knowledge_base import KbDocument, KbDocumentVersion
from schemas.knowledge_base import (
    KbDocumentChunkOut,
    KbDocumentCreate,
    KbDocumentDetailOut,
    KbDocumentEventOut,
    KbDocumentExecutionOut,
    KbDocumentOut,
    KbDocumentUpdate,
    KbDocumentVersionOut,
    KbReindexAllOut,
    KbStatusOut,
    KbVersionTextOut,
    KbVersionTextSaveIn,
)
from services.cache import response_cache
from services.knowledge_base import (
    DocumentNotFoundError,
    KnowledgeBaseError,
    KnowledgeBaseService,
    UnsupportedFileError,
)
from services.logger import LoggerService

router = APIRouter(prefix="/kb", tags=["admin-kb"])


def get_kb_service(db: AsyncSession = Depends(get_db)) -> KnowledgeBaseService:
    """Dependency factory for Knowledge Base service."""
    return KnowledgeBaseService(db)


async def _log_audit(action: str, resource_type: str, resource_id, db: AsyncSession):
    """Helper to persist an audit event for KB admin actions."""
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        user_id="admin",
        user_role="admin",
    )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _document_out(document: KbDocument) -> KbDocumentOut:
    """Convert an ORM document to the output schema with active version id."""
    active_version_id = None
    if document.versions:
        # Prefer the version explicitly marked active; otherwise use the latest.
        active_versions = [v for v in document.versions if v.is_active]
        latest = max(document.versions, key=lambda v: v.version_number)
        active_version_id = active_versions[0].id if active_versions else latest.id
    data = KbDocumentOut.model_validate(document)
    data.active_version_id = active_version_id
    return data


def _version_out(version: KbDocumentVersion) -> KbDocumentVersionOut:
    """Convert an ORM version to the output schema."""
    return KbDocumentVersionOut.model_validate(version)


def _event_out(event: Any) -> KbDocumentEventOut:
    """Convert an ORM lifecycle event to the output schema."""
    return KbDocumentEventOut.model_validate(event)


def _invalidate_response_cache() -> None:
    """Invalidate the chat response cache after KB mutations."""
    try:
        response_cache.invalidate_all()
    except Exception:
        pass


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
        await _log_audit("create", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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
        await _log_audit("update", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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
        await _log_audit("delete", "kb_document", document_id, service.db)
        _invalidate_response_cache()
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
        version = await service.add_version(document_id, file)
        document = await service.get_document(document_id)
        await _log_audit("add_version", "kb_document_version", version.id, service.db)
        _invalidate_response_cache()
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
        await _log_audit("publish" if publish else "unpublish", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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


@router.post("/documents/{document_id}/process", response_model=KbDocumentOut)
async def process_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Process the active version of a document: extract text, chunk, embed, index."""
    try:
        document = await service.process_document(document_id)
        await _log_audit("process", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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
# Operational console endpoints
# ------------------------------------------------------------------


@router.get(
    "/documents/{document_id}/detail",
    response_model=KbDocumentDetailOut,
)
async def get_document_detail(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return document metadata, active version, chunks and lifecycle timeline."""
    try:
        bundle = await service.get_document_detail_bundle(document_id)
        # Read-only views are intentionally not audited to avoid self-generated noise.
        return KbDocumentDetailOut(
            document=_document_out(bundle["document"]),
            active_version=_version_out(bundle["active_version"])
            if bundle["active_version"]
            else None,
            chunks=[KbDocumentChunkOut.model_validate(c) for c in bundle["chunks"]],
            timeline=[_event_out(e) for e in bundle["timeline"]],
            execution=KbDocumentExecutionOut(**bundle["execution"]),
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/documents/{document_id}/versions/{version_id}/text",
    response_model=KbVersionTextOut,
)
async def get_version_text(
    document_id: int,
    version_id: int,
    full: bool = Query(False),
    stage: str = Query("cleaned"),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return raw or cleaned text preview for a document version."""
    try:
        limit = 10_000_000 if full else 262144
        preview = await service.get_version_text_preview(
            version_id, limit=limit, stage=stage
        )
        # Read-only views are intentionally not audited to avoid self-generated noise.
        return KbVersionTextOut(**preview)
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


@router.post(
    "/documents/{document_id}/versions/{version_id}/text",
    response_model=KbDocumentOut,
)
async def save_version_text(
    document_id: int,
    version_id: int,
    payload: KbVersionTextSaveIn,
    stage: str = Query("cleaned"),
    reindex: bool = Query(True),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Save edited cleaned text for a document version and optionally reindex it."""
    if stage != "cleaned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only 'cleaned' stage can be saved.",
        )
    try:
        document = await service.save_version_text(
            document_id, version_id, payload.text, reindex=reindex
        )
        await _log_audit("save_cleaned_text", "kb_document_version", version_id, service.db)
        _invalidate_response_cache()
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


@router.get(
    "/documents/{document_id}/versions/{version_id}/chunks",
    response_model=List[KbDocumentChunkOut],
)
async def get_version_chunks(
    document_id: int,
    version_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return traceability chunks for a document version."""
    try:
        chunks = await service.get_version_chunks(version_id)
        # Read-only views are intentionally not audited to avoid self-generated noise.
        return [KbDocumentChunkOut.model_validate(c) for c in chunks]
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/documents/{document_id}/timeline",
    response_model=List[KbDocumentEventOut],
)
async def get_document_timeline(
    document_id: int,
    limit: int = Query(100, ge=1, le=500),
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Return lifecycle timeline for a document."""
    from services.kb_lifecycle import KbLifecycleService

    lifecycle = KbLifecycleService(service.db)
    events = await lifecycle.get_timeline(document_id, limit=limit)
    return [_event_out(e) for e in events]


@router.post(
    "/documents/{document_id}/versions/{version_id}/activate",
    response_model=KbDocumentOut,
)
async def activate_version(
    document_id: int,
    version_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Activate a specific document version without reindexing."""
    try:
        document = await service.activate_version(document_id, version_id)
        await _log_audit("activate_version", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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


@router.post(
    "/documents/{document_id}/versions/{version_id}/reindex",
    response_model=KbDocumentOut,
)
async def reindex_version(
    document_id: int,
    version_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Activate and reindex a specific document version."""
    try:
        document = await service.reindex_version(document_id, version_id)
        await _log_audit("reindex_version", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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


@router.post("/documents/{document_id}/reindex", response_model=KbDocumentOut)
async def reindex_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Reindex the currently active version of a document."""
    try:
        document = await service.get_document(document_id)
        active_version = document.active_version
        if active_version is None:
            raise KnowledgeBaseError(
                f"Document {document_id} has no active version to reindex."
            )
        document = await service.reindex_version(document_id, active_version.id)
        await _log_audit("reindex", "kb_document", document.id, service.db)
        _invalidate_response_cache()
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


@router.post("/reindex-all", response_model=KbReindexAllOut)
async def reindex_all(
    service: KnowledgeBaseService = Depends(get_kb_service),
):
    """Reindex all currently published documents."""
    result = await service.reindex_all_published()
    await _log_audit("reindex_all", "kb_document", None, service.db)
    _invalidate_response_cache()
    return KbReindexAllOut(**result)


# ------------------------------------------------------------------
# Status
# ------------------------------------------------------------------


@router.get("/status", response_model=KbStatusOut)
async def get_kb_status(service: KnowledgeBaseService = Depends(get_kb_service)):
    """Return aggregated Knowledge Base status."""
    status_data = await service.get_status()
    return KbStatusOut(**status_data)
