"""
RunLedger OTLP Span Exporter.

Implements the OpenTelemetry SpanExporter interface so any OTel-instrumented
codebase (openinference-instrumentation-openai, openinference-instrumentation-anthropic,
etc.) can ship traces directly to RunLedger's /v1/traces endpoint.

Usage::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

    exporter = RunLedgerOTLPExporter(
        api_key="rl_live_...",
        base_url="https://api.runledger.io",  # or http://localhost:8000
    )
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))

Or via the RunLedger client::

    import runledger_sdk as rl

    client = rl.RunLedger(api_key="rl_live_...")
    client.instrument_otel(provider)  # attaches exporter to existing provider
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

import httpx

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.runledger.io"
_TIMEOUT = 10.0

# ── OTLP JSON helpers ─────────────────────────────────────────────────────────


def _attr_value(v: Any) -> dict[str, Any]:
    """Convert a Python value to an OTLP AttributeValue dict."""
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, bytes):
        import base64  # noqa: PLC0415
        return {"bytesValue": base64.b64encode(v).decode()}
    if isinstance(v, (list, tuple)):
        values = [_attr_value(i) for i in v]
        return {"arrayValue": {"values": values}}
    return {"stringValue": str(v)}


def _attrs(d: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not d:
        return []
    return [{"key": k, "value": _attr_value(v)} for k, v in d.items() if v is not None]


def _hex_id(n: int, width: int) -> str:
    """Convert an integer trace/span id to zero-padded lowercase hex."""
    return format(n, f"0{width}x")


def _ns(t: int | None) -> str:
    """Nanoseconds as string (OTLP JSON uses string for int64)."""
    return str(t) if t is not None else "0"


def _span_kind(kind: Any) -> int:
    """Map OTel SpanKind enum to OTLP integer."""
    try:
        from opentelemetry.trace import SpanKind  # noqa: PLC0415
        mapping = {
            SpanKind.INTERNAL: 1,
            SpanKind.SERVER: 2,
            SpanKind.CLIENT: 3,
            SpanKind.PRODUCER: 4,
            SpanKind.CONSUMER: 5,
        }
        return mapping.get(kind, 0)
    except ImportError:
        return 0


def _status_code(status: Any) -> int:
    """Map OTel StatusCode to OTLP integer."""
    try:
        from opentelemetry.trace import StatusCode  # noqa: PLC0415
        if status.status_code == StatusCode.OK:
            return 1
        if status.status_code == StatusCode.ERROR:
            return 2
    except (ImportError, AttributeError):
        pass
    return 0


def spans_to_otlp_json(spans: Sequence[Any]) -> dict[str, Any]:
    """
    Convert a sequence of OTel ReadableSpan objects to OTLP JSON payload.
    Groups spans by resource + instrumentation scope.
    """
    # Group by resource identity
    by_resource: dict[int, dict[str, Any]] = {}

    for span in spans:
        resource = span.resource
        resource_attrs = dict(getattr(resource, "attributes", {}) or {})
        resource_key = id(resource)

        if resource_key not in by_resource:
            by_resource[resource_key] = {
                "resource": {"attributes": _attrs(resource_attrs)},
                "scopeSpans": {},
            }

        scope = getattr(span, "instrumentation_scope", None) or getattr(
            span, "instrumentation_info", None
        )
        scope_name = getattr(scope, "name", "runledger-sdk")
        scope_version = getattr(scope, "version", "") or ""

        scope_key = (scope_name, scope_version)
        if scope_key not in by_resource[resource_key]["scopeSpans"]:
            by_resource[resource_key]["scopeSpans"][scope_key] = {
                "scope": {"name": scope_name, "version": scope_version},
                "spans": [],
            }

        ctx = span.context
        parent_ctx = getattr(span, "parent", None)

        otlp_span: dict[str, Any] = {
            "traceId": _hex_id(ctx.trace_id, 32),
            "spanId": _hex_id(ctx.span_id, 16),
            "name": span.name,
            "kind": _span_kind(span.kind),
            "startTimeUnixNano": _ns(span.start_time),
            "endTimeUnixNano": _ns(span.end_time),
            "attributes": _attrs(dict(span.attributes or {})),
            "status": {
                "code": _status_code(span.status),
                "message": getattr(span.status, "description", "") or "",
            },
            "events": [],
            "links": [],
        }

        if parent_ctx is not None:
            otlp_span["parentSpanId"] = _hex_id(
                getattr(parent_ctx, "span_id", 0), 16
            )

        # Span events
        for event in getattr(span, "events", []):
            otlp_span["events"].append({
                "timeUnixNano": _ns(getattr(event, "timestamp", None)),
                "name": event.name,
                "attributes": _attrs(dict(event.attributes or {})),
            })

        by_resource[resource_key]["scopeSpans"][scope_key]["spans"].append(otlp_span)

    resource_spans = []
    for rs in by_resource.values():
        resource_spans.append({
            "resource": rs["resource"],
            "scopeSpans": list(rs["scopeSpans"].values()),
        })

    return {"resourceSpans": resource_spans}


# ── Exporter ──────────────────────────────────────────────────────────────────


class RunLedgerOTLPExporter:
    """
    OpenTelemetry SpanExporter that ships traces to RunLedger.

    Drop-in replacement for any OTLP HTTP exporter. Works with
    BatchSpanProcessor for production use, or SimpleSpanProcessor for debugging.

    Parameters
    ----------
    api_key:
        RunLedger API key (``rl_live_...`` or ``rl_test_...``).
        Falls back to ``RUNLEDGER_API_KEY`` env var if not provided.
    base_url:
        RunLedger API base URL. Defaults to ``https://api.runledger.io``.
        Set to ``http://localhost:8000`` for local development.
    timeout:
        HTTP request timeout in seconds (default 10).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT,
    ) -> None:
        import os  # noqa: PLC0415

        self._api_key = api_key or os.environ.get("RUNLEDGER_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "api_key is required. Pass it explicitly or set RUNLEDGER_API_KEY."
            )
        self._endpoint = base_url.rstrip("/") + "/v1/traces"
        self._timeout = timeout
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

    def export(self, spans: Sequence[Any]) -> Any:
        """Export spans to RunLedger. Called by BatchSpanProcessor."""
        try:
            from opentelemetry.sdk.trace.export import SpanExportResult  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "opentelemetry-sdk is required to use RunLedgerOTLPExporter. "
                "Install with: pip install opentelemetry-sdk"
            ) from exc

        if not spans:
            return SpanExportResult.SUCCESS

        payload = spans_to_otlp_json(spans)
        try:
            resp = self._client.post(self._endpoint, content=json.dumps(payload))
            if resp.status_code < 300:
                return SpanExportResult.SUCCESS
            log.warning(
                "RunLedgerOTLPExporter: export failed status=%s body=%s",
                resp.status_code,
                resp.text[:256],
            )
            return SpanExportResult.FAILURE
        except Exception as exc:
            log.warning("RunLedgerOTLPExporter: export error error=%s", str(exc))
            return SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: int = 30_000) -> bool:  # noqa: ARG002
        return True

    def shutdown(self) -> None:
        self._client.close()
