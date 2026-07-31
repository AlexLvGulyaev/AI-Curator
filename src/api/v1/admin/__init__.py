"""Admin API router aggregation."""

from fastapi import APIRouter, Depends

from api.v1.admin import ai_config, analytics, audit, auth, kb, monitoring, retrieval

admin_router = APIRouter(prefix="/admin", dependencies=[Depends(auth.admin_auth)])
admin_router.include_router(kb.router)
admin_router.include_router(ai_config.router)
admin_router.include_router(retrieval.router)
admin_router.include_router(analytics.router)
admin_router.include_router(monitoring.router)
admin_router.include_router(audit.router)
