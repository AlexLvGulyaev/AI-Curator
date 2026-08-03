"""GigaChat LLM adapter for AI Curator fallback."""

import ssl
import time
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Optional

from config import settings


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


class GigaChatAdapter:
    """Minimal async-compatible GigaChat adapter using direct HTTP requests.

    GigaChat uses short-lived OAuth2 access tokens obtained from the
    ``/token`` endpoint with HTTP Basic auth (``Authorization: Basic <key>``).
    The access token is then used in ``Authorization: Bearer <token>``
    against ``/chat/completions``.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.model = model or settings.gigachat_model or "GigaChat-Max"
        self.temperature = temperature if temperature is not None else getattr(settings, "gigachat_temperature", 0.1)
        self.default_max_tokens = max_tokens if max_tokens is not None else getattr(settings, "gigachat_max_tokens", 1024)
        self.base_url = (base_url or settings.gigachat_base_url or "https://gigachat.devices.sberbank.ru/api/v1").rstrip("/")
        token_url = getattr(settings, "gigachat_token_url", None)
        self.token_url = token_url or "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.auth_key = auth_key or settings.gigachat_auth_key or ""
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    def _request_json(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        data: Optional[bytes] = None,
    ) -> dict:
        """Perform a synchronous HTTPS request and return parsed JSON."""
        request_headers = dict(headers or {})
        request_headers.setdefault("Accept", "application/json")
        req = urllib.request.Request(
            url,
            method=method,
            data=data,
            headers=request_headers,
        )
        with urllib.request.urlopen(req, timeout=60, context=self._ssl_context) as response:
            return __import__("json").loads(response.read().decode("utf-8"))

    def _get_access_token(self) -> str:
        """Obtain a GigaChat access token via client credentials flow."""
        if not self.auth_key:
            raise RuntimeError("GIGACHAT_AUTH_KEY is not configured")
        url = self.token_url
        headers = {
            "Authorization": f"Basic {self.auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = b"scope=GIGACHAT_API_PERS"
        response = self._request_json(url, method="POST", headers=headers, data=data)
        access_token = response.get("access_token")
        if not access_token:
            raise RuntimeError(f"GigaChat token response missing access_token: {response}")
        return access_token

    def generate_sync(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> LlmResponse:
        """Synchronous generation via GigaChat (to be called in thread)."""
        start = time.perf_counter()
        try:
            access_token = self._get_access_token()
            url = f"{self.base_url}/chat/completions"
            effective_max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": effective_max_tokens,
                "temperature": self.temperature,
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            data = __import__("json").dumps(payload, ensure_ascii=False).encode("utf-8")
            response = self._request_json(url, method="POST", headers=headers, data=data)

            choice = (response.get("choices") or [{}])[0]
            message = choice.get("message", {}) if isinstance(choice, dict) else {}
            content = message.get("content", "") if isinstance(message, dict) else ""
            usage = response.get("usage") or {}
            finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            error: Optional[str] = None
            if finish_reason == "length":
                error = "response_truncated_by_max_tokens"
            return LlmResponse(
                content=content or "",
                model=response.get("model", self.model),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                latency_ms=elapsed,
                error=error,
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            return LlmResponse(
                content="",
                model=self.model,
                latency_ms=elapsed,
                error=f"{type(exc).__name__}: {exc}",
            )

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
    ) -> LlmResponse:
        """Async wrapper around the synchronous GigaChat HTTP client."""
        return await __import__("asyncio").to_thread(self.generate_sync, prompt, max_tokens)
