"""
Tests for RunLedgerNodeWrapper and instrument_graph.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from runledger_sdk.context import RunLedgerContext, _run_id
from runledger_sdk.langgraph import RunLedgerNodeWrapper, instrument_graph
from runledger_sdk.transport import SyncTransport

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_transport() -> tuple[SyncTransport, list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.enqueue = lambda e: captured.append(e)
    return transport, captured


# ── RunLedgerNodeWrapper (sync) ───────────────────────────────────────────────


def test_node_wrapper_fires_span_start_and_end() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    def my_node(state: dict) -> dict:
        return {**state, "visited": True}

    wrapped = RunLedgerNodeWrapper(my_node, "my_node", transport)
    result = wrapped({"x": 1})

    assert result == {"x": 1, "visited": True}

    types = [e["event_type"] for e in captured]
    assert "span_start" in types
    assert "span_end" in types

    span_start = next(e for e in captured if e["event_type"] == "span_start")
    assert span_start["name"] == "my_node"
    assert span_start["span_type"] == "chain"

    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert span_end["status"] == "succeeded"


def test_node_wrapper_fires_failed_span_on_exception() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    def failing_node(state: dict) -> dict:
        raise ValueError("node failed")

    wrapped = RunLedgerNodeWrapper(failing_node, "bad_node", transport)

    with pytest.raises(ValueError, match="node failed"):
        wrapped({})

    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert span_end["status"] == "failed"
    assert span_end["metadata"]["error_type"] == "ValueError"


def test_node_wrapper_span_ids_are_unique() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    def node(state: dict) -> dict:
        return state

    wrapped = RunLedgerNodeWrapper(node, "n", transport)
    wrapped({})
    wrapped({})

    span_ids = [e["span_id"] for e in captured if e["event_type"] == "span_start"]
    assert len(set(span_ids)) == 2  # two distinct UUIDs


def test_node_wrapper_preserves_function_metadata() -> None:
    transport, _ = _make_transport()

    def my_special_node(state: dict) -> dict:
        return state

    wrapped = RunLedgerNodeWrapper(my_special_node, "my_special_node", transport)
    assert wrapped.__name__ == "my_special_node"


def test_node_wrapper_uses_rl_run_id_from_context() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    def node(state: dict) -> dict:
        return state

    wrapped = RunLedgerNodeWrapper(node, "n", transport)

    with RunLedgerContext(feature_tag="test-flow") as run_id:
        wrapped({})

    span_start = next(e for e in captured if e["event_type"] == "span_start")
    assert span_start["run_id"] == run_id


# ── RunLedgerNodeWrapper (async) ──────────────────────────────────────────────


async def test_node_wrapper_async_fires_spans() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    async def async_node(state: dict) -> dict:
        return {**state, "async": True}

    wrapped = RunLedgerNodeWrapper(async_node, "async_node", transport)
    result = await wrapped.ainvoke({"x": 1})

    assert result == {"x": 1, "async": True}

    types = [e["event_type"] for e in captured]
    assert "span_start" in types
    assert "span_end" in types

    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert span_end["status"] == "succeeded"


async def test_node_wrapper_async_fires_failed_on_exception() -> None:
    transport, captured = _make_transport()
    _run_id.set(None)

    async def bad_async_node(state: dict) -> dict:
        raise RuntimeError("async fail")

    wrapped = RunLedgerNodeWrapper(bad_async_node, "bad", transport)

    with pytest.raises(RuntimeError):
        await wrapped.ainvoke({})

    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert span_end["status"] == "failed"
    assert span_end["metadata"]["error_type"] == "RuntimeError"


# ── instrument_graph ──────────────────────────────────────────────────────────


def test_instrument_graph_calls_with_config() -> None:
    transport, _ = _make_transport()

    fake_graph = MagicMock()
    fake_instrumented = MagicMock()
    fake_graph.with_config = MagicMock(return_value=fake_instrumented)

    result = instrument_graph(fake_graph, transport)

    assert result is fake_instrumented
    fake_graph.with_config.assert_called_once()

    # Verify callbacks were passed
    call_kwargs = fake_graph.with_config.call_args[0][0]
    assert "callbacks" in call_kwargs
    assert len(call_kwargs["callbacks"]) == 1


def test_instrument_graph_raises_on_invalid_graph() -> None:
    transport, _ = _make_transport()

    with pytest.raises(TypeError, match="instrument_graph"):
        instrument_graph("not_a_graph", transport)
