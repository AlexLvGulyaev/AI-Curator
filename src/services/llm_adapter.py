"""LLM adapter for OpenAI via LangChain inside AI Curator Backend."""

import time
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from models.ai_config import AiConfig


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
    """Thin wrapper around LangChain ChatOpenAI."""

    def __init__(self, config: Optional[AiConfig] = None):
        self.config = config
        self._client: Optional[ChatOpenAI] = None
        self._client_max_tokens: Optional[int] = None

    def _get_client(self, max_tokens: Optional[int] = None) -> ChatOpenAI:
        """Lazy-build ChatOpenAI from active config or fall back to settings.

        Reuses the cached client when the same max_tokens is requested.
        """
        model = self.config.model if self.config else settings.openai_model
        temperature = self.config.temperature if self.config else 0.3
        config_max_tokens = self.config.max_tokens if self.config else settings.openai_model_max_tokens
        effective_max_tokens = (
            min(max_tokens, config_max_tokens)
            if max_tokens is not None
            else config_max_tokens
        )
        if self._client is None or self._client_max_tokens != effective_max_tokens:
            self._client = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=effective_max_tokens,
                api_key=settings.openai_api_key,
            )
            self._client_max_tokens = effective_max_tokens
        return self._client

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> LlmResponse:
        """Send prompt to LLM and return structured response.

        Args:
            prompt: Full prompt text.
            max_tokens: Optional override for output token limit. If not set,
                uses the configured value.
        """
        start = time.perf_counter()
        try:
            client = self._get_client(max_tokens=max_tokens)
            # Split the prompt on system/user separator and use messages API.
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
            return LlmResponse(
                content=response.content,
                model=metadata.get("model_name", self.config.model if self.config else settings.openai_model),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                latency_ms=elapsed,
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            return LlmResponse(
                content="",
                model=self.config.model if self.config else settings.openai_model,
                latency_ms=elapsed,
                error=f"{type(exc).__name__}: {exc}",
            )
