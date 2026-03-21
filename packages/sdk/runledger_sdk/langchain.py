"""
LangChain instrumentation for RunLedger.

``RunLedgerCallbackHandler`` implements LangChain's ``BaseCallbackHandler``
interface and turns every chain/LLM/tool invocation into RunLedger spans.

Usage::

    from runledger_sdk import RunLedger
    from runledger_sdk.langchain import RunLedgerCallbackHandler

    rl = RunLedger(api_key="rl_live_...")
    handler = rl.callback_handler()

    chain = prompt | llm
    chain.invoke({"question": "..."}, config={"callbacks": [handler]})

Span mapping
────────────
LangChain fires ``run_id`` (UUID) per callback event and ``parent_run_id``
for nesting.  We map these directly to RunLedger ``span_id`` /
``parent_span_id`` so the full DAG is reconstructed on the server.

The overall RunLedger ``run_id`` (the outermost run) is taken from the
contextvars context (``get_run_id()``), or generated fresh for the root chain.
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

# ── BaseCallbackHandler stub (replaced if langchain_core is installed) ────────

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Minimal stub used when langchain_core is not installed."""

        raise_error: bool = False

        def on_chain_start(self, *a: Any, **kw: Any) -> None: ...
        def on_chain_end(self, *a: Any, **kw: Any) -> None: ...
        def on_chain_error(self, *a: Any, **kw: Any) -> None: ...
        def on_llm_start(self, *a: Any, **kw: Any) -> None: ...
        def on_llm_end(self, *a: Any, **kw: Any) -> None: ...
        def on_llm_error(self, *a: Any, **kw: Any) -> None: ...
        def on_tool_start(self, *a: Any, **kw: Any) -> None: ...
        def on_tool_end(self, *a: Any, **kw: Any) -> None: ...
        def on_tool_error(self, *a: Any, **kw: Any) -> None: ...
        def on_agent_action(self, *a: Any, **kw: Any) -> None: ...
        def on_agent_finish(self, *a: Any, **kw: Any) -> None: ...


# ── Internal span state ───────────────────────────────────────────────────────


class _SpanState:
    __slots__ = ("span_id", "run_id", "start_time", "started_at", "name", "span_type")

    def __init__(self, span_id: str, run_id: str, name: str, span_type: str) -> None:
        self.span_id = span_id
        self.run_id = run_id
        self.name = name
        self.span_type = span_type
        self.start_time: float = time.perf_counter()
        self.started_at: str = datetime.now(UTC).isoformat()


# ── RunLedgerCallbackHandler ──────────────────────────────────────────────────


class RunLedgerCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """
    LangChain callback handler that emits RunLedger span and provider events.

    Parameters
    ----------
    transport:
        The RunLedger ``SyncTransport`` instance (from ``rl._get_sync_transport()``).
    track_llm_cost:
        If True (default), emit a ``provider_call`` event from ``on_llm_end``.
        Set to False if you're also using ``rl.instrument()`` (OpenAI patch) to
        avoid duplicate provider_call events.
    """

    def __init__(
        self,
        transport: SyncTransport,
        *,
        track_llm_cost: bool = True,
    ) -> None:
        self._transport = transport
        self._track_llm_cost = track_llm_cost

        # Keyed by str(lc_run_id) → _SpanState
        self._spans: dict[str, _SpanState] = {}
        # The LC run_id of the outermost call (parent_run_id=None)
        self._root_lc_run_id: str | None = None
        # The RunLedger run_id captured at root chain start
        self._rl_run_id: str | None = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _lc_key(self, run_id: Any) -> str:
        return str(run_id)

    def _get_rl_run_id(self) -> str:
        if self._rl_run_id:
            return self._rl_run_id
        return get_run_id()

    def _open_span(
        self,
        lc_run_id: Any,
        lc_parent_run_id: Any,
        span_type: str,
        name: str,
    ) -> _SpanState:
        run_id = self._get_rl_run_id()
        key = self._lc_key(lc_run_id)
        span_id = key  # use LC run_id as span_id for exact parent-child linking
        parent_span_id = self._lc_key(lc_parent_run_id) if lc_parent_run_id else None

        state = _SpanState(
            span_id=span_id, run_id=run_id, name=name, span_type=span_type
        )
        self._spans[key] = state

        event: dict[str, Any] = {
            "event_type": "span_start",
            "span_id": span_id,
            "run_id": run_id,
            "span_type": span_type,
            "name": name,
            "started_at": state.started_at,
        }
        if parent_span_id:
            event["parent_span_id"] = parent_span_id

        self._transport.enqueue(event)
        return state

    def _close_span(
        self,
        lc_run_id: Any,
        status: str,
        cost_usd: str | None = None,
    ) -> None:
        key = self._lc_key(lc_run_id)
        state = self._spans.pop(key, None)
        if state is None:
            return

        event: dict[str, Any] = {
            "event_type": "span_end",
            "span_id": key,
            "run_id": state.run_id,
            "status": status,
            "ended_at": datetime.now(UTC).isoformat(),
        }
        if cost_usd is not None:
            event["cost_usd"] = cost_usd

        self._transport.enqueue(event)

    def _fire_run_start(self, ctx: dict[str, str | None]) -> None:
        event: dict[str, Any] = {
            "event_type": "run_start",
            "run_id": self._get_rl_run_id(),
            "started_at": datetime.now(UTC).isoformat(),
        }
        for key in ("end_user_id", "session_id", "feature_tag", "deployment_version"):
            val = ctx.get(key)
            if val:
                event[key] = val
        self._transport.enqueue(event)

    def _fire_run_end(self, status: str) -> None:
        self._transport.enqueue(
            {
                "event_type": "run_end",
                "run_id": self._get_rl_run_id(),
                "status": status,
                "ended_at": datetime.now(UTC).isoformat(),
            }
        )

    # ── Chain callbacks ───────────────────────────────────────────────────────

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        is_root = parent_run_id is None

        if is_root and self._root_lc_run_id is None:
            self._root_lc_run_id = self._lc_key(run_id)
            self._rl_run_id = get_run_id()
            ctx = get_context_snapshot()
            self._fire_run_start(ctx)

        name = (serialized or {}).get("name") or (serialized or {}).get(
            "id", ["chain"]
        )[-1]
        self._open_span(run_id, parent_run_id, "chain", str(name))

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "succeeded")

        if self._lc_key(run_id) == self._root_lc_run_id:
            self._fire_run_end("succeeded")
            self._root_lc_run_id = None
            self._rl_run_id = None

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "failed")

        if self._lc_key(run_id) == self._root_lc_run_id:
            self._fire_run_end("failed")
            self._root_lc_run_id = None
            self._rl_run_id = None

    # ── LLM callbacks ─────────────────────────────────────────────────────────

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name") or "llm"
        self._open_span(run_id, parent_run_id, "llm", str(name))

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        key = self._lc_key(run_id)
        state = self._spans.get(key)

        if state and self._track_llm_cost:
            latency_ms = int((time.perf_counter() - state.start_time) * 1000)
            provider_event = _build_provider_call_from_llm_result(
                run_id=state.run_id,
                span_id=key,
                model=state.name,
                result=response,
                latency_ms=latency_ms,
            )
            self._transport.enqueue(provider_event)

        self._close_span(run_id, "succeeded")

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "failed")

    # ── Tool callbacks ────────────────────────────────────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        name = (serialized or {}).get("name") or "tool"

        # Runtime tool enforcement — check policy *before* the tool executes.
        # Raises ToolBlockedError which propagates up through the LangChain
        # callback system and into the agent loop as an exception.
        if getattr(self._transport, "tool_enforcement", False):
            from runledger_sdk.tool_check import check_tool_sync  # noqa: PLC0415

            check_tool_sync(str(name), self._transport)

        self._open_span(run_id, parent_run_id, "tool", str(name))

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "succeeded")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "failed")

    # ── Agent callbacks ───────────────────────────────────────────────────────

    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        tool_name = getattr(action, "tool", None) or "agent_action"
        self._open_span(run_id, parent_run_id, "agent", str(tool_name))

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._close_span(run_id, "succeeded")

        # Emit an outcome event for the agent finishing successfully
        rl_run_id = self._get_rl_run_id()
        self._transport.enqueue(
            {
                "event_type": "outcome",
                "run_id": rl_run_id,
                "outcome_type": "agent_finish",
                "success": True,
            }
        )


# ── Provider call extraction ──────────────────────────────────────────────────


def _build_provider_call_from_llm_result(
    *,
    run_id: str,
    span_id: str,
    model: str,
    result: Any,
    latency_ms: int,
) -> dict[str, Any]:
    """Extract token usage from a LangChain ``LLMResult`` object."""
    event: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": run_id,
        "span_id": span_id,
        "provider": "unknown",
        "model": model,
        "latency_ms": latency_ms,
        "status": "success",
    }

    llm_output: dict[str, Any] = getattr(result, "llm_output", None) or {}

    # Detect actual model name + provider from llm_output
    model_name: str | None = llm_output.get("model_name") or llm_output.get("model")
    if model_name:
        event["model"] = model_name

    if "gpt" in event["model"] or "o1" in event["model"] or "o3" in event["model"]:
        event["provider"] = "openai"
    elif "claude" in event["model"]:
        event["provider"] = "anthropic"
    elif "gemini" in event["model"]:
        event["provider"] = "google"

    # OpenAI token format: llm_output.token_usage
    token_usage = llm_output.get("token_usage") or {}
    if token_usage:
        if "prompt_tokens" in token_usage:
            event["input_tokens"] = token_usage["prompt_tokens"]
        if "completion_tokens" in token_usage:
            event["output_tokens"] = token_usage["completion_tokens"]
        return event

    # Anthropic token format: llm_output.usage
    usage = llm_output.get("usage") or {}
    if usage:
        if "input_tokens" in usage:
            event["input_tokens"] = usage["input_tokens"]
        if "output_tokens" in usage:
            event["output_tokens"] = usage["output_tokens"]

    return event
