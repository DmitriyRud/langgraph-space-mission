import asyncio
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Raised when an LLM call fails during invocation or structured parsing."""


class LLMUnavailableError(LLMProviderError):
    """Raised when the configured local/remote LLM server is unreachable."""


@dataclass
class LLMCallResult:
    parsed: BaseModel
    provider: str
    model: str
    duration_ms: int
    token_usage: dict[str, int] | None
    raw_content: str | None = None


class LLMProvider:
    """Single-model LLM provider with concurrency limiting for 16GB local hardware."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._semaphore = asyncio.Semaphore(max(1, settings.llm_max_concurrency))

    @property
    def active_model_name(self) -> str:
        if self.settings.llm_provider == "openai_compatible":
            return self.settings.openai_model
        return self.settings.ollama_model

    def _build_chat_model(self) -> Any:
        if self.settings.llm_provider == "openai_compatible":
            if not self.settings.openai_api_key:
                raise LLMUnavailableError(
                    "OPENAI_API_KEY is not configured for openai_compatible provider."
                )
            return ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                temperature=self.settings.llm_temperature,
                timeout=self.settings.llm_timeout_seconds,
            )

        return ChatOllama(
            model=self.settings.ollama_model,
            base_url=self.settings.ollama_base_url,
            temperature=self.settings.llm_temperature,
            client_kwargs={"timeout": self.settings.llm_timeout_seconds},
        )

    async def check_health(self) -> dict[str, Any]:
        if self.settings.llm_provider == "openai_compatible":
            configured = bool(self.settings.openai_api_key)
            return {
                "provider": "openai_compatible",
                "connected": configured,
                "base_url": self.settings.openai_base_url,
                "active_model": self.settings.openai_model,
                "available_models": [self.settings.openai_model] if configured else [],
                "error": None if configured else "OPENAI_API_KEY not set",
            }

        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                model_present = any(
                    m == self.settings.ollama_model or m.startswith(f"{self.settings.ollama_model}:")
                    for m in models
                )
                return {
                    "provider": "ollama",
                    "connected": True,
                    "base_url": self.settings.ollama_base_url,
                    "active_model": self.settings.ollama_model,
                    "model_available": model_present,
                    "available_models": models,
                    "error": None
                    if model_present
                    else f"Ollama is running, but model '{self.settings.ollama_model}' is not pulled yet.",
                }
        except Exception as exc:
            return {
                "provider": "ollama",
                "connected": False,
                "base_url": self.settings.ollama_base_url,
                "active_model": self.settings.ollama_model,
                "model_available": False,
                "available_models": [],
                "error": f"Cannot reach Ollama at {self.settings.ollama_base_url}: {exc}",
            }

    async def invoke_structured(
        self,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
    ) -> LLMCallResult:
        """Invoke the configured LLM with strict Pydantic structured output and concurrency limit."""
        async with self._semaphore:
            started = time.perf_counter()
            try:
                model = self._build_chat_model()
                structured = model.with_structured_output(schema, include_raw=True)
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
                response = await asyncio.wait_for(
                    structured.ainvoke(messages),
                    timeout=self.settings.llm_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise LLMUnavailableError(
                    f"LLM request timed out after {self.settings.llm_timeout_seconds}s"
                ) from exc
            except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as exc:
                raise LLMUnavailableError(
                    f"LLM provider '{self.settings.llm_provider}' is unavailable: {exc}"
                ) from exc
            except LLMUnavailableError:
                raise
            except Exception as exc:
                err_text = str(exc).lower()
                if any(tok in err_text for tok in ("connection refused", "connect error", "failed to connect", "not found")):
                    raise LLMUnavailableError(
                        f"Ollama / LLM server error ({self.active_model_name}): {exc}"
                    ) from exc
                raise LLMProviderError(f"Structured LLM call failed: {exc}") from exc

            duration_ms = int((time.perf_counter() - started) * 1000)

            parsed = response.get("parsed") if isinstance(response, dict) else response
            parsing_error = response.get("parsing_error") if isinstance(response, dict) else None
            raw_msg = response.get("raw") if isinstance(response, dict) else None

            if parsing_error or parsed is None:
                raise LLMProviderError(
                    f"LLM failed to match Pydantic schema {schema.__name__}: {parsing_error}"
                )

            token_usage: dict[str, int] | None = None
            raw_content: str | None = None
            if raw_msg is not None:
                raw_content = getattr(raw_msg, "content", None)
                usage = getattr(raw_msg, "usage_metadata", None)
                if isinstance(usage, dict):
                    token_usage = {
                        k: int(v)
                        for k, v in usage.items()
                        if k in ("input_tokens", "output_tokens", "total_tokens") and isinstance(v, (int, float))
                    }

            return LLMCallResult(
                parsed=parsed,
                provider=self.settings.llm_provider,
                model=self.active_model_name,
                duration_ms=duration_ms,
                token_usage=token_usage,
                raw_content=raw_content if isinstance(raw_content, str) else None,
            )


_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = LLMProvider(get_settings())
    return _provider_instance


def reset_llm_provider() -> None:
    global _provider_instance
    _provider_instance = None
