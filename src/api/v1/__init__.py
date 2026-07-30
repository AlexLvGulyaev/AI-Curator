"""API v1 router aggregation."""

from fastapi import APIRouter

from api.v1 import chat, courses, deadlines, health, progress, rag
from api.v1.admin import admin_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(courses.router)
api_v1_router.include_router(deadlines.router)
api_v1_router.include_router(progress.router)
api_v1_router.include_router(rag.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(admin_router)
