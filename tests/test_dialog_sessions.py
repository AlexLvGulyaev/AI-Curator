"""Tests for Dialog Sessions admin API."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.anyio
async def test_dialog_sessions_list_and_filters(client):
    """Dialog sessions list returns canonical sessions with pagination."""
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
            chat_response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "Какие дедлайны?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert chat_response.status_code == 200
            session_id = chat_response.json()["session_id"]

            list_response = await client.get("/api/v1/admin/dialog-sessions")
            assert list_response.status_code == 200
            data = list_response.json()
            assert "items" in data
            assert "total" in data
            assert any(item["session_id"] == session_id for item in data["items"])

            filtered_response = await client.get(
                f"/api/v1/admin/dialog-sessions?mode=lms&hours=1"
            )
            assert filtered_response.status_code == 200
            filtered = filtered_response.json()
            assert any(item["session_id"] == session_id for item in filtered["items"])


@pytest.mark.anyio
async def test_dialog_session_detail(client):
    """Detail endpoint returns turns, execution timeline and budget."""
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
            chat_response = await client.post(
                "/api/v1/chat",
                json={
                    "message": "Какие дедлайны?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
            )
            assert chat_response.status_code == 200
            session_id = chat_response.json()["session_id"]

            detail_response = await client.get(
                f"/api/v1/admin/dialog-sessions/{session_id}"
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["session_id"] == session_id
            assert "turns" in detail
            assert detail["turns"]
            assert "execution_sessions" in detail
            assert detail["execution_sessions"]
            assert "budget" in detail
            assert detail["memory_source"] == "PostgreSQL"

            for turn in detail["turns"]:
                assert "user_message" in turn
                assert "assistant_answer" in turn


@pytest.mark.anyio
async def test_dialog_session_not_found(client):
    async with client:
        response = await client.get("/api/v1/admin/dialog-sessions/non-existent-session")
        assert response.status_code == 404
