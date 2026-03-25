"""
Tests for Shared-Cost Policies (Phase 33 / Chargeback v2).

Covers:
  - POST /billing/shared-cost-policies  — create policy
  - GET  /billing/shared-cost-policies  — list (active_only filter)
  - GET  /billing/shared-cost-policies/{id}  — get / 404
  - PUT  /billing/shared-cost-policies/{id}  — update
  - DELETE /billing/shared-cost-policies/{id}  — delete / 404
  - POST /billing/shared-cost-policies/{id}/allocate  — compute
  - Service: compute_shared_cost_allocation — equal_split / fixed_weight / proportional
  - Service: missing pool_usd → 422; missing policy → 404
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_policy(
    workspace_id: uuid.UUID | None = None,
    name: str = "Infra Split",
    formula_type: str = "equal_split",
    allocations: list | None = None,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id or uuid.uuid4(),
        name=name,
        description=None,
        formula_type=formula_type,
        allocations=allocations or [],
        is_active=is_active,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _result_with_scalar(obj):  # type: ignore[return]
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _result_with_scalars(items):  # type: ignore[return]
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


# ── POST /billing/shared-cost-policies ────────────────────────────────────────


@pytest.mark.anyio
async def test_create_shared_cost_policy(authed_client, mock_db_session, mock_workspace):
    """Create a shared-cost policy with equal_split."""
    policy = _make_policy(workspace_id=mock_workspace.id)

    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: (
            setattr(obj, "id", policy.id)
            or setattr(obj, "created_at", policy.created_at)
            or setattr(obj, "updated_at", policy.updated_at)
            or setattr(obj, "allocations", [])
        )
    )

    resp = await authed_client.post(
        "/billing/shared-cost-policies",
        json={
            "name": "Infra Split",
            "formula_type": "equal_split",
            "allocations": [
                {"label": "eng", "cost_center_id": str(uuid.uuid4())},
                {"label": "ops"},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Infra Split"
    assert data["formula_type"] == "equal_split"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_create_shared_cost_policy_invalid_formula(authed_client):
    """Invalid formula_type → 422."""
    resp = await authed_client.post(
        "/billing/shared-cost-policies",
        json={"name": "Bad", "formula_type": "magic_split"},
    )
    assert resp.status_code == 422


# ── GET /billing/shared-cost-policies ─────────────────────────────────────────


@pytest.mark.anyio
async def test_list_shared_cost_policies(authed_client, mock_db_session, mock_workspace):
    """GET list returns policies."""
    p1 = _make_policy(workspace_id=mock_workspace.id, name="Policy A")
    p2 = _make_policy(workspace_id=mock_workspace.id, name="Policy B", is_active=False)

    mock_db_session.execute = AsyncMock(return_value=_result_with_scalars([p1, p2]))

    resp = await authed_client.get("/billing/shared-cost-policies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert {d["name"] for d in data["items"]} == {"Policy A", "Policy B"}


# ── GET /billing/shared-cost-policies/{id} ────────────────────────────────────


@pytest.mark.anyio
async def test_get_shared_cost_policy(authed_client, mock_db_session, mock_workspace):
    """GET by ID returns policy."""
    policy = _make_policy(workspace_id=mock_workspace.id)

    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(policy))

    resp = await authed_client.get(f"/billing/shared-cost-policies/{policy.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == policy.name


@pytest.mark.anyio
async def test_get_shared_cost_policy_404(authed_client, mock_db_session):
    """GET by unknown ID → 404."""
    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(None))

    resp = await authed_client.get(f"/billing/shared-cost-policies/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PUT /billing/shared-cost-policies/{id} ────────────────────────────────────


@pytest.mark.anyio
async def test_update_shared_cost_policy(authed_client, mock_db_session, mock_workspace):
    """PUT updates name and is_active."""
    policy = _make_policy(workspace_id=mock_workspace.id, name="Old Name")

    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(policy))
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "name", "New Name"))

    resp = await authed_client.put(
        f"/billing/shared-cost-policies/{policy.id}",
        json={"name": "New Name", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.anyio
async def test_update_shared_cost_policy_404(authed_client, mock_db_session):
    """PUT on unknown ID → 404."""
    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(None))

    resp = await authed_client.put(
        f"/billing/shared-cost-policies/{uuid.uuid4()}",
        json={"name": "X"},
    )
    assert resp.status_code == 404


# ── DELETE /billing/shared-cost-policies/{id} ─────────────────────────────────


@pytest.mark.anyio
async def test_delete_shared_cost_policy(authed_client, mock_db_session, mock_workspace):
    """DELETE returns 204."""
    policy = _make_policy(workspace_id=mock_workspace.id)

    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(policy))

    resp = await authed_client.delete(f"/billing/shared-cost-policies/{policy.id}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_shared_cost_policy_404(authed_client, mock_db_session):
    """DELETE on unknown ID → 404."""
    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(None))

    resp = await authed_client.delete(f"/billing/shared-cost-policies/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── POST /billing/shared-cost-policies/{id}/allocate ──────────────────────────


@pytest.mark.anyio
async def test_allocate_shared_cost(authed_client, mock_db_session, mock_workspace):
    """POST /allocate returns computed allocation."""
    policy = _make_policy(
        workspace_id=mock_workspace.id,
        formula_type="equal_split",
        allocations=[{"label": "eng"}, {"label": "ops"}],
    )

    # Two execute calls: ownership check + compute_shared_cost_allocation lookup
    results = [_result_with_scalar(policy), _result_with_scalar(policy)]
    mock_db_session.execute = AsyncMock(side_effect=lambda _: results.pop(0))

    resp = await authed_client.post(
        f"/billing/shared-cost-policies/{policy.id}/allocate",
        json={"pool_usd": "200.00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["formula_type"] == "equal_split"
    assert len(data["allocations"]) == 2
    # Equal split: 200 / 2 = 100 each
    for alloc in data["allocations"]:
        assert Decimal(alloc["allocated_usd"]) == Decimal("100")


@pytest.mark.anyio
async def test_allocate_missing_pool_usd(authed_client, mock_db_session, mock_workspace):
    """POST /allocate without pool_usd → 422."""
    policy = _make_policy(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_result_with_scalar(policy))

    resp = await authed_client.post(
        f"/billing/shared-cost-policies/{policy.id}/allocate",
        json={},
    )
    assert resp.status_code == 422


# ── Service: compute_shared_cost_allocation ───────────────────────────────────


@pytest.mark.anyio
async def test_compute_equal_split():
    """equal_split distributes pool evenly."""
    from runledger_api.services.billing import compute_shared_cost_allocation

    policy_id = uuid.uuid4()
    policy = SimpleNamespace(
        id=policy_id,
        name="Test",
        formula_type="equal_split",
        allocations=[
            {"label": "a", "cost_center_id": None},
            {"label": "b", "cost_center_id": None},
            {"label": "c", "cost_center_id": None},
        ],
    )

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = policy
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await compute_shared_cost_allocation(mock_db, policy_id, Decimal("300"))
    allocations = result["allocations"]
    assert len(allocations) == 3
    for a in allocations:
        assert Decimal(str(a["allocated_usd"])) == Decimal("100")


@pytest.mark.anyio
async def test_compute_fixed_weight():
    """fixed_weight multiplies pool by each weight."""
    from runledger_api.services.billing import compute_shared_cost_allocation

    policy_id = uuid.uuid4()
    policy = SimpleNamespace(
        id=policy_id,
        name="Fixed",
        formula_type="fixed_weight",
        allocations=[
            {"label": "a", "weight": "0.7"},
            {"label": "b", "weight": "0.3"},
        ],
    )

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = policy
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await compute_shared_cost_allocation(mock_db, policy_id, Decimal("1000"))
    allocations = {a["label"]: Decimal(str(a["allocated_usd"])) for a in result["allocations"]}
    assert allocations["a"] == Decimal("700")
    assert allocations["b"] == Decimal("300")


@pytest.mark.anyio
async def test_compute_proportional():
    """proportional divides pool by sum of denominator_values."""
    from runledger_api.services.billing import compute_shared_cost_allocation

    policy_id = uuid.uuid4()
    policy = SimpleNamespace(
        id=policy_id,
        name="Prop",
        formula_type="proportional",
        allocations=[
            {"label": "x", "denominator_value": "3"},  # 3/5 * 1000 = 600
            {"label": "y", "denominator_value": "2"},  # 2/5 * 1000 = 400
        ],
    )

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = policy
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await compute_shared_cost_allocation(mock_db, policy_id, Decimal("1000"))
    allocations = {a["label"]: Decimal(str(a["allocated_usd"])) for a in result["allocations"]}
    assert allocations["x"] == Decimal("600")
    assert allocations["y"] == Decimal("400")


@pytest.mark.anyio
async def test_compute_empty_allocations():
    """empty allocations list returns empty result."""
    from runledger_api.services.billing import compute_shared_cost_allocation

    policy_id = uuid.uuid4()
    policy = SimpleNamespace(
        id=policy_id,
        name="Empty",
        formula_type="equal_split",
        allocations=[],
    )

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = policy
    mock_db.execute = AsyncMock(return_value=result_mock)

    result = await compute_shared_cost_allocation(mock_db, policy_id, Decimal("500"))
    assert result["allocations"] == []


@pytest.mark.anyio
async def test_compute_policy_not_found():
    """ValueError raised when policy not found."""
    from runledger_api.services.billing import compute_shared_cost_allocation

    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(ValueError, match="not found"):
        await compute_shared_cost_allocation(mock_db, uuid.uuid4(), Decimal("100"))
