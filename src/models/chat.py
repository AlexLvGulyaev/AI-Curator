"""Chat and logging SQLAlchemy models for AI Curator."""

from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ChatSession(Base):
    """Canonical dialog session grouping chat requests from one student."""

    __tablename__ = "chat_sessions"

    session_id = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    role = Column(String(50), nullable=True, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    difficulty = Column(String(50), nullable=True)
    mode = Column(String(20), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    requests: Mapped[list["ChatRequest"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    execution_sessions: Mapped[list["ExecutionSession"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChatRequest(Base):
    """A student request captured for analytics and context."""

    __tablename__ = "chat_requests"

    session_id = Column(String(255), nullable=True, index=True)
    chat_session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role = Column(String(50), nullable=True, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    difficulty = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    lms_calls = Column(JSON, nullable=True, default=list)
    rag_filters = Column(JSON, nullable=True, default=dict)

    chat_session: Mapped[Optional["ChatSession"]] = relationship(back_populates="requests")
    logs: Mapped[list["ChatLog"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ChatLog(Base):
    """Log entry for a generated AI response."""

    __tablename__ = "chat_logs"

    request_id = Column(Integer, ForeignKey("chat_requests.id", ondelete="CASCADE"), nullable=True, index=True)
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True, default=list)
    llm_model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    feedback_score = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, nullable=False, default=False, server_default="false")

    request: Mapped["ChatRequest"] = relationship(back_populates="logs")


class LlmCallTrace(Base):
    """Full prompt/response trace for an LLM call with short retention."""

    __tablename__ = "llm_call_traces"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("chat_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    model = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LlmCall(Base):
    """Metadata log of every LLM API call. Full content is stored in LlmCallTrace."""

    __tablename__ = "llm_calls"

    request_id = Column(Integer, ForeignKey("chat_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    trace_id = Column(Integer, ForeignKey("llm_call_traces.id", ondelete="SET NULL"), nullable=True, index=True)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(50), nullable=False, default="ok")
    error = Column(Text, nullable=True)


class ExecutionSession(Base):
    """Traced execution pipeline for a single chat request."""

    __tablename__ = "execution_sessions"

    chat_session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id = Column(
        Integer,
        ForeignKey("chat_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    route = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="started", index=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    provider_key = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    execution_metadata = Column(JSON, nullable=True, default=dict)
    is_backfilled = Column(Boolean, nullable=False, default=False)

    chat_session: Mapped["ChatSession"] = relationship(back_populates="execution_sessions")
    request: Mapped[Optional["ChatRequest"]] = relationship()
    steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="execution_session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ExecutionStep.step_order",
    )


class ExecutionStep(Base):
    """Single stage inside an execution pipeline."""

    __tablename__ = "execution_steps"

    execution_session_id = Column(
        Integer,
        ForeignKey("execution_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name = Column(String(50), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="ok")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    step_metadata = Column(JSON, nullable=True, default=dict)

    execution_session: Mapped["ExecutionSession"] = relationship(back_populates="steps")


class AnalyticsEvent(Base):
    """Discrete analytics events for aggregation."""

    __tablename__ = "analytics_events"

    session_id = Column(String(255), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    module_id = Column(Integer, nullable=True, index=True)
    topic_id = Column(Integer, nullable=True, index=True)
    difficulty = Column(String(50), nullable=True)
    intent = Column(String(50), nullable=True, index=True)
    payload = Column(JSON, nullable=True, default=dict)


class AuditLog(Base):
    """Audit trail for administrative actions."""

    __tablename__ = "audit_logs"

    user_id = Column(String(255), nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    user_role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    details = Column(JSON, nullable=True, default=dict)
