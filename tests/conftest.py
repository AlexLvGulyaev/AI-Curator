"""Shared pytest configuration and fixtures."""

import asyncio
import os
import sys
import warnings
from pathlib import Path
from urllib.parse import urlparse

# Ensure `src` is importable regardless of how pytest is invoked.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings

# ------------------------------------------------------------------
# Test database resolution
# ------------------------------------------------------------------

def _resolve_test_database_url() -> str:
    """Return the database URL tests should use.

    Prefers TEST_DATABASE_URL. If it is missing, falls back to DATABASE_URL only
    when PYTEST_ALLOW_PROD_DB is true. This prevents accidental test runs against
    the production database.
    """
    test_url = settings.test_database_url
    if test_url:
        return test_url
    if settings.pytest_allow_prod_db:
        warnings.warn(
            "TEST_DATABASE_URL is not set; falling back to DATABASE_URL (production).",
            stacklevel=2,
        )
        return settings.database_url
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured. Set TEST_DATABASE_URL to a dedicated "
        "test database, or set PYTEST_ALLOW_PROD_DB=true to intentionally use the "
        "production database for tests."
    )


TEST_DATABASE_URL = _resolve_test_database_url()


async def _ensure_test_database_exists() -> None:
    """Create the test database if it does not already exist."""
    parsed = urlparse(TEST_DATABASE_URL)
    db_name = parsed.path.lstrip("/") or "ai_curator_test"
    port = parsed.port or 5432
    admin_url = (
        f"{parsed.scheme}://{parsed.username}:{parsed.password}"
        f"@{parsed.hostname}:{port}/postgres"
    )
    engine_admin = create_async_engine(
        admin_url,
        poolclass=pool.NullPool,
        future=True,
        isolation_level="AUTOCOMMIT",
    )
    async with engine_admin.connect() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name},
        )
        exists = result.scalar() == 1
        if not exists:
            # PostgreSQL does not support parameterized CREATE DATABASE.
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await engine_admin.dispose()


def _run_alembic_migrations() -> None:
    """Apply Alembic migrations to the test database.

    Runs in a worker thread so that Alembic's internal asyncio.run() does not
    conflict with the event loop of the async test engine fixture.
    """
    from alembic import command
    from alembic.config import Config

    original_url = settings.database_url
    try:
        settings.database_url = TEST_DATABASE_URL
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    finally:
        settings.database_url = original_url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
async def test_engine():
    """Create the test database, apply migrations, and yield an async engine."""
    await _ensure_test_database_exists()
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_alembic_migrations)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Yield a transactional async session rolled back after each test."""
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        yield session
        await session.close()
        await trans.rollback()


# ------------------------------------------------------------------
# Patch the db module BEFORE importing the FastAPI application.
# This ensures main.py lifespan and background tasks use the test DB.
# ------------------------------------------------------------------

import db as db_module  # noqa: E402
from db import get_db  # noqa: E402

_db_module_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=pool.NullPool,
    future=True,
)
db_module.engine = _db_module_engine
db_module.AsyncSessionLocal = sessionmaker(
    bind=_db_module_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
db_module.async_session_factory = db_module.AsyncSessionLocal

from main import app  # noqa: E402

# ------------------------------------------------------------------
# FastAPI client and dependency overrides
# ------------------------------------------------------------------


@pytest.fixture
def client():
    """Return an AsyncClient for the FastAPI app. Tests must wrap it in async with."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
async def override_get_db(db_session):
    """Route FastAPI dependency get_db through the transactional test session."""
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def reset_response_cache():
    """Clear the global response cache before every test to avoid cross-test leaks."""
    from services.cache import response_cache
    response_cache.clear()
    yield


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


# ------------------------------------------------------------------
# External service isolation
# ------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def test_chroma_collection():
    """Redirect all RAG/Chroma operations to a dedicated test collection.

    This is an autouse session fixture. If Chroma is unreachable, we emit a
    warning and continue so that pure unit tests can still run in environments
    where Chroma is not locally exposed (e.g. a developer laptop without the
    docker proxy). Integration tests that actually need Chroma will fail later
    with a clear error.
    """
    from services.rag_pipeline import RagPipeline

    original_collection = settings.chroma_collection_name
    test_collection = settings.chroma_test_collection_name
    settings.chroma_collection_name = test_collection

    # Reset the test collection so previous test runs do not leak into this one.
    try:
        rag = RagPipeline(collection_name=test_collection)
        rag.client.delete_collection(name=test_collection)
    except Exception as exc:  # pragma: no cover
        warnings.warn(
            f"Could not reset Chroma test collection {test_collection}: {exc}",
            stacklevel=2,
        )

    yield

    settings.chroma_collection_name = original_collection
