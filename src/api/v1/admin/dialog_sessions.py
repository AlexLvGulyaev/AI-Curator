"""Admin endpoints for dialog sessions (student conversation history).

This module operates on the canonical chat_sessions / execution_sessions /
execution_steps schema introduced in Sprint 5.6. Legacy chat_requests are
linked via chat_session_id and session_id.
"""

from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from db import get_db
from models.chat import ChatLog, ChatRequest, ChatSession, ExecutionSession
from services.ai_config import AiConfigService
from services.logger import LoggerService

router = APIRouter(prefix="/dialog-sessions", tags=["admin-dialog-sessions"])


async def _log_audit(action: str, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="dialog_sessions",
        user_id="admin",
        user_role="admin",
    )


def _status_for_log(log: Optional[ChatLog]) -> str:
    if log is None:
        return "pending"
    if log.error:
        return "error"
    if log.answer:
        return "ok"
    return "pending"


def _status_from_execution_session(exec_session: Optional[ExecutionSession]) -> str:
    if exec_session is None:
        return "pending"
    if exec_session.status == "error":
        return "error"
    if exec_session.status == "started":
        return "pending"
    return "ok"


@router.get("")
async def list_dialog_sessions(
    hours: Optional[int] = Query(None, ge=1, le=720, description="Filter sessions updated within last N hours"),
    mode: Optional[str] = Query(None, description="Source mode: text, lms, rag, mixed"),
    active_only: Optional[bool] = Query(None, description="Filter only active sessions"),
    search: Optional[str] = Query(None, description="Search by session_id or role"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated canonical dialog sessions."""
    await _log_audit("view_dialog_sessions", db)

    req_agg = (
        select(
            ChatRequest.chat_session_id.label("chat_session_id"),
            func.count().label("message_count"),
            func.min(ChatRequest.created_at).label("first_message_at"),
            func.max(ChatRequest.created_at).label("last_message_at"),
        )
        .where(ChatRequest.chat_session_id.isnot(None))
        .group_by(ChatRequest.chat_session_id)
        .subquery()
    )

    stmt = (
        select(ChatSession, req_agg.c.message_count, req_agg.c.first_message_at, req_agg.c.last_message_at)
        .outerjoin(req_agg, req_agg.c.chat_session_id == ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
    )

    if hours is not None:
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = stmt.where(ChatSession.updated_at >= since)
    if mode:
        stmt = stmt.where(ChatSession.mode == mode)
    if active_only is True:
        stmt = stmt.where(ChatSession.is_active.is_(True))
    elif active_only is False:
        stmt = stmt.where(ChatSession.is_active.is_(False))
    if search:
        stmt = stmt.where(
            ChatSession.session_id.ilike(f"%{search}%")
            | ChatSession.role.ilike(f"%{search}%")
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    session_ids = [r.ChatSession.id for r in rows]
    last_exec_status: Dict[int, str] = {}
    if session_ids:
        last_exec = (
            select(
                ExecutionSession.chat_session_id.label("chat_session_id"),
                func.max(ExecutionSession.id).label("last_id"),
            )
            .where(ExecutionSession.chat_session_id.in_(session_ids))
            .group_by(ExecutionSession.chat_session_id)
            .subquery()
        )
        exec_result = await db.execute(
            select(ExecutionSession.chat_session_id, ExecutionSession.status)
            .join(last_exec, ExecutionSession.id == last_exec.c.last_id)
        )
        for sid, status in exec_result.all():
            last_exec_status[sid] = status

    items = []
    for session, message_count, first_message_at, last_message_at in rows:
        status = last_exec_status.get(session.id, "ok")
        items.append(
            {
                "id": session.id,
                "session_id": session.session_id,
                "message_count": message_count or 0,
                "first_message_at": first_message_at.isoformat() if first_message_at else None,
                "last_message_at": last_message_at.isoformat() if last_message_at else None,
                "role": session.role,
                "course_id": session.course_id,
                "difficulty": session.difficulty,
                "mode": session.mode,
                "is_active": session.is_active,
                "status": "error" if status == "error" else "ok",
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{session_id}")
async def get_dialog_session(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed dialog session with turns, execution timeline and budget."""
    await _log_audit("view_dialog_session_detail", db)

    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Dialog session not found")

    # Turns from linked chat_requests (and legacy session_id fallback).
    req_result = await db.execute(
        select(ChatRequest)
        .where(
            (ChatRequest.chat_session_id == session.id)
            | (ChatRequest.session_id == session_id)
        )
        .order_by(ChatRequest.created_at.asc())
        .offset(offset)
        .limit(limit)
        .options(joinedload(ChatRequest.logs))
    )
    requests = req_result.unique().scalars().all()

    count_stmt = (
        select(func.count())
        .where(
            (ChatRequest.chat_session_id == session.id)
            | (ChatRequest.session_id == session_id)
        )
    )
    total_messages = await db.scalar(count_stmt) or 0

    turns: List[Dict[str, Any]] = []
    for req in requests:
        log = req.logs[0] if req.logs else None
        turns.append(
            {
                "request_id": req.id,
                "log_id": log.id if log else None,
                "role": req.role,
                "course_id": req.course_id,
                "difficulty": req.difficulty,
                "intent": req.intent,
                "user_message": req.message,
                "assistant_answer": log.answer if log else None,
                "sources": log.sources if log else [],
                "status": _status_for_log(log),
                "llm_model": log.llm_model if log else None,
                "latency_ms": log.latency_ms if log else None,
                "total_tokens": log.total_tokens if log else None,
                "feedback_score": log.feedback_score if log else None,
                "error": log.error if log else None,
                "rag_filters": req.rag_filters,
                "lms_calls": req.lms_calls,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
        )

    # Execution timeline.
    exec_result = await db.execute(
        select(ExecutionSession)
        .where(ExecutionSession.chat_session_id == session.id)
        .order_by(ExecutionSession.created_at.asc())
        .options(selectinload(ExecutionSession.steps))
    )
    execution_sessions = exec_result.unique().scalars().all()
    execution_sessions_payload = []
    for es in execution_sessions:
        execution_sessions_payload.append(
            {
                "id": es.id,
                "request_id": es.request_id,
                "route": es.route,
                "status": es.status,
                "client_ip": es.client_ip,
                "provider_key": es.provider_key,
                "model_name": es.model_name,
                "duration_ms": es.duration_ms,
                "started_at": es.started_at.isoformat() if es.started_at else None,
                "finished_at": es.finished_at.isoformat() if es.finished_at else None,
                "execution_metadata": es.execution_metadata,
                "steps": [
                    {
                        "id": step.id,
                        "stage_name": step.stage_name,
                        "step_order": step.step_order,
                        "status": step.status,
                        "duration_ms": step.duration_ms,
                        "started_at": step.started_at.isoformat() if step.started_at else None,
                        "finished_at": step.finished_at.isoformat() if step.finished_at else None,
                        "step_metadata": step.step_metadata,
                    }
                    for step in es.steps
                ],
            }
        )

    # Budget / AI config snapshot.
    ai_config = await AiConfigService(db).get_active()
    budget = {
        "model": ai_config.model if ai_config else None,
        "max_tokens": ai_config.max_tokens if ai_config else None,
        "temperature": ai_config.temperature if ai_config else None,
    }

    return {
        "id": session.id,
        "session_id": session.session_id,
        "user_id": session.user_id,
        "role": session.role,
        "course_id": session.course_id,
        "difficulty": session.difficulty,
        "mode": session.mode,
        "is_active": session.is_active,
        "message_count": total_messages,
        "first_message_at": session.created_at.isoformat() if session.created_at else None,
        "last_message_at": session.updated_at.isoformat() if session.updated_at else None,
        "turns": turns,
        "execution_sessions": execution_sessions_payload,
        "budget": budget,
        "memory_source": "PostgreSQL",
        "limit": limit,
        "offset": offset,
    }
