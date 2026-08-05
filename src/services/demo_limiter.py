"""Demo session limiter for the public Web UI chat endpoint."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.demo_session import DemoSession


class DemoLimiterService:
    """Manage demo session tokens, quotas and rate limits."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _active_sessions_for_ip(self, client_ip: str, hours: int = 1) -> int:
        """Count demo sessions created for this IP within the last N hours."""
        if not client_ip:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            select(DemoSession).where(
                DemoSession.client_ip == client_ip,
                DemoSession.created_at >= cutoff,
                DemoSession.is_active.is_(True),
            )
        )
        return len(result.scalars().all())

    async def create_session(
        self,
        client_ip: Optional[str],
        session_id: Optional[str] = None,
    ) -> DemoSession:
        """Create a new demo session token.

        Raises HTTPException(429) when the IP has created too many recent sessions.
        """
        if settings.demo_max_sessions_per_ip_per_hour > 0 and client_ip:
            recent = await self._active_sessions_for_ip(client_ip, hours=1)
            if recent >= settings.demo_max_sessions_per_ip_per_hour:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many demo sessions from this IP address. Please try again later.",
                )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.demo_session_ttl_minutes)
        demo = DemoSession(
            token=self._generate_token(),
            session_id=session_id,
            client_ip=client_ip,
            requests_used=0,
            requests_limit=settings.demo_max_requests_per_session,
            is_active=True,
            created_at=now,
            expires_at=expires_at,
            last_request_at=None,
        )
        self.db.add(demo)
        await self.db.flush()
        await self.db.refresh(demo)
        return demo

    async def get_session(self, token: str) -> Optional[DemoSession]:
        """Return a demo session by token, or None if not found."""
        result = await self.db.execute(select(DemoSession).where(DemoSession.token == token))
        return result.scalar_one_or_none()

    async def check_and_record_request(
        self,
        token: str,
        client_ip: Optional[str],
    ) -> DemoSession:
        """Validate a token for a chat request and consume one request from the quota.

        Raises HTTPException for missing, expired, rate-limited or exhausted tokens.
        """
        demo = await self.get_session(token)
        if demo is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid demo token",
            )

        now = datetime.now(timezone.utc)
        if not demo.is_active or demo.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Demo session has expired. Please start a new demo session.",
            )

        # Rate limit: at least 5 seconds between requests from the same token.
        min_interval_seconds = 60.0 / max(settings.demo_rate_limit_per_minute, 1)
        if demo.last_request_at is not None:
            elapsed = (now - demo.last_request_at).total_seconds()
            if elapsed < min_interval_seconds:
                retry_after = int(min_interval_seconds - elapsed) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demo rate limit exceeded. Please wait before sending the next message.",
                    headers={"Retry-After": str(retry_after)},
                )

        if demo.requests_used >= demo.requests_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo request quota exhausted. Please start a new demo session.",
            )

        demo.requests_used += 1
        demo.last_request_at = now
        await self.db.flush()
        await self.db.refresh(demo)
        return demo

    async def get_status(self, token: str) -> dict:
        """Return the current quota status for a token."""
        demo = await self.get_session(token)
        if demo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Demo session not found",
            )
        remaining = max(0, demo.requests_limit - demo.requests_used)
        return {
            "token": demo.token,
            "session_id": demo.session_id,
            "requests_used": demo.requests_used,
            "requests_limit": demo.requests_limit,
            "requests_remaining": remaining,
            "expires_at": demo.expires_at.isoformat() if demo.expires_at else None,
            "is_active": demo.is_active and demo.expires_at > datetime.now(timezone.utc),
        }

    async def cleanup_expired(self) -> int:
        """Deactivate demo sessions that have passed their expiration time."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(DemoSession).where(
                DemoSession.is_active.is_(True),
                DemoSession.expires_at < now,
            )
        )
        expired = result.scalars().all()
        for demo in expired:
            demo.is_active = False
        await self.db.flush()
        return len(expired)

    @staticmethod
    def _generate_token() -> str:
        """Generate a opaque demo session token."""
        import uuid

        return uuid.uuid4().hex
