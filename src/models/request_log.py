"""Request log model for analytics and audit."""

from sqlalchemy import Column, Float, Integer, JSON, String, Text

from models.base import Base


class RequestLog(Base):
    """Log entry for a student request and AI response."""

    __tablename__ = "request_logs"

    session_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    request_type = Column(String(50), nullable=True, index=True)
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True, default=list)
    lms_calls = Column(JSON, nullable=True, default=list)
    llm_model = Column(String(100), nullable=True)
    latency_ms = Column(Float, nullable=True)
    feedback_score = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
