"""Admin endpoints for orchestrator configuration management."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.orchestrator_config import (
    DEFAULT_FALLBACK_MESSAGES,
    DEFAULT_INTENT_MAX_TOKENS,
    DEFAULT_INTENT_RULES,
    DEFAULT_INTENT_SOURCE_MAP,
    DEFAULT_NON_COURSE_STARTERS,
)
from services.cache import response_cache
from services.logger import LoggerService
from services.orchestrator_config import OrchestratorConfigService

router = APIRouter(prefix="/orchestrator", tags=["admin-orchestrator"])


def get_service(db: AsyncSession = Depends(get_db)) -> OrchestratorConfigService:
    return OrchestratorConfigService(db)


async def _log_audit(action: str, resource_id, db: AsyncSession):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="orchestrator_config",
        resource_id=str(resource_id) if resource_id is not None else None,
        user_id="admin",
        user_role="admin",
    )


def _invalidate_response_cache() -> None:
    """Invalidate the chat response cache after orchestrator config changes."""
    try:
        response_cache.invalidate_all()
    except Exception:
        pass


class OrchestratorConfigIn(BaseModel):
    """Payload for updating orchestrator configuration."""

    intent_rules: Optional[dict] = None
    default_intent: Optional[str] = Field(None, max_length=50)
    intent_source_map: Optional[dict] = None
    non_course_starters: Optional[list] = None
    max_lms_contents: Optional[int] = Field(None, ge=1, le=100)
    max_lms_deadlines: Optional[int] = Field(None, ge=1, le=50)
    intent_max_tokens: Optional[dict] = None
    fallback_messages: Optional[dict] = None

    @model_validator(mode="after")
    def check_intent_consistency(self):
        if self.intent_source_map is not None:
            for intent, flags in self.intent_source_map.items():
                if not isinstance(flags, dict):
                    raise ValueError(f"intent_source_map[{intent}] must be an object")
                for key in ("lms", "rag", "strict_course"):
                    if key not in flags:
                        raise ValueError(f"intent_source_map[{intent}] must contain '{key}'")
                    if not isinstance(flags[key], bool):
                        raise ValueError(f"intent_source_map[{intent}].{key} must be a boolean")
        if self.fallback_messages is not None:
            for key in ("no_lms_data", "no_rag_context", "out_of_scope_course"):
                if key not in self.fallback_messages:
                    raise ValueError(f"fallback_messages must contain '{key}'")
                if not isinstance(self.fallback_messages[key], str):
                    raise ValueError(f"fallback_messages.{key} must be a string")
        return self


class OrchestratorConfigOut(BaseModel):
    """Output representation of orchestrator configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    intent_rules: dict
    default_intent: str
    intent_source_map: dict
    non_course_starters: list
    max_lms_contents: int
    max_lms_deadlines: int
    intent_max_tokens: dict
    fallback_messages: dict
    created_at: datetime
    updated_at: datetime


@router.get("/config", response_model=OrchestratorConfigOut)
async def get_config(service: OrchestratorConfigService = Depends(get_service)):
    """Return the effective orchestrator configuration."""
    config = await service.get_or_create_default()
    return OrchestratorConfigOut.model_validate(config)


@router.put("/config", response_model=OrchestratorConfigOut)
async def update_config(
    payload: OrchestratorConfigIn,
    service: OrchestratorConfigService = Depends(get_service),
):
    """Update the effective orchestrator configuration."""
    try:
        config = await service.update(**payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    await _log_audit("update", config.id, service.db)
    _invalidate_response_cache()
    return OrchestratorConfigOut.model_validate(config)
