"""Tests for Admin Console authentication and read-only demo role."""

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from main import app

pytestmark = pytest.mark.anyio

ADMIN_TOKEN = "test_admin_token_12345"
DEMO_TOKEN = "test_demo_token_12345"


@pytest.fixture
def override_tokens(monkeypatch):
    """Temporarily set admin and demo tokens for the duration of a test."""
    monkeypatch.setattr(settings, "admin_console_token", ADMIN_TOKEN)
    monkeypatch.setattr(settings, "admin_console_demo_token", DEMO_TOKEN)


@pytest.fixture
async def authed_client(override_tokens):
    """Return an AsyncClient with admin auth enabled (tokens set)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestDemoReadOnly:
    """Demo token should have read access but cannot mutate state."""

    async def test_demo_can_access_monitoring(self, authed_client):
        response = await authed_client.get(
            "/api/v1/admin/monitoring/status",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "components" in data

    async def test_demo_cannot_create_ai_config(self, authed_client):
        payload = {
            "name": "Demo blocked",
            "system_prompt": "test",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        response = await authed_client.post(
            "/api/v1/admin/ai-config",
            json=payload,
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_update_orchestrator_config(self, authed_client):
        response = await authed_client.put(
            "/api/v1/admin/orchestrator/config",
            json={"default_intent": "study"},
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_upload_kb_document(self, authed_client):
        response = await authed_client.post(
            "/api/v1/admin/kb/documents",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_reindex_knowledge_base(self, authed_client):
        response = await authed_client.post(
            "/api/v1/admin/retrieval/reindex",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_test_llm_provider(self, authed_client):
        response = await authed_client.post(
            "/api/v1/admin/llm-providers/openai/test",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_reindex_kb_document(self, authed_client):
        response = await authed_client.post(
            "/api/v1/admin/kb/documents/1/reindex",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()

    async def test_demo_cannot_reindex_all_kb_documents(self, authed_client):
        response = await authed_client.post(
            "/api/v1/admin/kb/reindex-all",
            headers={"Authorization": f"Bearer {DEMO_TOKEN}"},
        )
        assert response.status_code == 403
        assert "read-only" in response.json()["detail"].lower()


class TestAdminMutations:
    """Full admin token should still be able to perform mutations."""

    async def test_admin_can_create_ai_config(self, authed_client):
        payload = {
            "name": "Admin created",
            "system_prompt": "You are a helpful assistant.",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 1024,
            "active_provider": "openai",
            "fallback_provider": "gigachat",
        }
        response = await authed_client.post(
            "/api/v1/admin/ai-config",
            json=payload,
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Admin created"
        assert data["created_by"] == "admin"

    async def test_invalid_token_rejected(self, authed_client):
        response = await authed_client.get(
            "/api/v1/admin/monitoring/status",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 403
