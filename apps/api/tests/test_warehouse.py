"""
Tests for Phase 28 — Warehouse Export APIs.

Covers:
  - WarehouseDestinationCreate schema validation
  - Destination CRUD endpoints
  - Connection test endpoint
  - ExportJob trigger + list + get endpoints
  - export_workspace_data service (JSONL path)
  - run_single_export worker (success + failure)
  - Scheduled export worker
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures & helpers ─────────────────────────────────────────────────────────


def _make_ws(ws_id: uuid.UUID | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=ws_id or uuid.uuid4())


def _make_dest(
    workspace_id: uuid.UUID | None = None,
    name: str = "Test S3",
    provider: str = "s3",
    bucket: str = "my-bucket",
    prefix: str = "runledger",
    region: str | None = "us-east-1",
    endpoint_url: str | None = None,
    access_key_id: str = "AKIATEST",
    secret_access_key: str = "secret",
    format: str = "jsonl",
    resources: list[str] | None = None,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        name=name,
        provider=provider,
        bucket=bucket,
        prefix=prefix,
        region=region,
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        format=format,
        resources=resources or ["runs", "spans", "provider_calls"],
        is_active=is_active,
        created_at=datetime.now(UTC),
        last_export_at=None,
    )


def _make_job(
    workspace_id: uuid.UUID | None = None,
    destination_id: uuid.UUID | None = None,
    export_date: date | None = None,
    status: str = "pending",
    resources: list[str] | None = None,
    file_keys: dict | None = None,
    row_counts: dict | None = None,
    error: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        destination_id=destination_id or uuid.uuid4(),
        export_date=export_date or date(2026, 3, 22),
        status=status,
        resources=resources or ["runs", "spans", "provider_calls"],
        file_keys=file_keys,
        row_counts=row_counts,
        error=error,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(UTC),
    )


def _scalar_result(value: object) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalars.return_value.all.return_value = [value] if value is not None else []
    return r


def _list_result(items: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.scalar_one_or_none.return_value = items[0] if items else None
    return r


# ── Schema validation ─────────────────────────────────────────────────────────


def test_destination_create_valid() -> None:
    from runledger_api.schemas.warehouse import WarehouseDestinationCreate
    d = WarehouseDestinationCreate(
        name="prod-s3",
        provider="s3",
        bucket="runledger-exports",
        access_key_id="AKIATEST",
        secret_access_key="secret",
        resources=["runs", "provider_calls"],
    )
    assert d.format == "jsonl"
    assert d.resources == ["runs", "provider_calls"]


def test_destination_create_invalid_resource_fails() -> None:
    from pydantic import ValidationError
    from runledger_api.schemas.warehouse import WarehouseDestinationCreate
    with pytest.raises(ValidationError, match="Invalid resources"):
        WarehouseDestinationCreate(
            name="x",
            provider="s3",
            bucket="b",
            access_key_id="k",
            secret_access_key="s",
            resources=["runs", "unknown_table"],
        )


def test_destination_create_empty_resources_fails() -> None:
    from pydantic import ValidationError
    from runledger_api.schemas.warehouse import WarehouseDestinationCreate
    with pytest.raises(ValidationError, match="At least one resource"):
        WarehouseDestinationCreate(
            name="x",
            provider="s3",
            bucket="b",
            access_key_id="k",
            secret_access_key="s",
            resources=[],
        )


# ── POST /warehouse/destinations ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_destination() -> None:
    from runledger_api.routers.warehouse import create_destination
    from runledger_api.schemas.warehouse import (
        WarehouseDestinationCreate,
        WarehouseDestinationResponse,
    )

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", dest.id) or
            setattr(obj, "created_at", dest.created_at) or
            setattr(obj, "last_export_at", None)
        )
    )

    ws = _make_ws(ws_id)
    body = WarehouseDestinationCreate(
        name="Test S3",
        provider="s3",
        bucket="my-bucket",
        access_key_id="AKIATEST",
        secret_access_key="secret",
    )

    with patch("runledger_api.routers.warehouse.emit_audit_event", new_callable=AsyncMock):
        result = await create_destination(body=body, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, WarehouseDestinationResponse)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()


# ── GET /warehouse/destinations ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_destinations() -> None:
    from runledger_api.routers.warehouse import list_destinations
    from runledger_api.schemas.warehouse import WarehouseDestinationList

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_list_result([dest]))

    ws = _make_ws(ws_id)
    result = await list_destinations(auth=(ws, None), db=mock_db, include_inactive=False)  # type: ignore[arg-type]

    assert isinstance(result, WarehouseDestinationList)
    assert result.total == 1
    assert result.items[0].bucket == "my-bucket"


# ── GET /warehouse/destinations/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_destination_found() -> None:
    from runledger_api.routers.warehouse import get_destination
    from runledger_api.schemas.warehouse import WarehouseDestinationResponse

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))

    ws = _make_ws(ws_id)
    result = await get_destination(destination_id=dest.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, WarehouseDestinationResponse)
    assert result.provider == "s3"


@pytest.mark.asyncio
async def test_get_destination_not_found() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.warehouse import get_destination

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(None))

    ws = _make_ws()
    with pytest.raises(HTTPException) as exc_info:
        await get_destination(destination_id=uuid.uuid4(), auth=(ws, None), db=mock_db)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


# ── PUT /warehouse/destinations/{id} ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_destination() -> None:
    from runledger_api.routers.warehouse import update_destination
    from runledger_api.schemas.warehouse import (
        WarehouseDestinationResponse,
        WarehouseDestinationUpdate,
    )

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    ws = _make_ws(ws_id)
    body = WarehouseDestinationUpdate(is_active=False)

    with patch("runledger_api.routers.warehouse.emit_audit_event", new_callable=AsyncMock):
        result = await update_destination(
            destination_id=dest.id, body=body, auth=(ws, None), db=mock_db  # type: ignore[arg-type]
        )

    assert isinstance(result, WarehouseDestinationResponse)
    assert dest.is_active is False


# ── DELETE /warehouse/destinations/{id} ──────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_destination() -> None:
    from runledger_api.routers.warehouse import delete_destination

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    ws = _make_ws(ws_id)
    with patch("runledger_api.routers.warehouse.emit_audit_event", new_callable=AsyncMock):
        await delete_destination(destination_id=dest.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    mock_db.delete.assert_awaited_once_with(dest)


# ── POST /warehouse/destinations/{id}/test ───────────────────────────────────


@pytest.mark.asyncio
async def test_connection_test_success() -> None:
    from runledger_api.routers.warehouse import test_destination
    from runledger_api.schemas.warehouse import ConnectionTestResult

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))

    ws = _make_ws(ws_id)
    # Patch at the services module — the router lazily imports from there
    with patch(
        "runledger_api.services.warehouse.test_destination_connection", new_callable=AsyncMock
    ):
        result = await test_destination(destination_id=dest.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, ConnectionTestResult)
    assert result.ok is True


@pytest.mark.asyncio
async def test_connection_test_failure() -> None:
    from runledger_api.routers.warehouse import test_destination

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))

    ws = _make_ws(ws_id)
    with patch(
        "runledger_api.services.warehouse.test_destination_connection",
        new_callable=AsyncMock,
        side_effect=Exception("NoSuchBucket: bucket does not exist"),
    ):
        result = await test_destination(destination_id=dest.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert result.ok is False
    assert "NoSuchBucket" in (result.error or "")


# ── POST /warehouse/jobs ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_export_job() -> None:
    from runledger_api.routers.warehouse import trigger_export_job
    from runledger_api.schemas.warehouse import ExportJobResponse, ExportJobTrigger

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)
    job = _make_job(workspace_id=ws_id, destination_id=dest.id)

    mock_db = AsyncMock()
    # First execute: destination lookup; second: not needed (flush+commit)
    mock_db.execute = AsyncMock(return_value=_scalar_result(dest))
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", job.id) or
            setattr(obj, "created_at", job.created_at) or
            setattr(obj, "started_at", None) or
            setattr(obj, "completed_at", None) or
            setattr(obj, "file_keys", None) or
            setattr(obj, "row_counts", None) or
            setattr(obj, "error", None)
        )
    )

    ws = _make_ws(ws_id)
    body = ExportJobTrigger(destination_id=dest.id, export_date=date(2026, 3, 22))

    # Pre-import workers module so the Celery task attribute exists before patching
    import runledger_api.workers.warehouse as _wh
    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    with patch.object(_wh, "run_single_export", mock_task):
        result = await trigger_export_job(body=body, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, ExportJobResponse)
    mock_task.delay.assert_called_once()


# ── GET /warehouse/jobs ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_export_jobs() -> None:
    from runledger_api.routers.warehouse import list_export_jobs
    from runledger_api.schemas.warehouse import ExportJobList

    ws_id = uuid.uuid4()
    job = _make_job(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_list_result([job]))

    ws = _make_ws(ws_id)
    result = await list_export_jobs(
        auth=(ws, None), db=mock_db, destination_id=None, status_filter=None, limit=50  # type: ignore[arg-type]
    )

    assert isinstance(result, ExportJobList)
    assert result.total == 1


# ── GET /warehouse/jobs/{id} ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_export_job_found() -> None:
    from runledger_api.routers.warehouse import get_export_job
    from runledger_api.schemas.warehouse import ExportJobResponse

    ws_id = uuid.uuid4()
    job = _make_job(workspace_id=ws_id)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=_scalar_result(job))

    ws = _make_ws(ws_id)
    result = await get_export_job(job_id=job.id, auth=(ws, None), db=mock_db)  # type: ignore[arg-type]

    assert isinstance(result, ExportJobResponse)
    assert result.status == "pending"


# ── Service: _to_jsonl ────────────────────────────────────────────────────────


def test_to_jsonl_empty() -> None:
    from runledger_api.services.warehouse import _to_jsonl
    assert _to_jsonl([]) == b""


def test_to_jsonl_with_rows() -> None:
    import json

    from runledger_api.services.warehouse import _to_jsonl

    # Create a minimal mock ORM row
    row = SimpleNamespace()
    row_id = uuid.uuid4()

    with patch("runledger_api.services.warehouse._orm_to_dict", return_value={"id": row_id, "cost": 1.5}):
        data = _to_jsonl([row])

    assert data.endswith(b"\n")
    parsed = json.loads(data.decode("utf-8").strip())
    assert parsed["id"] == str(row_id)
    assert parsed["cost"] == 1.5


# ── Service: export_workspace_data ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_workspace_data_jsonl() -> None:
    from runledger_api.services.warehouse import export_workspace_data

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id, format="jsonl", resources=["runs"])

    mock_db = AsyncMock()
    s3_uri = "s3://my-bucket/runs/date=2026-03-22/data.jsonl"
    with (
        patch("runledger_api.services.warehouse._query_runs", new_callable=AsyncMock, return_value=[]),
        # Patch asyncio.to_thread at service module level; it must be awaitable
        patch(
            "runledger_api.services.warehouse.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=s3_uri,
        ),
    ):
        results = await export_workspace_data(mock_db, dest, date(2026, 3, 22), ["runs"])

    assert "runs" in results
    uri, count = results["runs"]
    assert uri == s3_uri
    assert count == 0


@pytest.mark.asyncio
async def test_export_workspace_data_skips_unknown_resource() -> None:
    from runledger_api.services.warehouse import export_workspace_data

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id, format="jsonl")

    mock_db = AsyncMock()
    with (
        patch("runledger_api.services.warehouse._query_runs", new_callable=AsyncMock, return_value=[]),
        patch("runledger_api.services.warehouse._upload_sync", return_value="s3://b/k"),
        patch("asyncio.to_thread", new=lambda fn, *args: fn(*args)),
    ):
        results = await export_workspace_data(mock_db, dest, date(2026, 3, 22), ["unknown"])

    assert results == {}


# ── Worker: run_single_export success ────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_single_export_success() -> None:
    from runledger_api.workers.warehouse import _execute_job

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)
    job = _make_job(workspace_id=ws_id, destination_id=dest.id)

    mock_session = AsyncMock()
    # First execute → job; second → dest
    mock_session.execute = AsyncMock(
        side_effect=[_scalar_result(job), _scalar_result(dest)]
    )
    mock_session.commit = AsyncMock()

    # Patch at the services module — workers imports lazily from there
    with patch(
        "runledger_api.services.warehouse.export_workspace_data",
        new_callable=AsyncMock,
        return_value={"runs": ("s3://bucket/runs/date=2026-03-22/data.jsonl", 42)},
    ):
        await _execute_job(mock_session, job.id)

    assert job.status == "completed"
    assert job.row_counts == {"runs": 42}
    assert job.file_keys is not None


@pytest.mark.asyncio
async def test_run_single_export_failure() -> None:
    from runledger_api.workers.warehouse import _execute_job

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)
    job = _make_job(workspace_id=ws_id, destination_id=dest.id)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        side_effect=[_scalar_result(job), _scalar_result(dest)]
    )
    mock_session.commit = AsyncMock()

    with patch(
        "runledger_api.services.warehouse.export_workspace_data",
        new_callable=AsyncMock,
        side_effect=Exception("AccessDenied: s3 upload failed"),
    ):
        await _execute_job(mock_session, job.id)

    assert job.status == "failed"
    assert "AccessDenied" in (job.error or "")


@pytest.mark.asyncio
async def test_run_single_export_missing_destination() -> None:
    from runledger_api.workers.warehouse import _execute_job

    job = _make_job()

    mock_session = AsyncMock()
    # First execute → job; second → no destination
    mock_session.execute = AsyncMock(
        side_effect=[_scalar_result(job), _scalar_result(None)]
    )
    mock_session.commit = AsyncMock()

    await _execute_job(mock_session, job.id)

    assert job.status == "failed"
    assert job.error == "Destination not found"


# ── Worker: scheduled exports ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schedule_all_dispatches_jobs() -> None:
    from runledger_api.workers.warehouse import _schedule_all

    ws_id = uuid.uuid4()
    dest = _make_dest(workspace_id=ws_id)

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=_list_result([dest]))
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_task = MagicMock()
    mock_task.delay = MagicMock()
    with patch("runledger_api.workers.warehouse.run_single_export", mock_task):
        await _schedule_all(mock_session)

    mock_task.delay.assert_called_once()
    mock_session.add.assert_called_once()
