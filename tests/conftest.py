"""Shared pytest configuration and fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
def client():
    """Return an AsyncClient for the FastAPI app. Tests must wrap it in async with."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def anyio_backend():
    """Use asyncio as the anyio backend for tests."""
    return "asyncio"
