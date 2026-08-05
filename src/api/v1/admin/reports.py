"""Admin endpoints for Business Reports / Quality Reports.

Reports in this module are read-only management summaries derived from
chat logs and Knowledge Base metadata. They intentionally do not write to
audit_logs to avoid self-generated noise while browsing.
"""

import csv
import io
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.chat import ChatLog, ChatRequest
from models.knowledge_base import KbDocument, KbDocumentChunk, KbDocumentVersion

router = APIRouter(prefix="/reports", tags=["admin-reports"])

_DATE_FORMAT = "%Y-%m-%d"


_KB_GAP_INTENTS = ("study", "mixed")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string into a timezone-aware datetime."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, _DATE_FORMAT).date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid date: {value}. Use YYYY-MM-DD."
        ) from exc
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def _filter_by_date(
    stmt, model, date_from: Optional[datetime], date_to: Optional[datetime]
):
    """Apply date range filters to a query statement."""
    if date_from is not None:
        stmt = stmt.where(model.created_at >= date_from)
    if date_to is not None:
        end = datetime.combine(date_to.date(), time.max, tzinfo=timezone.utc)
        stmt = stmt.where(model.created_at <= end)
    return stmt


def _filters(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    course_id: Optional[int] = Query(None, description="Filter by course_id"),
):
    """Common dependency for reports filters."""
    return {
        "date_from": _parse_date(date_from),
        "date_to": _parse_date(date_to),
        "course_id": course_id,
    }


def _sources_have_rag(sources: Optional[List[Any]]) -> bool:
    """Return True if sources contain RAG/KB chunks (not only LMS references)."""
    if not sources:
        return False
    for item in sources:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "lms":
            continue
        if item.get("document_id") is not None or item.get("chunk_index") is not None:
            return True
        metadata = item.get("metadata", {})
        if metadata.get("document_id") is not None or metadata.get("chunk_index") is not None:
            return True
        if "distance" in item and "metadata" in item:
            return True
    return False


def _has_only_lms_sources(sources: Optional[List[Any]]) -> bool:
    """Return True when sources exist and every item is an LMS reference."""
    if not sources:
        return False
    return all(
        isinstance(item, dict) and item.get("type") == "lms" for item in sources
    )


def _kb_gap_sources_clause():
    """SQL clause matching responses without RAG/KB sources.

    Uses PostgreSQL JSON operators: NULL/empty sources, or sources where every
    element has type == 'lms' (no KB chunks).
    """
    return (
        (ChatLog.sources == None)
        | (func.json_array_length(ChatLog.sources) == 0)
        | text(
            "NOT EXISTS ("
            "SELECT 1 FROM json_array_elements(chat_logs.sources) s "
            "WHERE (s->>'type') IS DISTINCT FROM 'lms'"
            ")"
        )
    )


def _classify_source(
    lms_calls: Optional[List[Any]],
    sources: Optional[List[Any]],
    cache_hit: bool,
    error: Optional[str],
) -> str:
    """Classify the source of a single response."""
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


def _request_summary(request: ChatRequest, log: Optional[ChatLog]) -> Dict[str, Any]:
    """Build a lightweight summary of a chat request and its log."""
    return {
        "request_id": request.id,
        "session_id": request.session_id,
        "message": request.message,
        "intent": request.intent,
        "course_id": request.course_id,
        "role": request.role,
        "difficulty": request.difficulty,
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "answer": log.answer if log else None,
        "sources": log.sources if log else None,
        "feedback_score": log.feedback_score if log else None,
        "latency_ms": log.latency_ms if log else None,
        "cache_hit": log.cache_hit if log else False,
        "error": log.error if log else None,
    }


@router.get("/quality")
async def quality_report(
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return high-level quality metrics for the selected period/course."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    base_stmt = select(ChatRequest, ChatLog).join(
        ChatLog, ChatLog.request_id == ChatRequest.id, isouter=True
    )
    base_stmt = _filter_by_date(base_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        base_stmt = base_stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(base_stmt)
    rows = result.unique().all()

    total = len(rows)
    answered = 0
    errors = 0
    fallback = 0
    cache_hits = 0
    feedback_sum = 0
    feedback_count = 0
    rag_eligible = 0
    rag_covered = 0

    for request, log in rows:
        is_answered = bool(log and log.answer)
        if is_answered:
            answered += 1
        if log and log.error:
            errors += 1
        if is_answered:
            source_type = _classify_source(
                request.lms_calls,
                log.sources,
                log.cache_hit,
                log.error,
            )
            if source_type == "fallback":
                fallback += 1
        if log and log.cache_hit:
            cache_hits += 1
        if log and log.feedback_score is not None:
            feedback_sum += log.feedback_score
            feedback_count += 1
        if request.intent in _KB_GAP_INTENTS and is_answered:
            rag_eligible += 1
            if _sources_have_rag(log.sources):
                rag_covered += 1

    return {
        "total_requests": total,
        "answered_count": answered,
        "answered_rate": round((answered / total) * 100, 2) if total else 0,
        "error_count": errors,
        "error_rate": round((errors / total) * 100, 2) if total else 0,
        "fallback_count": fallback,
        "fallback_rate": round((fallback / total) * 100, 2) if total else 0,
        "cache_hit_count": cache_hits,
        "cache_hit_rate": round((cache_hits / total) * 100, 2) if total else 0,
        "average_feedback_score": round(feedback_sum / feedback_count, 2) if feedback_count else None,
        "rag_eligible_count": rag_eligible,
        "rag_covered_count": rag_covered,
        "rag_coverage_rate": round((rag_covered / rag_eligible) * 100, 2) if rag_eligible else None,
    }


@router.get("/unanswered")
async def unanswered_report(
    intent: Optional[str] = Query(None, description="Filter by intent"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated requests that did not receive an answer."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

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
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)
    if intent:
        stmt = stmt.where(ChatRequest.intent == intent)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = [_request_summary(req, None) for req in result.scalars().unique()]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/kb-gaps")
async def kb_gaps_report(
    intent: Optional[str] = Query(None, description="Filter by intent"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated study/mixed requests answered without KB/RAG sources.

    A KB gap means the student asked a content question but the response did
    not cite any Knowledge Base chunk. These questions are candidates for new
    or extended KB material.
    """
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    stmt = (
        select(ChatRequest, ChatLog)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id)
        .where(
            ChatRequest.intent.in_(_KB_GAP_INTENTS),
            ChatLog.answer != None,
            (ChatLog.error == None) | (ChatLog.error == ""),
            (
                (ChatLog.sources == None)
                | (func.json_array_length(ChatLog.sources) == 0)
                | _kb_gap_sources_clause()
            ),
        )
        .order_by(ChatRequest.created_at.desc())
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)
    if intent:
        stmt = stmt.where(ChatRequest.intent == intent)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = [
        _request_summary(req, log) for req, log in result.unique().all()
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/popular-topics")
async def popular_topics_report(
    limit: int = Query(20, ge=1, le=100),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return most frequent intents / topics."""
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
    return [
        {"intent": row.intent or "unknown", "count": row.count}
        for row in result.all()
    ]


@router.get("/kb-coverage")
async def kb_coverage_report(
    db: AsyncSession = Depends(get_db),
):
    """Return Knowledge Base coverage by course, document type and status."""
    # Documents by course.
    docs_stmt = (
        select(
            KbDocument.course_id,
            func.count(KbDocument.id).label("total_documents"),
            func.sum(func.cast(KbDocument.is_published, Integer)).label("published_documents"),
        )
        .group_by(KbDocument.course_id)
        .order_by(KbDocument.course_id)
    )
    docs_result = await db.execute(docs_stmt)

    # Active chunks by course via active/non-archived versions.
    chunks_stmt = (
        select(
            KbDocument.course_id,
            func.coalesce(func.sum(KbDocumentVersion.chunk_count), 0).label("chunk_count"),
        )
        .join(KbDocumentVersion, KbDocumentVersion.document_id == KbDocument.id)
        .where(
            KbDocumentVersion.is_active.is_(True),
            KbDocumentVersion.status != "archived",
        )
        .group_by(KbDocument.course_id)
        .order_by(KbDocument.course_id)
    )
    chunks_result = await db.execute(chunks_stmt)
    chunk_map = {row.course_id: row.chunk_count for row in chunks_result.all()}

    coverage = []
    for row in docs_result.all():
        coverage.append({
            "course_id": row.course_id,
            "total_documents": row.total_documents,
            "published_documents": int(row.published_documents or 0),
            "chunk_count": int(chunk_map.get(row.course_id, 0)),
        })

    # Documents by type.
    type_stmt = (
        select(KbDocument.document_type, func.count(KbDocument.id).label("count"))
        .group_by(KbDocument.document_type)
        .order_by(KbDocument.document_type)
    )
    type_result = await db.execute(type_stmt)
    documents_by_type = [
        {"document_type": row.document_type, "count": row.count}
        for row in type_result.all()
    ]

    total_stmt = select(func.count(KbDocument.id))
    total_documents = await db.scalar(total_stmt) or 0

    return {
        "total_documents": total_documents,
        "documents_by_type": documents_by_type,
        "coverage_by_course": coverage,
    }


@router.get("/expansion-candidates")
async def expansion_candidates_report(
    limit: int = Query(10, ge=1, le=100),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Return intents with the most KB gaps — candidates for KB expansion."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    stmt = (
        select(ChatRequest.intent, func.count(ChatRequest.id).label("gap_count"))
        .join(ChatLog, ChatLog.request_id == ChatRequest.id)
        .where(
            ChatRequest.intent.in_(_KB_GAP_INTENTS),
            ChatLog.answer != None,
            (ChatLog.error == None) | (ChatLog.error == ""),
            (
                (ChatLog.sources == None)
                | (func.json_array_length(ChatLog.sources) == 0)
                | _kb_gap_sources_clause()
            ),
        )
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
        .limit(limit)
    )
    stmt = _filter_by_date(stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        stmt = stmt.where(ChatRequest.course_id == course_id)

    result = await db.execute(stmt)
    return [
        {
            "intent": row.intent or "unknown",
            "gap_count": row.gap_count,
            "recommendation": "Добавить или расширить материалы Knowledge Base по этой теме.",
        }
        for row in result.all()
    ]


@router.get("/export")
async def export_report(
    section: Optional[str] = Query(
        None,
        description="Export section: unanswered, kb-gaps, or all (default)",
    ),
    filters: Dict[str, Any] = Depends(_filters),
    db: AsyncSession = Depends(get_db),
):
    """Export unanswered and KB-gap questions as CSV."""
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    course_id = filters["course_id"]

    answered_subq = (
        select(ChatLog.request_id)
        .where(ChatLog.answer != None)
        .distinct()
        .subquery()
    )
    unanswered_stmt = (
        select(ChatRequest)
        .where(ChatRequest.id.notin_(select(answered_subq.c.request_id)))
        .order_by(ChatRequest.created_at.desc())
    )
    unanswered_stmt = _filter_by_date(
        unanswered_stmt, ChatRequest, date_from, date_to
    )
    if course_id is not None:
        unanswered_stmt = unanswered_stmt.where(ChatRequest.course_id == course_id)

    kb_gap_stmt = (
        select(ChatRequest, ChatLog)
        .join(ChatLog, ChatLog.request_id == ChatRequest.id)
        .where(
            ChatRequest.intent.in_(_KB_GAP_INTENTS),
            ChatLog.answer != None,
            (ChatLog.error == None) | (ChatLog.error == ""),
            (
                (ChatLog.sources == None)
                | (func.json_array_length(ChatLog.sources) == 0)
                | _kb_gap_sources_clause()
            ),
        )
        .order_by(ChatRequest.created_at.desc())
    )
    kb_gap_stmt = _filter_by_date(kb_gap_stmt, ChatRequest, date_from, date_to)
    if course_id is not None:
        kb_gap_stmt = kb_gap_stmt.where(ChatRequest.course_id == course_id)

    unanswered_rows = []
    kb_gap_rows = []

    if section in (None, "all", "unanswered"):
        result = await db.execute(unanswered_stmt)
        unanswered_rows = [
            _request_summary(req, None) for req in result.scalars().unique()
        ]

    if section in (None, "all", "kb-gaps"):
        result = await db.execute(kb_gap_stmt)
        kb_gap_rows = [
            _request_summary(req, log) for req, log in result.unique().all()
        ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "report_section",
        "request_id",
        "session_id",
        "created_at",
        "role",
        "course_id",
        "intent",
        "difficulty",
        "message",
        "answer_preview",
        "feedback_score",
        "latency_ms",
        "cache_hit",
        "error",
    ])

    for item in unanswered_rows:
        writer.writerow([
            "unanswered",
            item["request_id"],
            item["session_id"] or "",
            item["created_at"] or "",
            item["role"] or "",
            item["course_id"] or "",
            item["intent"] or "",
            item["difficulty"] or "",
            (item["message"] or "").replace("\n", " ")[:500],
            "",
            "",
            "",
            "",
            "",
        ])

    for item in kb_gap_rows:
        log = None
        writer.writerow([
            "kb_gap",
            item["request_id"],
            item["session_id"] or "",
            item["created_at"] or "",
            item["role"] or "",
            item["course_id"] or "",
            item["intent"] or "",
            item["difficulty"] or "",
            (item["message"] or "").replace("\n", " ")[:500],
            (item["answer"] or "").replace("\n", " ")[:200],
            item["feedback_score"] if item["feedback_score"] is not None else "",
            item["latency_ms"] if item["latency_ms"] is not None else "",
            "yes" if item["cache_hit"] else "no",
            (item["error"] or "").replace("\n", " ")[:200],
        ])

    output.seek(0)
    from_date = date_from.date() if date_from else "all"
    to_date = date_to.date() if date_to else "all"
    filename = f"ai_curator_reports_{section or 'all'}_{from_date}_{to_date}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
