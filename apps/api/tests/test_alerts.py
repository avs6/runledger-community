"""
Tests for Phase 21A Advanced Alerting endpoints.

Covers:
  POST   /alerts/rules          — create rule (validation, auth, success)
  GET    /alerts/rules          — list rules
  PUT    /alerts/rules/{id}     — update / toggle rule
  DELETE /alerts/rules/{id}     — delete rule
  GET    /alerts/history        — alert firing history

Uses authed_client / mock_db_session / mock_workspace fixtures from conftest.
No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Mock result helpers ────────────────────────────────────────────────────────


def _scalars_all_result(rows: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars)
    return m


def _all_result(rows: list[object]) -> MagicMock:
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _make_rule(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="High error rate",
        metric="error_rate",
        operator="gt",
        threshold=Decimal("0.05"),
        window_minutes=60,
        action="notify",
        channel_id=None,
        email_enabled=False,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /alerts/rules ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_alert_rule_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /alerts/rules → 201, response has id/name/metric/threshold."""
    rule = _make_rule(workspace_id=mock_workspace.id)

    async def set_attrs(obj: object) -> None:
        obj.id = rule.id  # type: ignore[attr-defined]
        obj.created_at = rule.created_at  # type: ignore[attr-defined]
        obj.action = "notify"  # type: ignore[attr-defined]
        obj.is_active = True  # type: ignore[attr-defined]
        obj.window_minutes = 60  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/alerts/rules",
        json={
            "name": "High error rate",
            "metric": "error_rate",
            "operator": "gt",
            "threshold": 0.05,
            "window_minutes": 60,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "High error rate"
    assert data["metric"] == "error_rate"
    assert float(data["threshold"]) == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_create_alert_rule_requires_auth(
    client: AsyncClient,
) -> None:
    """Unauthenticated POST → 401."""
    resp = await client.post(
        "/alerts/rules",
        json={"name": "x", "metric": "error_rate", "operator": "gt", "threshold": 0.1},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_alert_rule_invalid_metric(
    authed_client: AsyncClient,
) -> None:
    """Invalid metric value → 422."""
    resp = await authed_client.post(
        "/alerts/rules",
        json={"name": "x", "metric": "cpu_usage", "operator": "gt", "threshold": 0.1},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_rule_invalid_operator(
    authed_client: AsyncClient,
) -> None:
    """Invalid operator value → 422."""
    resp = await authed_client.post(
        "/alerts/rules",
        json={"name": "x", "metric": "error_rate", "operator": "eq", "threshold": 0.1},
    )
    assert resp.status_code == 422


# ── GET /alerts/rules ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_alert_rules_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /alerts/rules with no rules → empty items."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result([]))
    resp = await authed_client.get("/alerts/rules")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_alert_rules_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /alerts/rules returns all active rules."""
    rules = [
        _make_rule(workspace_id=mock_workspace.id, metric="error_rate"),
        _make_rule(workspace_id=mock_workspace.id, metric="spend_velocity"),
    ]
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result(rules))
    resp = await authed_client.get("/alerts/rules")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


# ── PUT /alerts/rules/{id} ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_alert_rule_toggle(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """PUT /alerts/rules/{id} with is_active=False → rule is deactivated."""
    rule = _make_rule(workspace_id=mock_workspace.id, is_active=True)
    mock_db_session.get = AsyncMock(return_value=rule)
    mock_db_session.refresh = AsyncMock(return_value=None)

    resp = await authed_client.put(
        f"/alerts/rules/{rule.id}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    # rule.is_active was set to False by the router
    assert rule.is_active is False


# ── DELETE /alerts/rules/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_alert_rule(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """DELETE /alerts/rules/{id} → 204."""
    rule = _make_rule(workspace_id=mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=rule)

    resp = await authed_client.delete(f"/alerts/rules/{rule.id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(rule)


# ── GET /alerts/history ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alert_history_returns_firings(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /alerts/history returns recent alert firings with rule_name."""
    from types import SimpleNamespace as NS

    firing_row = (
        NS(
            id=uuid.uuid4(),
            rule_id=uuid.uuid4(),
            workspace_id=mock_workspace.id,
            fired_at=datetime.now(UTC),
            metric_value=Decimal("0.12"),
            resolved_at=None,
        ),
        "High error rate",  # rule_name from JOIN
    )
    mock_db_session.execute = AsyncMock(return_value=_all_result([firing_row]))

    resp = await authed_client.get("/alerts/history")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["rule_name"] == "High error rate"
    assert float(items[0]["metric_value"]) == pytest.approx(0.12)
