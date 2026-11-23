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


def _result(
    rows: list[SimpleNamespace] | None = None,
    one: SimpleNamespace | None = None,
    scalar: object = None,
) -> MagicMock:
    """A result answering .all(), .one() and .scalar_one_or_none() (rollup watermark)."""
    result = MagicMock()
    result.all = MagicMock(return_value=rows or [])
    result.one = MagicMock(return_value=one)
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    return result


def _calls_row(
    cost: str, inp: int, out: int, runs: int, calls: int, users: int = 0
) -> SimpleNamespace:
    return _make_row(
        cost=Decimal(cost),
        savings=Decimal("0"),
        inp=inp,
        out=out,
        runs=runs,
        calls=calls,
        users=users,
    )


def _runs_row(succeeded: int = 0, finished: int = 0, cost: str = "0") -> SimpleNamespace:
    return _make_row(
        cost=Decimal(cost), inp=0, out=0, succeeded=succeeded, finished=finished, users=0
    )


def _summary_side_effect(
    cur: SimpleNamespace, prev: SimpleNamespace, runs: SimpleNamespace
) -> list[MagicMock]:
    # compute_summary: current calls, previous calls, current runs, previous runs.
    return [_result(one=cur), _result(one=prev), _result(one=runs), _result(one=_runs_row())]


# ── /analytics/summary ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_aggregates(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=_summary_side_effect(
            _calls_row("0.05", 10000, 2000, 5, 12),
            _calls_row("0", 0, 0, 0, 0),
            _runs_row(succeeded=4, finished=5),
        )
    )

    response = await authed_client.get("/analytics/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_usd"] == "0.05"
    assert data["total_input_tokens"] == 10000
    assert data["total_output_tokens"] == 2000
    assert data["run_count"] == 5
    assert data["call_count"] == 12
    # Success rate comes from the API, over every finished run (review O-22).
    assert data["success_rate"] == "0.8000"
    assert data["finished_runs"] == 5


@pytest.mark.asyncio
async def test_summary_rejects_access_group_outside_workspace_scope(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    response = await authed_client.get(
        "/analytics/summary",
        params={"scope": "org", "access_group_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_summary_with_time_range(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    zero = _calls_row("0", 0, 0, 0, 0)
    mock_db_session.execute = AsyncMock(side_effect=_summary_side_effect(zero, zero, _runs_row()))

    response = await authed_client.get(
        "/analytics/summary",
        params={"from": "2026-01-01T00:00:00+00:00", "to": "2026-01-31T23:59:59+00:00"},
    )

    assert response.status_code == 200
    assert response.json()["success_rate"] is None


# ── /analytics/spend-over-time ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_over_time_daily(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows = [
        _make_row(
            period=datetime(2026, 1, 1, 3, tzinfo=UTC),
            cost_usd=Decimal("0.01"),
            input_tokens=1000,
            output_tokens=200,
            call_count=3,
        ),
        _make_row(
            period=datetime(2026, 1, 1, 9, tzinfo=UTC),
            cost_usd=Decimal("0.01"),
            input_tokens=500,
            output_tokens=100,
            call_count=1,
        ),
        _make_row(
            period=datetime(2026, 1, 2, tzinfo=UTC),
            cost_usd=Decimal("0.02"),
            input_tokens=2000,
            output_tokens=400,
            call_count=6,
        ),
    ]
    # No rollup yet (watermark None) → raw hourly rows bucketed into days.
    mock_db_session.execute = AsyncMock(side_effect=[_result(scalar=None), _result(rows=rows)])

    response = await authed_client.get("/analytics/spend-over-time?granularity=daily")

    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "daily"
    assert data["source"] == "raw"
    assert len(data["points"]) == 2
    assert data["points"][0]["cost_usd"] == "0.02"
    assert data["points"][0]["call_count"] == 4


@pytest.mark.asyncio
async def test_spend_over_time_uses_rollup_before_watermark(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    from datetime import timedelta

    watermark_hour = now - timedelta(hours=3)
    rollup_rows = [
        _make_row(
            period=watermark_hour,
            cost_usd=Decimal("1.00"),
            input_tokens=10,
            output_tokens=5,
            call_count=2,
        )
    ]
    raw_rows = [
        _make_row(
            period=now,
            cost_usd=Decimal("0.50"),
            input_tokens=1,
            output_tokens=1,
            call_count=1,
        )
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _result(scalar=watermark_hour),
            _result(rows=rollup_rows),
            _result(rows=raw_rows),
        ]
    )

    response = await authed_client.get("/analytics/spend-over-time?granularity=hourly")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "rollup+raw"
    assert [p["cost_usd"] for p in data["points"]] == ["1.00", "0.50"]


@pytest.mark.asyncio
async def test_spend_over_time_hourly(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_result(rows=[], scalar=None))

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
    mock_db_session.execute = AsyncMock(side_effect=[_result(scalar=None), _result(rows=rows)])

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
    mock_db_session.execute = AsyncMock(return_value=_result(rows=[], scalar=None))
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
            last_active=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            first_seen=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        ),
        _make_row(
            end_user_id="user-beta",
            cost_usd=Decimal("0.75"),
            run_count=15,
            call_count=60,
            last_active=None,
            first_seen=None,
        ),
    ]
    mock_db_session.execute = AsyncMock(return_value=_list_result(rows))

    response = await authed_client.get("/analytics/spend-by-user")

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["end_user_id"] == "user-alpha"
    assert data["items"][0]["cost_usd"] == "1.50"
    assert data["items"][0]["avg_cost_per_run"] == "0.05"
    assert data["items"][1]["last_active"] is None


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


# ── /analytics/summary delta ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_delta_computed(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """cost_delta_pct is computed from current vs prior period."""
    mock_db_session.execute = AsyncMock(
        side_effect=_summary_side_effect(
            _calls_row("0.10", 5000, 1000, 10, 20),
            _calls_row("0.05", 2500, 500, 5, 10),
            _runs_row(),
        )
    )

    response = await authed_client.get("/analytics/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["prev_cost_usd"] == "0.05"
    # delta = (0.10 - 0.05) / 0.05 * 100 = 100
    assert float(data["cost_delta_pct"]) == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_summary_delta_none_when_prev_zero(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """cost_delta_pct is None when prior period cost is zero."""
    mock_db_session.execute = AsyncMock(
        side_effect=_summary_side_effect(
            _calls_row("0.10", 5000, 1000, 10, 20), _calls_row("0", 0, 0, 0, 0), _runs_row()
        )
    )

    response = await authed_client.get("/analytics/summary")

    assert response.status_code == 200
    assert response.json()["cost_delta_pct"] is None


# ── /analytics/users/{end_user_id} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_spend_detail(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    summary_row = _make_row(
        cost_usd=Decimal("1.50"),
        run_count=10,
        call_count=40,
        last_active=datetime(2026, 1, 20, 9, 0, tzinfo=UTC),
    )
    summary_result = MagicMock()
    summary_result.one = MagicMock(return_value=summary_row)

    time_result = _list_result([])
    model_result = _list_result(
        [
            _make_row(
                provider="openai",
                model="gpt-4o",
                cost_usd=Decimal("1.50"),
                input_tokens=5000,
                output_tokens=1000,
                call_count=40,
            )
        ]
    )
    feature_result = _list_result([])

    mock_db_session.execute = AsyncMock(
        side_effect=[summary_result, time_result, model_result, feature_result]
    )

    response = await authed_client.get("/analytics/users/user-alpha")

    assert response.status_code == 200
    data = response.json()
    assert data["end_user_id"] == "user-alpha"
    assert data["cost_usd"] == "1.50"
    assert data["avg_cost_per_run"] == "0.15"
    assert data["models_used"][0]["model"] == "gpt-4o"
    assert data["spend_over_time"] == []
    assert data["features_used"] == []


# ── Auth enforcement ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated requests should be rejected."""
    response = await client.get("/analytics/summary")
    assert response.status_code == 401
