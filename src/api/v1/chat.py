"""Public chat endpoint powered by the LLM orchestrator."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from services.logger import LoggerService
from services.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


def _client_ip(request: Request) -> Optional[str]:
    """Extract the real client IP from proxy headers or the connection."""
    # Trust proxy headers first: traefik passes the original client IP here.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First address in the chain is the original client.
        client = forwarded.split(",")[0].strip()
        if client:
            return client
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None
    if request.client:
        return request.client.host
    return None


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
    cache_hit: bool = False
    error: Optional[str] = None


def get_orchestrator(db: AsyncSession = Depends(get_db)) -> Orchestrator:
    """Dependency factory for the chat orchestrator."""
    return Orchestrator(db)


def _audit_user_id(role: Optional[str]) -> str:
    """Return a stable user identifier for the public chat endpoint."""
    return role or "anonymous"


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequestPayload,
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
):
    """Ask AI Curator a question and get an LLM-generated answer with sources."""
    client_ip = _client_ip(request)
    user_agent = request.headers.get("user-agent")
    try:
        history = [m.model_dump() for m in (payload.history or [])]
        result = await orchestrator.process(
            message=payload.message,
            role=payload.role,
            difficulty=payload.difficulty,
            course_id=payload.course_id,
            session_id=payload.session_id,
            history=history,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        logger = LoggerService(db)
        await logger.log_audit(
            action="chat_request",
            resource_type="chat_request",
            resource_id=result.get("session_id") or payload.session_id,
            user_id=_audit_user_id(payload.role),
            user_name="student",
            ip_address=client_ip,
            details={
                "course_id": payload.course_id,
                "difficulty": payload.difficulty,
                "intent": result.get("intent"),
                "model": result.get("model"),
                "latency_ms": result.get("latency_ms"),
                "cache_hit": result.get("cache_hit", False),
                "has_answer": bool(result.get("answer")),
                "sources_count": len(result.get("sources") or []),
                "user_agent": user_agent,
                "message_preview": payload.message[:200],
            },
        )

        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {exc}",
        ) from exc
