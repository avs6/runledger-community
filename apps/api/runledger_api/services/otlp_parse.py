"""
OTLP/HTTP JSON parser and normalizer.

Converts an ExportTraceServiceRequest (JSON) into RunLedger canonical event dicts
that can be fed directly into the existing ingest pipeline.

Priority order for attribute extraction:
  1. OpenInference semantic conventions  (openinference.*)
  2. OpenTelemetry GenAI conventions     (gen_ai.*)
  3. Generic span name / kind heuristics

ID strategy:
  run_id  = uuid5(NAMESPACE_URL, "otlp-trace:<workspace_id>:<trace_id_hex>")
  span_id = uuid5(NAMESPACE_URL, "otlp-span:<workspace_id>:<trace_id_hex>:<span_id_hex>")
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

# ── OpenInference span kind values ─────────────────────────────────────────────
_OI_KIND_MAP: dict[str, str] = {
    "AGENT": "agent",
    "CHAIN": "chain",
    "LLM": "llm",
    "TOOL": "tool",
    "RETRIEVER": "retrieval",
    "PROMPT": "chain",
    "EVALUATOR": "chain",
    "GUARDRAIL": "chain",
    "EMBEDDING": "retrieval",
}

# ── OTel GenAI span name prefixes → span type ─────────────────────────────────
_GENAI_NAME_HINTS: list[tuple[str, str]] = [
    ("chat", "llm"),
    ("completion", "llm"),
    ("embed", "retrieval"),
    ("tool", "tool"),
    ("agent", "agent"),
    ("retriev", "retrieval"),
]


def _decode_id(raw: str | None) -> str:
    """
    OTLP JSON encodes bytes as base64.  Some SDKs emit hex strings instead.
    Normalise to lowercase hex regardless of input.
    """
    if not raw:
        return ""
    # If it looks like hex already (16 or 32 hex chars) use it directly
    clean = raw.strip()
    try:
        bytes.fromhex(clean)
        return clean.lower()
    except ValueError:
        pass
    # Otherwise assume base64
    try:
        return base64.b64decode(clean + "==").hex()
    except Exception:
        return clean.lower()


def _ns_to_dt(ns: str | int | None) -> datetime | None:
    """Convert nanosecond Unix timestamp to UTC datetime."""
    if ns is None:
        return None
    try:
        secs = int(ns) / 1e9
        return datetime.fromtimestamp(secs, tz=UTC)
    except (ValueError, OSError):
        return None


def _flatten_attrs(attr_list: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert OTLP attribute list:
      [{"key": "foo", "value": {"stringValue": "bar"}}, ...]
    → flat dict:
      {"foo": "bar", ...}
    """
    out: dict[str, Any] = {}
    for item in attr_list or []:
        key = item.get("key", "")
        val_wrap = item.get("value", {})
        # Pick the first non-None value from the oneOf fields
        for vfield in (
            "stringValue",
            "intValue",
            "doubleValue",
            "boolValue",
            "bytesValue",
            "arrayValue",
            "kvlistValue",
        ):
            if vfield in val_wrap:
                raw = val_wrap[vfield]
                if vfield == "arrayValue":
                    raw = [_flatten_one(v) for v in (raw.get("values") or [])]
                elif vfield == "kvlistValue":
                    raw = _flatten_attrs(raw.get("values") or [])
                elif vfield == "intValue":
                    raw = int(raw)
                elif vfield == "doubleValue":
                    raw = float(raw)
                elif vfield == "boolValue":
                    raw = bool(raw)
                out[key] = raw
                break
    return out


def _flatten_one(val_wrap: dict[str, Any]) -> Any:
    """Unwrap a single OTLP AnyValue."""
    for vfield in ("stringValue", "intValue", "doubleValue", "boolValue", "bytesValue"):
        if vfield in val_wrap:
            return val_wrap[vfield]
    return None


def _make_run_id(workspace_id: uuid.UUID, trace_id_hex: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"otlp-trace:{workspace_id}:{trace_id_hex}")


def _make_span_uuid(workspace_id: uuid.UUID, trace_id_hex: str, span_id_hex: str) -> uuid.UUID:
    return uuid.uuid5(
        uuid.NAMESPACE_URL, f"otlp-span:{workspace_id}:{trace_id_hex}:{span_id_hex}"
    )


def _classify_span(attrs: dict[str, Any], span_name: str) -> str:
    """Determine RunLedger span type from OpenInference / OTel GenAI attributes."""
    oi_kind = attrs.get("openinference.span.kind", "").upper()
    if oi_kind in _OI_KIND_MAP:
        return _OI_KIND_MAP[oi_kind]

    # OTel GenAI: if system attribute present it's an LLM span
    if attrs.get("gen_ai.system") or attrs.get("gen_ai.request.model"):
        return "llm"

    # Heuristic on span name
    lower = span_name.lower()
    for hint, kind in _GENAI_NAME_HINTS:
        if hint in lower:
            return kind

    return "chain"


def _extract_llm_fields(attrs: dict[str, Any]) -> dict[str, Any]:
    """Pull token counts, model, provider, and cost/request ID from OI or OTel GenAI attributes."""
    result: dict[str, Any] = {}

    # Model
    result["model"] = (
        attrs.get("llm.model_name")
        or attrs.get("gen_ai.request.model")
        or attrs.get("gen_ai.response.model")
        or "unknown"
    )

    # Provider
    result["provider"] = (
        attrs.get("llm.provider")
        or attrs.get("gen_ai.system")
        or _infer_provider(str(result["model"]))
    )

    # Hosting provider (if different — e.g. Azure-hosted OpenAI)
    api_type = attrs.get("gen_ai.openai.api_type") or attrs.get("llm.api_type")
    result["model_provider"] = (
        attrs.get("llm.hosting_provider")
        or (str(api_type) if api_type and str(api_type).lower() != result["provider"] else None)
    )

    # Tokens (OpenInference / OTel GenAI)
    result["input_tokens"] = _int_or_none(
        attrs.get("llm.token_count.prompt") or attrs.get("gen_ai.usage.input_tokens")
    )
    result["output_tokens"] = _int_or_none(
        attrs.get("llm.token_count.completion") or attrs.get("gen_ai.usage.output_tokens")
    )

    # Token detail breakdowns (reasoning, cached, audio tokens)
    result["input_tokens_details"] = _extract_token_details(
        attrs, prefix="llm.token_count.prompt_details", genai_prefix="gen_ai.usage.prompt"
    )
    result["output_tokens_details"] = _extract_token_details(
        attrs, prefix="llm.token_count.completion_details", genai_prefix="gen_ai.usage.completion"
    )

    # Reported cost (OpenInference llm.cost.* or llm.token_count.total_cost)
    result["reported_cost_usd"] = _float_or_none(
        attrs.get("llm.cost.total")
        or attrs.get("llm.token_count.total_cost")
    )

    # Provider request ID — critical for finance-grade reconciliation
    result["provider_request_id"] = (
        attrs.get("llm.openai.response.id")     # openinference-instrumentation-openai
        or attrs.get("gen_ai.openai.api.id")    # OTel GenAI / Azure
        or attrs.get("gen_ai.response.id")      # OTel GenAI generic
        or attrs.get("llm.request_id")          # generic OpenInference
        or attrs.get("anthropic.request_id")    # openinference-instrumentation-anthropic
        or attrs.get("x_request_id")            # header-forwarded IDs
    )

    return result


def _extract_token_details(
    attrs: dict[str, Any],
    prefix: str,
    genai_prefix: str,
) -> dict[str, int] | None:
    """
    Extract token count breakdown details from OpenInference or OTel GenAI span attrs.

    OpenInference: ``{prefix}.cached_tokens``, ``{prefix}.reasoning_tokens``, etc.
    OTel GenAI:    ``{genai_prefix}_tokens.cached``, etc.

    Returns a dict of non-None values, or None if nothing was found.
    """
    details: dict[str, int] = {}
    for subkey in ("cached_tokens", "reasoning_tokens", "audio_tokens", "text_tokens"):
        # OpenInference: llm.token_count.prompt_details.cached_tokens
        val = _int_or_none(attrs.get(f"{prefix}.{subkey}"))
        if val is None:
            # OTel GenAI: gen_ai.usage.prompt_tokens.cached
            short = subkey.replace("_tokens", "")
            val = _int_or_none(attrs.get(f"{genai_prefix}_tokens.{short}"))
        if val is not None:
            details[subkey] = val
    return details if details else None


def _infer_provider(model: str) -> str:
    lower = model.lower()
    if "gpt" in lower or "o1" in lower or "o3" in lower:
        return "openai"
    if "claude" in lower:
        return "anthropic"
    if "gemini" in lower:
        return "google"
    if "mistral" in lower or "mixtral" in lower:
        return "mistral"
    if "llama" in lower:
        return "meta"
    return "unknown"


def _int_or_none(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _float_or_none(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ── Run-context extraction ─────────────────────────────────────────────────────


def _extract_run_context(
    resource_attrs: dict[str, Any],
    root_span_attrs: dict[str, Any],
) -> dict[str, str]:
    """
    Extract RunLedger run-context fields from OpenInference / RunLedger helper attributes.

    Priority order (first non-None wins):
      runledger.*  >  openinference.*  >  otel.resource.*  >  generic

    Returns only the keys that have a value — the caller must NOT pass None
    to pipeline events as that overwrites existing run fields.
    """
    # Merge: root span attrs take priority over resource attrs for user-level fields
    all_attrs = {**resource_attrs, **root_span_attrs}

    out: dict[str, str] = {}

    val = (
        all_attrs.get("runledger.session_id")
        or all_attrs.get("session.id")
        or all_attrs.get("openinference.session_id")
    )
    if val:
        out["session_id"] = str(val)

    val = (
        all_attrs.get("runledger.end_user_id")
        or all_attrs.get("user.id")
        or all_attrs.get("openinference.user_id")
        or all_attrs.get("enduser.id")
    )
    if val:
        out["end_user_id"] = str(val)

    val = (
        all_attrs.get("runledger.feature_tag")
        or all_attrs.get("tag.feature")
        or all_attrs.get("feature_tag")
    )
    if val:
        out["feature_tag"] = str(val)

    val = (
        all_attrs.get("runledger.deployment_version")
        # service.version from resource is the natural deployment version signal
        or resource_attrs.get("service.version")
    )
    if val:
        out["deployment_version"] = str(val)

    return out


# ── Message payload extraction ─────────────────────────────────────────────────


def _extract_message_payloads(
    attrs: dict[str, Any],
    span_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Extract prompt/completion content from OpenInference LLM span attributes
    or OTel GenAI span events.

    Priority:
      1. OpenInference span attributes (llm.input_messages.*)
      2. OTel GenAI span events (gen_ai.*.message event names)
      3. Generic input.value / output.value fallback

    The returned dict uses the same keys the privacy pipeline expects:
      {"messages": [...], "response": {...}}

    Returns None when no content is found.
    """
    messages: list[dict[str, Any]] = []
    response: dict[str, Any] | None = None

    # ── 1. OpenInference: llm.input_messages.N.message.{role,content} ─────────
    idx = 0
    while True:
        role = attrs.get(f"llm.input_messages.{idx}.message.role")
        content = attrs.get(f"llm.input_messages.{idx}.message.content")
        if role is None and content is None:
            break
        if content is not None:
            messages.append({"role": str(role or "user"), "content": str(content)})
        idx += 1

    # OpenInference: llm.output_messages.0.message.content
    out_content = attrs.get("llm.output_messages.0.message.content")
    if out_content is not None:
        response = {"role": "assistant", "content": str(out_content)}

    # ── 2. OTel GenAI span events ──────────────────────────────────────────────
    # OTel GenAI emits message content as span events named gen_ai.{role}.message
    if not messages and response is None and span_events:
        for ev in span_events:
            ev_name = ev.get("name") or ""
            ev_attrs = ev.get("attrs") or {}
            content_val = ev_attrs.get("gen_ai.event.content") or ev_attrs.get("content")
            if content_val is None:
                continue
            # Map OTel GenAI event names to roles
            if ev_name in ("gen_ai.system.message", "gen_ai.user.message"):
                role = "system" if "system" in ev_name else "user"
                messages.append({"role": role, "content": str(content_val)})
            elif ev_name == "gen_ai.assistant.message":
                response = {"role": "assistant", "content": str(content_val)}
            elif ev_name == "gen_ai.tool.message":
                messages.append({"role": "tool", "content": str(content_val)})

    # ── 3. Generic fallbacks ───────────────────────────────────────────────────
    if not messages:
        raw_input = attrs.get("input.value")
        if raw_input is not None:
            messages.append({"role": "user", "content": str(raw_input)})

    if response is None:
        raw_output = attrs.get("output.value")
        if raw_output is not None:
            response = {"role": "assistant", "content": str(raw_output)}

    if not messages and response is None:
        return None

    result: dict[str, Any] = {}
    if messages:
        result["messages"] = messages
    if response is not None:
        result["response"] = response
    return result


def _extract_retrieval_metadata(attrs: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract retrieval result summary from OpenInference RETRIEVER span attributes.

    OpenInference: retrieval.documents.N.document.{id, content, score, metadata}
    Returns a dict with document_count and top scores, or None if absent.
    """
    docs: list[dict[str, Any]] = []
    idx = 0
    while True:
        doc_id = attrs.get(f"retrieval.documents.{idx}.document.id")
        score = attrs.get(f"retrieval.documents.{idx}.document.score")
        content = attrs.get(f"retrieval.documents.{idx}.document.content")
        if doc_id is None and score is None and content is None:
            break
        doc: dict[str, Any] = {}
        if doc_id is not None:
            doc["id"] = str(doc_id)
        if score is not None:
            try:
                doc["score"] = float(score)
            except (ValueError, TypeError):
                pass
        if content is not None:
            doc["content"] = str(content)
        docs.append(doc)
        idx += 1

    if not docs:
        return None
    return {
        "document_count": len(docs),
        "documents": docs,
    }


def _extract_convention_metadata(resource_attrs: dict[str, Any], scope_name: str | None, scope_version: str | None) -> dict[str, Any] | None:
    """
    Extract OTel SDK / convention version metadata for convention version tracking (Phase 2).

    Stored in run_start.metadata.instrumentation so analytics can filter by convention.
    """
    info: dict[str, Any] = {}
    sdk_name = resource_attrs.get("telemetry.sdk.name")
    sdk_version = resource_attrs.get("telemetry.sdk.version")
    sdk_language = resource_attrs.get("telemetry.sdk.language")
    if sdk_name:
        info["sdk_name"] = str(sdk_name)
    if sdk_version:
        info["sdk_version"] = str(sdk_version)
    if sdk_language:
        info["sdk_language"] = str(sdk_language)
    if scope_name:
        info["instrumentation_scope"] = str(scope_name)
    if scope_version:
        info["instrumentation_scope_version"] = str(scope_version)
    return info if info else None


# ── Public API ─────────────────────────────────────────────────────────────────


class OtlpParseResult:
    """Holds everything extracted from one ExportTraceServiceRequest."""

    def __init__(self) -> None:
        self.traces: list[OtlpTrace] = []
        self.total_spans: int = 0


class OtlpTrace:
    def __init__(
        self,
        trace_id_hex: str,
        resource_attrs: dict[str, Any],
        spans: list[OtlpParsedSpan],
    ) -> None:
        self.trace_id_hex = trace_id_hex
        self.resource_attrs = resource_attrs
        self.spans = spans


class OtlpParsedSpan:
    def __init__(
        self,
        trace_id_hex: str,
        span_id_hex: str,
        parent_span_id_hex: str | None,
        name: str,
        span_type: str,
        started_at: datetime | None,
        ended_at: datetime | None,
        status_code: str | None,
        attrs: dict[str, Any],
        scope_name: str | None,
        scope_version: str | None,
        otel_kind: int,
        span_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self.trace_id_hex = trace_id_hex
        self.span_id_hex = span_id_hex
        self.parent_span_id_hex = parent_span_id_hex
        self.name = name
        self.span_type = span_type
        self.started_at = started_at
        self.ended_at = ended_at
        self.status_code = status_code
        self.attrs = attrs
        self.scope_name = scope_name
        self.scope_version = scope_version
        self.otel_kind = otel_kind
        # OTel span events (gen_ai.*.message events for GenAI payload capture)
        self.span_events: list[dict[str, Any]] = span_events or []

    @property
    def is_root(self) -> bool:
        return not self.parent_span_id_hex

    @property
    def is_llm(self) -> bool:
        return self.span_type == "llm"

    @property
    def is_tool(self) -> bool:
        return self.span_type == "tool"


def parse_otlp_json(payload: dict[str, Any]) -> OtlpParseResult:
    """
    Parse an OTLP ExportTraceServiceRequest JSON dict into OtlpParseResult.

    Handles both standard OTLP JSON and common SDK variants.
    """
    result = OtlpParseResult()

    resource_spans = payload.get("resourceSpans") or payload.get("resource_spans") or []

    for rs in resource_spans:
        resource = rs.get("resource") or {}
        resource_attrs = _flatten_attrs(resource.get("attributes") or [])

        scope_spans_list = rs.get("scopeSpans") or rs.get("scope_spans") or []

        # Group spans by trace_id
        traces_map: dict[str, list[OtlpParsedSpan]] = {}

        for ss in scope_spans_list:
            scope = ss.get("scope") or {}
            scope_name: str | None = scope.get("name")
            scope_version: str | None = scope.get("version")
            spans = ss.get("spans") or []

            for raw_span in spans:
                trace_id_hex = _decode_id(raw_span.get("traceId") or raw_span.get("trace_id"))
                span_id_hex = _decode_id(raw_span.get("spanId") or raw_span.get("span_id"))
                parent_raw = raw_span.get("parentSpanId") or raw_span.get("parent_span_id")
                parent_span_id_hex = _decode_id(parent_raw) if parent_raw else None

                name = raw_span.get("name") or "unnamed"
                otel_kind = int(raw_span.get("kind") or 0)

                attrs = _flatten_attrs(raw_span.get("attributes") or [])
                span_type = _classify_span(attrs, name)

                status = raw_span.get("status") or {}
                status_code_int = status.get("code", 0)
                if status_code_int == 2:
                    status_code = "ERROR"
                elif status_code_int == 1:
                    status_code = "OK"
                else:
                    status_code = "UNSET"

                started_at = _ns_to_dt(
                    raw_span.get("startTimeUnixNano") or raw_span.get("start_time_unix_nano")
                )
                ended_at = _ns_to_dt(
                    raw_span.get("endTimeUnixNano") or raw_span.get("end_time_unix_nano")
                )

                # Parse OTel span events (used for OTel GenAI message content)
                raw_events = raw_span.get("events") or []
                span_events: list[dict[str, Any]] = [
                    {
                        "name": ev.get("name") or "",
                        "attrs": _flatten_attrs(ev.get("attributes") or []),
                    }
                    for ev in raw_events
                ]

                parsed = OtlpParsedSpan(
                    trace_id_hex=trace_id_hex,
                    span_id_hex=span_id_hex,
                    parent_span_id_hex=parent_span_id_hex or None,
                    name=name,
                    span_type=span_type,
                    started_at=started_at,
                    ended_at=ended_at,
                    status_code=status_code,
                    attrs=attrs,
                    scope_name=scope_name,
                    scope_version=scope_version,
                    otel_kind=otel_kind,
                    span_events=span_events,
                )
                traces_map.setdefault(trace_id_hex, []).append(parsed)
                result.total_spans += 1

        for trace_id_hex, spans in traces_map.items():
            result.traces.append(
                OtlpTrace(
                    trace_id_hex=trace_id_hex,
                    resource_attrs=resource_attrs,
                    spans=spans,
                )
            )

    return result


def synthesize_canonical_events(
    workspace_id: uuid.UUID,
    trace: OtlpTrace,
    service_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convert one OtlpTrace into a list of RunLedger canonical event dicts.

    Events produced:
      run_start, span_start*, provider_call*, tool_call*, span_end*, run_end
    """
    events: list[dict[str, Any]] = []
    run_id = _make_run_id(workspace_id, trace.trace_id_hex)

    # Find root span — prefer AGENT > CHAIN > any span without parent
    root = _find_root(trace.spans)
    if root is None:
        return []  # empty / corrupt trace

    resource = trace.resource_attrs
    svc_name = (
        service_name
        or resource.get("service.name")
        or resource.get("service_name")
        or "otlp-ingest"
    )
    run_started = root.started_at or datetime.now(UTC)
    run_ended = root.ended_at

    # ── run-context (session / user / feature / deployment) ───────────────────
    run_ctx = _extract_run_context(resource, root.attrs)

    # ── run_start ─────────────────────────────────────────────────────────────
    run_metadata: dict[str, Any] = {
        "service_name": svc_name,
        "resource_attributes": resource,
    }
    # Convention / SDK version tracking (Phase 2) — derive from root span's scope
    convention_meta = _extract_convention_metadata(resource, root.scope_name, root.scope_version)
    if convention_meta:
        run_metadata["instrumentation"] = convention_meta

    run_start_event: dict[str, Any] = {
        "event_type": "run_start",
        "run_id": str(run_id),
        "workspace_id": str(workspace_id),
        "started_at": run_started.isoformat(),
        # Top-level source fields — pipeline reads these into ORM columns
        "source_type": "otlp",
        "external_trace_id": trace.trace_id_hex,
        "metadata": run_metadata,
    }
    # Spread run-context fields as top-level keys (pipeline reads them directly)
    run_start_event.update(run_ctx)
    events.append(run_start_event)

    # ── per-span events ───────────────────────────────────────────────────────
    for span in trace.spans:
        span_uuid = _make_span_uuid(workspace_id, trace.trace_id_hex, span.span_id_hex)
        parent_uuid = (
            _make_span_uuid(workspace_id, trace.trace_id_hex, span.parent_span_id_hex)
            if span.parent_span_id_hex
            else None
        )
        span_started = span.started_at or run_started
        span_ended = span.ended_at

        # span_start
        events.append(
            {
                "event_type": "span_start",
                "run_id": str(run_id),
                "span_id": str(span_uuid),
                "parent_span_id": str(parent_uuid) if parent_uuid else None,
                "span_type": span.span_type,
                "name": span.name,
                "started_at": span_started.isoformat(),
                # Top-level source fields — pipeline persists to ORM columns
                "external_span_id": span.span_id_hex,
                "external_parent_span_id": span.parent_span_id_hex,
                "instrumentation_scope_name": span.scope_name,
                "instrumentation_scope_version": span.scope_version,
                "metadata": {
                    "source_attributes": span.attrs,
                },
            }
        )

        # provider_call for LLM spans
        if span.is_llm and span_ended:
            llm = _extract_llm_fields(span.attrs)
            latency_ms = None
            if span.started_at and span.ended_at:
                latency_ms = int(
                    (span.ended_at - span.started_at).total_seconds() * 1000
                )
            pstatus = "error" if span.status_code == "ERROR" else "success"
            pc_event: dict[str, Any] = {
                "event_type": "provider_call",
                "run_id": str(run_id),
                "span_id": str(span_uuid),
                "provider": llm["provider"],
                "model": llm["model"],
                "input_tokens": llm["input_tokens"],
                "output_tokens": llm["output_tokens"],
                "latency_ms": latency_ms,
                "status": pstatus,
                # Finance-grade fields — top-level so pipeline persists to ORM columns
                "cost_source": "reported" if llm["reported_cost_usd"] else "pricing_engine",
            }
            # Only set when values are present — avoids overwriting with None
            if llm["reported_cost_usd"] is not None:
                pc_event["reported_cost_usd"] = llm["reported_cost_usd"]
            if llm["provider_request_id"] is not None:
                pc_event["provider_request_id"] = llm["provider_request_id"]
            if llm["model_provider"] is not None:
                pc_event["model_provider"] = llm["model_provider"]
            if llm["input_tokens_details"] is not None:
                pc_event["input_tokens_details"] = llm["input_tokens_details"]
            if llm["output_tokens_details"] is not None:
                pc_event["output_tokens_details"] = llm["output_tokens_details"]
            events.append(pc_event)

        # tool_call for TOOL spans
        if span.is_tool and span_ended:
            latency_ms = None
            if span.started_at and span.ended_at:
                latency_ms = int(
                    (span.ended_at - span.started_at).total_seconds() * 1000
                )
            tool_name = (
                span.attrs.get("tool.name")
                or span.attrs.get("openinference.tool.name")
                or span.attrs.get("gen_ai.tool.name")
                or span.name
            )
            tool_args = (
                span.attrs.get("tool.parameters")
                or span.attrs.get("gen_ai.tool.call.function.arguments")
                or span.attrs.get("tool_call.function.arguments")
            )
            pstatus = "error" if span.status_code == "ERROR" else "success"
            tool_event: dict[str, Any] = {
                "event_type": "tool_call",
                "run_id": str(run_id),
                "span_id": str(span_uuid),
                "tool_name": tool_name,
                "tool_type": "read",
                "duration_ms": latency_ms,
                "status": pstatus,
            }
            tool_meta: dict[str, Any] = {"external_span_id": span.span_id_hex}
            if tool_args is not None:
                tool_meta["tool_arguments"] = tool_args
            tool_event["metadata"] = tool_meta
            events.append(tool_event)

        # span_end
        if span_ended:
            rl_status = "failed" if span.status_code == "ERROR" else "succeeded"
            span_end_event: dict[str, Any] = {
                "event_type": "span_end",
                "run_id": str(run_id),
                "span_id": str(span_uuid),
                "ended_at": span_ended.isoformat(),
                "status": rl_status,
            }
            # LLM spans: attach message payloads (OpenInference + OTel GenAI span events)
            # Privacy pipeline applies capture policy (METADATA_ONLY / ERRORS_ONLY / SAMPLED / FULL)
            if span.is_llm:
                payloads = _extract_message_payloads(span.attrs, span.span_events)
                if payloads:
                    span_end_event["metadata"] = payloads
            # Retrieval spans: extract document metadata (Phase 2)
            elif span.span_type == "retrieval":
                retrieval_meta = _extract_retrieval_metadata(span.attrs)
                if retrieval_meta:
                    span_end_event["metadata"] = retrieval_meta
            events.append(span_end_event)

    # ── run_end ───────────────────────────────────────────────────────────────
    if run_ended:
        rl_run_status = "failed" if root.status_code == "ERROR" else "succeeded"
        events.append(
            {
                "event_type": "run_end",
                "run_id": str(run_id),
                "ended_at": run_ended.isoformat(),
                "status": rl_run_status,
            }
        )

    return events


def _find_root(spans: list[OtlpParsedSpan]) -> OtlpParsedSpan | None:
    """
    Find the root span of a trace.
    Priority: AGENT root > CHAIN root > any root > first span.
    """
    roots = [s for s in spans if s.is_root]
    if not roots:
        # Fall back: span whose parent isn't in this batch
        all_ids = {s.span_id_hex for s in spans}
        roots = [s for s in spans if s.parent_span_id_hex not in all_ids]
    if not roots:
        return spans[0] if spans else None

    for preferred_type in ("agent", "chain"):
        for s in roots:
            if s.span_type == preferred_type:
                return s

    return roots[0]
