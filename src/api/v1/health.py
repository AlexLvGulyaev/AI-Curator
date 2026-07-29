"""Health check endpoints for AI Curator backend."""

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from adapters.lms_adapter import lms_adapter
from config import settings
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
        return {"status": "ok", "database": "connected", "result": result.scalar()}
    except Exception as exc:
        return {"status": "error", "database": "disconnected", "detail": str(exc)}


@router.get("/lms", status_code=status.HTTP_200_OK)
async def health_lms():
    """Check LMS connectivity through the LMS Adapter."""
    result = await lms_adapter.health_check()
    if result.status != "ok":
        return {
            "status": "error",
            "lms": "disconnected",
            "detail": result.detail,
            "response_time_ms": result.response_time_ms,
        }
    return {
        "status": "ok",
        "lms": "connected",
        "response_time_ms": result.response_time_ms,
    }


@router.get("/chroma", status_code=status.HTTP_200_OK)
async def health_chroma():
    """Check Chroma vector store connectivity.

    Uses the Chroma v2 heartbeat endpoint directly because the installed
    chromadb client (0.5.3) targets the deprecated v1 API. This is sufficient
    for a health check; the RAG pipeline will handle client compatibility
    separately on Day 4.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
            )
            response.raise_for_status()
            heartbeat = response.json()
        return {
            "status": "ok",
            "chroma": "connected",
            "heartbeat": heartbeat.get("nanosecond heartbeat"),
        }
    except Exception as exc:
        return {
            "status": "error",
            "chroma": "disconnected",
            "detail": str(exc),
        }
