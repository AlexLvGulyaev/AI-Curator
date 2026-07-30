"""Public chat endpoint powered by the LLM orchestrator."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from services.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequestPayload(BaseModel):
    """Payload for the chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000)
    role: Optional[str] = Field(None, max_length=50)
    difficulty: Optional[str] = Field("beginner", max_length=50)
    course_id: Optional[int] = None
    session_id: Optional[str] = Field(None, max_length=255)
    history: Optional[List[ChatMessage]] = Field(default_factory=list)


class ChatSource(BaseModel):
    """A source attached to an answer."""

    type: str
    title: str
    url: Optional[str] = None
    document_id: Optional[int] = None
    chunk_index: Optional[int] = None


class ChatResponse(BaseModel):
    """Response from the LLM chat endpoint."""

    answer: str
    sources: List[ChatSource]
    intent: str
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


def get_orchestrator(db: AsyncSession = Depends(get_db)) -> Orchestrator:
    """Dependency factory for the chat orchestrator."""
    return Orchestrator(db)


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequestPayload,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    """Ask AI Curator a question and get an LLM-generated answer with sources."""
    try:
        history = [m.model_dump() for m in (payload.history or [])]
        result = await orchestrator.process(
            message=payload.message,
            role=payload.role,
            difficulty=payload.difficulty,
            course_id=payload.course_id,
            session_id=payload.session_id,
            history=history,
        )
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {exc}",
        ) from exc
