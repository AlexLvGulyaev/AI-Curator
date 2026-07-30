"""Tests for LLM chat endpoint and orchestrator components."""

from unittest.mock import AsyncMock, patch

import pytest

from services.answer_validator import AnswerValidator
from services.orchestrator import Orchestrator


@pytest.mark.anyio
async def test_chat_endpoint_organizational(client):
    """Chat endpoint returns answer with LMS sources for organizational intent."""
    with patch(
        "services.orchestrator.lms_adapter.get_course_deadlines",
        new=AsyncMock(return_value=[]),
    ), patch(
        "services.orchestrator.lms_adapter.get_user_course_progress",
        new=AsyncMock(return_value={
            "user_id": 3,
            "course_id": 3,
            "completion_status": "in_progress",
            "grade_items": [],
        }),
    ), patch(
        "services.llm_adapter.ChatOpenAI.ainvoke",
        new=AsyncMock(return_value=type("R", (), {
            "content": "Дедлайн по заданию — 5 августа.",
            "response_metadata": {"model_name": "gpt-4o-mini", "token_usage": {}},
        })()),
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
            assert data["intent"] == "organizational"
            assert data["model"] == "gpt-4o-mini"


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


def test_detect_intent():
    assert Orchestrator.detect_intent("Какие дедлайны?") == "organizational"
    assert Orchestrator.detect_intent("Объясни промпты") == "study"
    assert Orchestrator.detect_intent("Когда сдача лекции?") == "mixed"


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
