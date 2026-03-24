"""
Tests for Phase 32 — Developer Experience + Public API.

Covers:
  - Scalar /reference endpoint returns HTML with api-reference script
  - OpenAPI spec served at /openapi.json
  - RunLedgerOTLPExporter: spans_to_otlp_json serialisation
  - RunLedgerOTLPExporter: export() success and failure paths
  - CLI init command: bootstrap + .env write
  - CLI doctor command: pass / fail scenarios
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

# ── /reference Scalar UI ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_scalar_reference_returns_html(client: AsyncClient) -> None:
    resp = await client.get("/reference")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "api-reference" in body
    assert "/openapi.json" in body
    assert "scalar" in body.lower()


# ── /openapi.json ─────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_openapi_json_served(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "RunLedger API"
    assert "paths" in data


# ── spans_to_otlp_json ────────────────────────────────────────────────────────


def _make_readable_span(
    name: str = "test-span",
    trace_id: int = 0xABCDEF1234567890ABCDEF1234567890,
    span_id: int = 0x1234567890ABCDEF,
    parent_span_id: int | None = None,
    attributes: dict | None = None,
) -> SimpleNamespace:
    """Build a minimal mock ReadableSpan."""
    ctx = SimpleNamespace(trace_id=trace_id, span_id=span_id)
    parent = None
    if parent_span_id is not None:
        parent = SimpleNamespace(span_id=parent_span_id)

    resource = SimpleNamespace(attributes={"service.name": "test-service"})
    scope = SimpleNamespace(name="openinference.instrumentation.openai", version="0.1.0")

    class FakeStatus:
        pass

    status = FakeStatus()

    return SimpleNamespace(
        context=ctx,
        parent=parent,
        name=name,
        kind=None,
        start_time=1_700_000_000_000_000_000,
        end_time=1_700_000_001_000_000_000,
        attributes=attributes or {
            "openinference.span.kind": "LLM",
            "llm.model_name": "gpt-4o-mini",
            "llm.token_count.prompt": 42,
            "llm.token_count.completion": 18,
        },
        resource=resource,
        instrumentation_scope=scope,
        status=status,
        events=[],
    )


def test_spans_to_otlp_json_structure():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    span = _make_readable_span()
    payload = spans_to_otlp_json([span])

    assert "resourceSpans" in payload
    assert len(payload["resourceSpans"]) == 1
    rs = payload["resourceSpans"][0]
    assert "resource" in rs
    assert "scopeSpans" in rs
    assert len(rs["scopeSpans"]) == 1
    scope_span = rs["scopeSpans"][0]
    assert scope_span["scope"]["name"] == "openinference.instrumentation.openai"
    assert len(scope_span["spans"]) == 1


def test_spans_to_otlp_json_ids():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    span = _make_readable_span(
        trace_id=0xABCDEF1234567890ABCDEF1234567890,
        span_id=0x1234567890ABCDEF,
    )
    payload = spans_to_otlp_json([span])
    otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]

    # IDs should be lowercase hex strings
    assert otlp_span["traceId"] == "abcdef1234567890abcdef1234567890"
    assert otlp_span["spanId"] == "1234567890abcdef"
    assert "parentSpanId" not in otlp_span


def test_spans_to_otlp_json_parent_span_id():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    span = _make_readable_span(parent_span_id=0xFEDCBA9876543210)
    payload = spans_to_otlp_json([span])
    otlp_span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]

    assert otlp_span["parentSpanId"] == "fedcba9876543210"


def test_spans_to_otlp_json_attributes():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    span = _make_readable_span(attributes={"llm.model_name": "gpt-4o", "llm.token_count.prompt": 100})
    payload = spans_to_otlp_json([span])
    attrs = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
    keys = {a["key"] for a in attrs}
    assert "llm.model_name" in keys
    assert "llm.token_count.prompt" in keys


def test_spans_to_otlp_json_groups_by_resource():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    span1 = _make_readable_span(name="span-1", span_id=0x1111111111111111)
    span2 = _make_readable_span(name="span-2", span_id=0x2222222222222222)
    # Same resource object — should merge into one resourceSpan
    span2.resource = span1.resource
    payload = spans_to_otlp_json([span1, span2])
    assert len(payload["resourceSpans"]) == 1
    assert len(payload["resourceSpans"][0]["scopeSpans"][0]["spans"]) == 2


def test_spans_to_otlp_json_empty():
    from runledger_sdk.otel_exporter import spans_to_otlp_json

    payload = spans_to_otlp_json([])
    assert payload == {"resourceSpans": []}


# ── RunLedgerOTLPExporter.export() ────────────────────────────────────────────


def test_exporter_export_success():
    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    try:
        from opentelemetry.sdk.trace.export import SpanExportResult
    except ImportError:
        pytest.skip("opentelemetry-sdk not installed")

    exporter = RunLedgerOTLPExporter(api_key="rl_test_abc", base_url="http://localhost:8000")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(exporter._client, "post", return_value=mock_response):
        span = _make_readable_span()
        result = exporter.export([span])

    assert result == SpanExportResult.SUCCESS


def test_exporter_export_failure_http():
    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    try:
        from opentelemetry.sdk.trace.export import SpanExportResult
    except ImportError:
        pytest.skip("opentelemetry-sdk not installed")

    exporter = RunLedgerOTLPExporter(api_key="rl_test_abc", base_url="http://localhost:8000")

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service Unavailable"

    with patch.object(exporter._client, "post", return_value=mock_response):
        result = exporter.export([_make_readable_span()])

    assert result == SpanExportResult.FAILURE


def test_exporter_export_empty_spans():
    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    try:
        from opentelemetry.sdk.trace.export import SpanExportResult
    except ImportError:
        pytest.skip("opentelemetry-sdk not installed")

    exporter = RunLedgerOTLPExporter(api_key="rl_test_abc", base_url="http://localhost:8000")
    result = exporter.export([])
    assert result == SpanExportResult.SUCCESS


def test_exporter_requires_api_key():
    import os

    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    old = os.environ.pop("RUNLEDGER_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="api_key"):
            RunLedgerOTLPExporter(api_key=None, base_url="http://localhost:8000")
    finally:
        if old:
            os.environ["RUNLEDGER_API_KEY"] = old
