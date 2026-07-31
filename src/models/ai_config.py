"""AI Configuration SQLAlchemy model for versioned prompt and LLM settings."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class AiConfig(Base):
    """Versioned configuration for LLM prompts and retrieval parameters."""

    __tablename__ = "ai_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o-mini")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    beginner_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    advanced_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    few_shot_examples: Mapped[str] = mapped_column(Text, nullable=True)
    output_rules: Mapped[str] = mapped_column(Text, nullable=True)
    refusal_answer_text: Mapped[str] = mapped_column(Text, nullable=True)
    max_history_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)
