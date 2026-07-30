"""Admin endpoints for analytics and audit."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.chat import AnalyticsEvent, AuditLog, ChatLog, ChatRequest
from services.logger import LoggerService

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])


async def _log_audit(action: str, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="analytics",
        user_id="admin",
        user_role="admin",
    )


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    await _log_audit("view_dashboard", db)
    """Return high-level analytics metrics."""
    total_requests = await db.scalar(select(func.count(ChatRequest.id)))
    total_logs = await db.scalar(select(func.count(ChatLog.id)))
    avg_latency = await db.scalar(select(func.avg(ChatLog.latency_ms)))
    feedback_avg = await db.scalar(select(func.avg(ChatLog.feedback_score)))
    unanswered = await db.scalar(
        select(func.count(ChatLog.id)).where(ChatLog.answer == None)
    )

    intent_distribution = await db.execute(
        select(ChatRequest.intent, func.count(ChatRequest.id))
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
    )

    return {
        "total_requests": total_requests or 0,
        "total_answers": total_logs or 0,
        "average_latency_ms": round(avg_latency, 2) if avg_latency else 0,
        "average_feedback_score": round(feedback_avg, 2) if feedback_avg else None,
        "unanswered_count": unanswered or 0,
        "intent_distribution": [
            {"intent": intent, "count": count}
            for intent, count in intent_distribution.all()
        ],
    }


@router.get("/topics")
async def topics(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return most common intents / topics."""
    result = await db.execute(
        select(ChatRequest.intent, func.count(ChatRequest.id).label("count"))
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
        .limit(limit)
    )
    return [{"intent": row.intent or "unknown", "count": row.count} for row in result.all()]


@router.get("/unanswered")
async def unanswered(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return recent requests with no answer or empty sources."""
    result = await db.execute(
        select(ChatRequest, ChatLog)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id, isouter=True)
        .where((ChatLog.answer == None) | (ChatLog.sources == None) | (ChatLog.sources == []))
        .order_by(ChatRequest.created_at.desc())
        .limit(limit)
    )
    output = []
    for request, log in result.all():
        output.append({
            "request_id": request.id,
            "message": request.message,
            "intent": request.intent,
            "course_id": request.course_id,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "answer": log.answer if log else None,
        })
    return output


@router.get("/feedback")
async def feedback(db: AsyncSession = Depends(get_db)):
    """Return aggregated feedback scores."""
    result = await db.execute(
        select(ChatLog.feedback_score, func.count(ChatLog.id))
        .where(ChatLog.feedback_score != None)
        .group_by(ChatLog.feedback_score)
        .order_by(ChatLog.feedback_score)
    )
    return [
        {"score": score, "count": count}
        for score, count in result.all()
    ]


@router.get("/events")
async def events(
    event_type: Optional[str] = None,
    course_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return raw analytics events."""
    stmt = select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(AnalyticsEvent.event_type == event_type)
    if course_id:
        stmt = stmt.where(AnalyticsEvent.course_id == course_id)
    result = await db.execute(stmt)
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "course_id": e.course_id,
            "intent": e.intent,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in result.scalars().unique()
    ]
