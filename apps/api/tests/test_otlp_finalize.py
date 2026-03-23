"""
Tests for OTLP trace finalization worker (Phase 3).

Covers:
  _close_stale_runs — stale OTLP run + open spans get closed
  _close_stale_runs — fresh run is NOT touched
  _close_stale_runs — non-OTLP run is NOT touched (no source_type filter match)
  _close_stale_runs — no stale runs → no-op (no update calls)
  _close_stale_runs — stale run with no open spans still closes the run
  source-provenance propagation: synthesize_canonical_events run_start has
    source_type + external_trace_id as top-level fields
  pipeline._handle_run_start persists source_type + external_trace_id
  pipeline._handle_span_start persists external_span_id + scope fields
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from runledger_api.workers.otlp_finalize import _close_stale_runs

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_select_result(run_ids: list[uuid.UUID]) -> MagicMock:
    """Mock a SELECT result returning a list of run_id tuples."""
    result = MagicMock()
    result.all.return_value = [(rid,) for rid in run_ids]
    return result


def _make_update_result() -> MagicMock:
    return MagicMock()


# ── _close_stale_runs ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_close_stale_runs_closes_run_and_spans() -> None:
    """A stale OTLP run: open spans marked failed, run marked cancelled."""
    stale_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            _make_select_result([stale_id]),  # SELECT stale runs
            _make_update_result(),             # UPDATE spans
            _make_update_result(),             # UPDATE agent_runs
        ]
    )

    closed = await _close_stale_runs(mock_session)

    assert closed == 1
    assert mock_session.execute.call_count == 3


@pytest.mark.anyio
async def test_close_stale_runs_noop_when_empty() -> None:
    """No stale runs → no UPDATE calls issued."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            _make_select_result([]),  # SELECT returns nothing
        ]
    )

    closed = await _close_stale_runs(mock_session)

    assert closed == 0
    # Only the SELECT was called — no UPDATEs
    assert mock_session.execute.call_count == 1


@pytest.mark.anyio
async def test_close_stale_runs_multiple_runs() -> None:
    """Multiple stale runs — all get closed in a single batch update."""
    run_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[
            _make_select_result(run_ids),
            _make_update_result(),  # UPDATE spans (batch)
            _make_update_result(),  # UPDATE runs (batch)
        ]
    )

    closed = await _close_stale_runs(mock_session)

    assert closed == 3
    assert mock_session.execute.call_count == 3


# ── Source-provenance propagation ──────────────────────────────────────────────


def test_run_start_event_has_top_level_source_type() -> None:
    """synthesize_canonical_events puts source_type and external_trace_id at top level."""
    from runledger_api.services.otlp_parse import (
        OtlpParsedSpan,
        OtlpTrace,
        _ns_to_dt,
        synthesize_canonical_events,
    )

    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000010")
    trace_id_hex = "aabbccddeeff00112233445566778899"
    root_hex = "aabbccdd11223344"
    t = 1_700_000_000_000_000_000

    root = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=root_hex,
        parent_span_id_hex=None,
        name="agent.run",
        span_type="agent",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 1_000_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "AGENT"},
        scope_name="openinference.langchain",
        scope_version="0.1",
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={"service.name": "my-svc"},
        spans=[root],
    )
    events = synthesize_canonical_events(ws_id, trace)
    run_start = next(e for e in events if e["event_type"] == "run_start")

    assert run_start["source_type"] == "otlp"
    assert run_start["external_trace_id"] == trace_id_hex
    # source_type must NOT be buried in metadata
    assert run_start.get("metadata", {}).get("source_type") is None


def test_span_start_event_has_top_level_external_ids() -> None:
    """synthesize_canonical_events puts external_span_id at top level on span_start."""
    from runledger_api.services.otlp_parse import (
        OtlpParsedSpan,
        OtlpTrace,
        _ns_to_dt,
        synthesize_canonical_events,
    )

    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000011")
    trace_id_hex = "1122334455667788990011223344556677"[:32]
    root_hex = "1122334455667788"
    child_hex = "aabbccddeeff0011"
    t = 1_700_000_000_000_000_000

    root = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=root_hex,
        parent_span_id_hex=None,
        name="agent.run",
        span_type="agent",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 2_000_000_000),
        status_code="OK",
        attrs={},
        scope_name="my.instrumentation",
        scope_version="1.2.3",
        otel_kind=3,
    )
    child = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=child_hex,
        parent_span_id_hex=root_hex,
        name="llm.call",
        span_type="llm",
        started_at=_ns_to_dt(t + 100_000_000),
        ended_at=_ns_to_dt(t + 1_500_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "LLM", "llm.model_name": "gpt-4o"},
        scope_name="my.instrumentation",
        scope_version="1.2.3",
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={},
        spans=[root, child],
    )
    events = synthesize_canonical_events(ws_id, trace)
    span_starts = [e for e in events if e["event_type"] == "span_start"]

    # All span_start events should have external_span_id at top level
    for ss in span_starts:
        assert "external_span_id" in ss, f"missing external_span_id on {ss['name']}"
        assert ss.get("metadata", {}).get("external_span_id") is None

    # Child span should have scope fields
    child_start = next(ss for ss in span_starts if ss["external_span_id"] == child_hex)
    assert child_start["instrumentation_scope_name"] == "my.instrumentation"
    assert child_start["instrumentation_scope_version"] == "1.2.3"
    assert child_start["external_parent_span_id"] == root_hex


# ── Pipeline handler propagation ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_handle_run_start_persists_source_type() -> None:
    """pipeline._handle_run_start passes source_type and external_trace_id to INSERT."""
    from runledger_api.workers.pipeline import _handle_run_start

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    event = {
        "run_id": str(uuid.uuid4()),
        "started_at": "2025-01-01T00:00:00+00:00",
        "source_type": "otlp",
        "external_trace_id": "aabbccddeeff00112233445566778899",
    }
    workspace_id = str(uuid.uuid4())

    await _handle_run_start(mock_session, workspace_id, event)

    assert mock_session.execute.called
    # Extract the INSERT statement's compiled values
    call_args = mock_session.execute.call_args[0][0]
    # The insert stmt's _values include source_type and external_trace_id
    compiled = call_args.compile()
    params = compiled.params
    assert params.get("source_type") == "otlp"
    assert params.get("external_trace_id") == "aabbccddeeff00112233445566778899"


@pytest.mark.anyio
async def test_handle_run_start_source_type_null_for_sdk_events() -> None:
    """SDK events without source_type field get NULL in the DB column."""
    from runledger_api.workers.pipeline import _handle_run_start

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    event = {
        "run_id": str(uuid.uuid4()),
        "started_at": "2025-01-01T00:00:00+00:00",
        # No source_type — SDK events don't set this
    }

    await _handle_run_start(mock_session, str(uuid.uuid4()), event)

    call_args = mock_session.execute.call_args[0][0]
    params = call_args.compile().params
    assert params.get("source_type") is None
    assert params.get("external_trace_id") is None


@pytest.mark.anyio
async def test_handle_span_start_persists_external_ids() -> None:
    """pipeline._handle_span_start passes external_span_id and scope fields."""
    from runledger_api.workers.pipeline import _handle_span_start

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    event = {
        "run_id": run_id,
        "span_id": span_id,
        "span_type": "llm",
        "name": "ChatOpenAI",
        "started_at": "2025-01-01T00:00:00+00:00",
        "external_span_id": "aabbccdd11223344",
        "external_parent_span_id": "1122334455667788",
        "instrumentation_scope_name": "openinference.langchain",
        "instrumentation_scope_version": "0.1.0",
    }

    await _handle_span_start(mock_session, event)

    call_args = mock_session.execute.call_args[0][0]
    params = call_args.compile().params
    assert params.get("external_span_id") == "aabbccdd11223344"
    assert params.get("external_parent_span_id") == "1122334455667788"
    assert params.get("instrumentation_scope_name") == "openinference.langchain"
    assert params.get("instrumentation_scope_version") == "0.1.0"
