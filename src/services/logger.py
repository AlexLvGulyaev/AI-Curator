"""Logging, analytics and audit service for AI Curator."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import (
    AnalyticsEvent,
    AuditLog,
    ChatLog,
    ChatRequest,
    ChatSession,
    LlmCall,
    LlmCallTrace,
)
from services.execution_tracer import ExecutionTracerService


class LoggerService:
    """Async logger for chat, LLM, analytics and audit events."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tracer = ExecutionTracerService(db)

    async def create_or_update_chat_session(
        self,
        *,
        session_id: str,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        course_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> ChatSession:
        """Get or upsert a canonical ChatSession and wire it to tracer."""
        return await self.tracer.get_or_create_chat_session(
            session_id,
            user_id=user_id,
            role=role,
            course_id=course_id,
            difficulty=difficulty,
            mode=mode,
        )

    async def create_chat_request(
        self,
        *,
        session_id: Optional[str] = None,
        chat_session_id: Optional[int] = None,
        role: Optional[str] = None,
        course_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        message: str,
        intent: Optional[str] = None,
        lms_calls: Optional[List[Dict[str, Any]]] = None,
        rag_filters: Optional[Dict[str, Any]] = None,
    ) -> ChatRequest:
        """Persist a student chat request."""
        request = ChatRequest(
            session_id=session_id,
            chat_session_id=chat_session_id,
            role=role,
            course_id=course_id,
            difficulty=difficulty,
            message=message,
            intent=intent,
            lms_calls=lms_calls or [],
            rag_filters=rag_filters or {},
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def create_chat_log(
        self,
        request_id: int,
        *,
        answer: str,
        sources: List[Dict[str, Any]],
        llm_model: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> ChatLog:
        """Persist the generated answer for a request."""
        log = ChatLog(
            request_id=request_id,
            answer=answer,
            sources=sources,
            llm_model=llm_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            error=error,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def create_llm_call(
        self,
        request_id: Optional[int],
        *,
        model: str,
        prompt: str,
        response: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        status: str = "ok",
        error: Optional[str] = None,
    ) -> LlmCall:
        """Persist LLM call metadata and a short-retention full trace."""
        trace = LlmCallTrace(
            request_id=request_id,
            model=model,
            prompt=prompt,
            response=response,
        )
        self.db.add(trace)
        await self.db.flush()
        await self.db.refresh(trace)

        call = LlmCall(
            request_id=request_id,
            trace_id=trace.id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status=status,
            error=error,
        )
        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        return call

    async def log_analytics_event(
        self,
        *,
        event_type: str,
        session_id: Optional[str] = None,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        intent: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsEvent:
        """Persist a discrete analytics event."""
        event = AnalyticsEvent(
            session_id=session_id,
            event_type=event_type,
            course_id=course_id,
            module_id=module_id,
            topic_id=topic_id,
            difficulty=difficulty,
            intent=intent,
            payload=payload or {},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def log_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Persist an administrative audit event."""
        audit = AuditLog(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details or {},
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit

    async def cleanup_old_records(
        self,
        archive_dir: str,
        hot_retention_days: int = 30,
        trace_retention_days: int = 7,
    ) -> Dict[str, int]:
        """Archive records older than retention and delete them from hot storage.

        Archives are written as JSON lines gzip files to archive_dir.
        Returns counts of deleted rows per table.
        """
        import json
        import gzip
        import os

        os.makedirs(archive_dir, exist_ok=True)
        now = datetime.now(timezone.utc)
        cutoff_hot = now - timedelta(days=hot_retention_days)
        cutoff_trace = now - timedelta(days=trace_retention_days)

        deleted = {}

        # Archive and delete LLM call traces (short retention).
        trace_rows = await self.db.execute(
            sa.select(LlmCallTrace).where(LlmCallTrace.created_at < cutoff_trace)
        )
        trace_rows = trace_rows.scalars().all()
        if trace_rows:
            path = os.path.join(
                archive_dir,
                f"llm_call_traces_{cutoff_trace.isoformat()}.jsonl.gz",
            )
            with gzip.open(path, "wt", encoding="utf-8") as f:
                for row in trace_rows:
                    f.write(
                        json.dumps(
                            {
                                "id": row.id,
                                "request_id": row.request_id,
                                "model": row.model,
                                "prompt": row.prompt,
                                "response": row.response,
                                "created_at": row.created_at.isoformat() if row.created_at else None,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            trace_ids = [r.id for r in trace_rows]
            result = await self.db.execute(
                sa.delete(LlmCallTrace).where(LlmCallTrace.id.in_(trace_ids))
            )
            deleted["llm_call_traces"] = result.rowcount

        # Helper for archiving and deleting other hot tables by created_at.
        async def archive_and_delete(model, cutoff, name):
            rows_result = await self.db.execute(
                sa.select(model).where(model.created_at < cutoff)
            )
            rows = rows_result.scalars().all()
            if not rows:
                return 0
            path = os.path.join(
                archive_dir,
                f"{name}_{cutoff.isoformat()}.jsonl.gz",
            )
            with gzip.open(path, "wt", encoding="utf-8") as f:
                for row in rows:
                    data = {
                        c.name: getattr(row, c.name)
                        for c in model.__table__.columns
                    }
                    for key in list(data.keys()):
                        if isinstance(data[key], datetime):
                            data[key] = data[key].isoformat()
                    f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
            ids = [r.id for r in rows]
            result = await self.db.execute(
                sa.delete(model).where(model.id.in_(ids))
            )
            return result.rowcount

        deleted["chat_requests"] = await archive_and_delete(ChatRequest, cutoff_hot, "chat_requests")
        deleted["chat_logs"] = await archive_and_delete(ChatLog, cutoff_hot, "chat_logs")
        deleted["analytics_events"] = await archive_and_delete(AnalyticsEvent, cutoff_hot, "analytics_events")
        deleted["audit_logs"] = await archive_and_delete(AuditLog, cutoff_hot, "audit_logs")
        deleted["llm_calls"] = await archive_and_delete(LlmCall, cutoff_hot, "llm_calls")

        await self.db.commit()
        return deleted
