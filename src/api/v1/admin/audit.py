"""Admin endpoint for audit log."""

import csv
import io
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.chat import AuditLog
from services.logger import LoggerService

router = APIRouter(prefix="/audit", tags=["admin-audit"])


def _client_ip(request: Request) -> Optional[str]:
    """Extract the real client IP from proxy headers or the connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client = forwarded.split(",")[0].strip()
        if client:
            return client
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None
    if request.client:
        return request.client.host
    return None


async def _log_audit(action: str, db: AsyncSession, request: Request):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="audit_log",
        user_id="admin",
        user_name="admin",
        user_role="admin",
        ip_address=_client_ip(request),
    )


@router.get("")
async def list_audit(
    request: Request,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id_param: Optional[str] = Query(None, alias="user_id"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated audit log entries with optional filters."""
    # Read-only views are intentionally not audited to avoid self-generated noise.

    base_stmt = select(AuditLog)
    if action:
        base_stmt = base_stmt.where(AuditLog.action == action)
    if resource_type:
        base_stmt = base_stmt.where(AuditLog.resource_type == resource_type)
    if user_id_param:
        base_stmt = base_stmt.where(
            (AuditLog.user_id == user_id_param) | (AuditLog.user_name == user_id_param)
        )
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=None)
            base_stmt = base_stmt.where(AuditLog.created_at >= start)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid date_from: {date_from}"
            )
    if date_to:
        try:
            end = datetime.combine(datetime.strptime(date_to, "%Y-%m-%d"), time.max)
            base_stmt = base_stmt.where(AuditLog.created_at <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date_to: {date_to}")

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = base_stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)

    items = [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_name": a.user_name,
            "user_role": a.user_role,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "ip_address": a.ip_address,
            "details": a.details,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().unique()
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{audit_id}")
async def get_audit_entry(
    audit_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return a single audit log entry with full JSON snapshot."""
    # Read-only views are intentionally not audited to avoid self-generated noise.
    result = await db.execute(select(AuditLog).where(AuditLog.id == audit_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "user_name": entry.user_name,
        "user_role": entry.user_role,
        "action": entry.action,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "ip_address": entry.ip_address,
        "details": entry.details,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


@router.post("/export")
async def export_audit(
    request: Request,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id_param: Optional[str] = Query(None, alias="user_id"),
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(10000, ge=1, le=50000),
    db: AsyncSession = Depends(get_db),
):
    """Export audit log entries as CSV matching the current list filters."""
    result = await list_audit(
        request=request,
        action=action,
        resource_type=resource_type,
        user_id_param=user_id_param,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=0,
        db=db,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "user_id",
            "user_name",
            "user_role",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "details",
        ]
    )

    for item in result["items"]:
        writer.writerow(
            [
                item["id"],
                item["created_at"] or "",
                item["user_id"] or "",
                item["user_name"] or "",
                item["user_role"] or "",
                item["action"],
                item["resource_type"],
                item["resource_id"] or "",
                item["ip_address"] or "",
                str(item["details"]).replace("\n", " ")[:1000],
            ]
        )

    output.seek(0)
    filename = f"ai_curator_audit_{date_from or 'all'}_{date_to or 'all'}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
