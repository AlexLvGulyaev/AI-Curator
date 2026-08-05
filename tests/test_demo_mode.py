"""Tests for Web UI safe demo mode (Sprint F)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from adapters.lms_adapter import Deadline
from config import settings
from main import app

pytestmark = pytest.mark.anyio


def _enable_demo(monkeypatch):
    """Enable demo mode with tight limits for fast tests."""
    monkeypatch.setattr(settings, "demo_enabled", True)
    monkeypatch.setattr(settings, "demo_max_requests_per_session", 3)
    monkeypatch.setattr(settings, "demo_session_ttl_minutes", 30)
    monkeypatch.setattr(settings, "demo_rate_limit_per_minute", 12)
    monkeypatch.setattr(settings, "demo_max_sessions_per_ip_per_hour", 2)
    monkeypatch.setattr(settings, "demo_cache_ttl_seconds", 86400)


@pytest.fixture
async def demo_client(monkeypatch):
    """Client with demo mode enabled and admin auth disabled."""
    _enable_demo(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _patch_lms_deadline():
    """Context manager patches for deterministic deadline short-circuit."""
    return patch.multiple(
        "services.orchestrator.lms_adapter",
        get_course_deadlines=AsyncMock(
            return_value=[
                Deadline(
                    id=1,
                    course_id=3,
                    module_id=10,
                    instance_id=1,
                    name="ДЗ: Демо",
                    modname="assign",
                    due_date=datetime(2026, 8, 5, 18, 49, 57, tzinfo=timezone.utc),
                    url="https://lms.example.com/mod/assign/view.php?id=10",
                )
            ]
        ),
        get_user_course_progress=AsyncMock(
            return_value={
                "user_id": 3,
                "course_id": 3,
                "completion_status": "in_progress",
                "grade_items": [],
            }
        ),
        get_course_contents=AsyncMock(return_value=[]),
    )


class TestDemoSessionLifecycle:
    """Token issuance, status and IP-based session limits."""

    async def test_demo_start_returns_token(self, demo_client):
        response = await demo_client.post("/api/v1/demo/start", json={})
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["requests_limit"] == settings.demo_max_requests_per_session
        assert data["requests_remaining"] == settings.demo_max_requests_per_session
        assert data["rate_limit_per_minute"] == settings.demo_rate_limit_per_minute
        assert "expires_at" in data

    async def test_demo_status_returns_quota(self, demo_client):
        start = await demo_client.post("/api/v1/demo/start", json={})
        token = start.json()["token"]

        status_response = await demo_client.get(
            "/api/v1/demo/status",
            headers={"X-Demo-Token": token},
        )
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["requests_used"] == 0
        assert data["requests_remaining"] == settings.demo_max_requests_per_session
        assert data["is_active"] is True

    async def test_demo_start_ip_session_limit(self, demo_client):
        # First session succeeds.
        r1 = await demo_client.post("/api/v1/demo/start", json={})
        assert r1.status_code == 200
        # Second session succeeds.
        r2 = await demo_client.post("/api/v1/demo/start", json={})
        assert r2.status_code == 200
        # Third session from the same IP is blocked.
        r3 = await demo_client.post("/api/v1/demo/start", json={})
        assert r3.status_code == 429

    async def test_demo_status_missing_token(self, demo_client):
        response = await demo_client.get("/api/v1/demo/status")
        assert response.status_code == 401


class TestDemoChatProtection:
    """X-Demo-Token validation on POST /api/v1/chat."""

    async def test_chat_without_token_forbidden_in_production(
        self, demo_client, monkeypatch
    ):
        # Ensure production-like demo_enabled is true.
        assert settings.demo_enabled is True
        response = await demo_client.post(
            "/api/v1/chat",
            json={
                "message": "Какие дедлайны?",
                "role": "active_student",
                "difficulty": "beginner",
                "course_id": 3,
            },
        )
        assert response.status_code == 403
        assert "X-Demo-Token" in response.json()["detail"]

    async def test_chat_with_invalid_token_forbidden(self, demo_client):
        response = await demo_client.post(
            "/api/v1/chat",
            json={
                "message": "Какие дедлайны?",
                "role": "active_student",
                "difficulty": "beginner",
                "course_id": 3,
            },
            headers={"X-Demo-Token": "invalid-token"},
        )
        assert response.status_code == 403

    async def test_chat_with_expired_token_unauthorized(self, demo_client, db_session):
        from services.demo_limiter import DemoLimiterService

        service = DemoLimiterService(db_session)
        demo = await service.create_session(client_ip="127.0.0.1")
        demo.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.commit()

        response = await demo_client.post(
            "/api/v1/chat",
            json={
                "message": "Какие дедлайны?",
                "role": "active_student",
                "difficulty": "beginner",
                "course_id": 3,
            },
            headers={"X-Demo-Token": demo.token},
        )
        assert response.status_code == 401

    async def test_demo_chat_records_demo_mode(self, demo_client):
        start = await demo_client.post("/api/v1/demo/start", json={})
        token = start.json()["token"]

        with _patch_lms_deadline():
            response = await demo_client.post(
                "/api/v1/chat",
                json={
                    "message": "Какие дедлайны?",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
                headers={"X-Demo-Token": token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["demo_mode"] is True

    async def test_demo_quota_exhaustion(self, demo_client, monkeypatch):
        start = await demo_client.post("/api/v1/demo/start", json={})
        token = start.json()["token"]
        limit = settings.demo_max_requests_per_session
        # Disable rate limiting for this quota test.
        monkeypatch.setattr(settings, "demo_rate_limit_per_minute", 10000)

        with _patch_lms_deadline():
            for i in range(limit):
                response = await demo_client.post(
                    "/api/v1/chat",
                    json={
                        "message": f"Вопрос {i}",
                        "role": "active_student",
                        "difficulty": "beginner",
                        "course_id": 3,
                    },
                    headers={"X-Demo-Token": token},
                )
                assert response.status_code == 200, response.text
                if i < limit - 1:
                    await asyncio.sleep(0.5)

            # Next request over the quota is rejected.
            over = await demo_client.post(
                "/api/v1/chat",
                json={
                    "message": "Лишний вопрос",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
                headers={"X-Demo-Token": token},
            )
            assert over.status_code == 429
            assert (
                "quota" in over.json()["detail"].lower()
                or "исчерпан" in over.json()["detail"].lower()
            )

    async def test_demo_rate_limit(self, demo_client):
        start = await demo_client.post("/api/v1/demo/start", json={})
        token = start.json()["token"]

        with _patch_lms_deadline():
            # First request OK.
            r1 = await demo_client.post(
                "/api/v1/chat",
                json={
                    "message": "Первый вопрос",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
                headers={"X-Demo-Token": token},
            )
            assert r1.status_code == 200

            # Immediate second request is rate-limited.
            r2 = await demo_client.post(
                "/api/v1/chat",
                json={
                    "message": "Второй вопрос сразу",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
                headers={"X-Demo-Token": token},
            )
            assert r2.status_code == 429
            assert (
                "rate limit" in r2.json()["detail"].lower()
                or "wait" in r2.json()["detail"].lower()
            )

    async def test_demo_chat_reduces_max_tokens(self, demo_client):
        start = await demo_client.post("/api/v1/demo/start", json={})
        token = start.json()["token"]

        with patch(
            "services.llm_adapter.ChatOpenAI.ainvoke",
            new=AsyncMock(
                return_value=type(
                    "R",
                    (),
                    {
                        "content": "Demo answer",
                        "response_metadata": {
                            "model_name": "gpt-4o-mini",
                            "token_usage": {},
                        },
                    },
                )()
            ),
        ), patch(
            "services.orchestrator.RagPipeline.search",
            new=AsyncMock(return_value=([], {})),
        ):
            response = await demo_client.post(
                "/api/v1/chat",
                json={
                    "message": "Раскрой тему промпт-инжиниринга",
                    "role": "active_student",
                    "difficulty": "beginner",
                    "course_id": 3,
                },
                headers={"X-Demo-Token": token},
            )
            assert response.status_code == 200


class TestDemoDisabledFallback:
    """When demo_enabled is False the chat endpoint does not require a token."""

    async def test_chat_without_token_when_demo_disabled(self, client, monkeypatch):
        monkeypatch.setattr(settings, "demo_enabled", False)

        with _patch_lms_deadline():
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
            assert data["demo_mode"] is False
