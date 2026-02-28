"""
Tests for Phase 11 ledger endpoints.

Covers:
  GET  /ledger/snapshots              — list snapshots
  POST /ledger/snapshots/generate     — generate snapshot
  GET  /ledger/verify/{date}          — verify integrity
  Auth enforcement

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_ledger_key(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        key_value="a" * 64,
        active=True,
        expires_at=datetime(2099, 1, 1, tzinfo=UTC),
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_snapshot(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        snapshot_date=date(2026, 2, 27),
        total_cost_usd=Decimal("1.23456789"),
        model_breakdown={"gpt-4o": "1.00", "gpt-3.5-turbo": "0.23"},
        call_count=42,
        hash="abc123" * 10,
        key_id=uuid.uuid4(),
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _scalar_result(value: object) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    m.scalar_one = MagicMock(return_value=value)
    return m


def _scalars_list_result(rows: list[object]) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


def _row_result(rows: list[object]) -> MagicMock:
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _one_result(row: object) -> MagicMock:
    m = MagicMock()
    m.one = MagicMock(return_value=row)
    return m


# ── test_list_snapshots_empty ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_snapshots_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([]))
    resp = await authed_client.get("/ledger/snapshots")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


# ── test_generate_snapshot ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_snapshot(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    key = _make_ledger_key(workspace_id=mock_workspace.id)
    snap = _make_snapshot(workspace_id=mock_workspace.id, key_id=key.id)

    totals_row = SimpleNamespace(total_cost=Decimal("1.50"), call_count=10)
    model_rows: list = []

    def _execute_side_effect(*args, **kwargs):
        call_count = mock_db_session.execute.call_count
        if call_count == 1:
            # build_daily_snapshot: totals
            return _one_result(totals_row)
        elif call_count == 2:
            # build_daily_snapshot: model breakdown
            return _row_result(model_rows)
        elif call_count == 3:
            # get_or_create_active_key
            return _scalar_result(key)
        elif call_count == 4:
            # check existing snapshot
            return _scalar_result(None)
        else:
            return _scalar_result(snap)

    mock_db_session.execute = AsyncMock(side_effect=_execute_side_effect)
    mock_db_session.flush = AsyncMock()
    mock_db_session.commit = AsyncMock()

    async def _mock_refresh(obj):
        obj.id = snap.id
        obj.created_at = snap.created_at
        obj.workspace_id = mock_workspace.id
        obj.snapshot_date = snap.snapshot_date
        obj.total_cost_usd = Decimal("1.50")
        obj.model_breakdown = {}
        obj.call_count = 10
        obj.hash = "deadbeef" * 8
        obj.key_id = key.id

    mock_db_session.refresh = _mock_refresh

    resp = await authed_client.post("/ledger/snapshots/generate")
    assert resp.status_code == 201
    data = resp.json()
    assert "hash" in data
    assert data["call_count"] == 10


# ── test_verify_snapshot_ok ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_snapshot_ok(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    from runledger_api.services.billing import sign_snapshot

    key = _make_ledger_key(workspace_id=mock_workspace.id)
    snap_date = date(2026, 2, 27)

    # Build the snapshot data the same way the service does
    snapshot_data = {
        "workspace_id": str(mock_workspace.id),
        "snapshot_date": str(snap_date),
        "total_cost_usd": "1.50000000",
        "call_count": 10,
        "model_breakdown": {},
    }
    correct_hash = sign_snapshot(snapshot_data, key.key_value)

    snap = _make_snapshot(
        workspace_id=mock_workspace.id,
        snapshot_date=snap_date,
        key_id=key.id,
        hash=correct_hash,
    )

    totals_row = SimpleNamespace(total_cost=Decimal("1.50000000"), call_count=10)

    call_n = 0

    async def _execute_side_effect(*args, **kwargs):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            return _scalar_result(snap)
        elif call_n == 2:
            return _scalar_result(key)
        elif call_n == 3:
            return _one_result(totals_row)
        else:
            return _row_result([])

    mock_db_session.execute = AsyncMock(side_effect=_execute_side_effect)

    resp = await authed_client.get(f"/ledger/verify/{snap_date}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["match"] is True


# ── test_verify_snapshot_not_found ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_snapshot_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(None))
    resp = await authed_client.get("/ledger/verify/2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_found"
    assert data["match"] is False


# ── test_verify_snapshot_tampered ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_snapshot_tampered(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    key = _make_ledger_key(workspace_id=mock_workspace.id)
    snap_date = date(2026, 2, 27)
    snap = _make_snapshot(
        workspace_id=mock_workspace.id,
        snapshot_date=snap_date,
        key_id=key.id,
        hash="tampered_hash_value",
    )

    totals_row = SimpleNamespace(total_cost=Decimal("1.50"), call_count=10)
    call_n = 0

    async def _execute_side_effect(*args, **kwargs):
        nonlocal call_n
        call_n += 1
        if call_n == 1:
            return _scalar_result(snap)
        elif call_n == 2:
            return _scalar_result(key)
        elif call_n == 3:
            return _one_result(totals_row)
        else:
            return _row_result([])

    mock_db_session.execute = AsyncMock(side_effect=_execute_side_effect)

    resp = await authed_client.get(f"/ledger/verify/{snap_date}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "tampered"
    assert data["match"] is False


# ── test_ledger_requires_auth ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ledger_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/ledger/snapshots")
    assert resp.status_code == 401


# ── test_tool_registry_crud ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tool_registry_crud(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    tool = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        tool_name="search",
        policy="audit",
        description=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    def _scalar_result_tool(val):
        m = MagicMock()
        m.scalar_one_or_none = MagicMock(return_value=val)
        return m

    mock_db_session.execute = AsyncMock(return_value=_scalar_result_tool(None))
    mock_db_session.flush = AsyncMock()
    mock_db_session.commit = AsyncMock()

    async def _mock_refresh(obj):
        obj.id = tool.id
        obj.workspace_id = mock_workspace.id
        obj.tool_name = "search"
        obj.policy = "audit"
        obj.description = None
        obj.created_at = tool.created_at
        obj.updated_at = tool.updated_at

    mock_db_session.refresh = _mock_refresh

    resp = await authed_client.post(
        "/tools/registry",
        json={"tool_name": "search", "policy": "audit"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool_name"] == "search"
    assert data["policy"] == "audit"


# ── test_security_events_list ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_security_events_list(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([]))
    resp = await authed_client.get("/tools/security-events")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}
