"""Admin endpoint for audit log."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.chat import AuditLog
from services.logger import LoggerService

router = APIRouter(prefix="/audit", tags=["admin-audit"])


async def _log_audit(action: str, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="audit_log",
        user_id="admin",
        user_role="admin",
    )


@router.get("")
async def list_audit(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id_param: Optional[str] = Query(None, alias="user_id"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return audit log entries with optional filters."""
    await _log_audit("view_audit", db)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if user_id_param:
        stmt = stmt.where(AuditLog.user_id == user_id_param)
    result = await db.execute(stmt)
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_role": a.user_role,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "details": a.details,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().unique()
    ]
