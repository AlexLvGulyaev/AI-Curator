"""Public chat endpoint powered by the LLM orchestrator."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_db
from models.chat import ChatLog
from models.demo_session import DemoSession
from services.demo_limiter import DemoLimiterService
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
    document_type: Optional[str] = None
    module: Optional[str] = None
    topic: Optional[str] = None
    section: Optional[str] = None
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
    log_id: Optional[int] = None
    demo_mode: bool = False


class ChatFeedbackPayload(BaseModel):
    """Payload for submitting student feedback for a chat answer."""

    score: int = Field(..., ge=1, le=10, description="Feedback score from 1 to 10")


def get_orchestrator(db: AsyncSession = Depends(get_db)) -> Orchestrator:
    """Dependency factory for the chat orchestrator."""
    return Orchestrator(db)


async def require_demo_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[DemoSession]:
    """Validate the X-Demo-Token header when demo mode is enabled.

    In development/test environments (demo_enabled=False) the dependency is a
    no-op. In production it returns the validated DemoSession after consuming
    one request from the quota.
    """
    if not settings.demo_enabled:
        return None

    token = request.headers.get("x-demo-token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Demo-Token header is required",
        )

    service = DemoLimiterService(db)
    return await service.check_and_record_request(token, _client_ip(request))


def _audit_user_id(role: Optional[str]) -> str:
    """Return a stable user identifier for the public chat endpoint."""
    return role or "anonymous"


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequestPayload,
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
    demo_session: Optional[DemoSession] = Depends(require_demo_token),
):
    """Ask AI Curator a question and get an LLM-generated answer with sources."""
    client_ip = _client_ip(request)
    user_agent = request.headers.get("user-agent")
    demo_mode = demo_session is not None
    if demo_mode:
        await db.commit()
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
            demo_mode=demo_mode,
        )
        result.setdefault("demo_mode", demo_mode)

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
                "demo_mode": demo_mode,
            },
        )

        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {exc}",
        ) from exc


@router.post("/{log_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def submit_chat_feedback(
    log_id: int,
    payload: ChatFeedbackPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Store a student's feedback score for a specific chat answer.

    The score is written directly to the `chat_logs` row identified by `log_id`.
    Existing scores can be overwritten (idempotent from the student's point of
    view), but only once per request — repeated identical submissions return 204.
    """
    client_ip = _client_ip(request)
    user_agent = request.headers.get("user-agent")

    result = await db.execute(select(ChatLog).where(ChatLog.id == log_id))
    chat_log = result.scalar_one_or_none()
    if chat_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat log {log_id} not found",
        )

    previous_score = chat_log.feedback_score
    chat_log.feedback_score = payload.score
    await db.commit()

    logger = LoggerService(db)
    await logger.log_audit(
        action="chat_feedback",
        resource_type="chat_log",
        resource_id=str(log_id),
        user_id=None,
        user_name="student",
        ip_address=client_ip,
        details={
            "score": payload.score,
            "request_id": chat_log.request_id,
            "previous_score": previous_score if previous_score != payload.score else None,
            "user_agent": user_agent,
        },
    )
    return None
