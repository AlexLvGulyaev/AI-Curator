"""Admin endpoints for system monitoring."""

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.lms_adapter import lms_adapter
from db import get_db
from services.chroma_client import get_chroma_client
from services.logger import LoggerService

router = APIRouter(prefix="/monitoring", tags=["admin-monitoring"])


async def _log_audit(action: str, db):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="monitoring",
        user_id="admin",
        user_role="admin",
    )


@router.get("/status")
async def monitoring_status(db: AsyncSession = Depends(get_db)):
    await _log_audit("view_status", db)
    """Return health and latency for each integrated component."""
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
        db_detail = None
    except Exception as exc:
        db_status = "error"
        db_detail = str(exc)
    db_latency = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    try:
        lms_health = await lms_adapter.health_check()
        lms_status = lms_health.status
        lms_detail = lms_health.detail
        lms_latency = lms_health.response_time_ms
    except Exception as exc:
        lms_status = "error"
        lms_detail = str(exc)
        lms_latency = round((time.perf_counter() - start) * 1000, 2)

    start = time.perf_counter()
    try:
        client = get_chroma_client()
        client.heartbeat()
        chroma_status = "ok"
        chroma_detail = None
    except Exception as exc:
        chroma_status = "error"
        chroma_detail = str(exc)
    chroma_latency = round((time.perf_counter() - start) * 1000, 2)

    llm_status = "ok"
    llm_detail = "Configuration present; status verified on actual call."
    from config import settings
    if not settings.openai_api_key or settings.openai_api_key.startswith("YOUR"):
        llm_status = "error"
        llm_detail = "OpenAI API key is missing or placeholder."

    overall = "ok" if all(s == "ok" for s in [db_status, lms_status, chroma_status, llm_status]) else "degraded"

    return {
        "overall": overall,
        "components": {
            "database": {"status": db_status, "latency_ms": db_latency, "detail": db_detail},
            "lms": {"status": lms_status, "latency_ms": lms_latency, "detail": lms_detail},
            "chroma": {"status": chroma_status, "latency_ms": chroma_latency, "detail": chroma_detail},
            "llm": {"status": llm_status, "detail": llm_detail},
        },
    }


@router.get("/health")
async def aggregated_health(db: AsyncSession = Depends(get_db)):
    """Return a simple aggregated health status."""
    status_data = await monitoring_status(db)
    return {
        "status": status_data["overall"],
        "components": status_data["components"],
    }
