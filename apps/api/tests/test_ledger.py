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
    """Generate seals yesterday (201); a sealed day is returned unchanged (200)."""
    key = _make_ledger_key(workspace_id=mock_workspace.id)
    snap = _make_snapshot(workspace_id=mock_workspace.id, key_id=key.id)
    snap.call_count = 10
    for attr, value in (("prev_hash", None), ("entry_count", 10), ("sealed_at", None)):
        setattr(snap, attr, value)
    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    with patch(
        "runledger_api.routers.ledger.seal_snapshot",
        AsyncMock(side_effect=[(snap, True), (snap, False)]),
    ):
        first = await authed_client.post("/ledger/snapshots/generate")
        again = await authed_client.post("/ledger/snapshots/generate")
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["call_count"] == 10
    assert first.json()["entry_count"] == 10


def test_canonical_hash_separates_late_enrichment_from_tampering() -> None:
    """cd:M-02: pricing a call after sealing is distinguishable from editing it."""
    from runledger_api.services.ledger import canonical_row_hash, entries_digest

    row = SimpleNamespace(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        api_key_id=None,
        end_user_id="alice",
        provider="openai",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=20,
        cached_input_tokens=None,
        status="success",
        created_at=datetime(2026, 2, 27, 12, tzinfo=UTC),
        cost_usd=None,
    )
    sealed = canonical_row_hash(row)
    row.cost_usd = Decimal("0.0042")  # late enrichment
    assert canonical_row_hash(row) != sealed
    assert canonical_row_hash(row, cost=None) == sealed
    row.end_user_id = "mallory"  # chargeback manipulation
    assert canonical_row_hash(row, cost=None) != sealed
    a, b = ("1", "x"), ("2", "y")
    assert entries_digest([a, b]) == entries_digest([b, a])


@pytest.mark.asyncio
async def test_verify_sealed_snapshot_reports_late_data_not_tampering() -> None:
    from runledger_api.services import ledger as ledger_svc

    ws = uuid.uuid4()
    day = date(2026, 2, 27)
    key = _make_ledger_key(workspace_id=ws)
    base = dict(
        run_id=uuid.uuid4(),
        api_key_id=None,
        end_user_id="alice",
        provider="openai",
        model="gpt-4o",
        input_tokens=10,
        output_tokens=5,
        cached_input_tokens=None,
        status="success",
        created_at=datetime(2026, 2, 27, 9, tzinfo=UTC),
    )
    priced_late = SimpleNamespace(id=uuid.uuid4(), cost_usd=None, **base)
    stable = SimpleNamespace(id=uuid.uuid4(), cost_usd=Decimal("0.01"), **base)
    entries = [
        SimpleNamespace(
            provider_call_id=r.id, row_hash=ledger_svc.canonical_row_hash(r), cost_usd=r.cost_usd
        )
        for r in (priced_late, stable)
    ]
    root = ledger_svc.entries_digest([(str(e.provider_call_id), e.row_hash) for e in entries])
    snap = _make_snapshot(workspace_id=ws, snapshot_date=day, key_id=key.id)
    snap.total_cost_usd = Decimal("0.01")
    snap.call_count = 2
    snap.model_breakdown = {"gpt-4o": "0.01"}
    snap.prev_hash = None
    snap.entries_root = root
    snap.hash = ledger_svc.compute_snapshot_hash(
        ledger_svc._signed_payload(ledger_svc._snapshot_data(snap), root, 2, None),
        key.key_value,
    )
    live_late = SimpleNamespace(**{**vars(priced_late), "cost_usd": Decimal("0.02")})
    newcomer = SimpleNamespace(**{**vars(stable), "id": uuid.uuid4()})

    def _scalars(items: list) -> MagicMock:
        result = MagicMock()
        result.scalars.return_value = items
        return result

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(snap),
            _scalar_result(key),
            _scalars(entries),
            _scalar_result(None),  # previous snapshot hash
        ]
    )
    with patch.object(
        ledger_svc, "_day_calls", AsyncMock(return_value=[live_late, stable, newcomer])
    ):
        result = await ledger_svc.verify_snapshot(db, ws, day)
    assert result.status == "late_data", result
    assert result.late_enriched_rows == 1 and result.late_arrival_rows == 1
    assert result.modified_rows == 0 and result.match is True

    tampered = SimpleNamespace(**{**vars(stable), "end_user_id": "mallory"})
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(snap),
            _scalar_result(key),
            _scalars(entries),
            _scalar_result(None),
        ]
    )
    with patch.object(ledger_svc, "_day_calls", AsyncMock(return_value=[live_late, tampered])):
        result = await ledger_svc.verify_snapshot(db, ws, day)
    assert result.status == "tampered" and result.modified_rows == 1


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
    # A legacy (unsealed) snapshot can't tell tampering from late data (cd:M-02).
    assert data["status"] == "unsealed_drift"
    assert data["match"] is False


@pytest.mark.asyncio
async def test_get_closure_summary(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "readiness_status": "partial",
        "evidence_score": 3,
        "missing_evidence": ["chargeback_allocation", "backup_snapshot"],
        "latest_snapshot": None,
        "verification": {
            "total_snapshots": 2,
            "ok_count": 1,
            "tampered_count": 0,
            "pending_count": 1,
            "latest_status": "ok",
        },
        "latest_closed_period": None,
        "chargeback": None,
        "latest_backup_snapshot": None,
        "recent_audit_event_count": 12,
    }

    with patch(
        "runledger_api.routers.ledger.get_ledger_closure_summary",
        new=AsyncMock(return_value=summary),
    ):
        resp = await authed_client.get("/ledger/closure-summary")

    assert resp.status_code == 200
    data = resp.json()
    assert data["readiness_status"] == "partial"
    assert data["evidence_score"] == 3
    assert data["verification"]["ok_count"] == 1
    assert data["recent_audit_event_count"] == 12


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


# ── Off-box anchor (cd:M-02) ──────────────────────────────────────────────────


def _sealed_snap(**kw: object) -> SimpleNamespace:
    base = dict(
        workspace_id=uuid.uuid4(),
        snapshot_date=date(2026, 2, 27),
        hash="h1",
        prev_hash=None,
        entries_root="r1",
        entry_count=3,
        key_id=uuid.uuid4(),
        sealed_at=datetime(2026, 2, 28, 1, tzinfo=UTC),
        anchor_uri=None,
        anchored_at=None,
        anchor_locked=None,
    )
    return SimpleNamespace(**{**base, **kw})


@pytest.mark.asyncio
async def test_anchor_writes_object_and_records_lock() -> None:
    from runledger_api.services import ledger_anchor

    snap = _sealed_snap()
    target = SimpleNamespace(bucket="evidence", prefix="rl", workspace_id=snap.workspace_id)
    db = AsyncMock()
    with (
        patch.object(ledger_anchor, "_target", AsyncMock(return_value=target)),
        patch.object(ledger_anchor, "_put", MagicMock(return_value=(True, "v1"))) as put,
    ):
        assert await ledger_anchor.anchor_snapshot(db, snap) == "anchored"  # type: ignore[arg-type]
        assert await ledger_anchor.anchor_snapshot(db, snap) == "already_anchored"  # type: ignore[arg-type]
    key = put.call_args.args[1]
    assert key == f"rl/ledger-anchors/{snap.workspace_id}/2026-02-27.json"
    assert snap.anchor_uri == f"s3://evidence/{key}?versionId=v1" and snap.anchor_locked is True


@pytest.mark.asyncio
async def test_anchor_without_target_or_seal() -> None:
    from runledger_api.services import ledger_anchor

    with patch.object(ledger_anchor, "_target", AsyncMock(return_value=None)):
        assert await ledger_anchor.anchor_snapshot(AsyncMock(), _sealed_snap()) == "no_target"  # type: ignore[arg-type]
    assert (
        await ledger_anchor.anchor_snapshot(AsyncMock(), _sealed_snap(entries_root=None))  # type: ignore[arg-type]
        == "unsealed"
    )


@pytest.mark.asyncio
async def test_check_anchor_detects_resigned_snapshot() -> None:
    """A DB admin re-signing a snapshot can't change what was written off-box."""
    from runledger_api.services import ledger_anchor

    snap = _sealed_snap(anchor_uri="s3://evidence/rl/ledger-anchors/x/2026-02-27.json?versionId=v9")
    anchored = ledger_anchor.anchor_payload(snap)  # type: ignore[arg-type]
    target = SimpleNamespace(bucket="evidence", prefix="rl")
    with (
        patch.object(ledger_anchor, "_target", AsyncMock(return_value=target)),
        patch.object(ledger_anchor, "_get", MagicMock(return_value=anchored)) as get,
    ):
        assert await ledger_anchor.check_anchor(AsyncMock(), snap) == (True, None)  # type: ignore[arg-type]
        snap.hash = "re-signed"
        ok, detail = await ledger_anchor.check_anchor(AsyncMock(), snap)  # type: ignore[arg-type]
    assert ok is False and "hash" in (detail or "")
    assert get.call_args.args[1:] == ("rl/ledger-anchors/x/2026-02-27.json", "v9")
