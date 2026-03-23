"""
Cohere instrumentation (cohere-ai v5 SDK, ClientV2).

Monkey-patches ``cohere.ClientV2.chat`` and ``cohere.AsyncClientV2.chat``
so every call is captured as a ``provider_call`` event with surrounding
run/span events.

Usage::

    from runledger_sdk import RunLedger
    rl = RunLedger(api_key="rl_live_...")
    rl.instrument_cohere()

    import cohere
    co = cohere.ClientV2(api_key="...")
    response = co.chat(
        model="command-r-plus",
        messages=[{"role": "user", "content": "Hello"}],
    )

Requires::

    pip install cohere
"""

from __future__ import annotations

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


def instrument_cohere(transport: SyncTransport) -> None:
    """
    Monkey-patch ``cohere.ClientV2.chat`` and ``cohere.AsyncClientV2.chat``.

    Safe to call multiple times — subsequent calls are no-ops.
    Requires the ``cohere`` package (``pip install cohere``).
    """
    global _patched
    if _patched:
        return

    try:
        import cohere  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "cohere package is required for Cohere instrumentation. "
            "Install it with: pip install cohere"
        ) from exc

    _patch_sync(cohere, transport)
    _patch_async(cohere, transport)
    _patched = True
    log.info("runledger_cohere_instrumented")


def uninstrument_cohere() -> None:
    """Undo the monkey-patch. Primarily useful for testing."""
    global _patched
    if not _patched:
        return
    try:
        import cohere  # noqa: PLC0415

        for cls_name, method_name in [("ClientV2", "chat"), ("AsyncClientV2", "chat")]:
            cls = getattr(cohere, cls_name, None)
            if cls is not None and hasattr(cls, "_rl_original_chat"):
                setattr(cls, method_name, cls._rl_original_chat)  # noqa: SLF001
                del cls._rl_original_chat  # noqa: SLF001
    except ImportError:
        pass
    _patched = False


# ── Sync patch ─────────────────────────────────────────────────────────────────


def _patch_sync(cohere: Any, transport: SyncTransport) -> None:
    client_cls = getattr(cohere, "ClientV2", None)
    if client_cls is None:
        log.warning("runledger_cohere_sync_patch_skipped", reason="ClientV2 not found")
        return

    original = client_cls.chat
    client_cls._rl_original_chat = original  # noqa: SLF001

    def patched_chat(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = str(kwargs.get("model") or (args[0] if args else "unknown"))
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
            transport.enqueue(
                _build_provider_call(run_id, span_id, model, result, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(
                _build_provider_call_error(run_id, span_id, model, exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    client_cls.chat = patched_chat


# ── Async patch ────────────────────────────────────────────────────────────────


def _patch_async(cohere: Any, transport: SyncTransport) -> None:
    async_cls = getattr(cohere, "AsyncClientV2", None)
    if async_cls is None:
        log.warning(
            "runledger_cohere_async_patch_skipped", reason="AsyncClientV2 not found"
        )
        return

    original_async = async_cls.chat
    async_cls._rl_original_chat = original_async  # noqa: SLF001

    async def patched_async_chat(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = str(kwargs.get("model") or (args[0] if args else "unknown"))
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
            transport.enqueue(
                _build_provider_call(run_id, span_id, model, result, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(
                _build_provider_call_error(run_id, span_id, model, exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    async_cls.chat = patched_async_chat


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_text(result: Any) -> str | None:
    """Extract text from a Cohere v2 ChatResponse."""
    try:
        # v5 API: response.message.content is a list of ContentBlock
        message = getattr(result, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, list) and content:
                texts = [
                    getattr(block, "text", "")
                    for block in content
                    if hasattr(block, "text")
                ]
                return "\n".join(t for t in texts if t) or None
    except Exception:
        pass
    return None


def _extract_usage(result: Any) -> tuple[int | None, int | None]:
    """Return (input_tokens, output_tokens) from Cohere v2 response."""
    try:
        usage = getattr(result, "usage", None)
        if usage is not None:
            # v5: usage.tokens.input_tokens / usage.tokens.output_tokens
            tokens = getattr(usage, "tokens", None)
            if tokens is not None:
                return getattr(tokens, "input_tokens", None), getattr(
                    tokens, "output_tokens", None
                )
            # Fallback: billed_units
            billed = getattr(usage, "billed_units", None)
            if billed is not None:
                return getattr(billed, "input_tokens", None), getattr(
                    billed, "output_tokens", None
                )
    except Exception:
        pass
    return None, None


# ── Event builders ─────────────────────────────────────────────────────────────


def _build_run_start(
    run_id: str, ctx: dict[str, str | None], started_at: datetime
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
    run_id: str, span_id: str, model: str, started_at: datetime
) -> dict[str, Any]:
    return {
        "event_type": "span_start",
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "llm",
        "name": f"cohere:{model}",
        "started_at": started_at.isoformat(),
    }


def _build_span_end(
    run_id: str, span_id: str, status: str, result: Any
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
    run_id: str, span_id: str, model: str, result: Any, latency_ms: int
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": "cohere",
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }
    input_tokens, output_tokens = _extract_usage(result)
    if input_tokens is not None:
        event["input_tokens"] = input_tokens
    if output_tokens is not None:
        event["output_tokens"] = output_tokens
    return event


def _build_provider_call_error(
    run_id: str, span_id: str, model: str, exc: Exception, latency_ms: int
) -> dict[str, Any]:
    return {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": "cohere",
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }


def _build_run_end(run_id: str, status: str, result: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "run_end",
        "run_id": run_id,
        "status": status,
        "ended_at": datetime.now(UTC).isoformat(),
    }
    if result is not None:
        input_tokens, output_tokens = _extract_usage(result)
        if input_tokens is not None:
            event["total_input_tokens"] = input_tokens
        if output_tokens is not None:
            event["total_output_tokens"] = output_tokens
    return event
