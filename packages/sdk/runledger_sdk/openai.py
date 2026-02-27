"""
OpenAI client instrumentation.

Monkey-patches ``openai.OpenAI`` and ``openai.AsyncOpenAI`` so that every
``chat.completions.create`` call is automatically captured as a
``provider_call`` event with surrounding ``run_start`` / ``run_end`` events.

No payloads are transmitted in METADATA_ONLY mode (the default).

Usage::

    from runledger_sdk import RunLedger
    rl = RunLedger(api_key="rl_live_...")
    rl.instrument()

    import openai
    client = openai.OpenAI()
    # All subsequent calls are tracked automatically.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from runledger_sdk.context import get_context_snapshot, get_run_id

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()

# Tracks whether we've already patched to avoid double-patching.
_patched = False


def instrument_openai(transport: SyncTransport) -> None:
    """
    Monkey-patch ``openai.OpenAI`` and ``openai.AsyncOpenAI``.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _patched
    if _patched:
        return

    try:
        import openai  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "openai package is required for OpenAI instrumentation. "
            "Install it with: pip install openai"
        ) from exc

    _patch_sync_client(openai, transport)
    _patch_async_client(openai, transport)
    _patched = True
    log.info("runledger_openai_instrumented")


def uninstrument_openai() -> None:
    """Undo the monkey-patch. Primarily useful for testing."""
    global _patched
    if not _patched:
        return
    try:
        import openai  # noqa: PLC0415

        completions_cls = openai.resources.chat.completions.Completions
        async_completions_cls = openai.resources.chat.completions.AsyncCompletions

        if hasattr(completions_cls, "_rl_original_create"):
            completions_cls.create = completions_cls._rl_original_create
            del completions_cls._rl_original_create

        if hasattr(async_completions_cls, "_rl_original_create"):
            async_completions_cls.create = async_completions_cls._rl_original_create
            del async_completions_cls._rl_original_create

    except ImportError:
        pass

    _patched = False


# ── Sync patch ────────────────────────────────────────────────────────────────


def _patch_sync_client(openai: Any, transport: SyncTransport) -> None:
    completions_cls = openai.resources.chat.completions.Completions
    original = completions_cls.create
    completions_cls._rl_original_create = original  # noqa: SLF001

    def patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model", "unknown")
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        transport.enqueue(_build_run_start(run_id, ctx, started_at))

        try:
            result = original(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_provider_call(run_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_provider_call_error(run_id, model, exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    completions_cls.create = patched_create


# ── Async patch ───────────────────────────────────────────────────────────────


def _patch_async_client(openai: Any, transport: SyncTransport) -> None:
    async_completions_cls = openai.resources.chat.completions.AsyncCompletions
    original_async = async_completions_cls.create
    async_completions_cls._rl_original_create = original_async  # noqa: SLF001

    async def patched_async_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model", "unknown")
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        # SyncTransport.enqueue is non-blocking (schedules on background thread)
        transport.enqueue(_build_run_start(run_id, ctx, started_at))

        try:
            result = await original_async(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_provider_call(run_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_provider_call_error(run_id, model, exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    async_completions_cls.create = patched_async_create


# ── Event builders ────────────────────────────────────────────────────────────


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
    model: str,
    result: Any,
    latency_ms: int,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "provider": "openai",
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }
    usage = getattr(result, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        details = getattr(usage, "prompt_tokens_details", None)
        cached = getattr(details, "cached_tokens", None) if details else None

        if prompt_tokens is not None:
            event["input_tokens"] = prompt_tokens
        if completion_tokens is not None:
            event["output_tokens"] = completion_tokens
        if cached is not None:
            event["cached_input_tokens"] = cached
    return event


def _build_provider_call_error(
    run_id: str,
    model: str,
    exc: Exception,
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "event_type": "provider_call",
        "run_id": run_id,
        "provider": "openai",
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }
