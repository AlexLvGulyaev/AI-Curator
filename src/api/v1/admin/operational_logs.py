"""Admin endpoints for operational logs (chat execution records)."""

from datetime import datetime, time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db import get_db
from models.chat import AnalyticsEvent, ChatLog, ChatRequest, LlmCall, LlmCallTrace

router = APIRouter(prefix="/operational-logs", tags=["admin-operational-logs"])


def _status_for_log(log: Optional[ChatLog]) -> str:
    if log is None:
        return "pending"
    if log.error:
        return "error"
    if log.answer:
        return "ok"
    return "pending"


def _log_to_summary(req: ChatRequest, log: Optional[ChatLog]) -> Dict[str, Any]:
    return {
        "id": req.id,
        "session_id": req.session_id,
        "role": req.role,
        "course_id": req.course_id,
        "difficulty": req.difficulty,
        "intent": req.intent,
        "message_preview": (req.message or "")[:200],
        "status": _status_for_log(log),
        "latency_ms": log.latency_ms if log else None,
        "total_tokens": log.total_tokens if log else None,
        "llm_model": log.llm_model if log else None,
        "cache_hit": log.cache_hit if log else False,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


@router.get("")
async def list_operational_logs(
    session_id: Optional[str] = None,
    role: Optional[str] = None,
    course_id: Optional[int] = None,
    intent: Optional[str] = None,
    status: Optional[str] = None,
    has_error: Optional[bool] = None,
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated operational log entries based on chat requests."""
    # Read-only views are intentionally not audited to avoid self-generated noise.

    stmt = (
        select(ChatRequest, ChatLog)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id, isouter=True)
        .order_by(ChatRequest.created_at.desc())
    )

    if session_id:
        stmt = stmt.where(ChatRequest.session_id == session_id)
    if role:
        stmt = stmt.where(ChatRequest.role == role)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)
    if intent:
        stmt = stmt.where(ChatRequest.intent == intent)
    if status:
        if status == "ok":
            stmt = stmt.where(ChatLog.answer != None).where(ChatLog.error == None)
        elif status == "error":
            stmt = stmt.where(ChatLog.error != None)
        elif status == "pending":
            stmt = stmt.where(ChatLog.id == None)
    if has_error is True:
        stmt = stmt.where(ChatLog.error != None).where(ChatLog.error != "")
    elif has_error is False:
        stmt = stmt.where((ChatLog.error == None) | (ChatLog.error == ""))
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=None)
            stmt = stmt.where(ChatRequest.created_at >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_from: {date_from}")
    if date_to:
        try:
            end = datetime.combine(datetime.strptime(date_to, "%Y-%m-%d"), time.max)
            stmt = stmt.where(ChatRequest.created_at <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to: {date_to}")

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)

    items = []
    for req, log in result.unique().all():
        items.append(_log_to_summary(req, log))

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{log_id}")
async def get_operational_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return detailed operational log entry for a chat request."""
    # Read-only views are intentionally not audited to avoid self-generated noise.

    result = await db.execute(
        select(ChatRequest)
        .where(ChatRequest.id == log_id)
        .options(joinedload(ChatRequest.logs))
    )
    req = result.unique().scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=404, detail="Operational log entry not found")

    chat_log = req.logs[0] if req.logs else None

    llm_calls_result = await db.execute(
        select(LlmCall, LlmCallTrace)
        .join(LlmCallTrace, LlmCall.trace_id == LlmCallTrace.id, isouter=True)
        .where(LlmCall.request_id == log_id)
        .order_by(LlmCall.id.asc())
    )
    llm_calls = []
    for call, trace in llm_calls_result.all():
        llm_calls.append({
            "id": call.id,
            "model": call.model,
            "status": call.status,
            "error": call.error,
            "prompt_tokens": call.prompt_tokens,
            "completion_tokens": call.completion_tokens,
            "total_tokens": call.total_tokens,
            "latency_ms": call.latency_ms,
            "trace": {
                "id": trace.id,
                "prompt_preview": (trace.prompt or "")[:500] if trace else None,
                "response_preview": (trace.response or "")[:500] if trace else None,
            } if trace else None,
        })

    analytics_result = await db.execute(
        select(AnalyticsEvent)
        .where(AnalyticsEvent.session_id == req.session_id)
        .order_by(AnalyticsEvent.id.asc())
    )
    analytics_events = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "intent": e.intent,
            "course_id": e.course_id,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in analytics_result.scalars().all()
    ]

    return {
        "id": req.id,
        "session_id": req.session_id,
        "role": req.role,
        "course_id": req.course_id,
        "difficulty": req.difficulty,
        "intent": req.intent,
        "message": req.message,
        "lms_calls": req.lms_calls,
        "rag_filters": req.rag_filters,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "status": _status_for_log(chat_log),
        "answer": chat_log.answer if chat_log else None,
        "sources": chat_log.sources if chat_log else [],
        "llm_model": chat_log.llm_model if chat_log else None,
        "latency_ms": chat_log.latency_ms if chat_log else None,
        "total_tokens": chat_log.total_tokens if chat_log else None,
        "feedback_score": chat_log.feedback_score if chat_log else None,
        "cache_hit": chat_log.cache_hit if chat_log else False,
        "error": chat_log.error if chat_log else None,
        "llm_calls": llm_calls,
        "analytics_events": analytics_events,
    }
