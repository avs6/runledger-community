"""
Tests for Phase 10 analytics extensions:
  GET /analytics/users/cohorts   — P0-P3 spend tier classification
  GET /analytics/users/anomalies — anomaly list from user_anomalies table

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Mock result helpers (copied from test_economics.py pattern) ────────────────


def _row_result(rows: list[object]) -> MagicMock:
    """Result where .all() returns a list of rows."""
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _scalars_list_result(rows: list[object]) -> MagicMock:
    """Result where .scalars().all() returns rows (ORM list query)."""
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


# ── GET /analytics/users/cohorts ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_cohorts_returns_tiers(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/users/cohorts → items list with cohort_tier fields."""
    tier_rows = [
        SimpleNamespace(
            tier="P0", user_count=5, avg_cost_usd=Decimal("0.50"), total_cost_usd=Decimal("2.50")
        ),
        SimpleNamespace(
            tier="P1", user_count=2, avg_cost_usd=Decimal("5.00"), total_cost_usd=Decimal("10.00")
        ),
    ]
    # cohorts endpoint makes 1 db.execute call (subquery is inline)
    mock_db_session.execute = AsyncMock(return_value=_row_result(tier_rows))

    response = await authed_client.get("/analytics/users/cohorts")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "window_days" in data
    tiers = [item["cohort_tier"] for item in data["items"]]
    assert "P0" in tiers
    assert "P1" in tiers


@pytest.mark.asyncio
async def test_user_cohorts_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/users/cohorts with no users → items=[]."""
    mock_db_session.execute = AsyncMock(return_value=_row_result([]))

    response = await authed_client.get("/analytics/users/cohorts")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["window_days"] > 0


# ── GET /analytics/users/anomalies ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_anomalies_returns_list(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/users/anomalies → items list from user_anomalies table."""
    anomaly = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        end_user_id="user-42",
        detected_at=date(2026, 2, 26),
        daily_spend=Decimal("9.50"),
        mean_spend=Decimal("1.20"),
        zscore=Decimal("4.2"),
        reason="Daily spend $9.5000 is 4.2σ above 30d mean $1.2000",
        created_at=datetime.now(UTC),
    )
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([anomaly]))

    response = await authed_client.get("/analytics/users/anomalies")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["end_user_id"] == "user-42"
    assert float(item["zscore"]) == pytest.approx(4.2)


@pytest.mark.asyncio
async def test_user_anomalies_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/users/anomalies with no anomalies → items=[]."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([]))

    response = await authed_client.get("/analytics/users/anomalies")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


# ── Auth guard ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cohorts_requires_auth(client: AsyncClient) -> None:
    """GET /analytics/users/cohorts without Bearer token → 401."""
    response = await client.get("/analytics/users/cohorts")
    assert response.status_code == 401
