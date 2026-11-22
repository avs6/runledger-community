"""
Tests for billing & chargeback: signing, CSV safety, validation, period lifecycle
guards, chargeback rules, shared-cost allocation, the nightly worker and auth.

Uses the authed_client / mock_db_session fixtures from conftest (no database).
Behaviour that needs Postgres — locked close, frozen snapshots, rules applied to
real usage, persisted shared costs, separation of duties — is replayed end to end
by ``scripts/core/verify_billing.py``.
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
from pydantic import ValidationError
from runledger_api.schemas.billing import (
    BillingPeriodCreate,
    ChargebackBreakdownItem,
    ChargebackReport,
    ChargebackRuleCreate,
    ChargebackRuleUpdate,
)
from runledger_api.services import billing_signing
from runledger_api.services.billing import (
    _budget_for_month,
    _chargeback_period_bounds,
    compute_shared_cost_allocation,
    csv_safe,
    sign_snapshot,
    validate_shared_cost_allocations,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _period(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        status="open",
        total_cost_usd=None,
        net_cost_usd=None,
        currency="USD",
        exchange_rate_to_usd=Decimal("1"),
        snapshot_hash=None,
        closed_at=None,
        closed_by=None,
        reopened_at=None,
        reopen_reason=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _result(value: object = None, first: object = None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    result.scalar_one = MagicMock(return_value=value)
    result.first = MagicMock(return_value=first)
    result.scalars = MagicMock(
        return_value=MagicMock(
            __iter__=MagicMock(return_value=iter([value] if value is not None else []))
        )
    )
    result.all = MagicMock(return_value=[])
    return result


# ── Signing ───────────────────────────────────────────────────────────────────


def test_sign_snapshot_is_deterministic() -> None:
    data = {"b": 2, "a": 1}
    assert sign_snapshot(data, "k") == sign_snapshot({"a": 1, "b": 2}, "k")
    expected = hmac.new(b"k", json.dumps(data, sort_keys=True).encode(), hashlib.sha256)
    assert sign_snapshot(data, "k") == expected.hexdigest()


def test_workspace_signing_roundtrip_and_isolation() -> None:
    ws_a, ws_b = uuid.uuid4(), uuid.uuid4()
    data = {"period_id": "p", "total_cost_usd": "1.23", "lines": [{"cost_usd": "1.23"}]}
    sig, key_id = billing_signing.sign(data, ws_a, 1)
    assert key_id == "ws-v1"
    assert billing_signing.verify(data, sig, ws_a, key_id)
    # Another workspace's key (or a tampered payload) does not verify.
    assert not billing_signing.verify(data, sig, ws_b, key_id)
    assert not billing_signing.verify({**data, "total_cost_usd": "0.01"}, sig, ws_a, key_id)


def test_rotation_keeps_old_signatures_verifiable() -> None:
    ws = uuid.uuid4()
    data = {"x": 1}
    old_sig, old_id = billing_signing.sign(data, ws, 1)
    new_sig, new_id = billing_signing.sign(data, ws, 2)
    assert old_sig != new_sig and new_id == "ws-v2"
    assert billing_signing.verify(data, old_sig, ws, old_id)
    assert billing_signing.verify(data, new_sig, ws, new_id)
    assert not billing_signing.verify(data, old_sig, ws, new_id)


def test_workspace_key_is_not_the_platform_secret() -> None:
    from runledger_api.core.config import settings

    key = billing_signing.workspace_billing_key(uuid.uuid4(), 1)
    assert key != settings.secret_key and settings.secret_key not in key


def test_unknown_key_id_rejected() -> None:
    assert not billing_signing.verify({"x": 1}, "00", uuid.uuid4(), "ws-vX")


# ── CSV safety, months, budgets ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=HYPERLINK(1)", "'=HYPERLINK(1)"),
        ("+cmd", "'+cmd"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("-2+3", "'-2+3"),
        ("-12.5", "-12.5"),
        ("support-triage", "support-triage"),
        (Decimal("-3"), Decimal("-3")),
        (None, ""),
    ],
)
def test_csv_safe(value: object, expected: object) -> None:
    assert csv_safe(value) == expected


def test_period_bounds() -> None:
    assert _chargeback_period_bounds("2026-02") == ("2026-02", date(2026, 2, 1), date(2026, 2, 28))
    with pytest.raises(ValueError):
        _chargeback_period_bounds("2026/02")


def test_budget_for_month() -> None:
    assert _budget_for_month("monthly", Decimal("100"), 30) == Decimal("100")
    assert _budget_for_month("daily", Decimal("2"), 31) == Decimal("62")
    assert _budget_for_month("weekly", Decimal("7"), 28) == Decimal("28.00")
    assert _budget_for_month("total", Decimal("500"), 30) is None


# ── Schemas ───────────────────────────────────────────────────────────────────


def test_period_dates_and_currency_validated() -> None:
    with pytest.raises(ValidationError):
        BillingPeriodCreate(period_start=date(2026, 2, 1), period_end=date(2026, 1, 1))
    with pytest.raises(ValidationError):
        BillingPeriodCreate(
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), currency="usd"
        )
    with pytest.raises(ValidationError):
        BillingPeriodCreate(period_start=date(2025, 1, 1), period_end=date(2026, 6, 1))
    ok = BillingPeriodCreate(
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), currency="EUR"
    )
    assert ok.currency == "EUR"


def test_rule_needs_value_and_cost_center() -> None:
    with pytest.raises(ValidationError):
        ChargebackRuleCreate(dimension="feature_tag", weight=Decimal("1"))  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ChargebackRuleCreate(
            dimension="workspace",
            dimension_value="x",
            weight=Decimal("1"),
            cost_center_id=uuid.uuid4(),
        )
    with pytest.raises(ValidationError):
        ChargebackRuleCreate(
            dimension="feature_tag",
            dimension_value="x",
            weight=Decimal("0"),
            cost_center_id=uuid.uuid4(),
        )
    rule = ChargebackRuleCreate(
        dimension="feature_tag",
        dimension_value="support",
        weight=Decimal("0.5"),
        cost_center_id=uuid.uuid4(),
    )
    assert rule.allocation_type == "shared_weight"


def test_rule_update_cannot_set_approval_states() -> None:
    for state in ("pending_approval", "denied"):
        with pytest.raises(ValidationError):
            ChargebackRuleUpdate(status=state)
    assert ChargebackRuleUpdate(status="inactive").status == "inactive"


# ── Shared-cost validation and allocation ─────────────────────────────────────


@pytest.mark.asyncio
async def test_fixed_weights_must_sum_to_one() -> None:
    db = AsyncMock()
    with pytest.raises(ValueError, match="sum to 1"):
        await validate_shared_cost_allocations(
            db,
            uuid.uuid4(),
            "fixed_weight",
            [{"label": "a", "weight": 0.5}, {"label": "b", "weight": 0.3}],
        )
    await validate_shared_cost_allocations(
        db,
        uuid.uuid4(),
        "fixed_weight",
        [{"label": "a", "weight": 0.7}, {"label": "b", "weight": 0.3}],
    )


@pytest.mark.asyncio
async def test_proportional_needs_denominators() -> None:
    with pytest.raises(ValueError):
        await validate_shared_cost_allocations(
            AsyncMock(), uuid.uuid4(), "proportional", [{"label": "a", "denominator_value": 0}]
        )


@pytest.mark.asyncio
async def test_unknown_cost_center_rejected() -> None:
    db = AsyncMock()
    found = MagicMock()
    found.scalars = MagicMock(return_value=iter([]))
    db.execute = AsyncMock(return_value=found)
    with pytest.raises(ValueError, match="not found"):
        await validate_shared_cost_allocations(
            db, uuid.uuid4(), "equal_split", [{"label": "a", "cost_center_id": str(uuid.uuid4())}]
        )


@pytest.mark.asyncio
async def test_allocation_shares_sum_exactly_to_pool() -> None:
    policy = SimpleNamespace(
        id=uuid.uuid4(),
        name="platform",
        formula_type="equal_split",
        allocations=[{"label": "a"}, {"label": "b"}, {"label": "c"}],
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(policy))
    out = await compute_shared_cost_allocation(db, policy.id, Decimal("100"))
    amounts = [a["allocated_usd"] for a in out["allocations"]]
    assert sum(amounts) == Decimal("100")
    assert amounts[0] == Decimal("33.333333")


# ── Period endpoints ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_period_rejects_overlap(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    clash = SimpleNamespace(
        id=uuid.uuid4(), period_start=date(2026, 1, 15), period_end=date(2026, 2, 14)
    )
    mock_db_session.execute = AsyncMock(return_value=_result(first=clash))
    resp = await authed_client.post(
        "/billing/periods", json={"period_start": "2026-01-01", "period_end": "2026-01-31"}
    )
    assert resp.status_code == 409
    assert "Overlaps" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_period(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_result(first=None))

    async def refresh(obj: object) -> None:
        for k, v in vars(_period()).items():
            if getattr(obj, k, None) is None:
                setattr(obj, k, v)

    mock_db_session.refresh = refresh
    resp = await authed_client.post(
        "/billing/periods",
        json={
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "currency": "EUR",
            "exchange_rate_to_usd": "1.08",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["currency"] == "EUR"


@pytest.mark.asyncio
async def test_create_period_bad_dates(authed_client: AsyncClient) -> None:
    resp = await authed_client.post(
        "/billing/periods", json={"period_start": "2026-02-01", "period_end": "2026-01-01"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_close_already_closed_409(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    period = _period(status="closed")
    mock_db_session.execute = AsyncMock(return_value=_result(period))
    resp = await authed_client.post(f"/billing/periods/{period.id}/close")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_closed_period_adjustments_frozen(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    period = _period(status="closed")
    mock_db_session.execute = AsyncMock(return_value=_result(period))
    adj = uuid.uuid4()
    deleted = await authed_client.delete(f"/billing/periods/{period.id}/adjustments/{adj}")
    updated = await authed_client.put(
        f"/billing/periods/{period.id}/adjustments/{adj}", json={"amount_usd": "5"}
    )
    created = await authed_client.post(
        f"/billing/periods/{period.id}/adjustments",
        json={"adjustment_type": "credit", "amount_usd": "5"},
    )
    assert deleted.status_code == updated.status_code == created.status_code == 409


@pytest.mark.asyncio
async def test_closed_period_cannot_be_edited_or_deleted(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    period = _period(status="closed")
    mock_db_session.execute = AsyncMock(return_value=_result(period))
    assert (
        await authed_client.patch(f"/billing/periods/{period.id}", json={"currency": "EUR"})
    ).status_code == 409
    assert (await authed_client.delete(f"/billing/periods/{period.id}")).status_code == 409


@pytest.mark.asyncio
async def test_reopen_requires_reason(authed_client: AsyncClient) -> None:
    resp = await authed_client.post(f"/billing/periods/{uuid.uuid4()}/reopen", json={})
    assert resp.status_code == 422


# ── Chargeback endpoints ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_rule_cannot_be_activated_directly(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        allocation_type="shared_weight",
        dimension="feature_tag",
        dimension_value="support",
        weight=Decimal("0.5"),
        cost_center_id=uuid.uuid4(),
        status="pending_approval",
        approval_id=uuid.uuid4(),
        created_by="a@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_db_session.execute = AsyncMock(return_value=_result(rule))
    resp = await authed_client.put(
        f"/billing/chargeback-rules/{rule.id}", json={"status": "active"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_chargeback_export_escapes_and_filters(authed_client: AsyncClient) -> None:
    report = ChargebackReport(
        period="2026-01",
        dimension="end_user",
        total_cost_usd=Decimal("1"),
        covered_cost_usd=Decimal("0"),
        unallocated_cost_usd=Decimal("0"),
        breakdown=[
            ChargebackBreakdownItem(
                dimension="end_user",
                dimension_key="=cmd|' /C calc'!A0",
                dimension_value="=cmd|' /C calc'!A0",
                cost_usd=Decimal("1"),
                pct_of_total=Decimal("100"),
            )
        ],
    )
    with patch(
        "runledger_api.routers.billing.build_chargeback_report", new=AsyncMock(return_value=report)
    ) as build:
        resp = await authed_client.get(
            "/billing/chargeback-report/export",
            params={"dimension": "end_user", "end_user_id": "u-1"},
        )
    assert resp.status_code == 200
    assert "'=cmd" in resp.text and "\n=cmd" not in resp.text
    assert build.await_args.kwargs["end_user_id"] == "u-1"


@pytest.mark.asyncio
async def test_chargeback_report_rejects_bad_period(authed_client: AsyncClient) -> None:
    resp = await authed_client.get("/billing/chargeback-report", params={"period": "2026-13"})
    assert resp.status_code == 422


# ── Nightly reconciliation worker ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nightly_reconciliation_worker() -> None:
    from runledger_api.schemas.billing import ReconciliationResult
    from runledger_api.workers.billing import _run_nightly_reconciliation

    period = SimpleNamespace(id=uuid.uuid4(), status="closed", created_at=datetime.now(UTC))
    session = AsyncMock()
    session.add = MagicMock()
    periods_result = MagicMock()
    periods_result.scalars = MagicMock(
        return_value=MagicMock(__iter__=MagicMock(return_value=iter([period])))
    )
    session.execute = AsyncMock(return_value=periods_result)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    recon = ReconciliationResult(
        period_id=str(period.id),
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
            return_value=MagicMock(return_value=session),
        ),
        patch(
            "runledger_api.workers.billing.run_reconciliation", new=AsyncMock(return_value=recon)
        ),
    ):
        result = await _run_nightly_reconciliation()
    assert result == {"checked": 1, "failed": 0} or (
        result["checked"] == 1 and result["failed"] == 0
    )


# ── Auth ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_billing_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/billing/periods")).status_code == 401
    assert (await client.get("/billing/cost-centers")).status_code == 401
    assert (await client.get("/billing/signing-key")).status_code == 401


def test_budget_webhook_secret_is_per_destination() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert billing_signing.webhook_secret(a, 1) != billing_signing.webhook_secret(b, 1)
    assert billing_signing.webhook_secret(a, 1) != billing_signing.webhook_secret(a, 2)
    assert billing_signing.webhook_secret(a, 1) == billing_signing.webhook_secret(a, 1)
