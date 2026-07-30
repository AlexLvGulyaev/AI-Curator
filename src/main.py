"""AI Curator backend entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import api_v1_router
from api.v1.health import router as health_router
from config import settings
from db import async_session_factory, engine
from models.base import Base
from services.logger import LoggerService


async def _retention_cleanup_loop():
    """Periodically archive and delete old logs from hot storage."""
    while True:
        try:
            await asyncio.sleep(24 * 60 * 60)  # once per day
            async with async_session_factory() as db:
                logger = LoggerService(db)
                deleted = await logger.cleanup_old_records(
                    archive_dir=settings.archive_dir,
                    hot_retention_days=settings.hot_retention_days,
                    trace_retention_days=settings.trace_retention_days,
                )
                # Log the cleanup itself as an audit event.
                await logger.log_audit(
                    action="retention_cleanup",
                    resource_type="system",
                    user_id="system",
                    user_role="system",
                    details=deleted,
                )
        except Exception:
            # Cleanup must never crash the main application.
            await asyncio.sleep(60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables on startup and run background jobs."""
    if not settings.is_production:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    cleanup_task = asyncio.create_task(_retention_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await engine.dispose()


app = FastAPI(
    title="AI Curator Backend API",
    description="Backend orchestrator for the AI Curator educational assistant.",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS: allow configured public frontends in production, everything in dev
allowed_origins = [
    settings.web_ui_url,
    settings.admin_console_url,
]
if not settings.is_production:
    allowed_origins.extend(["http://localhost:3000", "http://localhost:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def close_upload_files_middleware(request, call_next):
    """Ensure uploaded file handles are closed after request handling."""
    response = await call_next(request)
    try:
        form = await request.form()
        for _, value in form.multi_items():
            if isinstance(value, UploadFile):
                await value.close()
    except Exception:
        pass
    return response


# Public health endpoints (outside /api/v1 for load balancers)
app.include_router(health_router)

# Versioned API
app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "AI Curator Backend", "version": "0.3.0"}
