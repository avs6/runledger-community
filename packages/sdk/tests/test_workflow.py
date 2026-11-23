"""@rl.workflow decorator: attribution, outcomes and the agent envelope preflight."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from runledger_sdk import RunLedger, RunLedgerBudgetExceededError


def _client() -> tuple[RunLedger, list[dict[str, Any]]]:
    rl = RunLedger(api_key="rl_test", base_url="http://localhost:9")
    events: list[dict[str, Any]] = []
    transport = MagicMock()
    transport.enqueue.side_effect = events.append
    rl._get_sync_transport = lambda: transport  # type: ignore[method-assign]
    return rl, events


def test_decorator_attributes_run_to_workflow_and_agent() -> None:
    rl, events = _client()

    @rl.workflow("support-triage", agent="triage-bot")
    def triage(x: int) -> int:
        return x * 2

    assert triage(2) == 4
    start = next(e for e in events if e["event_type"] == "run_start")
    assert start["workflow"] == "support-triage"
    assert start["agent_name"] == "triage-bot"
    outcome = next(e for e in events if e["event_type"] == "outcome")
    assert outcome["success"] is True


def test_decorator_records_failure_and_reraises() -> None:
    rl, events = _client()

    @rl.workflow("wf")
    def boom() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        boom()
    outcome = next(e for e in events if e["event_type"] == "outcome")
    assert outcome["success"] is False


def test_async_decorator() -> None:
    rl, events = _client()

    @rl.workflow("wf-async")
    async def run() -> str:
        return "ok"

    assert asyncio.run(run()) == "ok"
    assert any(e.get("workflow") == "wf-async" for e in events)


def test_envelope_exhausted_blocks_before_run_starts() -> None:
    rl, events = _client()
    resp = MagicMock()
    resp.json.return_value = {
        "allowed": False,
        "reason": "monthly budget envelope exhausted",
    }
    with patch("runledger_sdk.agent_helper.httpx.get", return_value=resp) as get:

        @rl.workflow("wf", agent_id="a1")
        def run() -> None:
            raise AssertionError("must not run")

        with pytest.raises(RunLedgerBudgetExceededError, match="envelope"):
            run()
    assert get.call_args.args[0].endswith("/agents/a1/envelope")
    assert not events
