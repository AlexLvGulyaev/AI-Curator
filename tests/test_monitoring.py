"""Tests for admin monitoring endpoints."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.monitoring import _recent_errors
from models.chat import ChatLog, ChatRequest, ChatSession, ExecutionSession, ExecutionStep
from services.execution_tracer import ExecutionTracerService
from services.logger import LoggerService


@pytest.mark.unit
@pytest.mark.anyio
async def test_recent_errors_includes_chat_log_errors(db_session: AsyncSession):
    logger = LoggerService(db_session)
    chat = await logger.create_or_update_chat_session(
        session_id="monitor-test-session-1",
        user_id=10,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        mode="mixed",
    )
    request = await logger.create_chat_request(
        session_id="monitor-test-session-1",
        chat_session_id=chat.id,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        message="Какие дедлайны?",
        intent="deadline",
    )
    await logger.create_chat_log(
        request_id=request.id,
        answer="",
        sources=[],
        llm_model="gpt-4o-mini",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        latency_ms=0,
        error="LLM timeout",
    )

    errors = await _recent_errors(db_session, limit=10)
    assert any(
        e["source"] == "chat_log" and e["session_id"] == "monitor-test-session-1"
        for e in errors
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_recent_errors_includes_execution_step_warnings(db_session: AsyncSession):
    tracer = ExecutionTracerService(db_session)
    chat = await tracer.get_or_create_chat_session(
        session_id="monitor-test-session-2",
        user_id=10,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        mode="mixed",
    )
    exec_session = await tracer.start_execution_session(
        chat.id,
        client_ip="127.0.0.1",
        provider_key="openai",
        model_name="gpt-4o-mini",
    )
    await tracer.add_execution_steps(
        exec_session.id,
        [
            {
                "stage_name": "lms_fetch",
                "step_order": 2,
                "status": "warning",
                "duration_ms": 100,
                "step_metadata": {
                    "errors": [{"type": "deadlines", "error": "LMS unreachable"}]
                },
            },
        ],
    )
    await tracer.finish_execution_session(exec_session.id, "ok", duration_ms=100)

    errors = await _recent_errors(db_session, limit=10)
    step_errors = [e for e in errors if e["source"] == "execution_step"]
    assert any(
        e["session_id"] == "monitor-test-session-2"
        and e["stage_name"] == "lms_fetch"
        and "LMS unreachable" in e["error"]
        for e in step_errors
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_recent_errors_includes_execution_session_errors(db_session: AsyncSession):
    tracer = ExecutionTracerService(db_session)
    chat = await tracer.get_or_create_chat_session(
        session_id="monitor-test-session-3",
        user_id=10,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        mode="mixed",
    )
    exec_session = await tracer.start_execution_session(
        chat.id,
        client_ip="127.0.0.1",
        provider_key="openai",
        model_name="gpt-4o-mini",
    )
    await tracer.finish_execution_session(
        exec_session.id,
        "error",
        duration_ms=0,
        execution_metadata={"error": "OpenAI API key expired"},
    )

    errors = await _recent_errors(db_session, limit=10)
    assert any(
        e["source"] == "execution_session"
        and e["session_id"] == "monitor-test-session-3"
        and "OpenAI API key expired" in e["error"]
        for e in errors
    )


@pytest.mark.unit
@pytest.mark.anyio
async def test_recent_errors_deduplicates_similar_entries(db_session: AsyncSession):
    logger = LoggerService(db_session)
    chat = await logger.create_or_update_chat_session(
        session_id="monitor-test-session-4",
        user_id=10,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        mode="mixed",
    )

    for _ in range(3):
        request = await logger.create_chat_request(
            session_id="monitor-test-session-4",
            chat_session_id=chat.id,
            role="active_student",
            course_id=3,
            difficulty="beginner",
            message="Какие дедлайны?",
            intent="deadline",
        )
        await logger.create_chat_log(
            request_id=request.id,
            answer="",
            sources=[],
            llm_model="gpt-4o-mini",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            error="Same error message",
        )

    errors = await _recent_errors(db_session, limit=10)
    session_errors = [e for e in errors if e["session_id"] == "monitor-test-session-4"]
    # All three share the same session_id + stage_name (None) + truncated error,
    # so only one should survive deduplication.
    assert len(session_errors) == 1
