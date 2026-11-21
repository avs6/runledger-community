"""
Turn Claude Code's OTLP log events into RunLedger canonical events.

Claude Code reports usage as OTLP log records (events), not traces. Each
``claude_code.api_request`` event describes one model request with its model,
token counts, reported cost and duration. Without this module those events are
only stored as raw OTLP batches and never show up as runs or spend.

Mapping:
  * one run per Claude Code prompt (``prompt.id``), so a user turn is one run;
  * one LLM span plus one ``provider_call`` per ``api_request`` event.

IDs are derived deterministically from the workspace, session, prompt and
request, so a collector retrying a batch cannot create duplicate rows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from runledger_api.services.otlp_parse import _flatten_attrs, _int_or_none, _ns_to_dt

API_REQUEST_EVENT = "api_request"
_EVENT_BODY_PREFIX = "claude_code."
_SPAN_NAME = "claude_code.api_request"

# Request attributes worth keeping on the run. Identity fields such as
# user.email or user.account_uuid are deliberately left out.
_RUN_METADATA_KEYS = ("terminal.type", "query_source", "effort", "speed", "anthropic.plan")


def _event_name(record: dict[str, Any], attrs: dict[str, Any]) -> str | None:
    name = attrs.get("event.name")
    if name:
        return str(name)
    body = (record.get("body") or {}).get("stringValue")
    if isinstance(body, str) and body.startswith(_EVENT_BODY_PREFIX):
        return body.removeprefix(_EVENT_BODY_PREFIX)
    return None


def _is_claude_code(resource: dict[str, Any], scope_name: str | None) -> bool:
    service = str(resource.get("service.name") or "")
    return service.startswith("claude-code") or (scope_name or "").startswith(
        "com.anthropic.claude_code"
    )


def _run_id(workspace_id: uuid.UUID, session_id: str, prompt_id: str) -> uuid.UUID:
    return uuid.uuid5(
        uuid.NAMESPACE_URL, f"claude-code-prompt:{workspace_id}:{session_id}:{prompt_id}"
    )


def _span_id(run_id: uuid.UUID, request_key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"claude-code-request:{run_id}:{request_key}")


def _api_request_events(
    workspace_id: uuid.UUID,
    resource: dict[str, Any],
    scope_name: str | None,
    scope_version: str | None,
    record: dict[str, Any],
    attrs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Canonical events for one ``api_request`` log record."""
    ended_at = _ns_to_dt(record.get("timeUnixNano") or record.get("observedTimeUnixNano"))
    if ended_at is None:
        ended_at = datetime.now(UTC)
    duration_ms = _int_or_none(attrs.get("duration_ms"))
    started_at = ended_at - timedelta(milliseconds=duration_ms or 0)

    session_id = str(attrs.get("session.id") or resource.get("session.id") or "")
    request_key = str(
        attrs.get("request_id")
        or attrs.get("client_request_id")
        or f"{session_id}:{attrs.get('event.sequence')}:{record.get('timeUnixNano')}"
    )
    # Group requests by prompt; fall back to one run per request.
    prompt_id = str(attrs.get("prompt.id") or request_key)
    run_id = _run_id(workspace_id, session_id, prompt_id)
    span_id = _span_id(run_id, request_key)

    input_tokens = _int_or_none(attrs.get("input_tokens")) or 0
    output_tokens = _int_or_none(attrs.get("output_tokens"))
    cache_read = _int_or_none(attrs.get("cache_read_tokens")) or 0
    cache_creation = _int_or_none(attrs.get("cache_creation_tokens")) or 0
    reported_cost = attrs.get("cost_usd")

    model = str(attrs.get("model") or "unknown")
    hosting = str(attrs.get("anthropic.provider") or "")

    run_metadata: dict[str, Any] = {
        "service_name": resource.get("service.name") or "claude-code",
        "source": "claude-code-logs",
        "prompt_id": prompt_id,
        "resource_attributes": resource,
    }
    run_metadata.update({k: attrs[k] for k in _RUN_METADATA_KEYS if attrs.get(k) is not None})
    if scope_name:
        run_metadata["instrumentation"] = {
            "instrumentation_scope_name": scope_name,
            "instrumentation_scope_version": scope_version,
        }

    run_start: dict[str, Any] = {
        "event_type": "run_start",
        "run_id": str(run_id),
        "workspace_id": str(workspace_id),
        "started_at": started_at.isoformat(),
        "source_type": "otlp",
        "external_trace_id": prompt_id,
        "metadata": run_metadata,
    }
    if session_id:
        run_start["session_id"] = session_id
    end_user = attrs.get("user.id") or resource.get("user.id")
    if end_user:
        run_start["end_user_id"] = str(end_user)
    version = resource.get("service.version")
    if version:
        run_start["deployment_version"] = str(version)

    provider_call: dict[str, Any] = {
        "event_type": "provider_call",
        "run_id": str(run_id),
        "span_id": str(span_id),
        "provider": "anthropic",
        "model": model,
        # Prompt tokens include cache reads and writes; cached tokens are a subset,
        # matching how RunLedger stores input/cached tokens for other providers.
        "input_tokens": input_tokens + cache_read + cache_creation,
        "output_tokens": output_tokens,
        "cached_input_tokens": cache_read,
        "input_tokens_details": {
            "cached_tokens": cache_read,
            "cache_creation_tokens": cache_creation,
        },
        "latency_ms": duration_ms,
        "status": "success",
        "cost_source": "reported" if reported_cost is not None else "pricing_engine",
    }
    if reported_cost is not None:
        provider_call["reported_cost_usd"] = float(reported_cost)
    if attrs.get("request_id"):
        provider_call["provider_request_id"] = str(attrs["request_id"])
    if hosting and hosting != "firstParty":
        provider_call["model_provider"] = hosting

    return [
        run_start,
        {
            "event_type": "span_start",
            "run_id": str(run_id),
            "span_id": str(span_id),
            "parent_span_id": None,
            "span_type": "llm",
            "name": _SPAN_NAME,
            "started_at": started_at.isoformat(),
            "external_span_id": request_key,
            "instrumentation_scope_name": scope_name,
            "instrumentation_scope_version": scope_version,
        },
        provider_call,
        {
            "event_type": "span_end",
            "run_id": str(run_id),
            "span_id": str(span_id),
            "ended_at": ended_at.isoformat(),
            "status": "succeeded",
        },
        {
            "event_type": "run_end",
            "run_id": str(run_id),
            "ended_at": ended_at.isoformat(),
            "status": "succeeded",
        },
    ]


def synthesize_claude_code_events(
    workspace_id: uuid.UUID, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Convert Claude Code ``api_request`` log records in an OTLP logs payload."""
    events: list[dict[str, Any]] = []
    for resource_logs in payload.get("resourceLogs") or []:
        resource = _flatten_attrs((resource_logs.get("resource") or {}).get("attributes") or [])
        for scope_logs in resource_logs.get("scopeLogs") or []:
            scope = scope_logs.get("scope") or {}
            scope_name = scope.get("name")
            if not _is_claude_code(resource, scope_name):
                continue
            for record in scope_logs.get("logRecords") or []:
                attrs = _flatten_attrs(record.get("attributes") or [])
                if _event_name(record, attrs) != API_REQUEST_EVENT:
                    continue
                events.extend(
                    _api_request_events(
                        workspace_id,
                        resource,
                        scope_name,
                        scope.get("version"),
                        record,
                        attrs,
                    )
                )
    return events
