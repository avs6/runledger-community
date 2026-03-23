"""
Tests for OTLP/HTTP trace ingestion — Phase 0.

Covers:
  POST /v1/traces           — happy path, auth, content-type, oversized, gzip
  POST /otlp/v1/traces      — alias route
  otlp_parse module         — ID decoding, attribute flattening, span classification,
                               LLM field extraction, canonical event synthesis

No live DB required — uses authed_client / mock_db_session from conftest.
"""

from __future__ import annotations

import base64
import gzip
import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from runledger_api.services.otlp_parse import (
    _classify_span,
    _decode_id,
    _extract_llm_fields,
    _extract_message_payloads,
    _extract_run_context,
    _flatten_attrs,
    _make_run_id,
    _make_span_uuid,
    _ns_to_dt,
    parse_otlp_json,
    synthesize_canonical_events,
)


# ── Fixtures / helpers ─────────────────────────────────────────────────────────


def _make_attr(key: str, value: str | int | float | bool) -> dict:
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": value}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": value}}


def _b64_trace_id() -> str:
    """16 random bytes as base64 (OTLP wire format)."""
    raw = bytes(range(16))
    return base64.b64encode(raw).decode()


def _b64_span_id(seed: int = 0) -> str:
    """8 random bytes as base64."""
    raw = bytes(range(seed, seed + 8))
    return base64.b64encode(raw).decode()


def _hex_trace_id() -> str:
    return "0102030405060708090a0b0c0d0e0f10"


def _hex_span_id(seed: int = 0) -> str:
    return "".join(f"{(seed + i) % 256:02x}" for i in range(8))


def _minimal_span(
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_id: str | None = None,
    name: str = "chain.run",
    attrs: list | None = None,
    start_ns: int = 1_700_000_000_000_000_000,
    end_ns: int = 1_700_000_001_000_000_000,
) -> dict:
    span: dict = {
        "traceId": trace_id or _b64_trace_id(),
        "spanId": span_id or _b64_span_id(),
        "name": name,
        "kind": 3,
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(end_ns),
        "attributes": attrs or [],
        "status": {"code": 1},
    }
    if parent_id:
        span["parentSpanId"] = parent_id
    return span


def _otlp_payload(spans: list[dict], resource_attrs: list | None = None) -> dict:
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": resource_attrs or []},
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "openinference.instrumentation.langchain",
                            "version": "0.1.0",
                        },
                        "spans": spans,
                    }
                ],
            }
        ]
    }


# ── Unit tests: otlp_parse helpers ─────────────────────────────────────────────


def test_decode_id_hex_passthrough():
    hex_id = "0102030405060708090a0b0c0d0e0f10"
    assert _decode_id(hex_id) == hex_id


def test_decode_id_base64():
    raw = bytes(range(16))
    b64 = base64.b64encode(raw).decode()
    assert _decode_id(b64) == raw.hex()


def test_decode_id_empty():
    assert _decode_id(None) == ""
    assert _decode_id("") == ""


def test_ns_to_dt_basic():
    ns = 1_700_000_000_000_000_000
    dt = _ns_to_dt(ns)
    assert dt is not None
    assert dt.tzinfo == UTC


def test_ns_to_dt_string():
    dt = _ns_to_dt("1700000000000000000")
    assert dt is not None


def test_ns_to_dt_none():
    assert _ns_to_dt(None) is None


def test_flatten_attrs_string():
    attrs = [_make_attr("foo", "bar")]
    result = _flatten_attrs(attrs)
    assert result == {"foo": "bar"}


def test_flatten_attrs_int():
    attrs = [_make_attr("count", 42)]
    result = _flatten_attrs(attrs)
    assert result["count"] == 42


def test_flatten_attrs_float():
    attrs = [_make_attr("score", 0.95)]
    result = _flatten_attrs(attrs)
    assert result["score"] == pytest.approx(0.95)


def test_flatten_attrs_bool():
    attrs = [_make_attr("success", True)]
    result = _flatten_attrs(attrs)
    assert result["success"] is True


def test_flatten_attrs_empty():
    assert _flatten_attrs([]) == {}
    assert _flatten_attrs(None) == {}  # type: ignore[arg-type]


def test_classify_span_openinference_llm():
    attrs = {"openinference.span.kind": "LLM"}
    assert _classify_span(attrs, "some.span") == "llm"


def test_classify_span_openinference_agent():
    attrs = {"openinference.span.kind": "AGENT"}
    assert _classify_span(attrs, "run") == "agent"


def test_classify_span_openinference_tool():
    attrs = {"openinference.span.kind": "TOOL"}
    assert _classify_span(attrs, "run") == "tool"


def test_classify_span_genai_system():
    attrs = {"gen_ai.system": "openai", "gen_ai.request.model": "gpt-4o"}
    assert _classify_span(attrs, "chat") == "llm"


def test_classify_span_name_hint():
    assert _classify_span({}, "chat.completion") == "llm"
    assert _classify_span({}, "tool_executor") == "tool"


def test_classify_span_fallback():
    assert _classify_span({}, "some_unknown_span") == "chain"


def test_extract_llm_fields_openinference():
    attrs = {
        "llm.model_name": "gpt-4o",
        "llm.provider": "openai",
        "llm.token_count.prompt": 100,
        "llm.token_count.completion": 50,
    }
    result = _extract_llm_fields(attrs)
    assert result["model"] == "gpt-4o"
    assert result["provider"] == "openai"
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50


def test_extract_llm_fields_genai():
    attrs = {
        "gen_ai.system": "anthropic",
        "gen_ai.request.model": "claude-3-5-sonnet",
        "gen_ai.usage.input_tokens": 200,
        "gen_ai.usage.output_tokens": 80,
    }
    result = _extract_llm_fields(attrs)
    assert result["model"] == "claude-3-5-sonnet"
    assert result["provider"] == "anthropic"
    assert result["input_tokens"] == 200
    assert result["output_tokens"] == 80


def test_deterministic_ids():
    workspace_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    trace_hex = "aabbccddeeff00112233445566778899"
    r1 = _make_run_id(workspace_id, trace_hex)
    r2 = _make_run_id(workspace_id, trace_hex)
    assert r1 == r2

    span_hex = "aabbccdd00112233"
    s1 = _make_span_uuid(workspace_id, trace_hex, span_hex)
    s2 = _make_span_uuid(workspace_id, trace_hex, span_hex)
    assert s1 == s2
    assert s1 != r1  # run and span IDs differ


# ── Unit tests: parse_otlp_json ────────────────────────────────────────────────


def test_parse_empty_payload():
    result = parse_otlp_json({})
    assert result.traces == []
    assert result.total_spans == 0


def test_parse_single_span():
    span = _minimal_span()
    payload = _otlp_payload([span])
    result = parse_otlp_json(payload)
    assert len(result.traces) == 1
    assert result.total_spans == 1
    assert result.traces[0].spans[0].name == "chain.run"


def test_parse_span_classification():
    llm_span = _minimal_span(
        attrs=[_make_attr("openinference.span.kind", "LLM")]
    )
    payload = _otlp_payload([llm_span])
    result = parse_otlp_json(payload)
    assert result.traces[0].spans[0].span_type == "llm"


def test_parse_resource_attributes():
    payload = _otlp_payload(
        [_minimal_span()],
        resource_attrs=[_make_attr("service.name", "my-agent")],
    )
    result = parse_otlp_json(payload)
    assert result.traces[0].resource_attrs.get("service.name") == "my-agent"


def test_parse_multiple_spans_same_trace():
    trace_id = _b64_trace_id()
    root_span_id = _b64_span_id(0)
    child_span_id = _b64_span_id(10)
    root = _minimal_span(trace_id=trace_id, span_id=root_span_id, name="agent.run")
    child = _minimal_span(
        trace_id=trace_id,
        span_id=child_span_id,
        parent_id=root_span_id,
        name="llm.call",
        attrs=[_make_attr("openinference.span.kind", "LLM")],
    )
    payload = _otlp_payload([root, child])
    result = parse_otlp_json(payload)
    assert len(result.traces) == 1
    assert result.total_spans == 2


def test_parse_hex_span_ids():
    """Some SDKs emit hex string IDs directly."""
    span = _minimal_span(
        trace_id=_hex_trace_id(),
        span_id=_hex_span_id(0),
        name="chain.run",
    )
    payload = _otlp_payload([span])
    result = parse_otlp_json(payload)
    assert result.total_spans == 1


# ── Unit tests: synthesize_canonical_events ────────────────────────────────────


def test_synthesize_minimal_trace():
    workspace_id = uuid.uuid4()
    span = _minimal_span(name="agent.run", attrs=[_make_attr("openinference.span.kind", "AGENT")])
    payload = _otlp_payload([span])
    result = parse_otlp_json(payload)
    events = synthesize_canonical_events(workspace_id, result.traces[0])

    event_types = [e["event_type"] for e in events]
    assert "run_start" in event_types
    assert "span_start" in event_types
    assert "span_end" in event_types
    assert "run_end" in event_types


def test_synthesize_llm_span_produces_provider_call():
    workspace_id = uuid.uuid4()
    trace_id = _b64_trace_id()
    root_id = _b64_span_id(0)
    llm_id = _b64_span_id(10)

    root = _minimal_span(trace_id=trace_id, span_id=root_id, name="agent.run")
    llm_span = _minimal_span(
        trace_id=trace_id,
        span_id=llm_id,
        parent_id=root_id,
        name="llm.call",
        attrs=[
            _make_attr("openinference.span.kind", "LLM"),
            _make_attr("llm.model_name", "gpt-4o"),
            _make_attr("llm.provider", "openai"),
            _make_attr("llm.token_count.prompt", 100),
            _make_attr("llm.token_count.completion", 50),
        ],
    )

    payload = _otlp_payload([root, llm_span])
    result = parse_otlp_json(payload)
    events = synthesize_canonical_events(workspace_id, result.traces[0])

    provider_calls = [e for e in events if e["event_type"] == "provider_call"]
    assert len(provider_calls) == 1
    pc = provider_calls[0]
    assert pc["model"] == "gpt-4o"
    assert pc["provider"] == "openai"
    assert pc["input_tokens"] == 100
    assert pc["output_tokens"] == 50


def test_synthesize_tool_span_produces_tool_call():
    workspace_id = uuid.uuid4()
    trace_id = _b64_trace_id()
    root_id = _b64_span_id(0)
    tool_id = _b64_span_id(20)

    root = _minimal_span(trace_id=trace_id, span_id=root_id, name="agent.run")
    tool_span = _minimal_span(
        trace_id=trace_id,
        span_id=tool_id,
        parent_id=root_id,
        name="search_tool",
        attrs=[
            _make_attr("openinference.span.kind", "TOOL"),
            _make_attr("tool.name", "search"),
        ],
    )

    payload = _otlp_payload([root, tool_span])
    result = parse_otlp_json(payload)
    events = synthesize_canonical_events(workspace_id, result.traces[0])

    tool_calls = [e for e in events if e["event_type"] == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_name"] == "search"


def test_synthesize_deterministic_run_id():
    workspace_id = uuid.uuid4()
    span = _minimal_span()
    payload = _otlp_payload([span])
    result = parse_otlp_json(payload)
    trace = result.traces[0]

    events1 = synthesize_canonical_events(workspace_id, trace)
    events2 = synthesize_canonical_events(workspace_id, trace)

    run_id_1 = events1[0]["run_id"]
    run_id_2 = events2[0]["run_id"]
    assert run_id_1 == run_id_2  # deterministic


# ── HTTP route tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_receive_traces_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /v1/traces with valid OTLP JSON → 200 + OTLP success response."""
    # Make flush() a no-op and give batch an id
    batch_id = uuid.uuid4()

    async def fake_flush() -> None:
        pass

    mock_db_session.flush = AsyncMock(side_effect=fake_flush)

    # batch.id is set on OtlpIngestBatch.__init__ (default=uuid.uuid4)
    span = _minimal_span()
    payload = _otlp_payload([span])

    with patch("runledger_api.workers.pipeline.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(
            "/v1/traces",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"partialSuccess": {}}


@pytest.mark.asyncio
async def test_receive_traces_alias(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /otlp/v1/traces (alias) → 200."""
    span = _minimal_span()
    payload = _otlp_payload([span])

    mock_db_session.flush = AsyncMock()

    with patch("runledger_api.workers.pipeline.process_events_task"):
        resp = await authed_client.post(
            "/otlp/v1/traces",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_receive_traces_requires_auth(client: AsyncClient) -> None:
    """POST /v1/traces without auth → 401."""
    resp = await client.post(
        "/v1/traces",
        content=b"{}",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_receive_traces_protobuf_rejected(
    authed_client: AsyncClient,
) -> None:
    """POST /v1/traces with protobuf content-type → 415."""
    resp = await authed_client.post(
        "/v1/traces",
        content=b"\x00\x01\x02",
        headers={"Content-Type": "application/x-protobuf"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_receive_traces_invalid_json(
    authed_client: AsyncClient,
) -> None:
    """POST /v1/traces with invalid JSON → 422."""
    resp = await authed_client.post(
        "/v1/traces",
        content=b"not-json{{{",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_receive_traces_gzip_compressed(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /v1/traces with gzip body → 200."""
    span = _minimal_span()
    payload = _otlp_payload([span])
    compressed = gzip.compress(json.dumps(payload).encode())

    mock_db_session.flush = AsyncMock()

    with patch("runledger_api.workers.pipeline.process_events_task"):
        resp = await authed_client.post(
            "/v1/traces",
            content=compressed,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_receive_traces_openinference_llm(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """Full OpenInference trace with LLM span → accepted, provider_call enqueued."""
    trace_id = _b64_trace_id()
    root_id = _b64_span_id(0)
    llm_id = _b64_span_id(10)

    root = _minimal_span(trace_id=trace_id, span_id=root_id, name="agent.run")
    llm_span = _minimal_span(
        trace_id=trace_id,
        span_id=llm_id,
        parent_id=root_id,
        name="llm.call",
        attrs=[
            _make_attr("openinference.span.kind", "LLM"),
            _make_attr("llm.model_name", "claude-3-5-sonnet"),
            _make_attr("llm.provider", "anthropic"),
            _make_attr("llm.token_count.prompt", 150),
            _make_attr("llm.token_count.completion", 60),
        ],
    )
    payload = _otlp_payload(
        [root, llm_span],
        resource_attrs=[_make_attr("service.name", "my-agent")],
    )

    mock_db_session.flush = AsyncMock()
    captured: list[tuple] = []

    with patch("runledger_api.workers.pipeline.process_events_task") as mock_task:
        mock_task.delay = MagicMock(side_effect=lambda ws_id, evs: captured.append((ws_id, evs)))
        resp = await authed_client.post(
            "/v1/traces",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert len(captured) == 1
    _ws_id, enqueued = captured[0]
    event_types = [e["event_type"] for e in enqueued]
    assert "provider_call" in event_types
    pc = next(e for e in enqueued if e["event_type"] == "provider_call")
    assert pc["model"] == "claude-3-5-sonnet"
    assert pc["input_tokens"] == 150


# ── Phase 1: run-context extraction ────────────────────────────────────────────


def test_extract_run_context_openinference_attrs():
    resource = {"service.name": "my-svc", "service.version": "2.1.0"}
    root_attrs = {
        "session.id": "sess_abc",
        "user.id": "user_123",
        "openinference.span.kind": "AGENT",
    }
    ctx = _extract_run_context(resource, root_attrs)
    assert ctx["session_id"] == "sess_abc"
    assert ctx["end_user_id"] == "user_123"
    assert ctx["deployment_version"] == "2.1.0"
    assert "feature_tag" not in ctx


def test_extract_run_context_runledger_prefix_takes_priority():
    resource = {"service.version": "1.0"}
    root_attrs = {
        "runledger.session_id": "rl_sess",
        "session.id": "otel_sess",
        "runledger.end_user_id": "rl_user",
        "user.id": "otel_user",
        "runledger.feature_tag": "checkout",
        "runledger.deployment_version": "v3",
    }
    ctx = _extract_run_context(resource, root_attrs)
    assert ctx["session_id"] == "rl_sess"
    assert ctx["end_user_id"] == "rl_user"
    assert ctx["feature_tag"] == "checkout"
    assert ctx["deployment_version"] == "v3"


def test_extract_run_context_empty_returns_empty_dict():
    ctx = _extract_run_context({}, {})
    assert ctx == {}


def test_extract_run_context_feature_tag_fallback():
    ctx = _extract_run_context({}, {"tag.feature": "search"})
    assert ctx["feature_tag"] == "search"


def test_extract_run_context_in_run_start_event():
    """synthesize_canonical_events spreads run_ctx as top-level fields on run_start."""
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    trace_id_hex = "0102030405060708090a0b0c0d0e0f10"
    span_id_hex = "0102030405060708"
    t = 1_700_000_000_000_000_000

    from runledger_api.services.otlp_parse import OtlpParsedSpan, OtlpTrace

    root_span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=span_id_hex,
        parent_span_id_hex=None,
        name="agent.run",
        span_type="agent",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 1_000_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "AGENT", "session.id": "sess_xyz", "user.id": "u99"},
        scope_name="openinference.langchain",
        scope_version="0.1",
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={"service.name": "svc", "service.version": "3.0"},
        spans=[root_span],
    )
    events = synthesize_canonical_events(ws_id, trace)
    run_start = next(e for e in events if e["event_type"] == "run_start")
    assert run_start["session_id"] == "sess_xyz"
    assert run_start["end_user_id"] == "u99"
    assert run_start["deployment_version"] == "3.0"


# ── Phase 1: message payload extraction ────────────────────────────────────────


def test_extract_message_payloads_openinference():
    attrs = {
        "llm.input_messages.0.message.role": "system",
        "llm.input_messages.0.message.content": "You are helpful.",
        "llm.input_messages.1.message.role": "user",
        "llm.input_messages.1.message.content": "Hello?",
        "llm.output_messages.0.message.content": "Hi there!",
    }
    result = _extract_message_payloads(attrs)
    assert result is not None
    assert result["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello?"},
    ]
    assert result["response"] == {"role": "assistant", "content": "Hi there!"}


def test_extract_message_payloads_generic_fallback():
    attrs = {
        "input.value": "What is 2+2?",
        "output.value": "4",
    }
    result = _extract_message_payloads(attrs)
    assert result is not None
    assert result["messages"] == [{"role": "user", "content": "What is 2+2?"}]
    assert result["response"] == {"role": "assistant", "content": "4"}


def test_extract_message_payloads_none_when_empty():
    assert _extract_message_payloads({}) is None
    assert _extract_message_payloads({"llm.model_name": "gpt-4"}) is None


def test_extract_message_payloads_output_only():
    attrs = {"llm.output_messages.0.message.content": "Done."}
    result = _extract_message_payloads(attrs)
    assert result is not None
    assert "messages" not in result
    assert result["response"] == {"role": "assistant", "content": "Done."}


def test_span_end_has_payload_for_llm_span():
    """synthesize_canonical_events attaches message payloads to LLM span_end events."""
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    trace_id_hex = "aabbccddeeff00112233445566778899"
    root_hex = "aabbccdd11223344"
    llm_hex = "aabbccdd55667788"
    t = 1_700_000_000_000_000_000

    from runledger_api.services.otlp_parse import OtlpParsedSpan, OtlpTrace

    root_span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=root_hex,
        parent_span_id_hex=None,
        name="agent.run",
        span_type="agent",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 2_000_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "AGENT"},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    llm_span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=llm_hex,
        parent_span_id_hex=root_hex,
        name="ChatOpenAI",
        span_type="llm",
        started_at=_ns_to_dt(t + 100_000_000),
        ended_at=_ns_to_dt(t + 1_500_000_000),
        status_code="OK",
        attrs={
            "openinference.span.kind": "LLM",
            "llm.model_name": "gpt-4o",
            "llm.input_messages.0.message.role": "user",
            "llm.input_messages.0.message.content": "Summarize this.",
            "llm.output_messages.0.message.content": "Here is a summary.",
        },
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={"service.name": "my-app"},
        spans=[root_span, llm_span],
    )
    events = synthesize_canonical_events(ws_id, trace)
    llm_span_uuid = str(_make_span_uuid(ws_id, trace_id_hex, llm_hex))
    span_end = next(
        e for e in events
        if e["event_type"] == "span_end" and e["span_id"] == llm_span_uuid
    )
    assert "metadata" in span_end
    assert span_end["metadata"]["messages"] == [{"role": "user", "content": "Summarize this."}]
    assert span_end["metadata"]["response"] == {"role": "assistant", "content": "Here is a summary."}


def test_span_end_no_payload_for_non_llm_span():
    """Non-LLM span_end events do not get a metadata payload dict."""
    ws_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    trace_id_hex = "1122334455667788990011223344556677"[:32]
    root_hex = "1122334455667788"
    t = 1_700_000_000_000_000_000

    from runledger_api.services.otlp_parse import OtlpParsedSpan, OtlpTrace

    root_span = OtlpParsedSpan(
        trace_id_hex=trace_id_hex,
        span_id_hex=root_hex,
        parent_span_id_hex=None,
        name="tool.call",
        span_type="tool",
        started_at=_ns_to_dt(t),
        ended_at=_ns_to_dt(t + 500_000_000),
        status_code="OK",
        attrs={"openinference.span.kind": "TOOL", "tool.name": "search"},
        scope_name=None,
        scope_version=None,
        otel_kind=3,
    )
    trace = OtlpTrace(
        trace_id_hex=trace_id_hex,
        resource_attrs={},
        spans=[root_span],
    )
    events = synthesize_canonical_events(ws_id, trace)
    span_end = next(e for e in events if e["event_type"] == "span_end")
    assert "metadata" not in span_end


# ── Phase 1: management endpoints ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_traces_stats(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /v1/traces/stats returns 24h + 7d aggregate counts."""
    from unittest.mock import MagicMock

    def _make_stats_row(batches: int, traces: int, spans: int) -> MagicMock:
        row = MagicMock()
        row.batches = batches
        row.traces = traces
        row.spans = spans
        result = MagicMock()
        result.one.return_value = row
        return result

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _make_stats_row(5, 10, 40),   # 24h
            _make_stats_row(30, 60, 240),  # 7d
        ]
    )

    resp = await authed_client.get("/v1/traces/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["last_24h"] == {"batches": 5, "traces": 10, "spans": 40}
    assert data["last_7d"] == {"batches": 30, "traces": 60, "spans": 240}


@pytest.mark.anyio
async def test_get_traces_batches(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /v1/traces/batches returns paginated batch list."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    fake_batch = SimpleNamespace(
        id=uuid.uuid4(),
        received_at=now,
        trace_count=3,
        span_count=12,
        status="accepted",
        error=None,
        content_type="application/json",
    )

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [fake_batch]
    list_result = MagicMock()
    list_result.scalars.return_value = scalars_mock

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    mock_db_session.execute = AsyncMock(side_effect=[list_result, count_result])

    resp = await authed_client.get("/v1/traces/batches?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["trace_count"] == 3
    assert item["span_count"] == 12
    assert item["status"] == "accepted"
    assert item["error"] is None
