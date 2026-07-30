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
from runledger_api.services.otlp_parse import (
    OtlpTrace,
    parse_otlp_json,
    synthesize_canonical_events,
)

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


async def _persist_batch(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    content_type: str,
    encoding: str | None,
    raw_body: bytes,
    trace_count: int,
    span_count: int,
    status_str: str = "accepted",
    error: str | None = None,
) -> OtlpIngestBatch:
    batch = OtlpIngestBatch(
        workspace_id=workspace_id,
        content_type=content_type,
        encoding=encoding,
        trace_count=trace_count,
        span_count=span_count,
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
      last_24h: {batches, traces, spans}
      last_7d:  {batches, traces, spans}
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
            ).where(
                OtlpIngestBatch.workspace_id == workspace.id,
                OtlpIngestBatch.received_at >= cutoff,
            )
        )
        r = row.one()
        result[label] = {"batches": r.batches, "traces": int(r.traces), "spans": int(r.spans)}

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

    Useful for debugging ingestion issues in the Settings → OTLP tab.
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
                "trace_count": b.trace_count,
                "span_count": b.span_count,
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
