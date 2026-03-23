"""
OpenAI client instrumentation.

Monkey-patches ``openai.OpenAI`` and ``openai.AsyncOpenAI`` so that every
``chat.completions.create`` call is automatically captured as a
``provider_call`` event with surrounding ``run_start`` / ``run_end`` events
and a ``span_start`` / ``span_end`` pair that carries the prompt and response
when the workspace privacy mode permits it.

Privacy modes (set in the dashboard under Ledger > Privacy)
-----------------------------------------------------------
METADATA_ONLY (default)  — tokens, model, latency only.  No messages/content.
ERRORS_ONLY              — payload stored only on failed/error calls.
SAMPLED                  — payload stored at the configured sampling rate.
FULL                     — full prompt messages + response stored on every call.

The SDK always transmits the payload to the API; the Celery pipeline decides
what to persist based on the workspace's CapturePolicy.

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
import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from runledger_sdk.context import get_context_snapshot, get_run_id
from runledger_sdk.exceptions import RunLedgerBudgetExceededError, ToolBlockedError

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
            setattr(completions_cls, "create", completions_cls._rl_original_create)
            del completions_cls._rl_original_create

        if hasattr(async_completions_cls, "_rl_original_create"):
            setattr(async_completions_cls, "create", async_completions_cls._rl_original_create)
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
        span_id = str(_uuid_mod.uuid4())
        messages = _safe_serialize(kwargs.get("messages", []))
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()
        provider = _detect_provider(str(getattr(self._client, "base_url", "")))

        # Pre-call budget check (optional, enabled by budget_check=True)
        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = original(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            # Runtime tool enforcement — check tool_calls in response before returning
            if transport.tool_enforcement:
                _check_response_tool_calls(result, transport)

            transport.enqueue(
                _build_span_end(run_id, span_id, "succeeded", messages, result)
            )
            transport.enqueue(
                _build_provider_call(
                    run_id, span_id, model, result, latency_ms, provider=provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except ToolBlockedError:
            # Re-raise blocked tool errors without wrapping them in run_end(failed)
            # so they surface clearly to the caller
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "failed", messages, None)
            )
            transport.enqueue(
                _build_provider_call_error(
                    run_id, span_id, model, exc, latency_ms, provider=provider
                )
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
        span_id = str(_uuid_mod.uuid4())
        messages = _safe_serialize(kwargs.get("messages", []))
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()
        provider = _detect_provider(str(getattr(self._client, "base_url", "")))

        # Pre-call budget check (optional, enabled by budget_check=True)
        if transport.budget_check and not transport._local:
            _sync_budget_check(transport, ctx, kwargs)

        # SyncTransport.enqueue is non-blocking (schedules on background thread)
        transport.enqueue(_build_run_start(run_id, ctx, started_at))
        transport.enqueue(_build_span_start(run_id, span_id, model, started_at))

        try:
            result = await original_async(self, *args, **kwargs)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            # Runtime tool enforcement — check tool_calls in response before returning
            if transport.tool_enforcement:
                _check_response_tool_calls(result, transport)

            transport.enqueue(
                _build_span_end(run_id, span_id, "succeeded", messages, result)
            )
            transport.enqueue(
                _build_provider_call(
                    run_id, span_id, model, result, latency_ms, provider=provider
                )
            )
            transport.enqueue(_build_run_end(run_id, "succeeded", result))
            return result
        except ToolBlockedError:
            transport.enqueue(_build_run_end(run_id, "failed", None))
            raise
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_span_end(run_id, span_id, "failed", messages, None)
            )
            transport.enqueue(
                _build_provider_call_error(
                    run_id, span_id, model, exc, latency_ms, provider=provider
                )
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


def _build_span_start(
    run_id: str,
    span_id: str,
    model: str,
    started_at: datetime,
) -> dict[str, Any]:
    """Span open event — creates the Span row in the DB."""
    return {
        "event_type": "span_start",
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "llm",
        "name": f"openai:{model}",
        "started_at": started_at.isoformat(),
    }


def _build_span_end(
    run_id: str,
    span_id: str,
    status: str,
    messages: list[Any],
    result: Any,
) -> dict[str, Any]:
    """Span close event — carries request messages and response content.

    The pipeline applies the workspace's CapturePolicy before storing
    ``span_metadata``; ``messages`` and ``response`` are only persisted
    when the mode is FULL, ERRORS_ONLY (on failure), or SAMPLED.
    """
    event: dict[str, Any] = {
        "event_type": "span_end",
        "run_id": run_id,
        "span_id": span_id,
        "status": status,
        "ended_at": datetime.now(UTC).isoformat(),
    }

    # Always include messages + response so the pipeline can apply policy.
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


def _detect_provider(base_url: str) -> str:
    """Infer the provider name from the OpenAI-client base URL."""
    url = base_url.lower()
    if "11434" in url or "ollama" in url:
        return "ollama"
    if "openai.com" in url:
        return "openai"
    if "anthropic.com" in url:
        return "anthropic"
    if "googleapis.com" in url or "generativelanguage" in url:
        return "google"
    if "x.ai" in url or "xai.com" in url:
        return "xai"
    if "mistral.ai" in url:
        return "mistral"
    if "cohere.com" in url:
        return "cohere"
    if "together.xyz" in url or "togetherai" in url:
        return "together"
    if "fireworks.ai" in url:
        return "fireworks"
    if "groq.com" in url:
        return "groq"
    if "perplexity.ai" in url:
        return "perplexity"
    # Derive from hostname for custom / self-hosted endpoints
    try:
        from urllib.parse import urlparse  # noqa: PLC0415

        host = urlparse(base_url).hostname or "unknown"
        parts = host.split(".")
        return parts[-2] if len(parts) >= 2 else host
    except Exception:
        return "unknown"


def _build_provider_call(
    run_id: str,
    span_id: str,
    model: str,
    result: Any,
    latency_ms: int,
    provider: str = "openai",
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

    # Provider request ID — e.g. "chatcmpl-abc123"; critical for invoice reconciliation
    req_id = getattr(result, "id", None)
    if req_id:
        event["provider_request_id"] = req_id

    usage = getattr(result, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)
        cached = (
            getattr(prompt_details, "cached_tokens", None) if prompt_details else None
        )

        if prompt_tokens is not None:
            event["input_tokens"] = prompt_tokens
        if completion_tokens is not None:
            event["output_tokens"] = completion_tokens
        if cached is not None:
            event["cached_input_tokens"] = cached

        # Token detail breakdowns (reasoning, audio tokens for billing transparency)
        if prompt_details:
            in_det: dict[str, int] = {}
            for f in ("cached_tokens", "audio_tokens", "text_tokens"):
                v = getattr(prompt_details, f, None)
                if v is not None:
                    in_det[f] = v
            if in_det:
                event["input_tokens_details"] = in_det

        if completion_details:
            out_det: dict[str, int] = {}
            for f in ("reasoning_tokens", "audio_tokens", "text_tokens"):
                v = getattr(completion_details, f, None)
                if v is not None:
                    out_det[f] = v
            if out_det:
                event["output_tokens_details"] = out_det

    return event


def _build_provider_call_error(
    run_id: str,
    span_id: str,
    model: str,
    exc: Exception,
    latency_ms: int,
    provider: str = "openai",
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "status": "error",
        "error_type": type(exc).__name__,
    }
    return event


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_serialize(obj: Any) -> Any:
    """Recursively convert obj to a JSON-safe structure.

    Handles Pydantic models (v1 .dict() / v2 .model_dump()), dicts, lists,
    and falls back to str() for any other type.
    """
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


# ── Runtime tool enforcement ───────────────────────────────────────────────────


def _check_response_tool_calls(result: Any, transport: SyncTransport) -> None:
    """
    Inspect an LLM response for tool_calls and check each tool name against
    the workspace Tool Registry policy.

    Called after the LLM responds but *before* returning to the caller, so the
    agent loop never gets to execute a blocked tool.

    Raises ToolBlockedError if any tool_call is blocked with runtime_enforcement=True.
    """
    from runledger_sdk.tool_check import check_tool_sync  # noqa: PLC0415

    choices = getattr(result, "choices", None) or []
    for choice in choices:
        if getattr(choice, "finish_reason", None) == "tool_calls":
            message = getattr(choice, "message", None)
            tool_calls = getattr(message, "tool_calls", None) or []
            for tc in tool_calls:
                func = getattr(tc, "function", None)
                tool_name = getattr(func, "name", None) if func else None
                if tool_name:
                    check_tool_sync(
                        tool_name, transport
                    )  # raises ToolBlockedError on block


# ── Budget pre-call check ──────────────────────────────────────────────────────


def _sync_budget_check(
    transport: SyncTransport,
    ctx: dict[str, str | None],
    kwargs: dict[str, Any],
) -> None:
    """
    Synchronous budget check against the RunLedger API.

    Raises RunLedgerBudgetExceededError if action='block'.
    Mutates kwargs['model'] in-place if action='downgrade'.
    Silently passes on any network / timeout error (fail open).
    """
    try:
        params: dict[str, str] = {}
        if ctx.get("end_user_id"):
            params["end_user_id"] = ctx["end_user_id"]  # type: ignore[assignment]
        if ctx.get("feature_tag"):
            params["feature_tag"] = ctx["feature_tag"]  # type: ignore[assignment]

        response = httpx.get(
            f"{transport._base_url}/budgets/check",
            params=params,
            headers={"Authorization": f"Bearer {transport._api_key}"},
            timeout=5.0,
        )
        if response.status_code != 200:
            log.warning("budget_check_non_200", status=response.status_code)
            return

        data = response.json()
        if not data.get("allowed", True):
            action = data.get("action")
            budget_id = data.get("budget_id", "unknown")
            if action == "block":
                raise RunLedgerBudgetExceededError(budget_id)
            if action == "downgrade":
                downgrade_model = data.get("downgrade_model")
                if downgrade_model:
                    kwargs["model"] = downgrade_model
                    log.info(
                        "budget_downgrade_applied",
                        budget_id=budget_id,
                        model=downgrade_model,
                    )
    except RunLedgerBudgetExceededError:
        raise
    except Exception as exc:
        # Fail open: never block the user's call due to budget check errors
        log.warning("budget_check_error", error=str(exc))
