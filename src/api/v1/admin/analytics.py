"""Admin endpoints for analytics and audit."""

from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from db import get_db
from models.chat import AnalyticsEvent, ChatLog, ChatRequest, LlmCall

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])


_DATE_FORMAT = "%Y-%m-%d"


def _sources_have_rag(sources):
    """Return True if sources contain RAG/KB chunks (not only LMS references)."""
    if not sources:
        return False
    for item in sources:
        if not isinstance(item, dict):
            continue
        # LMS references have type == "lms" and no document_id/chunk_index.
        if item.get("type") == "lms":
            continue
        # KB/RAG chunks expose document_id and chunk_index at top level or in metadata.
        if item.get("document_id") is not None or item.get("chunk_index") is not None:
            return True
        if item.get("metadata", {}).get("document_id") is not None or item.get("metadata", {}).get("chunk_index") is not None:
            return True
        if "distance" in item and "metadata" in item:
            return True
    return False


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, _DATE_FORMAT).date()
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail=f"Invalid date: {value}. Use YYYY-MM-DD.") from exc
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def _filter_by_date(stmt, model, date_from: Optional[datetime], date_to: Optional[datetime]):
    """Apply date range filters to a query statement."""
    if date_from is not None:
        stmt = stmt.where(model.created_at >= date_from)
    if date_to is not None:
        # Include the entire end day.
        end = datetime.combine(date_to.date(), time.max, tzinfo=timezone.utc)
        stmt = stmt.where(model.created_at <= end)
    return stmt


def _filters(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    course_id: Optional[int] = Query(None, description="Filter by course_id"),
):
    """Common dependency for analytics filters."""
    return {
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "course_id": course_id,
    }


@router.get("/dashboard")
async def dashboard(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return high-level analytics metrics with optional date and course filters."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    request_stmt = select(ChatRequest)
    request_stmt = _filter_by_date(request_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        request_stmt = request_stmt.where(ChatRequest.course_id == course_id)
    total_requests = await db.scalar(select(func.count()).select_from(request_stmt.subquery()))

    # Count unique ChatRequests that have a ChatLog with a non-null answer.
    answered_stmt = (
        select(func.count(ChatRequest.id))
        .select_from(ChatRequest)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id)
        .where(ChatLog.answer != None)
    )
    answered_stmt = _filter_by_date(answered_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        answered_stmt = answered_stmt.where(ChatRequest.course_id == course_id)
    answered_requests = await db.scalar(answered_stmt) or 0

    avg_latency = await db.scalar(
        select(func.avg(ChatLog.latency_ms))
        .select_from(ChatLog)
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
    )
    # Note: avg_latency currently ignores date/course filters; kept consistent with original implementation.

    feedback_avg = await db.scalar(
        select(func.avg(ChatLog.feedback_score))
        .select_from(ChatLog)
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
    )

    unanswered = max((total_requests or 0) - answered_requests, 0)

    intent_distribution_stmt = (
        select(ChatRequest.intent, func.count(ChatRequest.id))
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
    )
    intent_distribution_stmt = _filter_by_date(
        intent_distribution_stmt, ChatRequest, date_from, date_to
    )
    if course_id is not None:
        intent_distribution_stmt = intent_distribution_stmt.where(
            ChatRequest.course_id == course_id
        )
    intent_distribution = await db.execute(intent_distribution_stmt)

    return {
        "total_requests": total_requests or 0,
        "total_answers": answered_requests,
        "average_latency_ms": round(avg_latency, 2) if avg_latency else 0,
        "average_feedback_score": round(feedback_avg, 2) if feedback_avg else None,
        "unanswered_count": unanswered,
        "intent_distribution": [
            {"intent": intent or "unknown", "count": count}
            for intent, count in intent_distribution.all()
        ],
    }


@router.get("/topics")
async def topics(
    limit: int = Query(20, ge=1, le=100),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return most common intents / topics."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    stmt = (
        select(ChatRequest.intent, func.count(ChatRequest.id).label("count"))
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
        .limit(limit)
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)
    return [{"intent": row.intent or "unknown", "count": row.count} for row in result.all()]


@router.get("/unanswered")
async def unanswered(
    limit: int = Query(50, ge=1, le=200),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return recent requests with no answer or empty sources."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    # Return requests that do not have any associated ChatLog with a non-null answer.
    answered_subq = (
        select(ChatLog.request_id)
        .where(ChatLog.answer != None)
        .distinct()
        .subquery()
    )
    stmt = (
        select(ChatRequest)
        .where(ChatRequest.id.notin_(select(answered_subq.c.request_id)))
        .order_by(ChatRequest.created_at.desc())
        .limit(limit)
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)
    output = []
    for request in result.scalars().unique():
        output.append({
            "request_id": request.id,
            "message": request.message,
            "intent": request.intent,
            "course_id": request.course_id,
            "created_at": request.created_at.isoformat() if request.created_at else None,
            "answer": None,
        })
    return output


@router.get("/feedback")
async def feedback(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated feedback scores."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    stmt = (
        select(ChatLog.feedback_score, func.count(ChatLog.id))
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
        .where(ChatLog.feedback_score != None)
        .group_by(ChatLog.feedback_score)
        .order_by(ChatLog.feedback_score)
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)
    return [{"score": score, "count": count} for score, count in result.all()]


@router.get("/latency")
async def latency(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return latency histogram and percentile summary."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    stmt = select(ChatLog.latency_ms).join(
        ChatRequest, ChatLog.request_id == ChatRequest.id
    ).where(ChatLog.latency_ms != None)
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    rows = await db.execute(stmt)
    latencies = [row[0] for row in rows.all()]

    buckets = [
        ("0-500", 0, 500),
        ("500-1000", 500, 1000),
        ("1000-2000", 1000, 2000),
        ("2000-5000", 2000, 5000),
        ("5000+", 5000, float("inf")),
    ]
    histogram = {label: 0 for label, _, _ in buckets}
    for value in latencies:
        for label, low, high in buckets:
            if low <= value < high:
                histogram[label] += 1
                break

    avg = sum(latencies) / len(latencies) if latencies else 0
    sorted_vals = sorted(latencies)
    p50 = sorted_vals[len(sorted_vals) // 2] if sorted_vals else 0
    p95 = sorted_vals[int(len(sorted_vals) * 0.95)] if sorted_vals else 0
    p99 = sorted_vals[int(len(sorted_vals) * 0.99)] if sorted_vals else 0

    return {
        "count": len(latencies),
        "average_ms": round(avg, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "histogram": [
            {"bucket": label, "count": count}
            for label, count in histogram.items()
        ],
    }


@router.get("/sources")
async def sources(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return source usage breakdown (LMS, RAG, cache, model)."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    request_log = aliased(ChatLog)
    stmt = (
        select(
            ChatRequest.id,
            ChatRequest.lms_calls,
            request_log.sources,
            request_log.cache_hit,
            request_log.error,
        )
        .join(request_log, request_log.request_id == ChatRequest.id, isouter=True)
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)
    counts = {"lms": 0, "rag": 0, "both": 0, "cache": 0, "fallback": 0, "error": 0}
    seen_requests = set()
    for request_id, lms_calls, sources, cache_hit, error in result.all():
        if request_id in seen_requests:
            continue
        seen_requests.add(request_id)
        has_lms = bool(lms_calls)
        has_rag = _sources_have_rag(sources)
        is_cache = bool(cache_hit)
        is_error = bool(error)
        if is_cache:
            counts["cache"] += 1
        elif has_lms and has_rag:
            counts["both"] += 1
        elif has_lms:
            counts["lms"] += 1
        elif has_rag:
            counts["rag"] += 1
        elif is_error:
            counts["error"] += 1
        else:
            counts["fallback"] += 1

    return {
        "total": sum(counts.values()),
        "breakdown": [
            {"source": key, "count": value}
            for key, value in counts.items()
        ],
    }


@router.get("/errors")
async def errors(
    limit: int = Query(50, ge=1, le=200),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return error summary and recent failed LLM calls / chat logs."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    log_stmt = (
        select(func.count(ChatLog.id))
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
        .where(ChatLog.error != None)
    )
    log_stmt = _filter_by_date(log_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        log_stmt = log_stmt.where(ChatRequest.course_id == course_id)
    chat_errors = await db.scalar(log_stmt) or 0

    llm_stmt = select(func.count(LlmCall.id)).where(LlmCall.status != "ok")
    llm_stmt = _filter_by_date(llm_stmt, LlmCall, date_from, date_to)
    llm_errors = await db.scalar(llm_stmt) or 0

    total_stmt = select(func.count(ChatRequest.id))
    total_stmt = _filter_by_date(total_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        total_stmt = total_stmt.where(ChatRequest.course_id == course_id)
    total_requests = await db.scalar(total_stmt) or 0

    recent_stmt = (
        select(ChatRequest, ChatLog)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id)
        .where(ChatLog.error != None)
        .order_by(ChatRequest.created_at.desc())
        .limit(limit)
    )
    recent_stmt = _filter_by_date(recent_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        recent_stmt = recent_stmt.where(ChatRequest.course_id == course_id)

    recent = await db.execute(recent_stmt)
    recent_errors = []
    for request, log in recent.all():
        recent_errors.append({
            "request_id": request.id,
            "message": request.message,
            "intent": request.intent,
            "course_id": request.course_id,
            "error": log.error,
            "created_at": request.created_at.isoformat() if request.created_at else None,
        })

    return {
        "total_requests": total_requests,
        "chat_errors": chat_errors,
        "llm_errors": llm_errors,
        "error_rate": round((chat_errors / total_requests) * 100, 2) if total_requests else 0,
        "recent_errors": recent_errors,
    }


@router.get("/events")
async def events(
    event_type: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return raw analytics events."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]

    stmt = select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(AnalyticsEvent.event_type == event_type)
    if course_id is not None:
        stmt = stmt.where(AnalyticsEvent.course_id == course_id)
    stmt = _filter_by_date(stmt, AnalyticsEvent, date_from, date_to)

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


@router.get("/export")
async def export(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Export detailed analytics report as CSV for the selected filters."""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    request_log = aliased(ChatLog)
    stmt = (
        select(
            ChatRequest.id,
            ChatRequest.session_id,
            ChatRequest.created_at,
            ChatRequest.role,
            ChatRequest.course_id,
            ChatRequest.intent,
            ChatRequest.message,
            ChatRequest.lms_calls,
            request_log.answer,
            request_log.sources,
            request_log.latency_ms,
            request_log.error,
            request_log.cache_hit,
        )
        .join(request_log, request_log.request_id == ChatRequest.id, isouter=True)
        .order_by(ChatRequest.created_at.desc())
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)

    def classify_source(lms_calls, sources, cache_hit, error):
        if cache_hit:
            return "cache"
        has_lms = bool(lms_calls)
        has_rag = _sources_have_rag(sources)
        if has_lms and has_rag:
            return "both"
        if has_lms:
            return "lms"
        if has_rag:
            return "rag"
        if error:
            return "error"
        return "fallback"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "request_id",
        "session_id",
        "created_at",
        "role",
        "course_id",
        "intent",
        "message",
        "source_type",
        "lms_used",
        "rag_used",
        "cache_hit",
        "has_answer",
        "latency_ms",
        "error",
    ])

    for row in result.all():
        (
            request_id,
            session_id,
            created_at,
            role,
            course_id_val,
            intent,
            message,
            lms_calls,
            answer,
            sources,
            latency_ms,
            error,
            cache_hit,
        ) = row
        source_type = classify_source(lms_calls, sources, cache_hit, error)
        writer.writerow([
            request_id,
            session_id,
            created_at.isoformat() if created_at else "",
            role or "",
            course_id_val or "",
            intent or "",
            (message or "").replace("\n", " "),
            source_type,
            "yes" if lms_calls else "no",
            "yes" if sources else "no",
            "yes" if cache_hit else "no",
            "yes" if answer else "no",
            round(latency_ms) if latency_ms is not None else "",
            (error or "").replace("\n", " ")[:500],
        ])

    output.seek(0)
    filename = f"ai_curator_analytics_{date_from.date() if date_from else 'all'}_{date_to.date() if date_to else 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
