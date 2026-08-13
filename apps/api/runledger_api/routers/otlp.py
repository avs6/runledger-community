"""
OTLP/HTTP trace receiver.

Routes:
  POST /v1/traces            — primary OTLP endpoint
  POST /otlp/v1/traces       — compatibility alias for collectors using /otlp prefix

Auth: Bearer <RunLedger API key>  (same key used for SDK ingest)
Content-Type: application/json    (OTLP JSON; protobuf support deferred to Phase 2)

On success returns:
  {"partialSuccess": {}}          — OTLP-spec compliant response
"""

from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_org_admin
from runledger_api.core.ratelimit import ingest_rate_limit
from runledger_api.models.otlp import OtlpIngestBatch, OtlpSpanRaw
from runledger_api.services.otlp_parse import OtlpTrace, parse_otlp_json, synthesize_canonical_events

log = structlog.get_logger()

router = APIRouter(tags=["OTLP"])
OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]

_MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB hard limit
_SUPPORTED_CONTENT_TYPES = {
    "application/json",
    "application/x-protobuf",  # accepted but we return 415 for protobuf for now
}


async def _read_body(request: Request) -> tuple[bytes, str, str | None]:
    """Read, optionally decompress, and return (body, content_type, encoding)."""
    content_type = (request.headers.get("content-type") or "application/json").split(";")[0].strip()
    encoding: str | None = request.headers.get("content-encoding")

    body = await request.body()
    if len(body) > _MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large"
        )

    if encoding == "gzip":
        try:
            body = gzip.decompress(body)
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"gzip decompression failed: {exc}"
            ) from exc

    return body, content_type, encoding


def _parse_body(body: bytes, content_type: str) -> dict[str, Any]:
    if content_type == "application/x-protobuf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="OTLP protobuf not yet supported. Use Content-Type: application/json",
        )
    try:
        return json.loads(body)  # type: ignore[no-any-return]
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc}") from exc


def _unwrap_any_value(value: dict[str, Any] | None) -> Any:
    if not isinstance(value, dict):
        return None
    for key in ("stringValue", "intValue", "doubleValue", "boolValue", "bytesValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value.get("arrayValue", {}).get("values", []) or []
        return [_unwrap_any_value(item) for item in values]
    if "kvlistValue" in value:
        values = value.get("kvlistValue", {}).get("values", []) or []
        return {item.get("key"): _unwrap_any_value(item.get("value")) for item in values if item.get("key")}
    return None


def _attrs_list_to_dict(attrs: list[dict[str, Any]] | None) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for item in attrs or []:
        key = item.get("key")
        if not key:
            continue
        flattened[key] = _unwrap_any_value(item.get("value"))
    return flattened


def _iter_resource_attribute_maps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    resource_maps: list[dict[str, Any]] = []
    for container_key in ("resourceSpans", "resourceMetrics", "resourceLogs"):
        for resource_item in payload.get(container_key, []) or []:
            attrs = resource_item.get("resource", {}).get("attributes", []) or []
            resource_maps.append(_attrs_list_to_dict(attrs))
    return resource_maps


async def _persist_batch(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    content_type: str,
    encoding: str | None,
    raw_body: bytes,
    signal_type: str,
    trace_count: int,
    span_count: int,
    metric_count: int = 0,
    log_record_count: int = 0,
    status_str: str = "accepted",
    error: str | None = None,
) -> OtlpIngestBatch:
    batch = OtlpIngestBatch(
        workspace_id=workspace_id,
        content_type=content_type,
        encoding=encoding,
        signal_type=signal_type,
        trace_count=trace_count,
        span_count=span_count,
        metric_count=metric_count,
        log_record_count=log_record_count,
        status=status_str,
        error=error,
        raw_payload=raw_body,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _persist_raw_spans(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    batch_id: uuid.UUID,
    trace: OtlpTrace,
) -> None:
    for span in trace.spans:
        raw = OtlpSpanRaw(
            workspace_id=workspace_id,
            batch_id=batch_id,
            external_trace_id=trace.trace_id_hex,
            external_span_id=span.span_id_hex,
            external_parent_span_id=span.parent_span_id_hex,
            span_name=span.name,
            start_time=span.started_at,
            end_time=span.ended_at,
            status_code=span.status_code,
            resource_attributes=trace.resource_attrs,
            scope_attributes={
                "name": span.scope_name,
                "version": span.scope_version,
            }
            if span.scope_name
            else None,
            span_attributes=span.attrs,
            normalized=False,
        )
        db.add(raw)


async def _handle_traces(
    request: Request,
    workspace: Any,
    db: AsyncSession,
) -> dict[str, Any]:
    """Core handler shared by both routes."""
    body, content_type, encoding = await _read_body(request)
    payload = _parse_body(body, content_type)

    try:
        parse_result = parse_otlp_json(payload)
    except Exception as exc:
        log.warning("otlp_parse_error", error=str(exc), workspace_id=str(workspace.id))
        raise HTTPException(status_code=422, detail=f"OTLP parse error: {exc}") from exc

    trace_count = len(parse_result.traces)
    span_count = parse_result.total_spans

    # Persist raw batch record
    batch = await _persist_batch(
        db=db,
        workspace_id=workspace.id,
        content_type=content_type,
        encoding=encoding,
        raw_body=body,
        signal_type="trace",
        trace_count=trace_count,
        span_count=span_count,
    )

    # Persist raw spans for replay/debugging, then synthesize canonical events
    all_events: list[dict[str, Any]] = []
    for trace in parse_result.traces:
        await _persist_raw_spans(db, workspace.id, batch.id, trace)
        events = synthesize_canonical_events(workspace.id, trace)
        all_events.extend(events)

    await db.commit()

    # Enqueue canonical events via Celery pipeline (lazy import to avoid circular)
    if all_events:
        try:
            from runledger_api.workers.pipeline import process_events_task  # noqa: PLC0415

            process_events_task.delay(str(workspace.id), all_events)
        except Exception as exc:
            # Non-fatal — batch is already persisted; events can be re-synthesized from raw
            log.warning("otlp_pipeline_enqueue_failed", error=str(exc))

    log.info(
        "otlp_traces_accepted",
        workspace_id=str(workspace.id),
        traces=trace_count,
        spans=span_count,
        events=len(all_events),
    )

    return {"partialSuccess": {}}


def _count_metrics(payload: dict[str, Any]) -> int:
    total = 0
    for resource_metric in payload.get("resourceMetrics", []) or []:
        for scope_metric in resource_metric.get("scopeMetrics", []) or []:
            total += len(scope_metric.get("metrics", []) or [])
    return total


def _count_log_records(payload: dict[str, Any]) -> int:
    total = 0
    for resource_log in payload.get("resourceLogs", []) or []:
        for scope_log in resource_log.get("scopeLogs", []) or []:
            total += len(scope_log.get("logRecords", []) or [])
    return total


async def _handle_metrics(
    request: Request,
    workspace: Any,
    db: AsyncSession,
) -> dict[str, Any]:
    body, content_type, encoding = await _read_body(request)
    payload = _parse_body(body, content_type)
    metric_count = _count_metrics(payload)

    await _persist_batch(
        db=db,
        workspace_id=workspace.id,
        content_type=content_type,
        encoding=encoding,
        raw_body=body,
        signal_type="metric",
        trace_count=0,
        span_count=0,
        metric_count=metric_count,
    )
    await db.commit()

    log.info(
        "otlp_metrics_accepted",
        workspace_id=str(workspace.id),
        metrics=metric_count,
    )
    return {"partialSuccess": {}}


async def _handle_logs(
    request: Request,
    workspace: Any,
    db: AsyncSession,
) -> dict[str, Any]:
    body, content_type, encoding = await _read_body(request)
    payload = _parse_body(body, content_type)
    log_record_count = _count_log_records(payload)

    await _persist_batch(
        db=db,
        workspace_id=workspace.id,
        content_type=content_type,
        encoding=encoding,
        raw_body=body,
        signal_type="log",
        trace_count=0,
        span_count=0,
        log_record_count=log_record_count,
    )
    await db.commit()

    log.info(
        "otlp_logs_accepted",
        workspace_id=str(workspace.id),
        log_records=log_record_count,
    )
    return {"partialSuccess": {}}


@router.post(
    "/v1/traces",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP trace receiver",
)
async def receive_traces(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Accept OTLP ExportTraceServiceRequest (JSON) from any OTel-compatible sender.

    Compatible with:
    - opentelemetry-sdk exporters (OTLP/HTTP JSON)
    - OpenInference instrumentation
    - OTel Collector with OTLP/HTTP exporter
    """
    return await _handle_traces(request, workspace, db)


@router.post(
    "/otlp/v1/traces",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP trace receiver (collector-prefix alias)",
    include_in_schema=False,
)
async def receive_traces_alias(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Alias for collectors that prefix /otlp before /v1/traces."""
    return await _handle_traces(request, workspace, db)


@router.post(
    "/v1/metrics",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP metrics receiver",
)
async def receive_metrics(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept OTLP ExportMetricsServiceRequest (JSON)."""
    return await _handle_metrics(request, workspace, db)


@router.post(
    "/otlp/v1/metrics",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP metrics receiver (collector-prefix alias)",
    include_in_schema=False,
)
async def receive_metrics_alias(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Alias for collectors that prefix /otlp before /v1/metrics."""
    return await _handle_metrics(request, workspace, db)


@router.post(
    "/v1/logs",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP logs receiver",
)
async def receive_logs(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept OTLP ExportLogsServiceRequest (JSON)."""
    return await _handle_logs(request, workspace, db)


@router.post(
    "/otlp/v1/logs",
    status_code=200,
    dependencies=[Depends(ingest_rate_limit)],
    summary="OTLP/HTTP logs receiver (collector-prefix alias)",
    include_in_schema=False,
)
async def receive_logs_alias(
    request: Request,
    workspace: Any = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Alias for collectors that prefix /otlp before /v1/logs."""
    return await _handle_logs(request, workspace, db)


@router.get(
    "/v1/traces/stats",
    summary="OTLP ingestion statistics",
)
async def get_traces_stats(
    auth: OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return aggregate ingest stats for the current workspace.

    Response fields:
      last_24h: {batches, traces, spans, metrics, logs}
      last_7d:  {batches, traces, spans, metrics, logs}
    """
    workspace = auth[0]
    now = datetime.now(UTC)
    cutoffs = {
        "last_24h": now - timedelta(hours=24),
        "last_7d": now - timedelta(days=7),
    }

    result: dict[str, Any] = {}
    for label, cutoff in cutoffs.items():
        row = await db.execute(
            select(
                func.count(OtlpIngestBatch.id).label("batches"),
                func.coalesce(func.sum(OtlpIngestBatch.trace_count), 0).label("traces"),
                func.coalesce(func.sum(OtlpIngestBatch.span_count), 0).label("spans"),
                func.coalesce(func.sum(OtlpIngestBatch.metric_count), 0).label("metrics"),
                func.coalesce(func.sum(OtlpIngestBatch.log_record_count), 0).label("logs"),
            ).where(
                OtlpIngestBatch.workspace_id == workspace.id,
                OtlpIngestBatch.received_at >= cutoff,
            )
        )
        r = row.one()
        result[label] = {
            "batches": r.batches,
            "traces": int(r.traces),
            "spans": int(r.spans),
            "metrics": int(r.metrics),
            "logs": int(r.logs),
        }

    return result


@router.get(
    "/v1/traces/batches",
    summary="List recent OTLP ingest batches",
)
async def list_traces_batches(
    auth: OrgAdminDep,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """
    Paginated list of recent ingest batches for this workspace.

    Useful for debugging ingestion issues in the Observe -> Monitoring -> Telemetry page.
    """
    workspace = auth[0]
    rows = await db.execute(
        select(OtlpIngestBatch)
        .where(OtlpIngestBatch.workspace_id == workspace.id)
        .order_by(OtlpIngestBatch.received_at.desc())
        .limit(limit)
        .offset(offset)
    )
    batches = rows.scalars().all()

    total_row = await db.execute(
        select(func.count(OtlpIngestBatch.id)).where(OtlpIngestBatch.workspace_id == workspace.id)
    )
    total = total_row.scalar() or 0

    return {
        "items": [
            {
                "id": str(b.id),
                "created_at": b.received_at.isoformat() if b.received_at else None,
                "signal_type": b.signal_type,
                "trace_count": b.trace_count,
                "span_count": b.span_count,
                "metric_count": b.metric_count,
                "log_record_count": b.log_record_count,
                "status": b.status,
                "error": b.error,
                "content_type": b.content_type,
            }
            for b in batches
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/v1/traces/batches/{batch_id}",
    summary="Inspect OTLP ingest batch detail",
)
async def get_trace_batch_detail(
    batch_id: uuid.UUID,
    auth: OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    workspace = auth[0]
    batch = await db.get(OtlpIngestBatch, batch_id)
    if batch is None or batch.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OTLP ingest batch not found")

    payload_preview: str | None = None
    resource_maps: list[dict[str, Any]] = []
    resource_map_count = 0
    if batch.raw_payload:
        try:
            payload = json.loads(batch.raw_payload)
            payload_preview = json.dumps(payload, indent=2)[:12000]
            parsed_resource_maps = _iter_resource_attribute_maps(payload)
            resource_map_count = len(parsed_resource_maps)
            resource_maps = [
                {
                    "service_name": attrs.get("service.name"),
                    "attribute_keys": sorted(str(key) for key in attrs.keys())[:20],
                    "attribute_count": len(attrs),
                }
                for attrs in parsed_resource_maps[:10]
            ]
        except Exception:
            payload_preview = batch.raw_payload[:4000].decode("utf-8", errors="replace")

    return {
        "id": str(batch.id),
        "created_at": batch.received_at.isoformat() if batch.received_at else None,
        "signal_type": batch.signal_type,
        "trace_count": batch.trace_count,
        "span_count": batch.span_count,
        "metric_count": batch.metric_count,
        "log_record_count": batch.log_record_count,
        "status": batch.status,
        "error": batch.error,
        "content_type": batch.content_type,
        "encoding": batch.encoding,
        "raw_payload_bytes": len(batch.raw_payload or b""),
        "resource_map_count": resource_map_count,
        "resource_maps": resource_maps,
        "raw_payload_preview": payload_preview,
    }


@router.get(
    "/v1/traces/insights",
    summary="OTLP ingestion insights and derived metrics",
)
async def get_traces_insights(
    auth: OrgAdminDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    workspace = auth[0]
    now = datetime.now(UTC)
    last_24h_cutoff = now - timedelta(hours=24)
    last_7d_cutoff = now - timedelta(days=7)

    rows = await db.execute(
        select(OtlpIngestBatch)
        .where(
            OtlpIngestBatch.workspace_id == workspace.id,
            OtlpIngestBatch.received_at >= last_7d_cutoff,
        )
        .order_by(OtlpIngestBatch.received_at.asc())
    )
    batches = rows.scalars().all()

    hourly_buckets: dict[str, dict[str, Any]] = {}
    for hour_offset in range(24):
        bucket_dt = (last_24h_cutoff + timedelta(hours=hour_offset)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        hourly_buckets[bucket_dt.isoformat()] = {
            "timestamp": bucket_dt.isoformat(),
            "batches": 0,
            "traces": 0,
            "spans": 0,
            "metrics": 0,
            "logs": 0,
        }

    signal_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"batches": 0, "traces": 0, "spans": 0, "metrics": 0, "logs": 0}
    )
    status_breakdown: Counter[str] = Counter()
    service_counter: Counter[str] = Counter()
    attribute_hits: Counter[str] = Counter()
    semantic_dimensions: Counter[str] = Counter()
    resource_maps_seen = 0

    for batch in batches:
        signal_totals[batch.signal_type]["batches"] += 1
        signal_totals[batch.signal_type]["traces"] += int(batch.trace_count or 0)
        signal_totals[batch.signal_type]["spans"] += int(batch.span_count or 0)
        signal_totals[batch.signal_type]["metrics"] += int(batch.metric_count or 0)
        signal_totals[batch.signal_type]["logs"] += int(batch.log_record_count or 0)
        status_breakdown[batch.status or "unknown"] += 1

        if batch.received_at and batch.received_at >= last_24h_cutoff:
            bucket_key = batch.received_at.replace(minute=0, second=0, microsecond=0).isoformat()
            bucket = hourly_buckets.get(bucket_key)
            if bucket is not None:
                bucket["batches"] += 1
                bucket["traces"] += int(batch.trace_count or 0)
                bucket["spans"] += int(batch.span_count or 0)
                bucket["metrics"] += int(batch.metric_count or 0)
                bucket["logs"] += int(batch.log_record_count or 0)

        if not batch.raw_payload:
            continue
        try:
            payload = json.loads(batch.raw_payload)
        except Exception:
            continue

        resource_maps = _iter_resource_attribute_maps(payload)
        for attrs in resource_maps:
            resource_maps_seen += 1
            if attrs.get("service.name"):
                service_counter[str(attrs["service.name"])] += 1
                attribute_hits["service_name"] += 1
            if attrs.get("runledger.session_id") or attrs.get("session.id"):
                attribute_hits["session_id"] += 1
            if attrs.get("runledger.end_user_id") or attrs.get("user.id"):
                attribute_hits["end_user_id"] += 1
            if attrs.get("runledger.feature_tag") or attrs.get("feature_tag"):
                attribute_hits["feature_tag"] += 1
            if attrs.get("runledger.deployment_version") or attrs.get("service.version"):
                attribute_hits["deployment_version"] += 1
            if attrs.get("runledger.workspace_name"):
                attribute_hits["workspace_name"] += 1
            if attrs.get("runledger.organization_name"):
                attribute_hits["organization_name"] += 1

            for semantic_key in (
                "service.name",
                "service.version",
                "deployment.environment",
                "runledger.feature_tag",
                "runledger.workspace_name",
                "runledger.organization_name",
            ):
                if attrs.get(semantic_key):
                    semantic_dimensions[semantic_key] += 1

    def _pct(hit_key: str) -> float:
        if resource_maps_seen <= 0:
            return 0.0
        return round((attribute_hits[hit_key] / resource_maps_seen) * 100, 1)

    return {
        "window": {
            "resource_maps_seen": resource_maps_seen,
            "workspace_attribution_mode": "workspace_api_key",
            "workspace_name_hint": workspace.name,
        },
        "timeseries_24h": list(hourly_buckets.values()),
        "signal_breakdown": [
            {"signal_type": signal_type, **totals}
            for signal_type, totals in sorted(signal_totals.items(), key=lambda item: item[0])
        ],
        "top_services": [
            {"service_name": name, "resource_count": count}
            for name, count in service_counter.most_common(8)
        ],
        "attribute_coverage": {
            "service_name_pct": _pct("service_name"),
            "session_id_pct": _pct("session_id"),
            "end_user_id_pct": _pct("end_user_id"),
            "feature_tag_pct": _pct("feature_tag"),
            "deployment_version_pct": _pct("deployment_version"),
            "workspace_name_pct": _pct("workspace_name"),
            "organization_name_pct": _pct("organization_name"),
        },
        "semantic_dimensions": [
            {"key": key, "resource_count": count}
            for key, count in semantic_dimensions.most_common()
        ],
        "status_breakdown": [
            {"status": status_key, "count": count}
            for status_key, count in status_breakdown.most_common()
        ],
    }
