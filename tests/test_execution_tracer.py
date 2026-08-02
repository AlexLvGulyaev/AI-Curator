"""Tests for execution tracing service and schema."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import ChatSession, ExecutionSession, ExecutionStep
from services.execution_tracer import ExecutionTracerService


@pytest.mark.unit
@pytest.mark.anyio
async def test_tracer_creates_chat_session(db_session: AsyncSession):
    tracer = ExecutionTracerService(db_session)
    session = await tracer.get_or_create_chat_session(
        "test-session-1",
        user_id=10,
        role="active_student",
        course_id=3,
        difficulty="beginner",
        mode="mixed",
    )
    assert session.id is not None
    assert session.session_id == "test-session-1"
    assert session.mode == "mixed"

    # Second call with same session_id updates fields.
    updated = await tracer.get_or_create_chat_session(
        "test-session-1",
        mode="rag",
    )
    assert updated.id == session.id
    assert updated.mode == "rag"


@pytest.mark.unit
@pytest.mark.anyio
async def test_tracer_execution_session_lifecycle(db_session: AsyncSession):
    tracer = ExecutionTracerService(db_session)
    chat = await tracer.get_or_create_chat_session("test-session-2")
    exec_session = await tracer.start_execution_session(
        chat.id,
        route="mixed",
        client_ip="127.0.0.1",
        provider_key="openai",
        model_name="gpt-4o-mini",
    )
    assert exec_session.status == "started"
    assert exec_session.chat_session_id == chat.id

    steps = [
        {"stage_name": "intent_classify", "step_order": 1, "duration_ms": 12},
        {"stage_name": "rag_search", "step_order": 2, "duration_ms": 45, "step_metadata": {"chunks_count": 3}},
        {"stage_name": "llm_call", "step_order": 3, "duration_ms": 120},
    ]
    created_steps = await tracer.add_execution_steps(exec_session.id, steps)
    assert len(created_steps) == 3

    finished = await tracer.finish_execution_session(
        exec_session.id,
        "ok",
        duration_ms=177,
        execution_metadata={"route": "mixed"},
    )
    assert finished.status == "ok"
    assert finished.duration_ms == 177


@pytest.mark.integration
@pytest.mark.anyio
async def test_chat_endpoint_creates_execution_trace(client):
    """A real chat request creates ChatSession and ExecutionSession rows."""
    from datetime import datetime, timezone
    from adapters.lms_adapter import Deadline

    deadline = Deadline(
        id=1,
        course_id=3,
        module_id=10,
        instance_id=1,
        name="ДЗ: Пример",
        modname="assign",
        due_date=datetime(2026, 8, 5, 18, 49, 57, tzinfo=timezone.utc),
        url="https://lms.example.com/mod/assign/view.php?id=10",
    )

    with patch(
        "services.orchestrator.lms_adapter.get_course_deadlines",
        new=AsyncMock(return_value=[deadline]),
    ), patch(
        "services.orchestrator.lms_adapter.get_user_course_progress",
        new=AsyncMock(return_value={
            "user_id": 3,
            "course_id": 3,
            "completion_status": "in_progress",
            "grade_items": [],
        }),
    ), patch(
        "services.orchestrator.lms_adapter.get_course_contents",
        new=AsyncMock(return_value=[]),
    ):
        async with client:
            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "Какие дедлайны?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]

            dialog_response = await client.get(
                f"/api/v1/admin/dialog-sessions/{session_id}"
            )
            assert dialog_response.status_code == 200
            detail = dialog_response.json()
            assert detail["session_id"] == session_id
            assert detail["mode"] == "lms"
            assert detail["execution_sessions"]
            exec_session = detail["execution_sessions"][0]
            assert exec_session["status"] == "ok"
            stage_names = [step["stage_name"] for step in exec_session["steps"]]
            assert "intent_classify" in stage_names
            assert "lms_fetch" in stage_names
            assert "response_save" in stage_names


@pytest.mark.integration
@pytest.mark.anyio
async def test_chat_endpoint_study_creates_mixed_trace(client, tmp_path):
    """A mixed question creates a trace with RAG and LMS steps."""
    from unittest.mock import AsyncMock

    content = (
        "# Промпт-инжиниринг\n\n"
        "Промпт-инжиниринг — это процесс составления эффективных запросов к языковым моделям."
    )
    file_path = tmp_path / "prompts.md"
    file_path.write_text(content, encoding="utf-8")

    with patch(
        "services.llm_adapter.ChatOpenAI.ainvoke",
        new=AsyncMock(return_value=type("R", (), {
            "content": "Промпт-инжиниринг — это составление запросов к LLM.",
            "response_metadata": {"model_name": "gpt-4o-mini", "token_usage": {}},
        })()),
    ):
        async with client:
            create_response = await client.post(
                "/api/v1/admin/kb/documents",
                data={
                    "title": "Prompt Engineering",
                    "document_type": "lecture",
                    "course_id": 3,
                    "difficulty": "beginner",
                },
                files={"file": ("prompts.md", file_path.read_bytes(), "text/markdown")},
            )
            assert create_response.status_code == 201
            doc_id = create_response.json()["id"]

            await client.post(f"/api/v1/admin/kb/documents/{doc_id}/publish?publish=true")
            process_response = await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
            assert process_response.status_code == 200

            response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "Расскажи про промпт-инжиниринг и сколько модулей в курсе?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]
            assert data["intent"] == "mixed"

            detail_response = await client.get(
                f"/api/v1/admin/dialog-sessions/{session_id}"
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["mode"] == "mixed"
            exec_session = detail["execution_sessions"][0]
            stage_names = [step["stage_name"] for step in exec_session["steps"]]
            assert "lms_fetch" in stage_names
            assert "rag_search" in stage_names
            assert "llm_call" in stage_names
            assert "answer_validate" in stage_names
