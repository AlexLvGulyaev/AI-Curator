"""Admin endpoints for system monitoring."""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.lms_adapter import lms_adapter
from config import settings
from db import get_db
from models.chat import (
    ChatLog,
    ChatRequest,
    ChatSession,
    ExecutionSession,
    ExecutionStep,
    LlmCall,
)
from services.chroma_client import get_chroma_client
from services.knowledge_base import KnowledgeBaseService

router = APIRouter(prefix="/monitoring", tags=["admin-monitoring"])


def _llm_providers():
    """Return configured LLM providers summary."""
    providers = []
    openai_ok = bool(settings.openai_api_key and not settings.openai_api_key.startswith("YOUR"))
    providers.append({
        "name": "OpenAI",
        "active": True,
        "status": "ok" if openai_ok else "error",
        "detail": "Active provider" if openai_ok else "API key missing or placeholder",
        "model": settings.openai_model or "gpt-4o-mini",
    })
    # GigaChat is reserved as fallback for future sprints.
    gigachat_token = getattr(settings, "gigachat_token", None)
    providers.append({
        "name": "GigaChat",
        "active": False,
        "status": "ok" if gigachat_token else "disabled",
        "detail": "Fallback provider (not configured)" if not gigachat_token else "Fallback configured",
        "model": "GigaChat-Max",
    })
    return providers


async def _ai_activity(db: AsyncSession):
    """Return AI activity metrics for the last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    total_requests = await db.scalar(
        select(func.count(ChatRequest.id)).where(ChatRequest.created_at >= since)
    )

    total_answers = await db.scalar(
        select(func.count(ChatLog.id))
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
        .where(ChatRequest.created_at >= since)
        .where(ChatLog.answer != None)
    )

    avg_latency = await db.scalar(
        select(func.avg(ChatLog.latency_ms))
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
        .where(ChatRequest.created_at >= since)
    )

    total_tokens = await db.scalar(
        select(func.sum(LlmCall.total_tokens))
        .join(ChatRequest, LlmCall.request_id == ChatRequest.id)
        .where(ChatRequest.created_at >= since)
    )

    intent_result = await db.execute(
        select(ChatRequest.intent, func.count(ChatRequest.id).label("count"))
        .where(ChatRequest.created_at >= since)
        .group_by(ChatRequest.intent)
        .order_by(func.count(ChatRequest.id).desc())
    )

    return {
        "total_requests": total_requests or 0,
        "total_answers": total_answers or 0,
        "average_latency_ms": round(avg_latency, 2) if avg_latency else 0,
        "total_tokens": total_tokens or 0,
        "intent_breakdown": [
            {"intent": intent or "unknown", "count": count}
            for intent, count in intent_result.all()
        ],
    }


async def _recent_errors(db: AsyncSession, limit: int = 10):
    """Return recent error/warning entries from chat logs and execution trace.

    Unlike the older implementation that only looked at ``chat_logs.error``,
    this version also surfaces partial pipeline failures captured in
    ``execution_sessions`` and ``execution_steps`` (e.g. LMS fetch error or
    RAG search error that was masked by a fallback answer).
    """
    chat_log_rows = await db.execute(
        select(
            ChatRequest.session_id,
            ChatRequest.intent,
            ChatLog.error,
            ChatLog.created_at,
        )
        .join(ChatRequest, ChatLog.request_id == ChatRequest.id)
        .where(ChatLog.error != None)
        .where(ChatLog.error != "")
        .order_by(ChatLog.created_at.desc())
        .limit(limit)
    )

    session_rows = await db.execute(
        select(
            ChatSession.session_id,
            ChatRequest.intent,
            ExecutionSession.status,
            ExecutionSession.execution_metadata,
            ExecutionSession.finished_at,
            ExecutionSession.id,
        )
        .join(ChatSession, ExecutionSession.chat_session_id == ChatSession.id)
        .outerjoin(ChatRequest, ExecutionSession.request_id == ChatRequest.id)
        .where(ExecutionSession.status.in_(["error", "warning"]))
        .order_by(ExecutionSession.finished_at.desc().nullslast())
        .limit(limit)
    )

    step_rows = await db.execute(
        select(
            ChatSession.session_id,
            ChatRequest.intent,
            ExecutionSession.id.label("execution_session_id"),
            ExecutionStep.stage_name,
            ExecutionStep.status,
            ExecutionStep.step_metadata,
            ExecutionStep.finished_at,
            ExecutionStep.started_at,
        )
        .join(ExecutionSession, ExecutionStep.execution_session_id == ExecutionSession.id)
        .join(ChatSession, ExecutionSession.chat_session_id == ChatSession.id)
        .outerjoin(ChatRequest, ExecutionSession.request_id == ChatRequest.id)
        .where(ExecutionStep.status.in_(["error", "warning"]))
        .order_by(ExecutionStep.finished_at.desc().nullslast())
        .limit(limit)
    )

    errors: list[dict] = []

    for session_id, intent, error, created_at in chat_log_rows.all():
        errors.append({
            "source": "chat_log",
            "session_id": session_id,
            "intent": intent or "unknown",
            "stage_name": None,
            "status": "error",
            "error": (error or "")[:500],
            "created_at": created_at.isoformat() if created_at else None,
        })

    for session_id, intent, status, metadata, finished_at, exec_id in session_rows.all():
        meta = metadata or {}
        message = meta.get("error") or f"Execution session status: {status}"
        errors.append({
            "source": "execution_session",
            "session_id": session_id,
            "intent": intent or "unknown",
            "stage_name": None,
            "status": status,
            "error": message[:500],
            "execution_session_id": exec_id,
            "created_at": finished_at.isoformat() if finished_at else None,
        })

    for session_id, intent, exec_id, stage_name, status, metadata, finished_at, started_at in step_rows.all():
        meta = metadata or {}
        # Pull a human-readable error from step_metadata if available.
        step_errors = meta.get("errors", [])
        if step_errors:
            message = "; ".join(str(e.get("error", e)) for e in step_errors[:3])
        elif meta.get("error"):
            message = str(meta["error"])
        else:
            message = f"Step {stage_name} status: {status}"
        ts = finished_at or started_at
        errors.append({
            "source": "execution_step",
            "session_id": session_id,
            "intent": intent or "unknown",
            "stage_name": stage_name,
            "status": status,
            "error": message[:500],
            "execution_session_id": exec_id,
            "created_at": ts.isoformat() if ts else None,
        })

    # Deduplicate by session_id + stage_name + truncated error, keep newest first.
    seen: set = set()
    deduped: list[dict] = []
    for entry in sorted(errors, key=lambda x: x["created_at"] or "", reverse=True):
        key = (entry.get("session_id"), entry.get("stage_name"), entry["error"][:120])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
        if len(deduped) >= limit:
            break

    return deduped


async def _kb_status(db: AsyncSession):
    """Return Knowledge Base aggregate status."""
    service = KnowledgeBaseService(db)
    try:
        status = await service.get_status()
        return status
    except Exception as exc:
        return {
            "total_documents": 0,
            "published_documents": 0,
            "total_versions": 0,
            "indexed_chunks": 0,
            "error": str(exc),
        }


@router.get("/status")
async def monitoring_status(db: AsyncSession = Depends(get_db)):
    """Return health, latency, AI activity, KB status, providers and errors."""
    # Read-only views are intentionally not audited to avoid self-generated noise.
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
        db_detail = None
    except Exception as exc:
        db_status = "error"
        db_detail = str(exc)
    db_latency = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    try:
        lms_health = await lms_adapter.health_check()
        lms_status = lms_health.status
        lms_detail = lms_health.detail
        lms_latency = lms_health.response_time_ms
    except Exception as exc:
        lms_status = "error"
        lms_detail = str(exc)
        lms_latency = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    try:
        client = get_chroma_client()
        client.heartbeat()
        chroma_status = "ok"
        chroma_detail = None
    except Exception as exc:
        chroma_status = "error"
        chroma_detail = str(exc)
    chroma_latency = round((time.perf_counter() - start) * 1000, 2)

    openai_ok = bool(settings.openai_api_key and not settings.openai_api_key.startswith("YOUR"))
    llm_status = "ok" if openai_ok else "error"
    llm_detail = "Configuration present" if openai_ok else "OpenAI API key missing or placeholder"

    api_status = "ok"
    api_latency = round((time.perf_counter() - start) * 1000, 2)

    overall = "ok" if all(s == "ok" for s in [api_status, db_status, lms_status, chroma_status, llm_status]) else "degraded"

    ai_activity = await _ai_activity(db)
    kb_status = await _kb_status(db)
    providers = _llm_providers()
    errors = await _recent_errors(db)

    return {
        "overall": overall,
        "components": {
            "api": {"status": api_status, "latency_ms": api_latency},
            "database": {"status": db_status, "latency_ms": db_latency, "detail": db_detail},
            "lms": {"status": lms_status, "latency_ms": lms_latency, "detail": lms_detail},
            "chroma": {"status": chroma_status, "latency_ms": chroma_latency, "detail": chroma_detail},
            "llm": {"status": llm_status, "detail": llm_detail},
        },
        "ai_activity": ai_activity,
        "kb_status": kb_status,
        "llm_providers": providers,
        "recent_errors": errors,
    }


@router.get("/health")
async def aggregated_health(db: AsyncSession = Depends(get_db)):
    """Return a simple aggregated health status."""
    status_data = await monitoring_status(db)
    return {
        "status": status_data["overall"],
        "components": status_data["components"],
    }


@router.get("/errors")
async def recent_errors(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return recent non-empty error entries."""
    # Read-only views are intentionally not audited to avoid self-generated noise.
    return await _recent_errors(db, limit)

