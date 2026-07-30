"""Admin API router aggregation."""

from fastapi import APIRouter

from api.v1.admin import ai_config, analytics, audit, kb, monitoring

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(kb.router)
admin_router.include_router(ai_config.router)
admin_router.include_router(analytics.router)
admin_router.include_router(monitoring.router)
admin_router.include_router(audit.router)
