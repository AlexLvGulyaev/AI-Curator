"""Demo session endpoints for the public Web UI."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_db
from services.demo_limiter import DemoLimiterService

router = APIRouter(prefix="/demo", tags=["demo"])


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


class DemoStartPayload(BaseModel):
    """Optional client-provided session id when starting a demo session."""

    session_id: Optional[str] = Field(None, max_length=255)


class DemoStartResponse(BaseModel):
    """Demo session token and quota information."""

    token: str
    session_id: Optional[str] = None
    requests_limit: int
    requests_remaining: int
    rate_limit_per_minute: int
    expires_at: str


class DemoStatusResponse(BaseModel):
    """Current state of a demo session token."""

    token: str
    session_id: Optional[str] = None
    requests_used: int
    requests_limit: int
    requests_remaining: int
    expires_at: Optional[str] = None
    is_active: bool


def _ensure_demo_enabled() -> None:
    """Raise if demo mode is not enabled on the backend."""
    if not settings.demo_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode is not enabled on this instance",
        )


@router.post("/start", response_model=DemoStartResponse)
async def start_demo_session(
    request: Request,
    payload: DemoStartPayload,
    db: AsyncSession = Depends(get_db),
):
    """Create a new demo session token for the Web UI.

    Returns a token that must be sent as `X-Demo-Token` header on every
    `POST /api/v1/chat` request.
    """
    _ensure_demo_enabled()
    client_ip = _client_ip(request)
    service = DemoLimiterService(db)
    demo = await service.create_session(
        client_ip=client_ip,
        session_id=payload.session_id,
    )
    await db.commit()
    return DemoStartResponse(
        token=demo.token,
        session_id=demo.session_id,
        requests_limit=demo.requests_limit,
        requests_remaining=max(0, demo.requests_limit - demo.requests_used),
        rate_limit_per_minute=settings.demo_rate_limit_per_minute,
        expires_at=demo.expires_at.isoformat(),
    )


@router.get("/status", response_model=DemoStatusResponse)
async def demo_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return the current quota and expiration status of a demo token.

    The token is read from the `X-Demo-Token` header.
    """
    _ensure_demo_enabled()
    token = request.headers.get("x-demo-token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Demo-Token header is required",
        )
    service = DemoLimiterService(db)
    status_data = await service.get_status(token)
    return DemoStatusResponse(**status_data)
