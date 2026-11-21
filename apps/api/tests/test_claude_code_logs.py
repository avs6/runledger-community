"""
Tests for turning Claude Code OTLP log events into runs.

Covers the log-event converter, the /v1/logs hook that enqueues its events,
run_end no longer wiping rolled-up totals, and cost enrichment using the
client-reported cost.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from runledger_api.services.claude_code_logs import synthesize_claude_code_events

WORKSPACE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
# 2026-11-21T02:06:16.127Z
EVENT_NS = 1_795_226_776_127_000_000


def _attr(key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)}}


def _api_request(**overrides: Any) -> dict[str, Any]:
    """A log record shaped like a real Claude Code api_request event."""
    attrs: dict[str, Any] = {
        "session.id": "sess-1",
        "user.id": "user-hash",
        "user.email": "someone@example.com",
        "event.name": "api_request",
        "event.sequence": "473",
        "prompt.id": "prompt-1",
        "model": "claude-opus-5-5",
        "input_tokens": "2",
        "output_tokens": "641",
        "cache_read_tokens": "190578",
        "cache_creation_tokens": "907",
        "cost_usd": 0.0581996,
        "duration_ms": "8015",
        "request_id": "req_1",
        "anthropic.provider": "firstParty",
        "terminal.type": "non-interactive",
        "query_source": "sdk",
        "effort": "medium",
    }
    attrs.update(overrides)
    return {
        "timeUnixNano": str(EVENT_NS),
        "observedTimeUnixNano": str(EVENT_NS),
        "body": {"stringValue": "claude_code.api_request"},
        "attributes": [_attr(k, v) for k, v in attrs.items() if v is not None],
    }


def _logs_payload(
    records: list[dict[str, Any]],
    service: str = "claude-code-desktop",
    scope: str = "com.anthropic.claude_code.events",
) -> dict[str, Any]:
    return {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        _attr("service.name", service),
                        _attr("service.version", "6.28899.2"),
                    ]
                },
                "scopeLogs": [
                    {"scope": {"name": scope, "version": "2.1.328"}, "logRecords": records}
                ],
            }
        ]
    }


def _by_type(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [e for e in events if e["event_type"] == event_type]


# ── Converter ─────────────────────────────────────────────────────────────────


def test_api_request_becomes_run_span_and_provider_call() -> None:
    events = synthesize_claude_code_events(WORKSPACE_ID, _logs_payload([_api_request()]))

    assert [e["event_type"] for e in events] == [
        "run_start",
        "span_start",
        "provider_call",
        "span_end",
        "run_end",
    ]
    run_start, span_start, call, span_end, run_end = events

    assert run_start["session_id"] == "sess-1"
    assert run_start["end_user_id"] == "user-hash"
    assert run_start["deployment_version"] == "6.28899.2"
    assert run_start["source_type"] == "otlp"
    assert run_start["metadata"]["source"] == "claude-code-logs"
    assert run_start["metadata"]["query_source"] == "sdk"

    assert call["provider"] == "anthropic"
    assert call["model"] == "claude-opus-5-5"
    assert call["input_tokens"] == 2 + 190578 + 907
    assert call["output_tokens"] == 641
    assert call["cached_input_tokens"] == 190578
    assert call["input_tokens_details"] == {
        "cached_tokens": 190578,
        "cache_creation_tokens": 907,
    }
    assert call["reported_cost_usd"] == pytest.approx(0.0581996)
    assert call["cost_source"] == "reported"
    assert call["provider_request_id"] == "req_1"
    assert call["latency_ms"] == 8015
    assert "model_provider" not in call

    assert span_start["span_type"] == "llm"
    assert (
        span_start["started_at"] == datetime(2026, 11, 21, 2, 6, 8, 112000, tzinfo=UTC).isoformat()
    )
    assert span_end["ended_at"] == datetime(2026, 11, 21, 2, 6, 16, 127000, tzinfo=UTC).isoformat()
    assert run_end["status"] == "succeeded"
    assert {e["run_id"] for e in events} == {run_start["run_id"]}


def test_identity_fields_are_not_copied_into_run_metadata() -> None:
    events = synthesize_claude_code_events(WORKSPACE_ID, _logs_payload([_api_request()]))
    assert "someone@example.com" not in json.dumps(events)


def test_requests_in_one_prompt_share_a_run() -> None:
    payload = _logs_payload([_api_request(request_id="req_1"), _api_request(request_id="req_2")])
    events = synthesize_claude_code_events(WORKSPACE_ID, payload)

    calls = _by_type(events, "provider_call")
    assert len(calls) == 2
    assert calls[0]["run_id"] == calls[1]["run_id"]
    assert calls[0]["span_id"] != calls[1]["span_id"]


def test_ids_are_deterministic_so_retries_do_not_duplicate() -> None:
    payload = _logs_payload([_api_request()])
    first = synthesize_claude_code_events(WORKSPACE_ID, payload)
    second = synthesize_claude_code_events(WORKSPACE_ID, payload)
    assert first == second


def test_different_prompts_get_different_runs() -> None:
    payload = _logs_payload(
        [
            _api_request(**{"prompt.id": "prompt-1", "request_id": "req_1"}),
            _api_request(**{"prompt.id": "prompt-2", "request_id": "req_2"}),
        ]
    )
    runs = {
        e["run_id"]
        for e in _by_type(synthesize_claude_code_events(WORKSPACE_ID, payload), "run_start")
    }
    assert len(runs) == 2


def test_missing_prompt_id_falls_back_to_one_run_per_request() -> None:
    payload = _logs_payload(
        [
            _api_request(**{"prompt.id": None, "request_id": "req_1"}),
            _api_request(**{"prompt.id": None, "request_id": "req_2"}),
        ]
    )
    runs = {
        e["run_id"]
        for e in _by_type(synthesize_claude_code_events(WORKSPACE_ID, payload), "run_start")
    }
    assert len(runs) == 2


def test_other_claude_code_events_are_ignored() -> None:
    record = _api_request(**{"event.name": "tool_result"})
    record["body"] = {"stringValue": "claude_code.tool_result"}
    assert synthesize_claude_code_events(WORKSPACE_ID, _logs_payload([record])) == []


def test_logs_from_other_services_are_ignored() -> None:
    payload = _logs_payload([_api_request()], service="openclaw", scope="otel.logs")
    assert synthesize_claude_code_events(WORKSPACE_ID, payload) == []


def test_event_name_falls_back_to_body() -> None:
    record = _api_request(**{"event.name": None})
    events = synthesize_claude_code_events(WORKSPACE_ID, _logs_payload([record]))
    assert len(_by_type(events, "provider_call")) == 1


def test_missing_cost_uses_pricing_engine() -> None:
    events = synthesize_claude_code_events(
        WORKSPACE_ID, _logs_payload([_api_request(cost_usd=None)])
    )
    call = _by_type(events, "provider_call")[0]
    assert call["cost_source"] == "pricing_engine"
    assert "reported_cost_usd" not in call


def test_cloud_hosting_is_recorded_as_model_provider() -> None:
    events = synthesize_claude_code_events(
        WORKSPACE_ID, _logs_payload([_api_request(**{"anthropic.provider": "bedrock"})])
    )
    assert _by_type(events, "provider_call")[0]["model_provider"] == "bedrock"


# ── /v1/logs enqueues the events ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logs_endpoint_enqueues_claude_code_events(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    mock_db_session.flush = AsyncMock()
    with patch("runledger_api.workers.pipeline.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(
            "/v1/logs",
            content=json.dumps(_logs_payload([_api_request()])).encode(),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    mock_task.delay.assert_called_once()
    workspace_arg, events = mock_task.delay.call_args.args
    assert workspace_arg == str(mock_workspace.id)
    assert [e["event_type"] for e in events][2] == "provider_call"


@pytest.mark.asyncio
async def test_logs_endpoint_skips_enqueue_without_claude_code_events(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.flush = AsyncMock()
    payload = _logs_payload([_api_request()], service="openclaw", scope="otel.logs")
    with patch("runledger_api.workers.pipeline.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(
            "/v1/logs",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    mock_task.delay.assert_not_called()


# ── run_end keeps rolled-up totals ────────────────────────────────────────────


def _run_end_update_columns(session: AsyncMock) -> set[str]:
    stmt = session.execute.await_args_list[0].args[0]
    return {col.key for col in stmt._values}


@pytest.mark.asyncio
async def test_run_end_without_totals_does_not_overwrite_them() -> None:
    from runledger_api.workers.pipeline import _handle_run_end

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    await _handle_run_end(
        session,
        {
            "run_id": str(uuid.uuid4()),
            "status": "succeeded",
            "ended_at": "2026-11-21T02:06:16+00:00",
        },
    )

    assert _run_end_update_columns(session) == {"status", "ended_at"}


@pytest.mark.asyncio
async def test_run_end_with_totals_sets_them() -> None:
    from runledger_api.workers.pipeline import _handle_run_end

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    await _handle_run_end(
        session,
        {
            "run_id": str(uuid.uuid4()),
            "status": "succeeded",
            "ended_at": "2026-11-21T02:06:16+00:00",
            "total_cost_usd": "0.5",
            "total_input_tokens": 10,
            "total_output_tokens": 5,
        },
    )

    assert _run_end_update_columns(session) == {
        "status",
        "ended_at",
        "total_cost_usd",
        "total_input_tokens",
        "total_output_tokens",
    }


# ── Cost enrichment prefers the reported cost ─────────────────────────────────


def _provider_call(**fields: Any) -> SimpleNamespace:
    base: dict[str, Any] = {
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "input_tokens": 191487,
        "output_tokens": 641,
        "cached_input_tokens": 190578,
        "created_at": datetime.now(UTC),
        "workspace_id": WORKSPACE_ID,
        "cost_source": "reported",
        "reported_cost_usd": Decimal("0.0581996"),
    }
    base.update(fields)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_enrichment_uses_reported_cost() -> None:
    from runledger_api.workers import metering

    with patch.object(metering, "calculate_cost", AsyncMock()) as pricing:
        cost = await metering._provider_call_cost(AsyncMock(), _provider_call())

    assert cost == Decimal("0.0581996")
    pricing.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrichment_prices_calls_without_reported_cost() -> None:
    from runledger_api.workers import metering

    pc = _provider_call(cost_source="pricing_engine", reported_cost_usd=None)
    with patch.object(
        metering, "calculate_cost", AsyncMock(return_value=Decimal("0.2"))
    ) as pricing:
        cost = await metering._provider_call_cost(AsyncMock(), pc)

    assert cost == Decimal("0.2")
    pricing.assert_awaited_once()
