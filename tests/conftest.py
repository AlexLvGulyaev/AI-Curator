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
