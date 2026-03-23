"""
Mistral AI instrumentation (mistralai v1 SDK).

Monkey-patches ``mistralai.sync_client.Chat.complete`` and
``mistralai.async_client.AsyncChat.complete`` so every call is captured
as a ``provider_call`` event with surrounding run/span events.

Usage::

    from runledger_sdk import RunLedger
    rl = RunLedger(api_key="rl_live_...")
    rl.instrument_mistral()

    from mistralai import Mistral
    client = Mistral(api_key="...")
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": "Hello"}],
    )

Requires::

    pip install mistralai
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


def instrument_mistral(transport: SyncTransport) -> None:
    """
    Monkey-patch Mistral sync and async ``chat.complete`` methods.

    Safe to call multiple times — subsequent calls are no-ops.
    Requires the ``mistralai`` package (``pip install mistralai``).
    """
    global _patched
    if _patched:
        return

    try:
        import mistralai  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "mistralai package is required for Mistral instrumentation. "
            "Install it with: pip install mistralai"
        ) from exc

    _patch_sync(mistralai, transport)
    _patch_async(mistralai, transport)
    _patched = True
    log.info("runledger_mistral_instrumented")


def uninstrument_mistral() -> None:
    """Undo the monkey-patch. Primarily useful for testing."""
    global _patched
    if not _patched:
        return
    try:
        import mistralai  # noqa: PLC0415

        _restore_method(mistralai, sync=True)
        _restore_method(mistralai, sync=False)
    except ImportError:
        pass
    _patched = False


def _restore_method(mistralai: Any, sync: bool) -> None:
    try:
        cls = _get_chat_cls(mistralai, sync=sync)
        if cls is not None and hasattr(cls, "_rl_original_complete"):
            cls.complete = cls._rl_original_complete  # noqa: SLF001
            del cls._rl_original_complete  # noqa: SLF001
    except Exception:
        pass


def _get_chat_cls(mistralai: Any, sync: bool) -> Any:
    """Locate the Chat / AsyncChat class across different mistralai SDK layouts."""
    # v1 layout: mistralai.sdk.chat / mistralai.async_client ...
    # Try the most common paths
    candidates_sync = [
        ("mistralai.sdk.chat", "Chat"),
        ("mistralai.resources.chat", "Chat"),
        ("mistralai._sync.chat", "Chat"),
    ]
    candidates_async = [
        ("mistralai.sdk.chat", "AsyncChat"),
        ("mistralai.resources.chat", "AsyncChat"),
        ("mistralai._async.chat", "AsyncChat"),
    ]
    candidates = candidates_sync if sync else candidates_async
    import importlib  # noqa: PLC0415

    for mod_path, cls_name in candidates:
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name, None)
            if cls is not None:
                return cls
        except (ImportError, ModuleNotFoundError):
            continue
    return None


# ── Sync patch ─────────────────────────────────────────────────────────────────


def _patch_sync(mistralai: Any, transport: SyncTransport) -> None:
    chat_cls = _get_chat_cls(mistralai, sync=True)
    if chat_cls is None:
        log.warning(
            "runledger_mistral_sync_patch_skipped", reason="Chat class not found"
        )
        return

    original = chat_cls.complete
    chat_cls._rl_original_complete = original  # noqa: SLF001

    def patched_complete(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model") or (args[0] if args else "unknown")
        span_id = str(_uuid_mod.uuid4())
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, str(model), started_at))

        try:
            result = original(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", result))
            transport.enqueue(
                _build_provider_call(run_id, span_id, str(model), result, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(
                _build_provider_call_error(run_id, span_id, str(model), exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    chat_cls.complete = patched_complete


# ── Async patch ────────────────────────────────────────────────────────────────


def _patch_async(mistralai: Any, transport: SyncTransport) -> None:
    chat_cls = _get_chat_cls(mistralai, sync=False)
    if chat_cls is None:
        log.warning(
            "runledger_mistral_async_patch_skipped", reason="AsyncChat class not found"
        )
        return

    original_async = chat_cls.complete
    chat_cls._rl_original_complete = original_async  # noqa: SLF001

    async def patched_async_complete(self: Any, *args: Any, **kwargs: Any) -> Any:
        run_id = get_run_id()
        ctx = get_context_snapshot()
        model = kwargs.get("model") or (args[0] if args else "unknown")
        span_id = str(_uuid_mod.uuid4())
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, str(model), started_at))

        try:
            result = await original_async(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "succeeded", result))
            transport.enqueue(
                _build_provider_call(run_id, span_id, str(model), result, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(_build_span_end(run_id, span_id, "failed", None))
            transport.enqueue(
                _build_provider_call_error(run_id, span_id, str(model), exc, latency_ms)
            )
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise

    chat_cls.complete = patched_async_complete


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_text(result: Any) -> str | None:
    """Extract assistant message text from a Mistral ChatCompletion."""
    try:
        choices = getattr(result, "choices", None)
        if choices:
            content = getattr(choices[0].message, "content", None)
            if isinstance(content, str):
                return content
    except Exception:
        pass
    return None


def _extract_usage(result: Any) -> tuple[int | None, int | None]:
    """Return (input_tokens, output_tokens)."""
    usage = getattr(result, "usage", None)
    if usage is None:
        return None, None
    return getattr(usage, "prompt_tokens", None), getattr(
        usage, "completion_tokens", None
    )


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
        "name": f"mistral:{model}",
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
        "provider": "mistral",
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
        "provider": "mistral",
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
