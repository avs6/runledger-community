"""
Tests for OTLP Phase 4 — Reconciliation-grade enrichment.

Covers:
  _extract_llm_fields — provider_request_id from various attribute conventions
  _extract_llm_fields — reported_cost_usd from llm.cost.total + fallback
  _extract_llm_fields — model_provider (Azure hosting)
  _extract_token_details — prompt/completion detail breakdowns
  synthesize_canonical_events — provider_call event has top-level finance fields
  pipeline._handle_provider_call — INSERT includes all reconciliation columns
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from runledger_api.services.otlp_parse import (
    _extract_llm_fields,
    _extract_token_details,
    _ns_to_dt,
    synthesize_canonical_events,
)

# ── _extract_llm_fields — provider_request_id ─────────────────────────────────


def test_extract_llm_fields_openinference_request_id() -> None:
    attrs = {
        "openinference.span.kind": "LLM",
        "llm.model_name": "gpt-4o",
        "llm.openai.response.id": "chatcmpl-abc123",
    }
    result = _extract_llm_fields(attrs)
    assert result["provider_request_id"] == "chatcmpl-abc123"


def test_extract_llm_fields_genai_response_id() -> None:
    attrs = {
        "gen_ai.system": "anthropic",
        "gen_ai.request.model": "claude-3-5-sonnet-20241022",
        "gen_ai.response.id": "msg_01XxYy",
    }
    result = _extract_llm_fields(attrs)
    assert result["provider_request_id"] == "msg_01XxYy"


def test_extract_llm_fields_anthropic_request_id() -> None:
    attrs = {
        "llm.model_name": "claude-3-haiku",
        "anthropic.request_id": "req_abc",
    }
    result = _extract_llm_fields(attrs)
    assert result["provider_request_id"] == "req_abc"


def test_extract_llm_fields_no_request_id_returns_none() -> None:
    attrs = {"llm.model_name": "gpt-4o", "llm.token_count.prompt": 100}
    result = _extract_llm_fields(attrs)
    assert result["provider_request_id"] is None


def test_extract_llm_fields_openinference_priority_over_generic() -> None:
    """llm.openai.response.id takes priority over gen_ai.response.id."""
    attrs = {
        "llm.openai.response.id": "chatcmpl-first",
        "gen_ai.response.id": "msg-second",
    }
    result = _extract_llm_fields(attrs)
    assert result["provider_request_id"] == "chatcmpl-first"


# ── _extract_llm_fields — reported_cost_usd ───────────────────────────────────


def test_extract_llm_fields_cost_from_llm_cost_total() -> None:
    attrs = {"llm.model_name": "gpt-4o", "llm.cost.total": 0.00312}
    result = _extract_llm_fields(attrs)
    assert result["reported_cost_usd"] == pytest.approx(0.00312)


def test_extract_llm_fields_cost_fallback_to_token_count() -> None:
    attrs = {"llm.model_name": "gpt-4o", "llm.token_count.total_cost": 0.00150}
    result = _extract_llm_fields(attrs)
    assert result["reported_cost_usd"] == pytest.approx(0.00150)


def test_extract_llm_fields_cost_prefers_llm_cost_total() -> None:
    """llm.cost.total has priority over llm.token_count.total_cost."""
    attrs = {
        "llm.model_name": "gpt-4o",
        "llm.cost.total": 0.005,
        "llm.token_count.total_cost": 0.003,
    }
    result = _extract_llm_fields(attrs)
    assert result["reported_cost_usd"] == pytest.approx(0.005)


# ── _extract_llm_fields — model_provider (Azure) ──────────────────────────────


def test_extract_llm_fields_azure_api_type() -> None:
    attrs = {
        "gen_ai.system": "openai",
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.openai.api_type": "azure",
    }
    result = _extract_llm_fields(attrs)
    assert result["model_provider"] == "azure"


def test_extract_llm_fields_no_hosting_provider_is_none() -> None:
    attrs = {"llm.model_name": "gpt-4o", "llm.provider": "openai"}
    result = _extract_llm_fields(attrs)
    assert result["model_provider"] is None


# ── _extract_token_details ────────────────────────────────────────────────────


def test_extract_token_details_openinference_cached() -> None:
    attrs = {
        "llm.token_count.prompt_details.cached_tokens": 50,
        "llm.token_count.prompt_details.audio_tokens": 10,
    }
    result = _extract_token_details(
        attrs,
        prefix="llm.token_count.prompt_details",
        genai_prefix="gen_ai.usage.prompt",
    )
    assert result == {"cached_tokens": 50, "audio_tokens": 10}


def test_extract_token_details_completion_reasoning() -> None:
    attrs = {"llm.token_count.completion_details.reasoning_tokens": 128}
    result = _extract_token_details(
        attrs,
        prefix="llm.token_count.completion_details",
        genai_prefix="gen_ai.usage.completion",
    )
    assert result == {"reasoning_tokens": 128}


def test_extract_token_details_none_when_empty() -> None:
    result = _extract_token_details({}, "llm.token_count.prompt_details", "gen_ai.usage.prompt")
    assert result is None


def test_extract_token_details_genai_fallback() -> None:
    attrs = {"gen_ai.usage.prompt_tokens.cached": 30}
    result = _extract_token_details(
        attrs,
        prefix="llm.token_count.prompt_details",
        genai_prefix="gen_ai.usage.prompt",
    )
    assert result == {"cached_tokens": 30}


# ── synthesize_canonical_events — provider_call finance fields ─────────────────


def _make_llm_trace(
    attrs: dict,
    resource_attrs: dict | None = None,
) -> tuple[uuid.UUID, object]:
    """Helper: build a minimal OtlpTrace with one root LLM span."""
    from runledger_api.services.otlp_parse import OtlpParsedSpan, OtlpTrace

    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000020")
    trace_id_hex = "aabbccddeeff00112233445566778899"
    span_hex = "aabbccdd11223344"
    t = 1_700_000_000_000_000_000

    span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=span_hex,
        parent_span_id_hex=None,
        name="LLM.call",
        span_type="llm",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 1_200_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "LLM", **attrs},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs=resource_attrs or {},
        spans=[span],
    )
    return ws_id, trace


def test_provider_call_has_top_level_provider_request_id() -> None:
    ws_id, trace = _make_llm_trace(
        {
            "llm.model_name": "gpt-4o",
            "llm.openai.response.id": "chatcmpl-xyz789",
            "llm.token_count.prompt": 100,
            "llm.token_count.completion": 50,
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    pc = next(e for e in events if e["event_type"] == "provider_call")

    assert pc["provider_request_id"] == "chatcmpl-xyz789"
    # Must NOT be buried in metadata
    assert pc.get("metadata", {}).get("provider_request_id") is None


def test_provider_call_has_top_level_reported_cost_and_cost_source() -> None:
    ws_id, trace = _make_llm_trace(
        {
            "llm.model_name": "gpt-4o",
            "llm.cost.total": 0.0045,
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    pc = next(e for e in events if e["event_type"] == "provider_call")

    assert pc["reported_cost_usd"] == pytest.approx(0.0045)
    assert pc["cost_source"] == "reported"


def test_provider_call_cost_source_pricing_engine_when_no_reported_cost() -> None:
    ws_id, trace = _make_llm_trace(
        {
            "llm.model_name": "gpt-4o",
            "llm.token_count.prompt": 200,
            "llm.token_count.completion": 80,
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    pc = next(e for e in events if e["event_type"] == "provider_call")

    assert "reported_cost_usd" not in pc
    assert pc["cost_source"] == "pricing_engine"


def test_provider_call_has_top_level_token_details() -> None:
    ws_id, trace = _make_llm_trace(
        {
            "llm.model_name": "gpt-4o",
            "llm.token_count.prompt": 500,
            "llm.token_count.prompt_details.cached_tokens": 200,
            "llm.token_count.completion_details.reasoning_tokens": 64,
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    pc = next(e for e in events if e["event_type"] == "provider_call")

    assert pc["input_tokens_details"] == {"cached_tokens": 200}
    assert pc["output_tokens_details"] == {"reasoning_tokens": 64}


# ── pipeline._handle_provider_call — reconciliation columns ───────────────────


@pytest.mark.anyio
async def test_handle_provider_call_persists_reconciliation_fields() -> None:
    """_handle_provider_call passes provider_request_id, reported_cost_usd, etc. to INSERT."""
    from runledger_api.workers.pipeline import _handle_provider_call

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    run_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    ws_id = str(uuid.uuid4())

    event = {
        "run_id": run_id,
        "span_id": span_id,
        "provider": "openai",
        "model": "gpt-4o",
        "status": "success",
        "latency_ms": 1200,
        "provider_request_id": "chatcmpl-abc123",
        "reported_cost_usd": 0.00312,
        "cost_source": "reported",
        "model_provider": None,
        "input_tokens_details": {"cached_tokens": 50},
        "output_tokens_details": None,
    }

    await _handle_provider_call(mock_session, ws_id, event)

    call_args = mock_session.execute.call_args[0][0]
    params = call_args.compile().params
    assert params.get("provider_request_id") == "chatcmpl-abc123"
    assert params.get("cost_source") == "reported"
    assert params.get("input_tokens_details") == {"cached_tokens": 50}
    assert params.get("output_tokens_details") is None


@pytest.mark.anyio
async def test_handle_provider_call_sdk_events_get_null_reconciliation_fields() -> None:
    """SDK events without reconciliation fields get NULL in DB columns."""
    from runledger_api.workers.pipeline import _handle_provider_call

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    event = {
        "run_id": str(uuid.uuid4()),
        "span_id": str(uuid.uuid4()),
        "provider": "openai",
        "model": "gpt-4o",
        "status": "success",
        "input_tokens": 100,
        "output_tokens": 50,
        # No reconciliation fields — simulates SDK-originated events
    }

    await _handle_provider_call(mock_session, str(uuid.uuid4()), event)

    call_args = mock_session.execute.call_args[0][0]
    params = call_args.compile().params
    assert params.get("provider_request_id") is None
    assert params.get("reported_cost_usd") is None
    assert params.get("cost_source") is None
