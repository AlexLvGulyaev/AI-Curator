"""LLM adapter with configurable primary/fallback providers for AI Curator Backend."""

import time
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from models.ai_config import AiConfig, DEFAULT_PROVIDER_SETTINGS


@dataclass
class LlmResponse:
    """Structured response from the LLM adapter."""

    content: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class LLMAdapter:
    """Configurable LLM adapter supporting OpenAI primary + GigaChat fallback."""

    def __init__(self, config: Optional[AiConfig] = None):
        self.config = config
        self._openai_client: Optional[ChatOpenAI] = None
        self._openai_client_max_tokens: Optional[int] = None
        self._gigachat_adapter = None

    def _openai_configured(self) -> bool:
        return bool(settings.openai_api_key and not settings.openai_api_key.startswith("YOUR"))

    def _gigachat_configured(self) -> bool:
        return bool(settings.gigachat_auth_key and not settings.gigachat_auth_key.startswith("YOUR"))

    def _is_provider_enabled(self, provider: str) -> bool:
        if not self.config:
            # Without config, rely on environment availability.
            if provider == "openai":
                return self._openai_configured()
            if provider == "gigachat":
                return self._gigachat_configured()
            return False
        if provider == "openai":
            return self.config.openai_enabled and self._openai_configured()
        if provider == "gigachat":
            return self.config.gigachat_enabled and self._gigachat_configured()
        return False

    def _active_provider(self) -> str:
        if self.config and self.config.active_provider:
            return self.config.active_provider
        return "openai" if self._openai_configured() else "gigachat"

    def _fallback_provider(self) -> Optional[str]:
        active = self._active_provider()
        candidate = None
        if self.config and self.config.fallback_provider:
            candidate = self.config.fallback_provider
        if candidate == active:
            # Pick the other provider if the fallback equals active.
            candidate = "gigachat" if active == "openai" else "openai"
        return candidate if self._is_provider_enabled(candidate) else None

    def _provider_settings(self, provider: str) -> dict:
        """Return per-provider settings merged with defaults."""
        defaults = DEFAULT_PROVIDER_SETTINGS.get(provider, {})
        if not self.config:
            return dict(defaults)
        configured = (self.config.provider_settings or {}).get(provider, {})
        merged = {**defaults, **configured}
        # Clamp temperature and max_tokens to sane ranges if present.
        if "temperature" in merged:
            try:
                merged["temperature"] = max(0.0, min(2.0, float(merged["temperature"])))
            except (TypeError, ValueError):
                merged["temperature"] = defaults.get("temperature", 0.3)
        if "max_tokens" in merged:
            try:
                merged["max_tokens"] = max(1, min(4096, int(merged["max_tokens"])))
            except (TypeError, ValueError):
                merged["max_tokens"] = defaults.get("max_tokens", 1024)
        return merged

    def _get_openai_client(self, max_tokens: Optional[int] = None) -> ChatOpenAI:
        """Lazy-build ChatOpenAI from per-provider settings or fall back to settings."""
        provider_settings = self._provider_settings("openai")
        model = provider_settings.get("model") or settings.openai_model
        temperature = provider_settings.get("temperature") if self.config else 0.3
        config_max_tokens = provider_settings.get("max_tokens") if self.config else settings.openai_model_max_tokens
        effective_max_tokens = (
            min(max_tokens, config_max_tokens)
            if max_tokens is not None
            else config_max_tokens
        )
        if self._openai_client is None or self._openai_client_max_tokens != effective_max_tokens:
            self._openai_client = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=effective_max_tokens,
                api_key=settings.openai_api_key,
            )
            self._openai_client_max_tokens = effective_max_tokens
        return self._openai_client

    def _get_gigachat_adapter(self, max_tokens: Optional[int] = None):
        """Lazy-build GigaChat adapter with per-provider settings."""
        if self._gigachat_adapter is None:
            from services.gigachat_adapter import GigaChatAdapter
            provider_settings = self._provider_settings("gigachat")
            self._gigachat_adapter = GigaChatAdapter(
                model=provider_settings.get("model"),
                max_tokens=provider_settings.get("max_tokens"),
            )
        return self._gigachat_adapter

    async def _generate_openai(self, prompt: str, max_tokens: Optional[int] = None) -> LlmResponse:
        """Generate with OpenAI."""
        start = time.perf_counter()
        client = self._get_openai_client(max_tokens=max_tokens)
        system_content = ""
        user_content = prompt
        if "Вопрос студента:" in prompt:
            parts = prompt.split("Вопрос студента:", 1)
            system_content = parts[0].strip()
            user_content = "Вопрос студента:\n" + parts[1].strip()
        messages = []
        if system_content:
            messages.append(SystemMessage(content=system_content))
        messages.append(HumanMessage(content=user_content))
        response = await client.ainvoke(messages)
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        metadata = response.response_metadata or {}
        usage = metadata.get("token_usage", {})
        finish_reason = None
        choices = getattr(response, "choices", None) or metadata.get("choices") or []
        if choices and isinstance(choices, list):
            choice = choices[0]
            if isinstance(choice, dict):
                finish_reason = choice.get("finish_reason")
        error: Optional[str] = None
        if finish_reason == "length":
            error = "response_truncated_by_max_tokens"
        return LlmResponse(
            content=response.content,
            model=metadata.get("model_name", self.config.model if self.config else settings.openai_model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            latency_ms=elapsed,
            error=error,
        )

    async def _generate_gigachat(self, prompt: str, max_tokens: Optional[int] = None) -> LlmResponse:
        """Generate with GigaChat using per-provider effective max_tokens."""
        adapter = self._get_gigachat_adapter()
        effective_max_tokens = max_tokens
        if effective_max_tokens is None and self.config:
            effective_max_tokens = self._provider_settings("gigachat").get("max_tokens")
        return await adapter.generate(prompt, max_tokens=effective_max_tokens)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> LlmResponse:
        """Generate using configured active provider, falling back on error."""
        active = self._active_provider()
        fallback = self._fallback_provider()

        last_error = None
        for provider in [p for p in [active, fallback] if p]:
            try:
                if provider == "openai":
                    return await self._generate_openai(prompt, max_tokens=max_tokens)
                if provider == "gigachat":
                    return await self._generate_gigachat(prompt, max_tokens=max_tokens)
            except Exception as exc:
                last_error = f"{provider}: {type(exc).__name__}: {exc}"
                continue

        active_settings = self._provider_settings(active) if self.config else {}
        model = active_settings.get("model") if self.config else settings.openai_model
        return LlmResponse(
            content="",
            model=model or (self.config.model if self.config else settings.openai_model),
            latency_ms=None,
            error=last_error or "No LLM provider is configured or enabled",
        )
