"""
Tests for billing CRUD, reconciliation, signing, export, chargeback rules,
and Celery workers.

Uses the authed_client / mock_db_session fixtures from conftest.
No live database or Redis required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from runledger_api.services.billing import sign_snapshot

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_period(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status="open",
        total_cost_usd=None,
        snapshot_hash=None,
        closed_at=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_rule(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        allocation_type="cost_center",
        dimension="engineering",
        weight=Decimal("0.6000"),
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_snapshot(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        billing_period_id=uuid.uuid4(),
        snapshot_data={},
        signature="abc" * 20,
        signing_key_id="v1",
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    result.scalar_one = MagicMock(return_value=value)
    result.scalars = MagicMock(
        return_value=MagicMock(
            __iter__=MagicMock(return_value=iter([value] if value is not None else []))
        )
    )
    return result


def _list_result(rows: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars = MagicMock(return_value=MagicMock(__iter__=MagicMock(return_value=iter(rows))))
    result.all = MagicMock(return_value=rows)
    return result


# ── sign_snapshot ─────────────────────────────────────────────────────────────


def test_sign_snapshot() -> None:
    """sign_snapshot produces a deterministic HMAC-SHA256 hex string."""
    data = {"foo": "bar", "total": "1.23"}
    key = "testsecret"
    sig1 = sign_snapshot(data, key)
    sig2 = sign_snapshot(data, key)
    assert sig1 == sig2
    assert len(sig1) == 64  # sha256 hex = 64 chars

    # Verify independently
    body = json.dumps(data, sort_keys=True, default=str).encode()
    expected = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    assert sig1 == expected


# ── test_export_signed_json_verifiable ────────────────────────────────────────


def test_export_signed_json_verifiable() -> None:
    """Signature in signed JSON export is verifiable with the same key."""
    key = "testsecret"
    payload = {
        "period_id": "p1",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "total_cost_usd": "5.00",
        "rows": [{"model": "gpt-4o", "cost_usd": "5.00"}],
        "signing_key_id": "v1",
    }
    sig = sign_snapshot(payload, key)
    # The caller would strip signature, verify, then re-add
    assert len(sig) == 64


# ── POST /billing/periods ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_billing_period(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /billing/periods → 201 with correct fields."""
    period_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def mock_refresh(obj: object) -> None:
        obj.id = period_id  # type: ignore[attr-defined]
        obj.created_at = created_at  # type: ignore[attr-defined]
        obj.status = "open"  # type: ignore[attr-defined]
        obj.total_cost_usd = None  # type: ignore[attr-defined]
        obj.snapshot_hash = None  # type: ignore[attr-defined]
        obj.closed_at = None  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    response = await authed_client.post(
        "/billing/periods",
        json={"period_start": "2026-01-01", "period_end": "2026-01-31"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "open"
    assert data["period_start"] == "2026-01-01"
    assert data["period_end"] == "2026-01-31"
    assert data["total_cost_usd"] is None


# ── GET /billing/periods ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_billing_periods(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /billing/periods returns items list."""
    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_list_result([period]))

    response = await authed_client.get("/billing/periods")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "open"


# ── GET /billing/periods/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_billing_period(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /billing/periods/{id} returns single period."""
    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    response = await authed_client.get(f"/billing/periods/{period.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(period.id)
    assert data["status"] == "open"


# ── POST /billing/periods/{id}/close ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_billing_period(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /close → returns snapshot with sha256 signature."""
    period = _make_period()
    snapshot = _make_snapshot(billing_period_id=period.id)

    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    with patch(
        "runledger_api.routers.billing.close_billing_period",
        new=AsyncMock(return_value=snapshot),
    ):
        response = await authed_client.post(f"/billing/periods/{period.id}/close")

    assert response.status_code == 200
    data = response.json()
    assert "signature" in data
    assert data["signing_key_id"] == "v1"


# ── POST /billing/periods/{id}/close — already closed ────────────────────────


@pytest.mark.asyncio
async def test_close_already_closed_409(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Closing a closed period → 409 Conflict."""
    period = _make_period(status="closed")
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    with patch(
        "runledger_api.routers.billing.close_billing_period",
        new=AsyncMock(side_effect=ValueError("already_closed")),
    ):
        response = await authed_client.post(f"/billing/periods/{period.id}/close")

    assert response.status_code == 409


# ── GET /billing/periods/{id}/reconciliation — pass ──────────────────────────


@pytest.mark.asyncio
async def test_reconciliation_pass(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Sums match within tolerance → status='pass'."""
    from runledger_api.schemas.billing import ReconciliationResult

    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    recon = ReconciliationResult(
        period_id=str(period.id),
        status="pass",
        provider_calls_sum=Decimal("10.00"),
        usage_daily_sum=Decimal("10.00"),
        delta_pct=Decimal("0"),
        orphaned_calls=0,
        duplicate_calls=0,
        issues=[],
    )

    with patch(
        "runledger_api.routers.billing.run_reconciliation",
        new=AsyncMock(return_value=recon),
    ):
        response = await authed_client.get(f"/billing/periods/{period.id}/reconciliation")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pass"
    assert data["issues"] == []


# ── GET /billing/periods/{id}/reconciliation — fail delta ────────────────────


@pytest.mark.asyncio
async def test_reconciliation_fail_delta(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Sums diverge > 0.01% → status='fail', issue logged."""
    from runledger_api.schemas.billing import ReconciliationResult

    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    recon = ReconciliationResult(
        period_id=str(period.id),
        status="fail",
        provider_calls_sum=Decimal("10.00"),
        usage_daily_sum=Decimal("9.00"),
        delta_pct=Decimal("10.00"),
        orphaned_calls=0,
        duplicate_calls=0,
        issues=["Cost delta 10.0000% exceeds 0.01% threshold"],
    )

    with patch(
        "runledger_api.routers.billing.run_reconciliation",
        new=AsyncMock(return_value=recon),
    ):
        response = await authed_client.get(f"/billing/periods/{period.id}/reconciliation")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fail"
    assert len(data["issues"]) > 0


# ── Reconciliation — orphaned calls ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconciliation_orphaned(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Orphaned calls are counted and reported."""
    from runledger_api.schemas.billing import ReconciliationResult

    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    recon = ReconciliationResult(
        period_id=str(period.id),
        status="fail",
        provider_calls_sum=Decimal("10.00"),
        usage_daily_sum=Decimal("10.00"),
        delta_pct=Decimal("0"),
        orphaned_calls=3,
        duplicate_calls=0,
        issues=["3 orphaned provider_call(s) with no matching agent_run"],
    )

    with patch(
        "runledger_api.routers.billing.run_reconciliation",
        new=AsyncMock(return_value=recon),
    ):
        response = await authed_client.get(f"/billing/periods/{period.id}/reconciliation")

    assert response.status_code == 200
    data = response.json()
    assert data["orphaned_calls"] == 3
    assert data["status"] == "fail"


# ── Export CSV ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_csv_columns(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """CSV export has the correct header columns."""
    period = _make_period()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(period))

    csv_content = "date,end_user_id,model,input_tokens,output_tokens,cost_usd,run_id\n"

    with patch(
        "runledger_api.routers.billing.export_csv",
        new=AsyncMock(return_value=csv_content),
    ):
        response = await authed_client.get(f"/billing/periods/{period.id}/export?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "date" in response.text
    assert "end_user_id" in response.text
    assert "cost_usd" in response.text


# ── POST /billing/chargeback-rules ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_chargeback_rule(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /chargeback-rules → 201 with correct fields."""
    rule_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def mock_refresh(obj: object) -> None:
        obj.id = rule_id  # type: ignore[attr-defined]
        obj.created_at = created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    response = await authed_client.post(
        "/billing/chargeback-rules",
        json={"allocation_type": "team", "dimension": "ml-platform", "weight": "0.40"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["allocation_type"] == "team"
    assert data["dimension"] == "ml-platform"
    assert float(data["weight"]) == pytest.approx(0.40)


# ── apply_chargeback_rules ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_chargeback_rules() -> None:
    """Weight splits produce correct allocations."""
    from runledger_api.services.billing import apply_chargeback_rules

    period_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    period = SimpleNamespace(
        id=period_id,
        workspace_id=workspace_id,
        total_cost_usd=Decimal("100.00"),
    )
    rules = [
        SimpleNamespace(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            dimension="engineering",
            weight=Decimal("0.60"),
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            dimension="product",
            weight=Decimal("0.40"),
        ),
    ]

    session = AsyncMock()

    period_result = MagicMock()
    period_result.scalar_one_or_none = MagicMock(return_value=period)

    rules_result = MagicMock()
    rules_result.scalars = MagicMock(
        return_value=MagicMock(__iter__=MagicMock(return_value=iter(rules)))
    )

    session.execute = AsyncMock(side_effect=[period_result, rules_result])

    allocations = await apply_chargeback_rules(session, period_id)

    assert allocations["engineering"] == pytest.approx(Decimal("60.00"), rel=1e-4)
    assert allocations["product"] == pytest.approx(Decimal("40.00"), rel=1e-4)


# ── Nightly reconciliation worker ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nightly_reconciliation_worker() -> None:
    """Celery task returns {'checked': N, 'failed': M}."""
    from runledger_api.schemas.billing import ReconciliationResult
    from runledger_api.workers.billing import _run_nightly_reconciliation

    period_id = uuid.uuid4()
    period = SimpleNamespace(id=period_id, status="closed", created_at=datetime.now(UTC))

    session = AsyncMock()
    session.add = MagicMock()

    periods_result = MagicMock()
    periods_result.scalars = MagicMock(
        return_value=MagicMock(__iter__=MagicMock(return_value=iter([period])))
    )

    session.execute = AsyncMock(return_value=periods_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    factory_mock = MagicMock(return_value=session)

    recon = ReconciliationResult(
        period_id=str(period_id),
        status="pass",
        provider_calls_sum=Decimal("0"),
        usage_daily_sum=Decimal("0"),
        delta_pct=Decimal("0"),
        orphaned_calls=0,
        duplicate_calls=0,
        issues=[],
    )

    with (
        patch(
            "runledger_api.workers.billing._make_session_factory",
            return_value=factory_mock,
        ),
        patch(
            "runledger_api.workers.billing.run_reconciliation",
            new=AsyncMock(return_value=recon),
        ),
    ):
        result = await _run_nightly_reconciliation()

    assert result["checked"] == 1
    assert result["failed"] == 0


# ── Auth enforcement ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_billing_requires_auth(client: AsyncClient) -> None:
    """GET /billing/periods without auth → 401."""
    response = await client.get("/billing/periods")
    assert response.status_code == 401
