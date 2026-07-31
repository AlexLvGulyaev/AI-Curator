"""Admin endpoints for retrieval tuning and reindexing."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from services.knowledge_base import KnowledgeBaseService
from services.logger import LoggerService
from services.retrieval_tuning import RetrievalTuningService

router = APIRouter(prefix="/retrieval", tags=["admin-retrieval"])


def get_service(db: AsyncSession = Depends(get_db)) -> RetrievalTuningService:
    return RetrievalTuningService(db)


async def _log_audit(action: str, resource_id, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="retrieval_tuning",
        resource_id=str(resource_id) if resource_id is not None else None,
        user_id="admin",
        user_role="admin",
    )


class RetrievalTuningIn(BaseModel):
    """Payload for updating retrieval tuning."""

    top_k: Optional[int] = Field(None, ge=1, le=20)
    rag_distance_threshold: Optional[float] = Field(None, ge=0.0, le=10.0)
    chunk_size: Optional[int] = Field(None, ge=128, le=8192)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=4096)
    cache_enabled: Optional[bool] = None
    cache_ttl_seconds: Optional[int] = Field(None, ge=30, le=86400)
    retrieval_timeout_ms: Optional[int] = Field(None, ge=500, le=60000)
    embedding_timeout_ms: Optional[int] = Field(None, ge=1000, le=300000)
    course_boost_enabled: Optional[bool] = None
    course_boost_factor: Optional[float] = Field(None, ge=0.0, le=1.0)

    def model_post_init(self, __context):
        if self.chunk_size is not None and self.chunk_overlap is not None:
            if self.chunk_overlap >= self.chunk_size:
                raise ValueError("chunk_overlap must be less than chunk_size")


class RetrievalTuningOut(BaseModel):
    """Output representation of retrieval tuning."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    top_k: int
    rag_distance_threshold: float
    chunk_size: int
    chunk_overlap: int
    cache_enabled: bool
    cache_ttl_seconds: int
    retrieval_timeout_ms: int
    embedding_timeout_ms: int
    course_boost_enabled: bool
    course_boost_factor: float


class BackendInfo(BaseModel):
    """Information about a retrieval backend."""

    key: str
    display_name: str
    type: str
    status: str


@router.get("/tuning", response_model=RetrievalTuningOut)
async def get_tuning(service: RetrievalTuningService = Depends(get_service)):
    """Return the effective retrieval tuning settings."""
    tuning = await service.get_or_create_default()
    return RetrievalTuningOut.model_validate(tuning)


@router.put("/tuning", response_model=RetrievalTuningOut)
async def update_tuning(
    payload: RetrievalTuningIn,
    service: RetrievalTuningService = Depends(get_service),
):
    """Update the effective retrieval tuning settings."""
    try:
        tuning = await service.update(**payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    await _log_audit("update", tuning.id, service.db)
    return RetrievalTuningOut.model_validate(tuning)


@router.get("/backends", response_model=list[BackendInfo])
async def list_backends():
    """Return the configured retrieval backends."""
    return [
        BackendInfo(
            key="chroma",
            display_name="Chroma",
            type="vector_store",
            status="ready",
        ),
    ]


@router.post("/reindex")
async def reindex_all(
    db: AsyncSession = Depends(get_db),
):
    """Reindex all published Knowledge Base documents."""
    kb_service = KnowledgeBaseService(db)
    try:
        await kb_service.reindex_all_published()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {exc}",
        ) from exc
    await _log_audit("reindex", None, db)
    return {"status": "ok", "message": "Reindex started"}
