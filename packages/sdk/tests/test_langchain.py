"""
Tests for RunLedgerCallbackHandler.

Uses fake LangChain objects so langchain_core is not required as a test dep.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

from runledger_sdk.context import RunLedgerContext, _run_id
from runledger_sdk.langchain import (
    RunLedgerCallbackHandler,
    _build_provider_call_from_llm_result,
)
from runledger_sdk.transport import SyncTransport

# ── Fake LangChain objects ─────────────────────────────────────────────────────


def _fake_llm_result(
    model_name: str = "gpt-4o",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> Any:
    result = MagicMock()
    result.llm_output = {
        "model_name": model_name,
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return result


def _fake_anthropic_result(input_tokens: int = 80, output_tokens: int = 40) -> Any:
    result = MagicMock()
    result.llm_output = {
        "model": "claude-sonnet-4-6",
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
    return result


def _fake_agent_action(tool: str = "search") -> Any:
    action = MagicMock()
    action.tool = tool
    return action


def _fake_agent_finish() -> Any:
    finish = MagicMock()
    finish.return_values = {"output": "done"}
    return finish


def _make_handler() -> tuple[RunLedgerCallbackHandler, list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.enqueue = lambda e: captured.append(e)
    return RunLedgerCallbackHandler(transport), captured


# ── _build_provider_call_from_llm_result ─────────────────────────────────────


def test_provider_call_openai_format() -> None:
    result = _fake_llm_result("gpt-4o", 100, 50)
    event = _build_provider_call_from_llm_result(
        run_id="r1", span_id="s1", model="gpt-4o", result=result, latency_ms=200
    )
    assert event["provider"] == "openai"
    assert event["model"] == "gpt-4o"
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["latency_ms"] == 200
    assert event["status"] == "success"


def test_provider_call_anthropic_format() -> None:
    result = _fake_anthropic_result(80, 40)
    event = _build_provider_call_from_llm_result(
        run_id="r1", span_id="s1", model="llm", result=result, latency_ms=150
    )
    assert event["provider"] == "anthropic"
    assert event["model"] == "claude-sonnet-4-6"
    assert event["input_tokens"] == 80
    assert event["output_tokens"] == 40


# ── Chain callbacks ───────────────────────────────────────────────────────────


def test_chain_start_fires_run_start_and_span_start() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_run_id = uuid.uuid4()

    handler.on_chain_start({"name": "MyChain"}, {}, run_id=root_run_id)

    types = [e["event_type"] for e in captured]
    assert "run_start" in types
    assert "span_start" in types


def test_chain_start_only_fires_run_start_for_root() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    handler.on_chain_start(
        {"name": "Child"}, {}, run_id=child_id, parent_run_id=root_id
    )

    run_starts = [e for e in captured if e["event_type"] == "run_start"]
    assert len(run_starts) == 1  # only one run_start


def test_chain_end_fires_span_end_and_run_end_for_root() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    captured.clear()
    handler.on_chain_end({}, run_id=root_id)

    types = [e["event_type"] for e in captured]
    assert "span_end" in types
    assert "run_end" in types

    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert span_end["status"] == "succeeded"
    run_end = next(e for e in captured if e["event_type"] == "run_end")
    assert run_end["status"] == "succeeded"


def test_chain_error_fires_failed_status() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    captured.clear()
    handler.on_chain_error(ValueError("boom"), run_id=root_id)

    run_end = next(e for e in captured if e["event_type"] == "run_end")
    span_end = next(e for e in captured if e["event_type"] == "span_end")
    assert run_end["status"] == "failed"
    assert span_end["status"] == "failed"


def test_nested_chains_have_parent_span_id() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    handler.on_chain_start(
        {"name": "Child"}, {}, run_id=child_id, parent_run_id=root_id
    )

    child_span = next(
        e
        for e in captured
        if e["event_type"] == "span_start" and e["span_id"] == str(child_id)
    )
    assert child_span["parent_span_id"] == str(root_id)


# ── LLM callbacks ─────────────────────────────────────────────────────────────


def test_llm_end_fires_provider_call() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()
    llm_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    handler.on_llm_start({"name": "gpt-4o"}, [], run_id=llm_id, parent_run_id=root_id)
    handler.on_llm_end(_fake_llm_result(), run_id=llm_id)

    provider_call = next(e for e in captured if e["event_type"] == "provider_call")
    assert provider_call["input_tokens"] == 100
    assert provider_call["output_tokens"] == 50
    assert provider_call["span_id"] == str(llm_id)


def test_llm_end_skips_provider_call_when_track_llm_cost_false() -> None:
    captured: list[dict[str, Any]] = []
    transport = MagicMock(spec=SyncTransport)
    transport.enqueue = lambda e: captured.append(e)
    handler = RunLedgerCallbackHandler(transport, track_llm_cost=False)

    _run_id.set(None)
    llm_id = uuid.uuid4()
    handler.on_chain_start({"name": "Root"}, {}, run_id=uuid.uuid4())
    handler.on_llm_start(
        {"name": "gpt-4o"}, [], run_id=llm_id, parent_run_id=uuid.uuid4()
    )
    handler.on_llm_end(_fake_llm_result(), run_id=llm_id)

    provider_calls = [e for e in captured if e["event_type"] == "provider_call"]
    assert len(provider_calls) == 0


# ── Tool callbacks ────────────────────────────────────────────────────────────


def test_tool_start_and_end_create_spans() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()
    tool_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    handler.on_tool_start(
        {"name": "search"}, "query", run_id=tool_id, parent_run_id=root_id
    )
    handler.on_tool_end("result", run_id=tool_id)

    tool_start = next(
        e
        for e in captured
        if e["event_type"] == "span_start" and e["span_id"] == str(tool_id)
    )
    assert tool_start["span_type"] == "tool"
    assert tool_start["name"] == "search"

    tool_end = next(
        e
        for e in captured
        if e["event_type"] == "span_end" and e["span_id"] == str(tool_id)
    )
    assert tool_end["status"] == "succeeded"


def test_tool_error_fires_failed_span() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    tool_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=uuid.uuid4())
    handler.on_tool_start(
        {"name": "search"}, "q", run_id=tool_id, parent_run_id=uuid.uuid4()
    )
    handler.on_tool_error(RuntimeError("timeout"), run_id=tool_id)

    tool_end = next(
        e
        for e in captured
        if e["event_type"] == "span_end" and e["span_id"] == str(tool_id)
    )
    assert tool_end["status"] == "failed"


# ── Agent callbacks ───────────────────────────────────────────────────────────


def test_agent_finish_fires_outcome() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)
    handler.on_agent_action(
        _fake_agent_action("search"), run_id=agent_id, parent_run_id=root_id
    )
    handler.on_agent_finish(_fake_agent_finish(), run_id=agent_id)

    outcome = next(e for e in captured if e["event_type"] == "outcome")
    assert outcome["outcome_type"] == "agent_finish"
    assert outcome["success"] is True


# ── Context propagation from rl.context() ────────────────────────────────────


def test_handler_picks_up_rl_context() -> None:
    handler, captured = _make_handler()
    _run_id.set(None)
    root_id = uuid.uuid4()

    with RunLedgerContext(end_user_id="u_123", feature_tag="chat"):
        handler.on_chain_start({"name": "Root"}, {}, run_id=root_id)

    run_start = next(e for e in captured if e["event_type"] == "run_start")
    assert run_start.get("end_user_id") == "u_123"
    assert run_start.get("feature_tag") == "chat"
