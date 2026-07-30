"""Public RAG search endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from services.rag_pipeline import RagPipeline, SearchResult

router = APIRouter(prefix="/rag", tags=["rag"])


class RagSearchRequest(BaseModel):
    """Payload for semantic search over the Knowledge Base."""

    query: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[int] = None
    course_id: Optional[int] = None
    module_id: Optional[int] = None
    topic_id: Optional[int] = None
    difficulty: Optional[str] = None
    k: int = Field(5, ge=1, le=20)


class RagSearchResult(BaseModel):
    """A single ranked chunk returned by RAG search."""

    chunk_id: str
    content: str
    metadata: dict
    distance: float


class RagSearchResponse(BaseModel):
    """Response from RAG semantic search."""

    query: str
    results: List[RagSearchResult]
    total: int


def get_rag_pipeline() -> RagPipeline:
    """Dependency factory for the RAG pipeline."""
    return RagPipeline()


@router.post("/search", response_model=RagSearchResponse)
async def search(
    payload: RagSearchRequest,
    rag: RagPipeline = Depends(get_rag_pipeline),
):
    """Run semantic search over indexed Knowledge Base chunks."""
    try:
        results, _search_timings = await rag.search(
            query=payload.query,
            k=payload.k,
            document_id=payload.document_id,
            course_id=payload.course_id,
            module_id=payload.module_id,
            topic_id=payload.topic_id,
            difficulty=payload.difficulty,
        )
        return RagSearchResponse(
            query=payload.query,
            results=[
                RagSearchResult(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    metadata=r.metadata,
                    distance=r.distance,
                )
                for r in results
            ],
            total=len(results),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG search failed: {exc}",
        ) from exc
