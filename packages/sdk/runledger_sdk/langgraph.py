"""
LangGraph instrumentation for RunLedger.

Two entry points:

1. ``instrument_graph(graph, transport)`` — the recommended one-liner.
   Returns the graph pre-configured with a ``RunLedgerCallbackHandler`` so
   that every node fires span_start/span_end automatically via LangGraph's
   built-in callback infrastructure.

2. ``RunLedgerNodeWrapper`` — manually wraps a single node function.
   Useful when you want per-node control or when working with custom
   executors that don't use LangChain's callback system.

Usage (recommended)::

    from runledger_sdk import RunLedger
    from runledger_sdk.langgraph import instrument_graph

    rl = RunLedger(api_key="rl_live_...")

    graph = builder.compile()
    graph = instrument_graph(graph, rl)

    result = graph.invoke({"messages": [...]})

Usage (manual node wrapping)::

    from runledger_sdk.langgraph import RunLedgerNodeWrapper

    def my_node(state):
        ...

    wrapped = RunLedgerNodeWrapper(my_node, "my_node", transport)
    builder.add_node("my_node", wrapped)
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from runledger_sdk.context import get_run_id
from runledger_sdk.langchain import RunLedgerCallbackHandler

if TYPE_CHECKING:
    from collections.abc import Callable

    from runledger_sdk.transport import SyncTransport


# ── RunLedgerNodeWrapper ──────────────────────────────────────────────────────


class RunLedgerNodeWrapper:
    """
    Wraps a LangGraph node function to emit ``span_start`` / ``span_end``
    events directly (without the LangChain callback system).

    Supports both sync and async node functions.

    Parameters
    ----------
    fn:
        The original node function ``(state) -> state``.
    node_name:
        Human-readable name shown in the RunLedger DAG viewer.
    transport:
        The ``SyncTransport`` instance from the RunLedger client.
    """

    def __init__(
        self,
        fn: Callable[..., Any],
        node_name: str,
        transport: SyncTransport,
    ) -> None:
        self._fn = fn
        self._node_name = node_name
        self._transport = transport

        # Preserve function metadata for LangGraph introspection
        self.__name__ = getattr(fn, "__name__", node_name)
        self.__qualname__ = getattr(fn, "__qualname__", node_name)

    # ── Sync ──────────────────────────────────────────────────────────────────

    def __call__(self, state: Any, config: Any = None) -> Any:
        run_id = get_run_id()
        span_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        t0 = time.perf_counter()

        self._transport.enqueue(
            {
                "event_type": "span_start",
                "span_id": span_id,
                "run_id": run_id,
                "span_type": "chain",
                "name": self._node_name,
                "started_at": started_at,
            }
        )

        try:
            result = self._fn(state, config) if config is not None else self._fn(state)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            self._transport.enqueue(
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": "succeeded",
                    "ended_at": datetime.now(UTC).isoformat(),
                    "metadata": {"latency_ms": latency_ms, "node": self._node_name},
                }
            )
            return result
        except Exception as exc:
            self._transport.enqueue(
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": "failed",
                    "ended_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "node": self._node_name,
                        "error_type": type(exc).__name__,
                    },
                }
            )
            raise

    # ── Async ─────────────────────────────────────────────────────────────────

    async def ainvoke(self, state: Any, config: Any = None) -> Any:
        run_id = get_run_id()
        span_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()
        t0 = time.perf_counter()

        self._transport.enqueue(
            {
                "event_type": "span_start",
                "span_id": span_id,
                "run_id": run_id,
                "span_type": "chain",
                "name": self._node_name,
                "started_at": started_at,
            }
        )

        try:
            if config is not None:
                result = await self._fn(state, config)
            else:
                result = await self._fn(state)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            self._transport.enqueue(
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": "succeeded",
                    "ended_at": datetime.now(UTC).isoformat(),
                    "metadata": {"latency_ms": latency_ms, "node": self._node_name},
                }
            )
            return result
        except Exception as exc:
            self._transport.enqueue(
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": "failed",
                    "ended_at": datetime.now(UTC).isoformat(),
                    "metadata": {
                        "node": self._node_name,
                        "error_type": type(exc).__name__,
                    },
                }
            )
            raise


# ── instrument_graph ──────────────────────────────────────────────────────────


def instrument_graph(graph: Any, transport: SyncTransport) -> Any:
    """
    Add RunLedger instrumentation to a compiled LangGraph.

    Uses LangGraph's built-in ``with_config`` to attach a
    ``RunLedgerCallbackHandler``, so every node execution fires
    ``span_start`` / ``span_end`` events with full parent-child linking.

    Returns the instrumented graph (same object, new default config).
    The original graph is not modified.

    Parameters
    ----------
    graph:
        A compiled LangGraph (``CompiledGraph`` / ``CompiledStateGraph``).
    transport:
        The ``SyncTransport`` instance from the RunLedger client.

    Returns
    -------
    The graph with RunLedger callbacks baked into its default config.
    """
    handler = RunLedgerCallbackHandler(transport, track_llm_cost=True)

    try:
        # LangGraph / LangChain Runnable API
        return graph.with_config({"callbacks": [handler]})
    except (AttributeError, TypeError) as exc:
        raise TypeError(
            "instrument_graph() expects a compiled LangGraph (CompiledGraph). "
            f"Got {type(graph).__name__!r}. "
            "Make sure you call builder.compile() before instrumenting."
        ) from exc
