"""
Google Gemini instrumentation (google-genai v2 SDK).

Monkey-patches ``google.genai.models.Models.generate_content`` and
``google.genai.models.AsyncModels.generate_content`` so every call is
captured as a ``provider_call`` event with surrounding run/span events.

Usage::

    from runledger_sdk import RunLedger
    rl = RunLedger(api_key="rl_live_...")
    rl.instrument_gemini()   # patches google.genai

    from google import genai
    client = genai.Client(api_key="...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Summarise Q1 spend.",
    )

Requires::

    pip install google-genai
"""

from __future__ import annotations

import importlib
import time
import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from runledger_sdk.context import get_context_snapshot, get_run_id
from runledger_sdk.openai import _sync_budget_check

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()

_patched = False


def instrument_gemini(transport: SyncTransport) -> None:
    """
    Monkey-patch ``google.genai.models.Models`` and ``AsyncModels``.

    Safe to call multiple times — subsequent calls are no-ops.
    Requires the ``google-genai`` package (``pip install google-genai``).
    """
    global _patched
    if _patched:
        return

    try:
        _genai_models = importlib.import_module("google.genai.models")
    except ImportError as exc:
        raise ImportError(
            "google-genai package is required for Gemini instrumentation. "
            "Install it with: pip install google-genai"
        ) from exc

    _patch_sync(_genai_models, transport)
    _patch_async(_genai_models, transport)
    _patched = True
    log.info("runledger_gemini_instrumented")


def uninstrument_gemini() -> None:
    """Undo the monkey-patch. Primarily useful for testing."""
    global _patched
    if not _patched:
        return
    try:
        _genai_models = importlib.import_module("google.genai.models")

        if hasattr(_genai_models.Models, "_rl_original_generate_content"):
            _genai_models.Models.generate_content = _genai_models.Models._rl_original_generate_content  # noqa: SLF001
            del _genai_models.Models._rl_original_generate_content  # noqa: SLF001

        if hasattr(_genai_models.AsyncModels, "_rl_original_generate_content"):
            _genai_models.AsyncModels.generate_content = _genai_models.AsyncModels._rl_original_generate_content  # noqa: SLF001
            del _genai_models.AsyncModels._rl_original_generate_content  # noqa: SLF001

    except ImportError:
        pass
    _patched = False


# ── Sync patch ─────────────────────────────────────────────────────────────────


def _patch_sync(genai_models: Any, transport: SyncTransport) -> None:
    models_cls = genai_models.Models
    original = models_cls.generate_content
    models_cls._rl_original_generate_content = original  # noqa: SLF001

    def patched_generate_content(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = _extract_model(args, kwargs)
        span_id = str(_uuid_mod.uuid4())
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = original(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", result))
            transport.enqueue(_build_provider_call(run_id, span_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(_build_provider_call_error(run_id, span_id, model, exc, latency_ms))
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    models_cls.generate_content = patched_generate_content


# ── Async patch ────────────────────────────────────────────────────────────────


def _patch_async(genai_models: Any, transport: SyncTransport) -> None:
    async_cls = genai_models.AsyncModels
    original_async = async_cls.generate_content
    async_cls._rl_original_generate_content = original_async  # noqa: SLF001

    async def patched_async_generate_content(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = _extract_model(args, kwargs)
        span_id = str(_uuid_mod.uuid4())
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = await original_async(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", result))
            transport.enqueue(_build_provider_call(run_id, span_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(_build_provider_call_error(run_id, span_id, model, exc, latency_ms))
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    async_cls.generate_content = patched_async_generate_content


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_model(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Extract model name from positional or keyword args."""
    model = kwargs.get("model")
    if model is None and len(args) >= 1:
        model = args[0]
    return str(model) if model else "unknown"


def _extract_text(result: Any) -> str | None:
    """Extract text from a Gemini GenerateContentResponse."""
    try:
        # google-genai v2: response.text is a convenience property
        text = getattr(result, "text", None)
        if isinstance(text, str):
            return text
        # Fallback: iterate candidates
        candidates = getattr(result, "candidates", None)
        if candidates:
            parts = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                if content:
                    for part in getattr(content, "parts", []):
                        t = getattr(part, "text", None)
                        if t:
                            parts.append(t)
            return "\n".join(parts) if parts else None
    except Exception:
        pass
    return None


def _extract_usage(result: Any) -> tuple[int | None, int | None, int | None]:
    """Return (input_tokens, output_tokens, cached_input_tokens) from response."""
    meta = getattr(result, "usage_metadata", None)
    if meta is None:
        return None, None, None
    input_tokens = getattr(meta, "prompt_token_count", None)
    output_tokens = getattr(meta, "candidates_token_count", None)
    cached = getattr(meta, "cached_content_token_count", None)
    return input_tokens, output_tokens, cached


# ── Event builders ─────────────────────────────────────────────────────────────


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
    for key in ("end_user_id", "session_id", "feature_tag", "deployment_version"):
        if ctx.get(key):
            event[key] = ctx[key]
    return event


def _build_span_start(
    run_id: str,
    span_id: str,
    model: str,
    started_at: datetime,
) -> dict[str, Any]:
    return {
        "event_type": "span_start",
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "llm",
        "name": f"google:{model}",
        "started_at": started_at.isoformat(),
    }


def _build_span_end(
    run_id: str,
    span_id: str,
    status: str,
    result: Any,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "span_end",
        "run_id": run_id,
        "span_id": span_id,
        "status": status,
        "ended_at": datetime.now(UTC).isoformat(),
    }
    if result is not None:
        text = _extract_text(result)
        if text:
            event["metadata"] = {"response": text}
    return event


def _build_provider_call(
    run_id: str,
    span_id: str,
    model: str,
    result: Any,
    latency_ms: int,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": "google",
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }
    input_tokens, output_tokens, cached = _extract_usage(result)
    if input_tokens is not None:
        event["input_tokens"] = input_tokens
    if output_tokens is not None:
        event["output_tokens"] = output_tokens
    if cached is not None:
        event["cached_input_tokens"] = cached
    return event


def _build_provider_call_error(
    run_id: str,
    span_id: str,
    model: str,
    exc: Exception,
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": "google",
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }


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
        input_tokens, output_tokens, _ = _extract_usage(result)
        if input_tokens is not None:
            event["total_input_tokens"] = input_tokens
        if output_tokens is not None:
            event["total_output_tokens"] = output_tokens
    return event
