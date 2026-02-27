"""
Tests for the analytics API endpoints.

Uses the authed_client fixture (workspace auth bypassed) and mocks DB queries
so no live database is needed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_row(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def _agg_result(row: SimpleNamespace) -> MagicMock:
    result = MagicMock()
    result.one = MagicMock(return_value=row)
    return result


def _list_result(rows: list[SimpleNamespace]) -> MagicMock:
    result = MagicMock()
    result.all = MagicMock(return_value=rows)
    return result


# ── /analytics/summary ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_aggregates(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    row = _make_row(
        total_cost=Decimal("0.05"),
        total_input=10000,
        total_output=2000,
        run_count=5,
        call_count=12,
    )
    mock_db_session.execute = AsyncMock(return_value=_agg_result(row))

    response = await authed_client.get("/analytics/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_usd"] == "0.05"
    assert data["total_input_tokens"] == 10000
    assert data["total_output_tokens"] == 2000
    assert data["run_count"] == 5
    assert data["call_count"] == 12


@pytest.mark.asyncio
async def test_summary_with_time_range(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    row = _make_row(
        total_cost=Decimal("0"),
        total_input=0,
        total_output=0,
        run_count=0,
        call_count=0,
    )
    mock_db_session.execute = AsyncMock(return_value=_agg_result(row))

    response = await authed_client.get(
        "/analytics/summary",
        params={"from": "2026-01-01T00:00:00+00:00", "to": "2026-01-31T23:59:59+00:00"},
    )

    assert response.status_code == 200


# ── /analytics/spend-over-time ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_over_time_daily(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        _make_row(
            period=datetime(2026, 1, 1, tzinfo=UTC),
            cost_usd=Decimal("0.01"),
            input_tokens=1000,
            output_tokens=200,
            call_count=3,
        ),
        _make_row(
            period=datetime(2026, 1, 2, tzinfo=UTC),
            cost_usd=Decimal("0.02"),
            input_tokens=2000,
            output_tokens=400,
            call_count=6,
        ),
    ]
    mock_db_session.execute = AsyncMock(return_value=_list_result(rows))

    response = await authed_client.get("/analytics/spend-over-time?granularity=daily")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert len(data["points"]) == 2
    assert data["points"][0]["cost_usd"] == "0.01"


@pytest.mark.asyncio
async def test_spend_over_time_hourly(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_list_result([]))

    response = await authed_client.get("/analytics/spend-over-time?granularity=hourly")

    assert response.status_code == 200
    assert response.json()["granularity"] == "hourly"


@pytest.mark.asyncio
async def test_spend_over_time_invalid_granularity(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    response = await authed_client.get("/analytics/spend-over-time?granularity=weekly")
    assert response.status_code == 422


# ── /analytics/spend-by-model ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_by_model_returns_breakdown(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        _make_row(
            provider="openai",
            model="gpt-4o",
            cost_usd=Decimal("0.10"),
            input_tokens=5000,
            output_tokens=1000,
            call_count=10,
        ),
        _make_row(
            provider="anthropic",
            model="claude-sonnet-4-6",
            cost_usd=Decimal("0.05"),
            input_tokens=2000,
            output_tokens=500,
            call_count=4,
        ),
    ]
    mock_db_session.execute = AsyncMock(return_value=_list_result(rows))

    response = await authed_client.get("/analytics/spend-by-model")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["model"] == "gpt-4o"
    assert data["items"][0]["provider"] == "openai"
    assert data["items"][1]["model"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_spend_by_model_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_list_result([]))
    response = await authed_client.get("/analytics/spend-by-model")
    assert response.status_code == 200
    assert response.json()["items"] == []


# ── /analytics/spend-by-user ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_by_user_returns_top_spenders(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        _make_row(
            end_user_id="user-alpha",
            cost_usd=Decimal("1.50"),
            run_count=30,
            call_count=120,
        ),
        _make_row(
            end_user_id="user-beta",
            cost_usd=Decimal("0.75"),
            run_count=15,
            call_count=60,
        ),
    ]
    mock_db_session.execute = AsyncMock(return_value=_list_result(rows))

    response = await authed_client.get("/analytics/spend-by-user")

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["end_user_id"] == "user-alpha"
    assert data["items"][0]["cost_usd"] == "1.50"


@pytest.mark.asyncio
async def test_spend_by_user_respects_limit(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_list_result([]))
    response = await authed_client.get("/analytics/spend-by-user?limit=10")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_spend_by_user_limit_too_large_rejected(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    response = await authed_client.get("/analytics/spend-by-user?limit=999")
    assert response.status_code == 422


# ── /analytics/spend-by-feature ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_by_feature_returns_breakdown(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        _make_row(
            feature_tag="support-chat",
            cost_usd=Decimal("0.80"),
            run_count=20,
            call_count=80,
        ),
        _make_row(
            feature_tag=None,
            cost_usd=Decimal("0.20"),
            run_count=5,
            call_count=15,
        ),
    ]
    mock_db_session.execute = AsyncMock(return_value=_list_result(rows))

    response = await authed_client.get("/analytics/spend-by-feature")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["feature_tag"] == "support-chat"
    assert data["items"][1]["feature_tag"] is None


@pytest.mark.asyncio
async def test_spend_by_feature_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_list_result([]))
    response = await authed_client.get("/analytics/spend-by-feature")
    assert response.status_code == 200
    assert response.json()["items"] == []


# ── Auth enforcement ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated requests should be rejected."""
    response = await client.get("/analytics/summary")
    assert response.status_code == 401
