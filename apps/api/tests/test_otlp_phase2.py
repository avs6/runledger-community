"""
Tests for OTLP Phase 2 — OTel GenAI support, retrieval metadata, convention tracking.

Covers:
  _extract_message_payloads — OTel GenAI span events
  _extract_message_payloads — generic input.value / output.value fallbacks
  _extract_retrieval_metadata — OpenInference retrieval.documents.*
  _extract_convention_metadata — telemetry.sdk.* resource attrs
  synthesize_canonical_events — convention metadata in run_start.metadata
  synthesize_canonical_events — retrieval span_end has metadata.documents
  synthesize_canonical_events — tool_call uses gen_ai.tool.name / tool_call.function.arguments
  OtlpParsedSpan — span_events field populated from raw OTLP events
  parse_otlp_json — span events parsed from raw OTLP payload
"""

from __future__ import annotations

import base64
import uuid

import pytest
from runledger_api.services.otlp_parse import (
    OtlpParsedSpan,
    OtlpTrace,
    _extract_convention_metadata,
    _extract_message_payloads,
    _extract_retrieval_metadata,
    _ns_to_dt,
    parse_otlp_json,
    synthesize_canonical_events,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_attr(key: str, value: str | int | float | bool) -> dict:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": value}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": value}}


def _b64(n_bytes: int, seed: int = 0) -> str:
    return base64.b64encode(bytes([seed % 256] * n_bytes)).decode()


def _make_llm_span(
    attrs: dict,
    resource_attrs: dict | None = None,
    span_events: list | None = None,
) -> tuple[uuid.UUID, OtlpTrace]:
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000030")
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
        ended_at=_ns_to_dt(t + 1_000_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "LLM", **attrs},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
        span_events=span_events or [],
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs=resource_attrs or {},
        spans=[span],
    )
    return ws_id, trace


def _make_retrieval_span(attrs: dict) -> tuple[uuid.UUID, OtlpTrace]:
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000031")
    trace_id_hex = "ccddaabb00112233445566778899aabb"
    span_hex = "ccddaabb11223344"
    t = 1_700_000_000_000_000_000

    span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=span_hex,
        parent_span_id_hex=None,
        name="Retrieval.query",
        span_type="retrieval",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 500_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "RETRIEVER", **attrs},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={},
        spans=[span],
    )
    return ws_id, trace


def _make_tool_span(attrs: dict) -> tuple[uuid.UUID, OtlpTrace]:
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000032")
    trace_id_hex = "eeff001122334455667788990011aabb"
    span_hex = "eeff001100112233"
    t = 1_700_000_000_000_000_000

    span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=span_hex,
        parent_span_id_hex=None,
        name="tool_call",
        span_type="tool",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 200_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "TOOL", **attrs},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={},
        spans=[span],
    )
    return ws_id, trace


# ── _extract_message_payloads — OTel GenAI span events ────────────────────────


def test_extract_message_payloads_genai_user_event() -> None:
    """gen_ai.user.message span event maps to messages[role=user]."""
    span_events = [
        {"name": "gen_ai.user.message", "attrs": {"gen_ai.event.content": "Hello world"}},
    ]
    result = _extract_message_payloads({}, span_events)
    assert result is not None
    assert result["messages"] == [{"role": "user", "content": "Hello world"}]


def test_extract_message_payloads_genai_system_event() -> None:
    """gen_ai.system.message span event maps to messages[role=system]."""
    span_events = [
        {"name": "gen_ai.system.message", "attrs": {"gen_ai.event.content": "You are helpful."}},
    ]
    result = _extract_message_payloads({}, span_events)
    assert result is not None
    assert result["messages"][0]["role"] == "system"
    assert result["messages"][0]["content"] == "You are helpful."


def test_extract_message_payloads_genai_assistant_event() -> None:
    """gen_ai.assistant.message span event maps to response."""
    span_events = [
        {"name": "gen_ai.assistant.message", "attrs": {"gen_ai.event.content": "I can help!"}},
    ]
    result = _extract_message_payloads({}, span_events)
    assert result is not None
    assert result["response"] == {"role": "assistant", "content": "I can help!"}


def test_extract_message_payloads_genai_tool_event() -> None:
    """gen_ai.tool.message span event maps to messages[role=tool]."""
    span_events = [
        {"name": "gen_ai.tool.message", "attrs": {"gen_ai.event.content": '{"result": 42}'}},
    ]
    result = _extract_message_payloads({}, span_events)
    assert result is not None
    assert result["messages"][0]["role"] == "tool"


def test_extract_message_payloads_genai_multi_turn() -> None:
    """Multiple GenAI span events produce ordered messages list."""
    span_events = [
        {"name": "gen_ai.system.message", "attrs": {"gen_ai.event.content": "Be concise."}},
        {"name": "gen_ai.user.message", "attrs": {"gen_ai.event.content": "What is 2+2?"}},
        {"name": "gen_ai.assistant.message", "attrs": {"gen_ai.event.content": "4"}},
    ]
    result = _extract_message_payloads({}, span_events)
    assert result is not None
    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "system"
    assert result["messages"][1]["role"] == "user"
    assert result["response"]["content"] == "4"


def test_extract_message_payloads_openinference_takes_priority() -> None:
    """OpenInference attrs win over GenAI span events when both present."""
    attrs = {
        "llm.input_messages.0.message.role": "user",
        "llm.input_messages.0.message.content": "OI content",
    }
    span_events = [
        {"name": "gen_ai.user.message", "attrs": {"gen_ai.event.content": "GenAI content"}},
    ]
    result = _extract_message_payloads(attrs, span_events)
    assert result is not None
    assert result["messages"][0]["content"] == "OI content"


def test_extract_message_payloads_input_value_fallback() -> None:
    """input.value used when no OpenInference or GenAI attrs present."""
    result = _extract_message_payloads({"input.value": "generic prompt"})
    assert result is not None
    assert result["messages"] == [{"role": "user", "content": "generic prompt"}]


def test_extract_message_payloads_output_value_fallback() -> None:
    """output.value used as response fallback."""
    result = _extract_message_payloads({"output.value": "generic response"})
    assert result is not None
    assert result["response"] == {"role": "assistant", "content": "generic response"}


def test_extract_message_payloads_none_when_empty() -> None:
    result = _extract_message_payloads({})
    assert result is None


# ── _extract_retrieval_metadata ────────────────────────────────────────────────


def test_extract_retrieval_metadata_single_doc() -> None:
    attrs = {
        "retrieval.documents.0.document.id": "doc-abc",
        "retrieval.documents.0.document.score": 0.92,
        "retrieval.documents.0.document.content": "Paris is the capital.",
    }
    result = _extract_retrieval_metadata(attrs)
    assert result is not None
    assert result["document_count"] == 1
    assert result["documents"][0]["id"] == "doc-abc"
    assert result["documents"][0]["score"] == pytest.approx(0.92)
    assert result["documents"][0]["content"] == "Paris is the capital."


def test_extract_retrieval_metadata_multiple_docs() -> None:
    attrs = {
        "retrieval.documents.0.document.id": "d0",
        "retrieval.documents.0.document.score": 0.9,
        "retrieval.documents.1.document.id": "d1",
        "retrieval.documents.1.document.score": 0.75,
        "retrieval.documents.2.document.id": "d2",
        "retrieval.documents.2.document.score": 0.6,
    }
    result = _extract_retrieval_metadata(attrs)
    assert result is not None
    assert result["document_count"] == 3
    assert [d["id"] for d in result["documents"]] == ["d0", "d1", "d2"]


def test_extract_retrieval_metadata_none_when_absent() -> None:
    result = _extract_retrieval_metadata({})
    assert result is None


def test_extract_retrieval_metadata_id_only() -> None:
    """A document with only an ID (no score or content) is still captured."""
    attrs = {"retrieval.documents.0.document.id": "doc-x"}
    result = _extract_retrieval_metadata(attrs)
    assert result is not None
    assert result["document_count"] == 1
    assert "score" not in result["documents"][0]


# ── _extract_convention_metadata ──────────────────────────────────────────────


def test_extract_convention_metadata_full() -> None:
    resource = {
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.version": "1.25.0",
        "telemetry.sdk.language": "python",
    }
    result = _extract_convention_metadata(
        resource, "openinference.instrumentation.openai", "0.1.12"
    )
    assert result is not None
    assert result["sdk_name"] == "opentelemetry"
    assert result["sdk_version"] == "1.25.0"
    assert result["sdk_language"] == "python"
    assert result["instrumentation_scope"] == "openinference.instrumentation.openai"
    assert result["instrumentation_scope_version"] == "0.1.12"


def test_extract_convention_metadata_none_when_empty() -> None:
    result = _extract_convention_metadata({}, None, None)
    assert result is None


def test_extract_convention_metadata_partial() -> None:
    result = _extract_convention_metadata({"telemetry.sdk.name": "opentelemetry"}, None, None)
    assert result is not None
    assert result["sdk_name"] == "opentelemetry"
    assert "sdk_version" not in result


# ── synthesize_canonical_events — convention metadata in run_start ─────────────


def test_run_start_includes_convention_metadata() -> None:
    ws_id, trace = _make_llm_span(
        {"llm.model_name": "gpt-4o", "llm.token_count.prompt": 50},
        resource_attrs={
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.version": "1.25.0",
        },
    )
    # Give the root span a scope
    trace.spans[0].scope_name = "openinference.instrumentation.openai"
    trace.spans[0].scope_version = "0.1.12"

    events = synthesize_canonical_events(ws_id, trace)
    run_start = next(e for e in events if e["event_type"] == "run_start")

    instrumentation = run_start.get("metadata", {}).get("instrumentation")
    assert instrumentation is not None
    assert instrumentation["sdk_name"] == "opentelemetry"
    assert instrumentation["instrumentation_scope"] == "openinference.instrumentation.openai"


def test_run_start_no_convention_metadata_when_missing() -> None:
    ws_id, trace = _make_llm_span({"llm.model_name": "gpt-4o"})
    events = synthesize_canonical_events(ws_id, trace)
    run_start = next(e for e in events if e["event_type"] == "run_start")
    assert "instrumentation" not in run_start.get("metadata", {})


# ── synthesize_canonical_events — retrieval span metadata ─────────────────────


def test_retrieval_span_end_has_document_metadata() -> None:
    ws_id, trace = _make_retrieval_span(
        {
            "retrieval.documents.0.document.id": "doc-1",
            "retrieval.documents.0.document.score": 0.88,
            "retrieval.documents.1.document.id": "doc-2",
            "retrieval.documents.1.document.score": 0.71,
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    span_end = next(e for e in events if e["event_type"] == "span_end")

    meta = span_end.get("metadata", {})
    assert meta["document_count"] == 2
    assert meta["documents"][0]["id"] == "doc-1"


def test_retrieval_span_end_no_metadata_when_absent() -> None:
    ws_id, trace = _make_retrieval_span({})
    events = synthesize_canonical_events(ws_id, trace)
    span_end = next(e for e in events if e["event_type"] == "span_end")
    assert "metadata" not in span_end


# ── synthesize_canonical_events — GenAI span events in LLM span_end ───────────


def test_llm_span_end_captures_genai_span_events() -> None:
    """OTel GenAI span events produce message payloads in span_end.metadata."""
    ws_id, trace = _make_llm_span(
        {"gen_ai.system": "openai", "gen_ai.request.model": "gpt-4o"},
        span_events=[
            {"name": "gen_ai.user.message", "attrs": {"gen_ai.event.content": "Hi there"}},
            {"name": "gen_ai.assistant.message", "attrs": {"gen_ai.event.content": "Hello!"}},
        ],
    )
    events = synthesize_canonical_events(ws_id, trace)
    span_end = next(e for e in events if e["event_type"] == "span_end")

    meta = span_end.get("metadata", {})
    assert meta["messages"] == [{"role": "user", "content": "Hi there"}]
    assert meta["response"] == {"role": "assistant", "content": "Hello!"}


# ── synthesize_canonical_events — tool_call gen_ai attrs ──────────────────────


def test_tool_call_uses_gen_ai_tool_name() -> None:
    ws_id, trace = _make_tool_span(
        {
            "gen_ai.tool.name": "web_search",
            "gen_ai.tool.call.function.arguments": '{"query": "cats"}',
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    tc = next(e for e in events if e["event_type"] == "tool_call")
    assert tc["tool_name"] == "web_search"
    assert tc["metadata"]["tool_arguments"] == '{"query": "cats"}'


def test_tool_call_uses_tool_call_function_arguments_fallback() -> None:
    ws_id, trace = _make_tool_span(
        {
            "tool.name": "calculator",
            "tool_call.function.arguments": '{"expr": "1+1"}',
        }
    )
    events = synthesize_canonical_events(ws_id, trace)
    tc = next(e for e in events if e["event_type"] == "tool_call")
    assert tc["tool_name"] == "calculator"
    assert tc["metadata"]["tool_arguments"] == '{"expr": "1+1"}'


# ── parse_otlp_json — span events parsing ─────────────────────────────────────


def test_parse_otlp_json_captures_span_events() -> None:
    """Span events from raw OTLP are parsed into OtlpParsedSpan.span_events."""
    trace_id = base64.b64encode(bytes(range(16))).decode()
    span_id = base64.b64encode(bytes(range(8))).decode()

    payload = {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "scope": {"name": "openai", "version": "0.1.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": "chat.completions",
                                "kind": 3,
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000001000000000",
                                "status": {"code": 1},
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                                ],
                                "events": [
                                    {
                                        "name": "gen_ai.user.message",
                                        "attributes": [
                                            {
                                                "key": "gen_ai.event.content",
                                                "value": {"stringValue": "Hello"},
                                            },
                                        ],
                                    },
                                    {
                                        "name": "gen_ai.assistant.message",
                                        "attributes": [
                                            {
                                                "key": "gen_ai.event.content",
                                                "value": {"stringValue": "Hi!"},
                                            },
                                        ],
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    result = parse_otlp_json(payload)
    assert len(result.traces) == 1
    span = result.traces[0].spans[0]
    assert len(span.span_events) == 2
    assert span.span_events[0]["name"] == "gen_ai.user.message"
    assert span.span_events[0]["attrs"]["gen_ai.event.content"] == "Hello"
    assert span.span_events[1]["name"] == "gen_ai.assistant.message"
