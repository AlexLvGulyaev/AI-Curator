"""Knowledge Base document lifecycle event service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge_base import KbDocumentEvent


class KbLifecycleService:
    """Record and retrieve lifecycle events for KB documents and versions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        document_id: int,
        event_type: str,
        *,
        version_id: Optional[int] = None,
        status: str = "pending",
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> KbDocumentEvent:
        """Persist a lifecycle event.

        Args:
            document_id: FK to kb_documents.
            event_type: Type of the event, e.g. upload, index_start, index_done.
            version_id: Optional FK to kb_document_versions.
            status: pending, success, error.
            message: Human-readable description.
            details: JSON-serializable technical snapshot.
            commit: Whether to commit immediately. Set to False when the caller
                manages the transaction boundary.
        """
        now = datetime.now(timezone.utc)
        event = KbDocumentEvent(
            document_id=document_id,
            version_id=version_id,
            event_type=event_type,
            status=status,
            message=message,
            details=details or {},
        )
        # Instant events (upload, publish) have no separate finish step.
        if status != "pending":
            event.started_at = now
            event.finished_at = now
            event.duration_ms = 0
        self.db.add(event)
        if commit:
            await self.db.commit()
            await self.db.refresh(event)
        else:
            await self.db.flush()
            await self.db.refresh(event)
        return event

    async def start_event(
        self,
        document_id: int,
        event_type: str,
        *,
        version_id: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> KbDocumentEvent:
        """Start a timed lifecycle event and return it for later finishing."""
        now = datetime.now(timezone.utc)
        event = KbDocumentEvent(
            document_id=document_id,
            version_id=version_id,
            event_type=event_type,
            status="pending",
            message=message,
            details=details or {},
            started_at=now,
        )
        self.db.add(event)
        if commit:
            await self.db.commit()
            await self.db.refresh(event)
        else:
            await self.db.flush()
            await self.db.refresh(event)
        return event

    async def finish_event(
        self,
        event_id: int,
        status: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> Optional[KbDocumentEvent]:
        """Finish a previously started event, computing its duration."""
        stmt = select(KbDocumentEvent).where(KbDocumentEvent.id == event_id)
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()
        if event is None:
            return None

        now = datetime.now(timezone.utc)
        event.status = status
        if message is not None:
            event.message = message
        if details is not None:
            event.details = details
        event.finished_at = now
        if event.started_at is not None:
            delta = now - event.started_at
            event.duration_ms = int(delta.total_seconds() * 1000)
        else:
            event.duration_ms = 0

        if commit:
            await self.db.commit()
            await self.db.refresh(event)
        else:
            await self.db.flush()
            await self.db.refresh(event)
        return event

    async def get_timeline(
        self,
        document_id: int,
        limit: int = 100,
    ) -> List[KbDocumentEvent]:
        """Return chronological lifecycle events for a document."""
        stmt = (
            select(KbDocumentEvent)
            .where(KbDocumentEvent.document_id == document_id)
            .order_by(KbDocumentEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_timeline_for_version(
        self,
        version_id: int,
        limit: int = 100,
    ) -> List[KbDocumentEvent]:
        """Return chronological lifecycle events for a specific version."""
        stmt = (
            select(KbDocumentEvent)
            .where(KbDocumentEvent.version_id == version_id)
            .order_by(KbDocumentEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
