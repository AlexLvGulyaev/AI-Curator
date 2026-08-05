"""Admin endpoints for AI Configuration management."""

from typing import List, Optional

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.auth import AdminIdentity, admin_auth, require_admin
from db import get_db
from models.ai_config import AiConfig, DEFAULT_PROVIDER_SETTINGS
from services.ai_config import AiConfigService
from services.cache import response_cache
from services.logger import LoggerService

router = APIRouter(prefix="/ai-config", tags=["admin-ai-config"])


def _merge_provider_settings(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Merge incoming provider settings with defaults, keeping only known keys."""
    merged = {k: dict(v) for k, v in DEFAULT_PROVIDER_SETTINGS.items()}
    if not raw or not isinstance(raw, dict):
        return merged
    for key, settings in raw.items():
        if key not in merged or not isinstance(settings, dict):
            continue
        for field in ("model", "temperature", "max_tokens"):
            if field in settings:
                merged[key][field] = settings[field]
    return merged


def get_service(db: AsyncSession = Depends(get_db)) -> AiConfigService:
    return AiConfigService(db)


def _get_client_ip(request: Request) -> Optional[str]:
    """Return the client IP from X-Forwarded-For or the direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


async def _log_audit(
    action: str,
    resource_id,
    db: AsyncSession,
    admin: AdminIdentity,
    request: Request,
    details: Optional[Dict[str, Any]] = None,
):
    logger = LoggerService(db)
    await logger.log_audit(
        action=action,
        resource_type="ai_config",
        resource_id=str(resource_id) if resource_id is not None else None,
        user_id=admin.user_id,
        user_name=admin.user_name,
        user_role=admin.user_role,
        ip_address=_get_client_ip(request),
        details=details or {},
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
    system_prompt: str = Field(..., min_length=1)
    model: str = Field("gpt-4o-mini", max_length=100)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=1, le=4096)
    beginner_instructions: Optional[str] = None
    advanced_instructions: Optional[str] = None
    few_shot_examples: Optional[str] = None
    output_rules: Optional[str] = None
    refusal_answer_text: Optional[str] = None
    max_history_messages: int = Field(6, ge=0, le=50)
    active_provider: Optional[str] = Field("openai", pattern="^(openai|gigachat)$")
    fallback_provider: Optional[str] = Field("gigachat", pattern="^(openai|gigachat)$")
    openai_enabled: Optional[bool] = True
    gigachat_enabled: Optional[bool] = True
    provider_settings: Optional[Dict[str, Dict[str, Any]]] = None

    @field_validator("system_prompt")
    @classmethod
    def _system_prompt_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("system_prompt cannot be empty")
        return value

    @field_validator("provider_settings")
    @classmethod
    def _provider_settings_shape(cls, value: Any) -> Dict[str, Dict[str, Any]]:
        return _merge_provider_settings(value)


class AiConfigOut(BaseModel):
    """Output representation of an AI config version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int
    beginner_instructions: Optional[str]
    advanced_instructions: Optional[str]
    few_shot_examples: Optional[str]
    output_rules: Optional[str]
    refusal_answer_text: Optional[str]
    max_history_messages: int
    active_provider: str
    fallback_provider: str
    openai_enabled: bool
    gigachat_enabled: bool
    provider_settings: Dict[str, Dict[str, Any]]
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
    request: Request,
    payload: AiConfigIn,
    service: AiConfigService = Depends(get_service),
    admin: AdminIdentity = Depends(require_admin),
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
        active_provider=payload.active_provider,
        fallback_provider=payload.fallback_provider,
        openai_enabled=payload.openai_enabled,
        gigachat_enabled=payload.gigachat_enabled,
        provider_settings=payload.provider_settings,
        created_by=admin.user_name,
    )
    await _log_audit(
        "create",
        config.id,
        service.db,
        admin,
        request,
        details={"name": config.name, "model": config.model},
    )
    _invalidate_response_cache()
    return AiConfigOut.model_validate(config)


@router.post("/{config_id}/activate", response_model=AiConfigOut)
async def activate_config(
    request: Request,
    config_id: int,
    service: AiConfigService = Depends(get_service),
    admin: AdminIdentity = Depends(require_admin),
):
    """Activate the specified configuration version."""
    try:
        config = await service.activate(config_id)
        await _log_audit(
            "activate",
            config.id,
            service.db,
            admin,
            request,
            details={"name": config.name, "model": config.model},
        )
        _invalidate_response_cache()
        return AiConfigOut.model_validate(config)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
