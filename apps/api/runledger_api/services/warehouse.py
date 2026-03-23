"""
Warehouse export service — Phase 28.

Handles:
  - Querying workspace data for a given date
  - Serializing to JSONL (default) or Parquet
  - Uploading to S3-compatible object storage via boto3
  - Connection testing
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3  # type: ignore[import-untyped]
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


# ── JSON serializer ──────────────────────────────────────────────────────────

class _Encoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _orm_to_dict(obj: Any) -> dict[str, Any]:
    """Convert an ORM row to a plain dict using mapper attribute names."""
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(type(obj)).mapper
    return {attr.key: getattr(obj, attr.key) for attr in mapper.column_attrs}


# ── Serializers ───────────────────────────────────────────────────────────────

def _to_jsonl(rows: list[Any]) -> bytes:
    if not rows:
        return b""
    lines = [json.dumps(_orm_to_dict(r), cls=_Encoder) for r in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _to_parquet(rows: list[Any]) -> bytes:
    try:
        import pyarrow as pa  # type: ignore[import-untyped]
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "pyarrow is required for Parquet exports. Install it with: pip install pyarrow"
        ) from e

    buf = io.BytesIO()
    if not rows:
        pq.write_table(pa.table({}), buf, compression="snappy")
        return buf.getvalue()

    normalized: list[dict[str, Any]] = []
    for row in rows:
        d = _orm_to_dict(row)
        normalized.append({
            k: (
                str(v) if isinstance(v, uuid.UUID)
                else float(v) if isinstance(v, Decimal)
                else v.isoformat() if isinstance(v, (datetime, date))
                else v
            )
            for k, v in d.items()
        })

    table = pa.Table.from_pylist(normalized)
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


# ── DB queries ────────────────────────────────────────────────────────────────

async def _query_runs(
    db: AsyncSession, workspace_id: uuid.UUID, start: datetime, end: datetime
) -> list[Any]:
    from runledger_api.models.events import AgentRun
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at >= start,
            AgentRun.started_at < end,
        )
    )
    return list(result.scalars().all())


async def _query_spans(
    db: AsyncSession, workspace_id: uuid.UUID, start: datetime, end: datetime
) -> list[Any]:
    from runledger_api.models.events import AgentRun, Span
    run_subq = (
        select(AgentRun.id).where(AgentRun.workspace_id == workspace_id).scalar_subquery()
    )
    result = await db.execute(
        select(Span).where(
            Span.run_id.in_(run_subq),
            Span.started_at >= start,
            Span.started_at < end,
        )
    )
    return list(result.scalars().all())


async def _query_provider_calls(
    db: AsyncSession, workspace_id: uuid.UUID, start: datetime, end: datetime
) -> list[Any]:
    from runledger_api.models.events import ProviderCall
    result = await db.execute(
        select(ProviderCall).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= start,
            ProviderCall.created_at < end,
        )
    )
    return list(result.scalars().all())


# ── S3 helpers ────────────────────────────────────────────────────────────────

def _make_s3_client(destination: Any) -> Any:
    kwargs: dict[str, Any] = {
        "aws_access_key_id": destination.access_key_id,
        "aws_secret_access_key": destination.secret_access_key,
    }
    if destination.region:
        kwargs["region_name"] = destination.region
    if destination.endpoint_url:
        kwargs["endpoint_url"] = destination.endpoint_url
    return boto3.client("s3", **kwargs)


def _upload_sync(destination: Any, s3_key: str, data: bytes, content_type: str) -> str:
    """Synchronous S3 upload. Returns the full S3 URI."""
    client = _make_s3_client(destination)
    client.put_object(
        Bucket=destination.bucket,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
    )
    return f"s3://{destination.bucket}/{s3_key}"


def _test_connection_sync(destination: Any) -> None:
    """Raises BotoCoreError / ClientError if credentials or bucket are invalid."""
    client = _make_s3_client(destination)
    client.head_bucket(Bucket=destination.bucket)


def _file_key(prefix: str, resource: str, export_date: date, fmt: str) -> str:
    """Build Hive-style S3 key: {prefix}/{resource}/date={YYYY-MM-DD}/data.{ext}"""
    ext = "parquet" if fmt == "parquet" else "jsonl"
    parts = [p for p in [prefix.strip("/"), resource, f"date={export_date.isoformat()}", f"data.{ext}"] if p]
    return "/".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

async def test_destination_connection(destination: Any) -> None:
    """
    Test that credentials and bucket are reachable.
    Raises BotoCoreError / ClientError on failure.
    """
    await asyncio.to_thread(_test_connection_sync, destination)


async def export_workspace_data(
    db: AsyncSession,
    destination: Any,
    export_date: date,
    resources: list[str],
) -> dict[str, tuple[str, int]]:
    """
    Export workspace data for export_date to S3.

    Returns dict of resource -> (s3_uri, row_count).
    Raises on S3 or query error.
    """
    start_dt = datetime(export_date.year, export_date.month, export_date.day, tzinfo=UTC)
    end_dt = start_dt + timedelta(days=1)
    fmt = destination.format
    content_type = (
        "application/octet-stream" if fmt == "parquet" else "application/x-ndjson"
    )

    results: dict[str, tuple[str, int]] = {}
    ws_id = destination.workspace_id

    for resource in resources:
        if resource == "runs":
            rows = await _query_runs(db, ws_id, start_dt, end_dt)
        elif resource == "spans":
            rows = await _query_spans(db, ws_id, start_dt, end_dt)
        elif resource == "provider_calls":
            rows = await _query_provider_calls(db, ws_id, start_dt, end_dt)
        else:
            log.warning("warehouse_unknown_resource", resource=resource)
            continue

        data = _to_parquet(rows) if fmt == "parquet" else _to_jsonl(rows)
        key = _file_key(destination.prefix or "", resource, export_date, fmt)

        uri = await asyncio.to_thread(_upload_sync, destination, key, data, content_type)
        results[resource] = (uri, len(rows))
        log.info(
            "warehouse_resource_exported",
            resource=resource,
            rows=len(rows),
            uri=uri,
            export_date=str(export_date),
        )

    return results
