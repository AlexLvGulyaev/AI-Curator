"""Admin endpoints for AI Configuration management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.ai_config import AiConfig
from services.ai_config import AiConfigService
from services.cache import response_cache
from services.logger import LoggerService

router = APIRouter(prefix="/ai-config", tags=["admin-ai-config"])


def get_service(db: AsyncSession = Depends(get_db)) -> AiConfigService:
    return AiConfigService(db)


async def _log_audit(action: str, resource_id, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="ai_config",
        resource_id=str(resource_id) if resource_id is not None else None,
        user_id="admin",
        user_role="admin",
    )


def _invalidate_response_cache() -> None:
    """Invalidate the chat response cache after AI config changes."""
    try:
        response_cache.invalidate_all()
    except Exception:
        pass


class AiConfigIn(BaseModel):
    """Payload for creating an AI config version."""

    name: str = Field(..., max_length=255)
    system_prompt: str
    model: str = Field("gpt-4o-mini", max_length=100)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=1, le=4096)
    beginner_instructions: Optional[str] = None
    advanced_instructions: Optional[str] = None
    few_shot_examples: Optional[str] = None
    output_rules: Optional[str] = None
    refusal_answer_text: Optional[str] = None
    max_history_messages: int = Field(6, ge=0, le=50)


class AiConfigOut(BaseModel):
    """Output representation of an AI config version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model: str
    temperature: float
    max_tokens: int
    beginner_instructions: Optional[str]
    advanced_instructions: Optional[str]
    few_shot_examples: Optional[str]
    output_rules: Optional[str]
    refusal_answer_text: Optional[str]
    max_history_messages: int
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=AiConfigOut)
async def get_active_config(service: AiConfigService = Depends(get_service)):
    """Return the currently active AI configuration."""
    config = await service.get_active()
    return AiConfigOut.model_validate(config)


@router.get("/history", response_model=List[AiConfigOut])
async def list_configs(service: AiConfigService = Depends(get_service)):
    """Return all AI configuration versions."""
    configs = await service.list_configs()
    return [AiConfigOut.model_validate(c) for c in configs]


@router.post("", response_model=AiConfigOut, status_code=status.HTTP_201_CREATED)
async def create_config(
    payload: AiConfigIn,
    service: AiConfigService = Depends(get_service),
):
    """Create a new AI configuration version (inactive by default)."""
    config = await service.create_config(
        name=payload.name,
        system_prompt=payload.system_prompt,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        beginner_instructions=payload.beginner_instructions,
        advanced_instructions=payload.advanced_instructions,
        few_shot_examples=payload.few_shot_examples,
        output_rules=payload.output_rules,
        refusal_answer_text=payload.refusal_answer_text,
        max_history_messages=payload.max_history_messages,
        created_by="admin",
    )
    await _log_audit("create", config.id, service.db)
    _invalidate_response_cache()
    return AiConfigOut.model_validate(config)


@router.post("/{config_id}/activate", response_model=AiConfigOut)
async def activate_config(
    config_id: int,
    service: AiConfigService = Depends(get_service),
):
    """Activate the specified configuration version."""
    try:
        config = await service.activate(config_id)
        await _log_audit("activate", config.id, service.db)
        _invalidate_response_cache()
        return AiConfigOut.model_validate(config)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
