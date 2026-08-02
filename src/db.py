"""Async SQLAlchemy database setup for AI Curator backend."""

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings


def make_engine(database_url: str | None = None, **kwargs):
    """Create an async SQLAlchemy engine for the given (or configured) URL."""
    url = database_url or settings.database_url
    return create_async_engine(
        url,
        echo=kwargs.get("echo", settings.debug),
        future=True,
        # NullPool avoids "another operation is in progress" errors with asyncpg
        # when running tests through ASGITransport. Each request gets a fresh
        # connection; for the current workload this is acceptable.
        poolclass=pool.NullPool,
    )


engine = make_engine()

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Factory alias used by background tasks.
async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncSession:
    """Yield an async database session for FastAPI dependency injection."""
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
