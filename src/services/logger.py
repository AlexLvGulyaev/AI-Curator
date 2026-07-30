"""Logging, analytics and audit service for AI Curator."""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import AnalyticsEvent, AuditLog, ChatLog, ChatRequest, LlmCall


class LoggerService:
    """Async logger for chat, LLM, analytics and audit events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_chat_request(
        self,
        *,
        session_id: Optional[str] = None,
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
        """Persist a single LLM API call."""
        call = LlmCall(
            request_id=request_id,
            model=model,
            prompt=prompt,
            response=response,
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
        user_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Persist an administrative audit event."""
        audit = AuditLog(
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit
