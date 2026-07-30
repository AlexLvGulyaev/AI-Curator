"""Tests for analytics admin endpoints."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.anyio
async def test_analytics_dashboard_empty(client):
    async with client:
        response = await client.get("/api/v1/admin/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["unanswered_count"] == 0


@pytest.mark.anyio
async def test_analytics_dashboard_after_chat(client):
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
            "content": "Тестовый ответ.",
            "response_metadata": {"model_name": "gpt-4o-mini", "token_usage": {}},
        })()),
    ):
        async with client:
            await client.post(
                "/api/v1/chat",
                json={
                    "message": "Какие дедлайны?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            response = await client.get("/api/v1/admin/analytics/dashboard")
            data = response.json()
            assert data["total_requests"] == 1
            assert data["total_answers"] == 1
