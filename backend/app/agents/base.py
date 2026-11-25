import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from app.i18n import DEFAULT_LANGUAGE
from app.llm.provider import LLMUnavailableError, get_llm_provider
from app.prompts.system_prompts import get_system_prompt

T = TypeVar("T", bound=BaseModel)


@dataclass
class AgentCallMetadata:
    parsed: BaseModel
    mode: str
    provider: str
    model: str
    system_prompt: str
    user_prompt: str
    duration_ms: int
    token_usage: dict[str, int] | None


def _safe_emit_custom(payload: dict[str, Any]) -> None:
    try:
        writer = get_stream_writer()
        writer(payload)
    except Exception:
        # Outside a streaming context (e.g., direct unit test without stream_mode="custom")
        pass


async def run_structured_agent(
    *,
    agent_name: str,
    node_id: str,
    state: dict[str, Any],
    schema: type[T],
    user_prompt: str,
    demo_fn: Callable[[dict[str, Any]], Awaitable[T]],
) -> AgentCallMetadata:
    """Run an agent in either Demo Mode or Live Mode (Ollama / OpenAI-compatible).

    Never silently falls back to Demo Mode when Live Mode fails: raises LLMUnavailableError
    so the UI can notify the user and let them explicitly switch to Demo Mode if desired.
    """
    mode = state.get("mode", "demo")
    lang = state.get("language", DEFAULT_LANGUAGE)
    iteration = int(state.get("iteration", 1))
    system_prompt = get_system_prompt(agent_name, lang)
    provider = get_llm_provider()

    _safe_emit_custom(
        {
            "event_type": "llm_request_started",
            "node_id": node_id,
            "iteration": iteration,
            "payload": {
                "agent": agent_name,
                "mode": mode,
                "provider": "demo_deterministic" if mode == "demo" else provider.settings.llm_provider,
                "model": "demo-deterministic-v1" if mode == "demo" else provider.active_model_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            },
        }
    )

    started = time.perf_counter()
    if mode == "demo":
        parsed = await demo_fn(state)
        duration_ms = int((time.perf_counter() - started) * 1000)
        result = AgentCallMetadata(
            parsed=parsed,
            mode="demo",
            provider="demo_deterministic",
            model="demo-deterministic-v1",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            duration_ms=duration_ms,
            token_usage=None,
        )
    else:
        try:
            llm_res = await provider.invoke_structured(
                schema=schema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except LLMUnavailableError as exc:
            _safe_emit_custom(
                {
                    "event_type": "error",
                    "node_id": node_id,
                    "iteration": iteration,
                    "payload": {
                        "agent": agent_name,
                        "error_type": "LLMUnavailableError",
                        "message": str(exc),
                        "can_switch_to_demo": True,
                    },
                }
            )
            raise
        result = AgentCallMetadata(
            parsed=llm_res.parsed,
            mode="live",
            provider=llm_res.provider,
            model=llm_res.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            duration_ms=llm_res.duration_ms,
            token_usage=llm_res.token_usage,
        )

    _safe_emit_custom(
        {
            "event_type": "llm_response_received",
            "node_id": node_id,
            "iteration": iteration,
            "payload": {
                "agent": agent_name,
                "mode": result.mode,
                "provider": result.provider,
                "model": result.model,
                "duration_ms": result.duration_ms,
                "token_usage": result.token_usage,
                "structured_output": result.parsed.model_dump(),
            },
        }
    )
    return result
