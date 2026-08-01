"""Shared pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from config import settings
from main import app


@pytest.fixture
def client():
    """Return an AsyncClient for the FastAPI app. Tests must wrap it in async with."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def disable_admin_auth():
    """Disable admin bearer auth in tests to keep fixtures simple."""
    original = settings.admin_console_token
    settings.admin_console_token = ""
    yield
    settings.admin_console_token = original


@pytest.fixture
def anyio_backend():
    """Use asyncio as the anyio backend for tests."""
    return "asyncio"


@pytest.fixture(autouse=True)
async def reset_orchestrator_config_after_test():
    """Restore default orchestrator config after every test."""
    from models.orchestrator_config import (
        DEFAULT_FALLBACK_MESSAGES,
        DEFAULT_INTENT_MAX_TOKENS,
        DEFAULT_INTENT_RULES,
        DEFAULT_INTENT_SOURCE_MAP,
        DEFAULT_NON_COURSE_STARTERS,
    )
    yield
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.put(
            "/api/v1/admin/orchestrator/config",
            json={
                "intent_rules": dict(DEFAULT_INTENT_RULES),
                "default_intent": "study",
                "intent_source_map": dict(DEFAULT_INTENT_SOURCE_MAP),
                "non_course_starters": list(DEFAULT_NON_COURSE_STARTERS),
                "max_lms_contents": 12,
                "max_lms_deadlines": 5,
                "intent_max_tokens": dict(DEFAULT_INTENT_MAX_TOKENS),
                "fallback_messages": dict(DEFAULT_FALLBACK_MESSAGES),
            },
        )
