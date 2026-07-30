"""Async SQLAlchemy database setup for AI Curator backend."""

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    # NullPool avoids "another operation is in progress" errors with asyncpg
    # when running tests through ASGITransport. Each request gets a fresh
    # connection; for the current workload this is acceptable.
    poolclass=pool.NullPool,
)

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
