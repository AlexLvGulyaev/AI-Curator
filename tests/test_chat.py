"""Tests for LLM chat endpoint and orchestrator components."""

from unittest.mock import AsyncMock, patch

import pytest

from services.answer_validator import AnswerValidator
from services.orchestrator import Orchestrator


@pytest.mark.anyio
async def test_chat_endpoint_deadline(client):
    """Chat endpoint returns deterministic answer for deadline intent."""
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
            assert "answer" in data
            assert data["intent"] == "deadline"
            assert data["model"] is None
            assert "2026-08-05" in data["answer"]




@pytest.mark.anyio
async def test_chat_endpoint_study(client, tmp_path):
    """Chat endpoint returns answer with KB sources for study intent."""
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
                    "message": "Что такое промпт-инжиниринг?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "study"
            assert any(s["type"] == "kb" for s in data["sources"])


@pytest.mark.anyio
async def test_chat_endpoint_study_uses_generic_kb_without_course_filter(client, tmp_path):
    """Study questions retrieve KB materials even if their course_id does not match."""
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
                    "title": "Generic Prompt Engineering",
                    "document_type": "lecture",
                    # Explicitly different course_id from the student's current course.
                    "course_id": 99,
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
                    "message": "Что такое промпт-инжиниринг?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "study"
            assert any(s["type"] == "kb" for s in data["sources"])


def test_detect_intent():
    assert Orchestrator.detect_intent("Какие дедлайны?") == "deadline"
    assert Orchestrator.detect_intent("Когда сдать задание?") == "deadline"
    assert Orchestrator.detect_intent("Объясни промпты") == "study"
    assert Orchestrator.detect_intent("Когда сдача лекции?") == "mixed"
    assert Orchestrator.detect_intent("Сколько уроков?") == "organizational"
    assert Orchestrator.detect_intent("Сколько модулей?") == "organizational"
    assert Orchestrator.detect_intent("Структура курса") == "mixed"


def test_detect_intent_with_config():
    """detect_intent respects keywords and conditions from orchestrator config."""
    ocfg = {
        "intent_rules": {
            "deadline": {"keywords": ["дедлайн"], "priority": 1},
            "progress": {"keywords": ["прошёл"], "priority": 2},
            "study": {"keywords": ["объясни"], "priority": 3},
            "mixed": {
                "conditions": [
                    ["is_org", "has_keyword", ["итоговый проект"]],
                ],
                "priority": 4,
            },
            "organizational": {
                "keywords": ["о чём"],
                "conditions": [["is_org"]],
                "priority": 5,
            },
        },
        "default_intent": "study",
    }
    assert Orchestrator.detect_intent("Какие дедлайны?", ocfg=ocfg) == "deadline"
    assert Orchestrator.detect_intent("о чём будет итоговый проект", ocfg=ocfg) == "mixed"


@pytest.mark.anyio
async def test_chat_creates_canonical_session_and_execution_trace(client):
    """A chat request populates chat_sessions and execution_sessions."""
    from datetime import datetime, timezone
    from adapters.lms_adapter import Deadline

    deadline = Deadline(
        id=1,
        course_id=3,
        module_id=10,
        instance_id=1,
        name="ДЗ: Трассировка",
        modname="assign",
        due_date=datetime(2026, 8, 10, 18, 49, 57, tzinfo=timezone.utc),
        url="https://lms.example.com/mod/assign/view.php?id=11",
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
                    "message": "Когда сдать задание?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]

            detail = await client.get(f"/api/v1/admin/dialog-sessions/{session_id}")
            assert detail.status_code == 200
            payload = detail.json()
            assert payload["session_id"] == session_id
            assert payload["mode"] == "lms"
            assert payload["execution_sessions"]
            exec_session = payload["execution_sessions"][0]
            assert exec_session["status"] == "ok"
            stage_names = [step["stage_name"] for step in exec_session["steps"]]
            assert "intent_classify" in stage_names
            assert "lms_fetch" in stage_names
            assert "context_build" in stage_names
            assert "response_save" in stage_names


def test_answer_validator_accepts_valid():
    validator = AnswerValidator("Ответ с источником", [{"type": "kb"}], True)
    result = validator.validate()
    assert result.is_valid
    assert not result.fallback


def test_answer_validator_rejects_empty():
    validator = AnswerValidator("", [], True)
    result = validator.validate()
    assert not result.is_valid
    assert result.fallback


def test_answer_validator_sanitizes_fake_links():
    validator = AnswerValidator(
        "Курс посвящён Claude Code. [Фрагмент 1](84) [Фрагмент 2](95)",
        [{"type": "kb"}],
        True,
    )
    result = validator.validate()
    assert "Курс посвящён Claude Code" in result.answer
    assert "[Фрагмент 1](84)" not in result.answer
