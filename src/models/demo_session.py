"""Demo session model for Web UI safe demo mode."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from models.base import Base


class DemoSession(Base):
    """A time- and quota-bound session token for public Web UI demo access."""

    __tablename__ = "demo_sessions"

    token = Column(String(255), nullable=False, unique=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    client_ip = Column(String(45), nullable=True, index=True)
    requests_used = Column(Integer, nullable=False, default=0)
    requests_limit = Column(Integer, nullable=False, default=20)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_request_at = Column(DateTime(timezone=True), nullable=True)
