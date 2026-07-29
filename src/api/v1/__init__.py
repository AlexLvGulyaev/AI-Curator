"""API v1 router aggregation."""

from fastapi import APIRouter

from api.v1 import courses, deadlines, health, progress

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(courses.router)
api_v1_router.include_router(deadlines.router)
api_v1_router.include_router(progress.router)
