"""AI Curator backend entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import api_v1_router
from api.v1.health import router as health_router
from config import settings
from db import engine
from models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables on startup (dev helper)."""
    if not settings.is_production:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
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

# Public health endpoints (outside /api/v1 for load balancers)
app.include_router(health_router)

# Versioned API
app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "AI Curator Backend", "version": "0.3.0"}
