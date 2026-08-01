"""Execution tracing service for chat pipeline observability."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import ChatSession, ExecutionSession, ExecutionStep


class ExecutionTracerService:
    """Async logger for chat execution sessions and pipeline steps."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_chat_session(
        self,
        session_id: str,
        *,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        course_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> ChatSession:
        """Get or upsert a canonical ChatSession by business session_id."""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if session is None:
            session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                role=role,
                course_id=course_id,
                difficulty=difficulty,
                mode=mode,
                is_active=True,
                updated_at=now,
            )
            self.db.add(session)
        else:
            if user_id is not None:
                session.user_id = user_id
            if role is not None:
                session.role = role
            if course_id is not None:
                session.course_id = course_id
            if difficulty is not None:
                session.difficulty = difficulty
            if mode is not None:
                session.mode = mode
            session.is_active = True
            session.updated_at = now
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def start_execution_session(
        self,
        chat_session_id: int,
        *,
        request_id: Optional[int] = None,
        route: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        provider_key: Optional[str] = None,
        model_name: Optional[str] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionSession:
        """Create an ExecutionSession in 'started' state."""
        exec_session = ExecutionSession(
            chat_session_id=chat_session_id,
            request_id=request_id,
            route=route,
            status="started",
            client_ip=client_ip,
            user_agent=user_agent,
            provider_key=provider_key,
            model_name=model_name,
            execution_metadata=execution_metadata or {},
        )
        self.db.add(exec_session)
        await self.db.commit()
        await self.db.refresh(exec_session)
        return exec_session

    async def add_execution_step(
        self,
        execution_session_id: int,
        stage_name: str,
        step_order: int,
        *,
        status: str = "ok",
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        step_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionStep:
        """Persist a single execution step."""
        step = ExecutionStep(
            execution_session_id=execution_session_id,
            stage_name=stage_name,
            step_order=step_order,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            step_metadata=step_metadata or {},
        )
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step

    async def add_execution_steps(
        self,
        execution_session_id: int,
        steps: List[Dict[str, Any]],
    ) -> List[ExecutionStep]:
        """Persist multiple execution steps in one transaction."""
        created = []
        for step_data in steps:
            step = ExecutionStep(
                execution_session_id=execution_session_id,
                stage_name=step_data["stage_name"],
                step_order=step_data["step_order"],
                status=step_data.get("status", "ok"),
                started_at=step_data.get("started_at"),
                finished_at=step_data.get("finished_at"),
                duration_ms=step_data.get("duration_ms"),
                step_metadata=step_data.get("step_metadata") or {},
            )
            self.db.add(step)
            created.append(step)
        await self.db.commit()
        for step in created:
            await self.db.refresh(step)
        return created

    async def finish_execution_session(
        self,
        execution_session_id: int,
        status: str,
        *,
        duration_ms: Optional[int] = None,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionSession:
        """Close an ExecutionSession and update status/duration."""
        result = await self.db.execute(
            select(ExecutionSession).where(ExecutionSession.id == execution_session_id)
        )
        exec_session = result.scalar_one_or_none()
        if exec_session is None:
            raise ValueError(f"ExecutionSession {execution_session_id} not found")
        exec_session.status = status
        exec_session.finished_at = datetime.now(timezone.utc)
        if duration_ms is not None:
            exec_session.duration_ms = duration_ms
        if execution_metadata is not None:
            exec_session.execution_metadata = execution_metadata
        await self.db.commit()
        await self.db.refresh(exec_session)
        return exec_session

    async def update_execution_session(
        self,
        execution_session_id: int,
        *,
        request_id: Optional[int] = None,
        model_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ExecutionSession:
        """Partial update of an existing ExecutionSession."""
        result = await self.db.execute(
            select(ExecutionSession).where(ExecutionSession.id == execution_session_id)
        )
        exec_session = result.scalar_one_or_none()
        if exec_session is None:
            raise ValueError(f"ExecutionSession {execution_session_id} not found")
        if request_id is not None:
            exec_session.request_id = request_id
        if model_name is not None:
            exec_session.model_name = model_name
        if status is not None:
            exec_session.status = status
        await self.db.commit()
        await self.db.refresh(exec_session)
        return exec_session
