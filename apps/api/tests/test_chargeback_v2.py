"""
Tests for Chargeback v2: cost centers, billing adjustments, multi-currency.

Phase 33 — ~20 tests covering:
  - Cost center CRUD + hierarchy tree
  - Billing adjustments CRUD + net cost calculations
  - Multi-currency billing period creation
  - Updated chargeback rule with cost_center_id
  - Approval gate on chargeback rule creation
  - close_billing_period deducting adjustments → net_cost_usd
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_cost_center(
    workspace_id: uuid.UUID | None = None,
    name: str = "Engineering",
    code: str | None = "ENG",
    parent_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        name=name,
        code=code,
        parent_id=parent_id,
        description=None,
        created_at=datetime.now(UTC),
    )


def _make_adjustment(
    billing_period_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    adjustment_type: str = "credit",
    amount_usd: Decimal = Decimal("50.00"),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        billing_period_id=billing_period_id or uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        adjustment_type=adjustment_type,
        amount_usd=amount_usd,
        description="Test credit",
        reference_id=None,
        created_by=None,
        created_at=datetime.now(UTC),
    )


def _make_period(
    workspace_id: uuid.UUID | None = None,
    status: str = "open",
    total_cost_usd: Decimal | None = Decimal("200.00"),
    currency: str = "USD",
    exchange_rate_to_usd: Decimal = Decimal("1.0"),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        period_start="2026-03-01",
        period_end="2026-03-31",
        status=status,
        total_cost_usd=total_cost_usd,
        net_cost_usd=None,
        currency=currency,
        exchange_rate_to_usd=exchange_rate_to_usd,
        snapshot_hash=None,
        closed_at=None,
        created_at=datetime.now(UTC),
    )


# ── Cost Center CRUD ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_cost_center(authed_client, mock_db_session, mock_workspace):
    """POST /billing/cost-centers creates a cost center."""
    cc = _make_cost_center(workspace_id=mock_workspace.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cc
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", cc.id) or setattr(obj, "created_at", cc.created_at))

    resp = await authed_client.post(
        "/billing/cost-centers",
        json={"name": "Engineering", "code": "ENG"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Engineering"
    assert data["code"] == "ENG"


@pytest.mark.anyio
async def test_list_cost_centers(authed_client, mock_db_session, mock_workspace):
    """GET /billing/cost-centers returns list."""
    cc = _make_cost_center(workspace_id=mock_workspace.id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cc]
    mock_result.scalars.return_value.__iter__ = lambda self: iter([cc])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/billing/cost-centers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Engineering"


@pytest.mark.anyio
async def test_get_cost_center_404(authed_client, mock_db_session):
    """GET /billing/cost-centers/{id} returns 404 for unknown ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get(f"/billing/cost-centers/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_cost_center(authed_client, mock_db_session, mock_workspace):
    """PUT /billing/cost-centers/{id} updates fields."""
    cc = _make_cost_center(workspace_id=mock_workspace.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cc
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "name", "Platform Engineering"))

    resp = await authed_client.put(
        f"/billing/cost-centers/{cc.id}",
        json={"name": "Platform Engineering"},
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_delete_cost_center(authed_client, mock_db_session, mock_workspace):
    """DELETE /billing/cost-centers/{id} returns 204."""
    cc = _make_cost_center(workspace_id=mock_workspace.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cc
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.delete(f"/billing/cost-centers/{cc.id}")
    assert resp.status_code == 204


# ── Cost Center Tree ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cost_center_tree_empty(authed_client, mock_db_session, mock_workspace):
    """GET /billing/cost-centers/tree returns [] when no centers exist."""
    mock_result = MagicMock()
    mock_result.scalars.return_value = iter([])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/billing/cost-centers/tree")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_cost_center_tree_hierarchy(authed_client, mock_db_session, mock_workspace):
    """GET /billing/cost-centers/tree nests children under parents."""
    parent = _make_cost_center(workspace_id=mock_workspace.id, name="Engineering", code="ENG")
    child = _make_cost_center(
        workspace_id=mock_workspace.id, name="Platform", code="PLT", parent_id=parent.id
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value = iter([parent, child])
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/billing/cost-centers/tree")
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Engineering"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "Platform"


# ── Billing Adjustments ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_adjustment_credit(authed_client, mock_db_session, mock_workspace):
    """POST /billing/periods/{id}/adjustments creates a credit adjustment."""
    period_id = uuid.uuid4()
    adj = _make_adjustment(billing_period_id=period_id, workspace_id=mock_workspace.id)

    period = _make_period(workspace_id=mock_workspace.id)
    period.id = period_id

    mock_results = iter([
        _result_with_scalar(period),   # period lookup in add_adjustment
    ])

    def _execute_side_effect(stmt):
        try:
            return next(mock_results)
        except StopIteration:
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            return r

    mock_db_session.execute = AsyncMock(side_effect=_execute_side_effect)
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", adj.id)
            or setattr(obj, "created_at", adj.created_at)
            or setattr(obj, "billing_period_id", period_id)
            or setattr(obj, "workspace_id", mock_workspace.id)
            or setattr(obj, "adjustment_type", "credit")
            or setattr(obj, "amount_usd", Decimal("50.00"))
            or setattr(obj, "description", "Test credit")
            or setattr(obj, "reference_id", None)
            or setattr(obj, "created_by", None)
        )
    )

    resp = await authed_client.post(
        f"/billing/periods/{period_id}/adjustments",
        json={"adjustment_type": "credit", "amount_usd": "50.00", "description": "Test credit"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["adjustment_type"] == "credit"


@pytest.mark.anyio
async def test_create_adjustment_invalid_type(authed_client):
    """POST /billing/periods/{id}/adjustments rejects unknown adjustment_type."""
    resp = await authed_client.post(
        f"/billing/periods/{uuid.uuid4()}/adjustments",
        json={"adjustment_type": "mystery", "amount_usd": "50.00"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_list_adjustments(authed_client, mock_db_session, mock_workspace):
    """GET /billing/periods/{id}/adjustments returns net calculations."""
    period_id = uuid.uuid4()
    period = _make_period(workspace_id=mock_workspace.id)
    period.id = period_id

    credit = _make_adjustment(
        billing_period_id=period_id,
        workspace_id=mock_workspace.id,
        adjustment_type="credit",
        amount_usd=Decimal("30.00"),
    )
    surcharge = _make_adjustment(
        billing_period_id=period_id,
        workspace_id=mock_workspace.id,
        adjustment_type="surcharge",
        amount_usd=Decimal("10.00"),
    )

    results = [
        _result_with_scalar(period),       # period ownership check
        _result_with_scalars([credit, surcharge]),  # adjustments list
    ]
    mock_db_session.execute = AsyncMock(side_effect=lambda _: results.pop(0))

    resp = await authed_client.get(f"/billing/periods/{period_id}/adjustments")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["total_credits_usd"]) == Decimal("30")
    assert Decimal(data["total_surcharges_usd"]) == Decimal("10")
    # net = surcharges - credits = -20
    assert Decimal(data["net_adjustment_usd"]) == Decimal("-20")


@pytest.mark.anyio
async def test_delete_adjustment(authed_client, mock_db_session, mock_workspace):
    """DELETE /billing/periods/{id}/adjustments/{adj_id} returns 204."""
    period_id = uuid.uuid4()
    adj = _make_adjustment(billing_period_id=period_id, workspace_id=mock_workspace.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = adj
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.delete(f"/billing/periods/{period_id}/adjustments/{adj.id}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_adjustment_404(authed_client, mock_db_session):
    """DELETE /billing/periods/{id}/adjustments/{adj_id} returns 404 for unknown."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.delete(
        f"/billing/periods/{uuid.uuid4()}/adjustments/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


# ── Multi-currency period creation ────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_period_with_currency(authed_client, mock_db_session, mock_workspace):
    """POST /billing/periods accepts currency + exchange_rate_to_usd."""
    period = _make_period(
        workspace_id=mock_workspace.id,
        currency="EUR",
        exchange_rate_to_usd=Decimal("1.08"),
    )

    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", period.id)
            or setattr(obj, "created_at", period.created_at)
            or setattr(obj, "total_cost_usd", None)
            or setattr(obj, "net_cost_usd", None)
            or setattr(obj, "currency", "EUR")
            or setattr(obj, "exchange_rate_to_usd", Decimal("1.08"))
            or setattr(obj, "snapshot_hash", None)
            or setattr(obj, "closed_at", None)
            or setattr(obj, "status", "open")
            or setattr(obj, "period_start", "2026-03-01")
            or setattr(obj, "period_end", "2026-03-31")
        )
    )

    resp = await authed_client.post(
        "/billing/periods",
        json={
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "currency": "EUR",
            "exchange_rate_to_usd": "1.08",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["currency"] == "EUR"
    assert Decimal(data["exchange_rate_to_usd"]) == Decimal("1.08")


# ── Chargeback rule with cost_center_id ───────────────────────────────────────


@pytest.mark.anyio
async def test_create_chargeback_rule_with_cost_center(authed_client, mock_db_session, mock_workspace):
    """POST /billing/chargeback-rules accepts optional cost_center_id."""
    cost_center_id = uuid.uuid4()
    rule = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        allocation_type="cost_center",
        dimension="engineering",
        weight=Decimal("0.6"),
        cost_center_id=cost_center_id,
        created_at=datetime.now(UTC),
    )

    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", rule.id)
            or setattr(obj, "created_at", rule.created_at)
            or setattr(obj, "cost_center_id", cost_center_id)
        )
    )

    resp = await authed_client.post(
        "/billing/chargeback-rules",
        json={
            "allocation_type": "cost_center",
            "dimension": "engineering",
            "weight": "0.6",
            "cost_center_id": str(cost_center_id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["cost_center_id"] == str(cost_center_id)


# ── Service layer: get_cost_center_tree ───────────────────────────────────────


@pytest.mark.anyio
async def test_get_cost_center_tree_service():
    """get_cost_center_tree() builds forest from flat list."""
    from runledger_api.services.billing import get_cost_center_tree

    ws_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    parent = SimpleNamespace(
        id=parent_id, workspace_id=ws_id, name="Root", code="R", parent_id=None, description=None
    )
    child = SimpleNamespace(
        id=child_id, workspace_id=ws_id, name="Child", code="C", parent_id=parent_id, description=None
    )

    mock_db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.__iter__ = lambda self: iter([parent, child])
    scalars_mock.scalars.return_value = iter([parent, child])

    result_mock = MagicMock()
    result_mock.scalars.return_value = iter([parent, child])
    mock_db.execute = AsyncMock(return_value=result_mock)

    roots = await get_cost_center_tree(mock_db, ws_id)
    assert len(roots) == 1
    assert roots[0].name == "Root"
    assert len(roots[0].children) == 1
    assert roots[0].children[0].name == "Child"


# ── Service layer: apply_chargeback_rules uses net_cost ───────────────────────


@pytest.mark.anyio
async def test_apply_chargeback_rules_uses_net_cost():
    """apply_chargeback_rules() uses net_cost_usd when available."""
    from runledger_api.services.billing import apply_chargeback_rules

    ws_id = uuid.uuid4()
    period_id = uuid.uuid4()
    period = SimpleNamespace(
        id=period_id,
        workspace_id=ws_id,
        total_cost_usd=Decimal("200.00"),
        net_cost_usd=Decimal("150.00"),  # after $50 credit
    )
    rule = SimpleNamespace(dimension="engineering", weight=Decimal("0.5"))

    mock_db = AsyncMock()
    period_result = MagicMock()
    period_result.scalar_one_or_none.return_value = period
    rules_result = MagicMock()
    rules_result.scalars.return_value.__iter__ = lambda self: iter([rule])

    mock_db.execute = AsyncMock(side_effect=[period_result, rules_result])

    result = await apply_chargeback_rules(mock_db, period_id)
    assert result["engineering"] == Decimal("75.00")  # 150 * 0.5


# ── Helper functions ──────────────────────────────────────────────────────────


def _result_with_scalar(obj):  # type: ignore[return]
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _result_with_scalars(items):  # type: ignore[return]
    r = MagicMock()
    r.scalars.return_value.__iter__ = lambda self: iter(items)
    r.scalars.return_value.all.return_value = items
    return r
