"""Health check endpoints for AI Curator backend."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from db import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic liveness probe."""
    return {"status": "ok", "service": "ai-curator-backend"}


@router.get("/db", status_code=status.HTTP_200_OK)
async def health_db(db: AsyncSession = Depends(get_db)):
    """Check PostgreSQL connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        await db.commit()
        return {"status": "ok", "database": "connected", "result": result.scalar()}
    except Exception as exc:
        return {"status": "error", "database": "disconnected", "detail": str(exc)}
