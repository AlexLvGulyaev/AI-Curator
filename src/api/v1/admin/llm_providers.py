"""Admin endpoints for LLM provider testing and status."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.admin.auth import AdminIdentity, require_admin
from db import get_db
from services.ai_config import AiConfigService
from services.gigachat_adapter import GigaChatAdapter
from services.llm_adapter import LLMAdapter

router = APIRouter(prefix="/llm-providers", tags=["admin-llm-providers"])


class ProviderTestOut(BaseModel):
    """Result of a provider health test."""

    ok: bool
    message: str
    model: str | None = None
    latency_ms: float | None = None


@router.post("/{provider_key}/test", response_model=ProviderTestOut)
async def test_provider(
    provider_key: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminIdentity = Depends(require_admin),
):
    """Test a specific LLM provider by sending a minimal prompt."""
    if provider_key not in ("openai", "gigachat"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider_key}",
        )

    config_service = AiConfigService(db)
    config = await config_service.get_active()

    test_prompt = "Ответь одним словом: да или нет."
    try:
        if provider_key == "openai":
            adapter = LLMAdapter(config)
            # Force OpenAI as active provider for the test.
            config.active_provider = "openai"
            config.fallback_provider = None
            response = await adapter.generate(test_prompt, max_tokens=5)
        else:
            adapter = GigaChatAdapter()
            response = await adapter.generate(test_prompt, max_tokens=5)
    except Exception as exc:
        return ProviderTestOut(ok=False, message=f"{type(exc).__name__}: {exc}")

    if response.error:
        return ProviderTestOut(
            ok=False,
            message=response.error,
            model=response.model,
            latency_ms=response.latency_ms,
        )
    return ProviderTestOut(
        ok=True,
        message="Провайдер доступен",
        model=response.model,
        latency_ms=response.latency_ms,
    )
