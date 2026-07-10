"""
Tests for Phase 17B — Evaluator Framework.

Covers:
  POST   /evaluations/evaluators          — create (rule + llm_judge)
  GET    /evaluations/evaluators          — list
  GET    /evaluations/evaluators/{id}     — get single
  PUT    /evaluations/evaluators/{id}     — update
  DELETE /evaluations/evaluators/{id}     — delete
  POST   /evaluations/evaluators/{id}/run — queue batch evaluation
  GET    /analytics/scores/cost-quality   — cost vs quality per model
  GET    /analytics/scores/best-value     — quality÷cost ranking

Also covers unit tests for the rule evaluator service logic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Fixtures ───────────────────────────────────────────────────────────────────


def _scalars_list(rows: list) -> MagicMock:
    m = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m.scalars = MagicMock(return_value=scalars)
    return m


def _scalar_one_or_none(val) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=val)
    return m


def _scalar(val) -> MagicMock:
    m = MagicMock()
    m.scalar = MagicMock(return_value=val)
    return m


def _make_evaluator(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Quality Check",
        description="Checks run quality",
        type="rule",
        config={"rules": []},
        status="active",
        last_run_at=None,
        last_run_count=0,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── Create evaluator ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_evaluator_rule(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev = _make_evaluator(workspace_id=mock_workspace.id)

    async def mock_refresh(obj: object) -> None:
        obj.id = ev.id
        obj.created_at = ev.created_at
        obj.status = "active"
        obj.last_run_count = 0

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.post(
        "/evaluations/evaluators",
        json={
            "name": "Quality Check",
            "type": "rule",
            "config": {
                "rules": [
                    {
                        "field": "status",
                        "op": "eq",
                        "value": "succeeded",
                        "score_if_pass": 1,
                        "score_if_fail": 0,
                    }
                ]
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Quality Check"
    assert data["type"] == "rule"


@pytest.mark.asyncio
async def test_create_evaluator_llm_judge(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev = _make_evaluator(type="llm_judge", workspace_id=mock_workspace.id)

    async def mock_refresh(obj: object) -> None:
        obj.id = ev.id
        obj.created_at = ev.created_at
        obj.status = "active"
        obj.last_run_count = 0

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.post(
        "/evaluations/evaluators",
        json={
            "name": "LLM Judge",
            "type": "llm_judge",
            "config": {"model": "gpt-4o-mini", "criteria": "Rate quality 0-1"},
        },
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "llm_judge"


@pytest.mark.asyncio
async def test_create_evaluator_invalid_type(authed_client: AsyncClient) -> None:
    resp = await authed_client.post(
        "/evaluations/evaluators",
        json={
            "name": "Bad",
            "type": "invalid_type",
            "config": {},
        },
    )
    assert resp.status_code == 422


# ── List evaluators ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_evaluators_empty(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/evaluations/evaluators")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_evaluators(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev1 = _make_evaluator(workspace_id=mock_workspace.id, name="EvalA")
    ev2 = _make_evaluator(workspace_id=mock_workspace.id, name="EvalB", type="llm_judge")
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([ev1, ev2]))

    resp = await authed_client.get("/evaluations/evaluators")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["name"] == "EvalA"
    assert items[1]["type"] == "llm_judge"


# ── Get single evaluator ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_evaluator(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev_id = uuid.uuid4()
    ev = _make_evaluator(id=ev_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(ev))

    resp = await authed_client.get(f"/evaluations/evaluators/{ev_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(ev_id)


@pytest.mark.asyncio
async def test_get_evaluator_not_found(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.get(f"/evaluations/evaluators/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Update evaluator ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_evaluator(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev_id = uuid.uuid4()
    ev = _make_evaluator(id=ev_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(ev))

    async def mock_refresh(obj: object) -> None:
        pass

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.put(
        f"/evaluations/evaluators/{ev_id}",
        json={
            "name": "Updated Name",
            "status": "inactive",
        },
    )
    assert resp.status_code == 200
    # The name/status are set on the object directly
    assert ev.name == "Updated Name"
    assert ev.status == "inactive"


@pytest.mark.asyncio
async def test_update_evaluator_not_found(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.put(f"/evaluations/evaluators/{uuid.uuid4()}", json={"name": "X"})
    assert resp.status_code == 404


# ── Delete evaluator ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_evaluator(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev_id = uuid.uuid4()
    ev = _make_evaluator(id=ev_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(ev))
    mock_db_session.delete = AsyncMock()

    resp = await authed_client.delete(f"/evaluations/evaluators/{ev_id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(ev)


@pytest.mark.asyncio
async def test_delete_evaluator_not_found(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.delete(f"/evaluations/evaluators/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Run evaluator ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_evaluator(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    ev_id = uuid.uuid4()
    ev = _make_evaluator(id=ev_id, workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(ev))

    with patch("runledger_api.workers.evaluators.batch_evaluate") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post(f"/evaluations/evaluators/{ev_id}/run", json={"limit": 50})

    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluator_id"] == str(ev_id)
    assert data["evaluated"] == 0  # async — returns placeholder


@pytest.mark.asyncio
async def test_run_evaluator_not_found(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_one_or_none(None))
    resp = await authed_client.post(f"/evaluations/evaluators/{uuid.uuid4()}/run", json={})
    assert resp.status_code == 404


# ── Cost-quality analytics ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cost_quality_empty(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    m = MagicMock()
    m.all = MagicMock(return_value=[])
    mock_db_session.execute = AsyncMock(return_value=m)
    resp = await authed_client.get("/analytics/scores/cost-quality")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_cost_quality_with_data(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    row = SimpleNamespace(
        model="gpt-4o", avg_cost_usd=Decimal("0.002"), avg_score=Decimal("0.85"), run_count=10
    )
    m = MagicMock()
    m.all = MagicMock(return_value=[row])
    mock_db_session.execute = AsyncMock(return_value=m)

    resp = await authed_client.get("/analytics/scores/cost-quality")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["model"] == "gpt-4o"
    assert items[0]["avg_score"] == "0.8500"


@pytest.mark.asyncio
async def test_best_value_empty(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    m = MagicMock()
    m.all = MagicMock(return_value=[])
    mock_db_session.execute = AsyncMock(return_value=m)
    resp = await authed_client.get("/analytics/scores/best-value")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── Unit tests: rule evaluator service ────────────────────────────────────────


def test_rule_evaluator_eq_pass() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    config = {
        "rules": [
            {
                "field": "status",
                "op": "eq",
                "value": "succeeded",
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            }
        ]
    }
    score, evidence = run_rule_evaluator(config, {"status": "succeeded"})
    assert score == Decimal("1.0")
    assert evidence["rules"][0]["passed"] is True


def test_rule_evaluator_eq_fail() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    config = {
        "rules": [
            {
                "field": "status",
                "op": "eq",
                "value": "succeeded",
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            }
        ]
    }
    score, evidence = run_rule_evaluator(config, {"status": "failed"})
    assert score == Decimal("0.0")
    assert evidence["rules"][0]["passed"] is False


def test_rule_evaluator_gt() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    config = {
        "rules": [
            {
                "field": "duration_ms",
                "op": "lte",
                "value": 5000,
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            }
        ]
    }
    score, _ = run_rule_evaluator(config, {"duration_ms": 3000})
    assert score == Decimal("1.0")


def test_rule_evaluator_contains() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    config = {
        "rules": [
            {
                "field": "feature_tag",
                "op": "contains",
                "value": "prod",
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            }
        ]
    }
    score, _ = run_rule_evaluator(config, {"feature_tag": "production-v2"})
    assert score == Decimal("1.0")


def test_rule_evaluator_avg_aggregation() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    config = {
        "aggregation": "avg",
        "rules": [
            {
                "field": "status",
                "op": "eq",
                "value": "succeeded",
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            },
            {
                "field": "duration_ms",
                "op": "lte",
                "value": 1000,
                "score_if_pass": 1.0,
                "score_if_fail": 0.0,
            },
        ],
    }
    # First rule passes (1.0), second fails (0.0) → avg = 0.5
    score, _ = run_rule_evaluator(config, {"status": "succeeded", "duration_ms": 5000})
    assert score == Decimal("0.5")


def test_rule_evaluator_empty_rules() -> None:
    from runledger_api.services.evaluators import run_rule_evaluator

    score, _ = run_rule_evaluator({"rules": []}, {"status": "succeeded"})
    assert score == Decimal("0")
