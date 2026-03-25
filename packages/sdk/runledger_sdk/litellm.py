"""
LiteLLM instrumentation.

Monkey-patches ``litellm.completion`` and ``litellm.acompletion`` so every
provider call is automatically captured as a ``provider_call`` event with
surrounding ``run_start`` / ``run_end`` events and a ``span_start`` /
``span_end`` pair that carries the prompt and response.

LiteLLM abstracts 100+ providers (OpenAI, Anthropic, Gemini, Mistral,
Bedrock, Groq, Ollama, Azure, Vertex AI, Together AI, …) behind a single
API.  RunLedger detects the provider from the LiteLLM model name prefix and
records each call with the correct provider for accurate cost attribution.

LiteLLM also exposes a computed ``response_cost`` on each response via
``result._hidden_params["response_cost"]``.  RunLedger captures this as
``reported_cost_usd`` (cost_source="litellm"), giving you a second cost
signal that complements RunLedger's own pricing-engine calculation.

Usage::

    from runledger_sdk import RunLedger

    rl = RunLedger(api_key="rl_live_...")
    rl.instrument_litellm()

    import litellm

    response = litellm.completion(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    # Also works with any other provider — provider is auto-detected:
    response = litellm.completion(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    response = litellm.completion(
        model="gemini/gemini-1.5-pro",
        messages=[{"role": "user", "content": "Hello!"}],
    )

LiteLLM Proxy Gateway coexistence::

    # If you run a LiteLLM Proxy, point an OpenAI client at the proxy URL
    # and use rl.instrument() — the SDK intercepts all openai.* calls
    # regardless of which backend the proxy routes them to.

    import openai
    client = openai.OpenAI(
        base_url="http://localhost:4000/v1",
        api_key="any-string",            # LiteLLM proxy key (if set)
    )
    rl.instrument()  # intercepts client.chat.completions.create(...)

    # See examples/32_litellm_proxy.py for the full walkthrough.
"""

from __future__ import annotations

import time
import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from runledger_sdk.context import get_context_snapshot, get_run_id

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()

# Prevents double-patching across multiple rl.instrument_litellm() calls.
_patched = False


def instrument_litellm(transport: SyncTransport) -> None:
    """
    Monkey-patch ``litellm.completion`` and ``litellm.acompletion``.

    Safe to call multiple times — subsequent calls are no-ops.
    Raises ``ImportError`` if the ``litellm`` package is not installed.
    """
    global _patched
    if _patched:
        return

    try:
        import litellm  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "litellm package is required for LiteLLM instrumentation. "
            "Install it with: pip install litellm"
        ) from exc

    _patch_sync(litellm, transport)
    _patch_async(litellm, transport)
    _patched = True
    log.info("runledger_litellm_instrumented")


def uninstrument_litellm() -> None:
    """Undo the monkey-patch.  Primarily useful in tests."""
    global _patched
    if not _patched:
        return
    try:
        import litellm  # noqa: PLC0415

        if hasattr(litellm, "_rl_original_completion"):
            litellm.completion = litellm._rl_original_completion  # noqa: SLF001
            del litellm._rl_original_completion  # noqa: SLF001

        if hasattr(litellm, "_rl_original_acompletion"):
            litellm.acompletion = litellm._rl_original_acompletion  # noqa: SLF001
            del litellm._rl_original_acompletion  # noqa: SLF001

    except ImportError:
        pass

    _patched = False


# ── Sync patch ────────────────────────────────────────────────────────────────


def _patch_sync(litellm: Any, transport: SyncTransport) -> None:
    original = litellm.completion
    litellm._rl_original_completion = original  # noqa: SLF001

    def patched_completion(*args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model: str = kwargs.get("model", args[0] if args else "unknown")
        span_id = str(_uuid_mod.uuid4())
        messages = _safe_serialize(kwargs.get("messages", []))
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()
        provider = _detect_provider(model)

        # Pre-call budget check (optional, enabled via budget_check=True)
        if transport.budget_check and not transport._local:
            from runledger_sdk.openai import _sync_budget_check  # noqa: PLC0415

            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(
            _build_span_start(run_id, span_id, model, started_at, provider)
        )

        try:
            result = original(*args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "succeeded", messages, result)
            )
            transport.enqueue(
                _build_provider_call(
                    run_id, span_id, model, result, latency_ms, provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "failed", messages, None)
            )
            transport.enqueue(
                _build_provider_call_error(
                    run_id, span_id, model, exc, latency_ms, provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    litellm.completion = patched_completion


# ── Async patch ───────────────────────────────────────────────────────────────


def _patch_async(litellm: Any, transport: SyncTransport) -> None:
    original_async = litellm.acompletion
    litellm._rl_original_acompletion = original_async  # noqa: SLF001

    async def patched_acompletion(*args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model: str = kwargs.get("model", args[0] if args else "unknown")
        span_id = str(_uuid_mod.uuid4())
        messages = _safe_serialize(kwargs.get("messages", []))
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()
        provider = _detect_provider(model)

        # Pre-call budget check (SyncTransport.enqueue is non-blocking)
        if transport.budget_check and not transport._local:
            from runledger_sdk.openai import _sync_budget_check  # noqa: PLC0415

            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(
            _build_span_start(run_id, span_id, model, started_at, provider)
        )

        try:
            result = await original_async(*args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "succeeded", messages, result)
            )
            transport.enqueue(
                _build_provider_call(
                    run_id, span_id, model, result, latency_ms, provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "failed", messages, None)
            )
            transport.enqueue(
                _build_provider_call_error(
                    run_id, span_id, model, exc, latency_ms, provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    litellm.acompletion = patched_acompletion


# ── Provider detection ────────────────────────────────────────────────────────


def _detect_provider(model: str) -> str:
    """
    Infer the provider name from a LiteLLM model string.

    LiteLLM model naming conventions
    ---------------------------------
    Explicit prefix  →  "provider/model-name"
      azure/gpt-4, anthropic/claude-3-5-sonnet-20241022,
      bedrock/amazon.titan-text-express-v1, vertex_ai/gemini-1.5-pro,
      groq/llama3-70b-8192, ollama/llama3, together_ai/meta-llama/…

    Bare model name  →  OpenAI / Anthropic / Cohere convention
      gpt-4o, gpt-3.5-turbo, o1-preview   → openai
      claude-3-5-sonnet-20241022           → anthropic
      command-r-plus                       → cohere
      mistral-large-latest                 → mistral
      gemini-1.5-pro                       → google
    """
    m = model.lower()

    # ── Explicit provider prefix (provider/model) ─────────────────────────────
    if "/" in m:
        prefix = m.split("/")[0]
        _PREFIX_MAP: dict[str, str] = {
            "anthropic": "anthropic",
            "gemini": "google",
            "vertex_ai": "google",
            "vertex_ai_beta": "google",
            "azure": "azure",
            "azure_ai": "azure",
            "mistral": "mistral",
            "groq": "groq",
            "ollama": "ollama",
            "ollama_chat": "ollama",
            "bedrock": "bedrock",
            "together_ai": "together",
            "cohere": "cohere",
            "fireworks_ai": "fireworks",
            "perplexity": "perplexity",
            "ai21": "ai21",
            "huggingface": "huggingface",
            "replicate": "replicate",
            "cloudflare": "cloudflare",
            "openrouter": "openrouter",
            "deepinfra": "deepinfra",
            "anyscale": "anyscale",
            "vllm": "vllm",
            "predibase": "predibase",
            "watsonx": "watsonx",
            "sagemaker": "sagemaker",
        }
        provider = _PREFIX_MAP.get(prefix)
        if provider:
            return provider
        # Unknown prefix — use it directly (self-hosted / custom)
        return prefix

    # ── Bare model name heuristics ────────────────────────────────────────────
    if m.startswith(("gpt-", "o1", "o3", "o4-", "text-", "davinci", "chatgpt")):
        return "openai"
    if m.startswith("claude-"):
        return "anthropic"
    if m.startswith(("gemini-", "palm-", "bison")):
        return "google"
    if m.startswith(("mistral-", "mixtral-", "codestral-")):
        return "mistral"
    if m.startswith(("command-", "c4ai-")):
        return "cohere"
    if m.startswith(("j2-", "jamba-")):
        return "ai21"
    if m.startswith("llama"):
        return "meta"

    return "unknown"


# ── Event builders ────────────────────────────────────────────────────────────
# Same envelope as the OpenAI wrapper — identical schema understood by the
# RunLedger pipeline.


def _build_run_start(
    run_id: str,
    ctx: dict[str, str | None],
    started_at: datetime,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "run_start",
        "run_id": run_id,
        "started_at": started_at.isoformat(),
    }
    if ctx.get("end_user_id"):
        event["end_user_id"] = ctx["end_user_id"]
    if ctx.get("session_id"):
        event["session_id"] = ctx["session_id"]
    if ctx.get("feature_tag"):
        event["feature_tag"] = ctx["feature_tag"]
    if ctx.get("deployment_version"):
        event["deployment_version"] = ctx["deployment_version"]
    return event


def _build_span_start(
    run_id: str,
    span_id: str,
    model: str,
    started_at: datetime,
    provider: str = "litellm",
) -> dict[str, Any]:
    return {
        "event_type": "span_start",
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "llm",
        "name": f"{provider}:{model}",
        "started_at": started_at.isoformat(),
    }


def _build_span_end(
    run_id: str,
    span_id: str,
    status: str,
    messages: list[Any],
    result: Any,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "span_end",
        "run_id": run_id,
        "span_id": span_id,
        "status": status,
        "ended_at": datetime.now(UTC).isoformat(),
    }
    metadata: dict[str, Any] = {"messages": messages}
    if result is not None:
        choices = getattr(result, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            content = getattr(message, "content", None) if message else None
            finish_reason = getattr(first, "finish_reason", None)
            if content is not None:
                metadata["response"] = content
            if finish_reason is not None:
                metadata["finish_reason"] = finish_reason
    event["metadata"] = metadata
    return event


def _build_run_end(
    run_id: str,
    status: str,
    result: Any,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "run_end",
        "run_id": run_id,
        "status": status,
        "ended_at": datetime.now(UTC).isoformat(),
    }
    if result is not None:
        usage = getattr(result, "usage", None)
        if usage:
            total_in = getattr(usage, "prompt_tokens", None)
            total_out = getattr(usage, "completion_tokens", None)
            if total_in is not None:
                event["total_input_tokens"] = total_in
            if total_out is not None:
                event["total_output_tokens"] = total_out
    return event


def _build_provider_call(
    run_id: str,
    span_id: str,
    model: str,
    result: Any,
    latency_ms: int,
    provider: str = "litellm",
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }

    # Provider request ID (e.g. "chatcmpl-abc123" from OpenAI via LiteLLM)
    req_id = getattr(result, "id", None)
    if req_id:
        event["provider_request_id"] = req_id

    usage = getattr(result, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        if prompt_tokens is not None:
            event["input_tokens"] = prompt_tokens
        if completion_tokens is not None:
            event["output_tokens"] = completion_tokens

    # LiteLLM computes a cost estimate on every response — capture it as a
    # second cost signal alongside RunLedger's pricing-engine calculation.
    hidden: dict[str, Any] | None = getattr(result, "_hidden_params", None)
    if isinstance(hidden, dict):
        response_cost = hidden.get("response_cost")
        if response_cost is not None:
            event["reported_cost_usd"] = str(response_cost)
            event["cost_source"] = "litellm"

    return event


def _build_provider_call_error(
    run_id: str,
    span_id: str,
    model: str,
    exc: Exception,
    latency_ms: int,
    provider: str = "litellm",
) -> dict[str, Any]:
    return {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_serialize(obj: Any) -> Any:
    """Recursively convert obj to a JSON-safe structure."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(i) for i in obj]
    if hasattr(obj, "model_dump"):  # Pydantic v2
        return _safe_serialize(obj.model_dump())
    if hasattr(obj, "dict"):  # Pydantic v1
        return _safe_serialize(obj.dict())
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
