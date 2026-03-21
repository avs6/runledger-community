"""
Anthropic client instrumentation.

Monkey-patches ``anthropic.Anthropic`` and ``anthropic.AsyncAnthropic`` so that every
``messages.create`` call is automatically captured as a ``provider_call`` event with
surrounding ``run_start``/``run_end`` and ``span_start``/``span_end`` pairs.

Usage::

    from runledger_sdk import RunLedger
    rl = RunLedger(api_key="rl_live_...")
    rl.instrument()          # patches OpenAI
    rl.instrument_anthropic()  # patches Anthropic

    import anthropic
    client = anthropic.Anthropic()
    # All subsequent messages.create calls are tracked automatically.
"""

from __future__ import annotations

import time
import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from runledger_sdk.context import get_context_snapshot, get_run_id
from runledger_sdk.openai import _sync_budget_check, _safe_serialize

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()

_patched = False


def instrument_anthropic(transport: SyncTransport) -> None:
    """
    Monkey-patch ``anthropic.resources.messages.Messages`` and
    ``anthropic.resources.messages.AsyncMessages``.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _patched
    if _patched:
        return

    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "anthropic package is required for Anthropic instrumentation. "
            "Install it with: pip install anthropic"
        ) from exc

    _patch_sync(anthropic, transport)
    _patch_async(anthropic, transport)
    _patched = True
    log.info("runledger_anthropic_instrumented")


def uninstrument_anthropic() -> None:
    """Undo the monkey-patch. Primarily useful for testing."""
    global _patched
    if not _patched:
        return
    try:
        import anthropic  # noqa: PLC0415

        messages_cls = anthropic.resources.messages.Messages
        async_messages_cls = anthropic.resources.messages.AsyncMessages

        if hasattr(messages_cls, "_rl_original_create"):
            messages_cls.create = messages_cls._rl_original_create
            del messages_cls._rl_original_create

        if hasattr(async_messages_cls, "_rl_original_create"):
            async_messages_cls.create = async_messages_cls._rl_original_create
            del async_messages_cls._rl_original_create

    except ImportError:
        pass
    _patched = False


# ── Sync patch ─────────────────────────────────────────────────────────────────


def _patch_sync(anthropic: Any, transport: SyncTransport) -> None:
    messages_cls = anthropic.resources.messages.Messages
    original = messages_cls.create
    messages_cls._rl_original_create = original  # noqa: SLF001

    def patched_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model", "unknown")
        span_id = str(_uuid_mod.uuid4())
        messages = _build_messages_payload(kwargs)
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = original(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", messages, result))
            transport.enqueue(_build_provider_call(run_id, span_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", messages, None))
            transport.enqueue(_build_provider_call_error(run_id, span_id, model, exc, latency_ms))
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    messages_cls.create = patched_create


# ── Async patch ────────────────────────────────────────────────────────────────


def _patch_async(anthropic: Any, transport: SyncTransport) -> None:
    async_messages_cls = anthropic.resources.messages.AsyncMessages
    original_async = async_messages_cls.create
    async_messages_cls._rl_original_create = original_async  # noqa: SLF001

    async def patched_async_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model", "unknown")
        span_id = str(_uuid_mod.uuid4())
        messages = _build_messages_payload(kwargs)
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = await original_async(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", messages, result))
            transport.enqueue(_build_provider_call(run_id, span_id, model, result, latency_ms))
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", messages, None))
            transport.enqueue(_build_provider_call_error(run_id, span_id, model, exc, latency_ms))
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    async_messages_cls.create = patched_async_create


# ── Event builders ─────────────────────────────────────────────────────────────


def _build_messages_payload(kwargs: dict[str, Any]) -> list[Any]:
    """Build a unified messages list including system prompt if present."""
    msgs = _safe_serialize(kwargs.get("messages", []))
    system = kwargs.get("system")
    if system:
        # Prepend as a synthetic system message for consistency with OpenAI format
        if isinstance(system, str):
            msgs = [{"role": "system", "content": system}] + msgs
        elif isinstance(system, list):
            # List of content blocks — join text parts
            text = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in system
            )
            msgs = [{"role": "system", "content": text}] + msgs
    return msgs


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
        "name": f"anthropic:{model}",
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
        response_text = _extract_text(result)
        if response_text:
            metadata["response"] = response_text
        stop_reason = getattr(result, "stop_reason", None)
        if stop_reason:
            metadata["finish_reason"] = stop_reason
    event["metadata"] = metadata
    return event


def _extract_text(result: Any) -> str | None:
    """Extract text content from an Anthropic Message response."""
    content = getattr(result, "content", None)
    if not content:
        return None
    parts: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(getattr(block, "text", ""))
        elif block_type == "tool_use":
            # Include tool name so it's visible in payload viewer
            name = getattr(block, "name", "tool")
            parts.append(f"[tool_use:{name}]")
    return "\n".join(parts) if parts else None


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
            in_tok = getattr(usage, "input_tokens", None)
            out_tok = getattr(usage, "output_tokens", None)
            if in_tok is not None:
                event["total_input_tokens"] = in_tok
            if out_tok is not None:
                event["total_output_tokens"] = out_tok
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
        "provider": "anthropic",
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }
    usage = getattr(result, "usage", None)
    if usage:
        in_tok = getattr(usage, "input_tokens", None)
        out_tok = getattr(usage, "output_tokens", None)
        cache_read = getattr(usage, "cache_read_input_tokens", None)
        if in_tok is not None:
            event["input_tokens"] = in_tok
        if out_tok is not None:
            event["output_tokens"] = out_tok
        if cache_read is not None:
            event["cached_input_tokens"] = cache_read
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
        "provider": "anthropic",
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }
