"""Tests for analytics admin endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from db import engine

pytestmark = pytest.mark.unit


@pytest.fixture
async def clean_chat_tables():
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE chat_requests, chat_logs, analytics_events, audit_logs, llm_calls RESTART IDENTITY CASCADE"))
    yield


@pytest.mark.anyio
async def test_analytics_dashboard_empty(client, clean_chat_tables):
    async with client:
        response = await client.get("/api/v1/admin/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["unanswered_count"] == 0


