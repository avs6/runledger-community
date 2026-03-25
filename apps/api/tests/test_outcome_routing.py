"""
Tests for outcome-aware routing strategy and recommendation endpoint.

Covers:
  services/routing._outcome_optimized()
  services/routing.get_outcome_stats_by_model()
  GET /gateway/recommendations/{alias}
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_route(alias="llm", model="gpt-4o", priority=10, **kwargs):
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        alias=alias,
        provider="openai",
        target_model=model,
        priority=priority,
        is_active=True,
        per_user_rpm_limit=None,
        pii_redaction_enabled=False,
        daily_cost_limit_usd=None,
        monthly_cost_limit_usd=None,
        health_auto_disable=True,
        last_health_check_at=None,
        consecutive_health_failures=0,
        disabled_reason=None,
        base_url=None,
        api_key_env_var="OPENAI_API_KEY",
        config=None,
        created_at="2026-01-01T00:00:00Z",
        **kwargs,
    )


def _scalar_result(rows):
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _scalars_all_result(rows):
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars)
    return m


def _scalar_one_result(value):
    m = MagicMock()
    m.scalar_one = MagicMock(return_value=value)
    return m


# ── get_outcome_stats_by_model ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_outcome_stats_empty_models():
    """Returns empty dict immediately when models list is empty."""
    from runledger_api.services.routing import get_outcome_stats_by_model

    db = AsyncMock()
    result = await get_outcome_stats_by_model(db, uuid.uuid4(), [])
    assert result == {}
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_outcome_stats_returns_per_model_data():
    from runledger_api.services.routing import get_outcome_stats_by_model

    ws = uuid.uuid4()
    row = SimpleNamespace(
        model="gpt-4o-mini",
        sample_count=50,
        success_rate=0.86,
        cost_per_success=0.0018,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result([row]))

    stats = await get_outcome_stats_by_model(db, ws, ["gpt-4o", "gpt-4o-mini"])
    assert "gpt-4o-mini" in stats
    assert stats["gpt-4o-mini"]["sample_count"] == 50
    assert abs(stats["gpt-4o-mini"]["success_rate"] - 0.86) < 0.001
    assert abs(stats["gpt-4o-mini"]["cost_per_success"] - 0.0018) < 0.00001


@pytest.mark.asyncio
async def test_get_outcome_stats_null_cost_per_success():
    """cost_per_success=None when there are 0 successes."""
    from runledger_api.services.routing import get_outcome_stats_by_model

    row = SimpleNamespace(
        model="gpt-4o",
        sample_count=10,
        success_rate=0.0,
        cost_per_success=None,
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result([row]))

    stats = await get_outcome_stats_by_model(db, uuid.uuid4(), ["gpt-4o"])
    assert stats["gpt-4o"]["cost_per_success"] is None


# ── _outcome_optimized strategy ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_outcome_optimized_picks_lowest_cost_per_success():
    from runledger_api.services.routing import _outcome_optimized

    route_a = _make_route(alias="llm", model="gpt-4o", priority=10)
    route_b = _make_route(alias="llm", model="gpt-4o-mini", priority=20)
    routes = [route_a, route_b]

    stats = {
        "gpt-4o": {"sample_count": 80, "success_rate": 0.90, "cost_per_success": 0.0030},
        "gpt-4o-mini": {"sample_count": 70, "success_rate": 0.85, "cost_per_success": 0.0018},
    }

    db = AsyncMock()
    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value=stats),
    ):
        route, reason = await _outcome_optimized(db, uuid.uuid4(), routes, {})

    assert route.target_model == "gpt-4o-mini"
    assert "cost-per-success" in reason
    assert "gpt-4o-mini" in reason


@pytest.mark.asyncio
async def test_outcome_optimized_fallback_no_data():
    from runledger_api.services.routing import _outcome_optimized

    route_a = _make_route(alias="llm", model="gpt-4o", priority=10)
    routes = [route_a]

    db = AsyncMock()
    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value={}),
    ):
        route, reason = await _outcome_optimized(db, uuid.uuid4(), routes, {})

    assert route.target_model == "gpt-4o"
    assert "no-data-fallback" in reason


@pytest.mark.asyncio
async def test_outcome_optimized_deprioritizes_no_data_model():
    """Models without outcome data fall back behind models that have data."""
    from runledger_api.services.routing import _outcome_optimized

    route_a = _make_route(alias="llm", model="gpt-4o", priority=10)
    route_b = _make_route(alias="llm", model="gpt-4o-mini", priority=20)
    routes = [route_a, route_b]

    # Only gpt-4o-mini has data
    stats = {
        "gpt-4o-mini": {"sample_count": 30, "success_rate": 0.80, "cost_per_success": 0.002},
    }

    db = AsyncMock()
    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value=stats),
    ):
        route, reason = await _outcome_optimized(db, uuid.uuid4(), routes, {})

    assert route.target_model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_outcome_optimized_routes_through_select_route_with_policy(mock_workspace):
    """outcome_optimized is dispatched correctly through the main entry point."""
    from runledger_api.services.routing import select_route_with_policy

    ws_id = uuid.uuid4()
    route_a = _make_route(alias="llm", model="gpt-4o", priority=10)
    route_a.workspace_id = ws_id
    route_b = _make_route(alias="llm", model="gpt-4o-mini", priority=20)
    route_b.workspace_id = ws_id

    policy = SimpleNamespace(
        policy_type="outcome_optimized",
        config={"lookback_days": 14, "min_sample_size": 5},
    )

    stats = {
        "gpt-4o": {"sample_count": 20, "success_rate": 0.90, "cost_per_success": 0.003},
        "gpt-4o-mini": {"sample_count": 15, "success_rate": 0.85, "cost_per_success": 0.0015},
    }

    db = AsyncMock()
    with (
        patch(
            "runledger_api.services.routing._fetch_active_routes",
            new=AsyncMock(return_value=[route_a, route_b]),
        ),
        patch(
            "runledger_api.services.routing._fetch_policy",
            new=AsyncMock(return_value=policy),
        ),
        patch(
            "runledger_api.services.routing.get_outcome_stats_by_model",
            new=AsyncMock(return_value=stats),
        ),
    ):
        route, reason = await select_route_with_policy(db, ws_id, "llm", [])

    assert route.target_model == "gpt-4o-mini"
    assert "outcome_optimized" in reason


# ── GET /gateway/recommendations/{alias} ──────────────────────────────────────


@pytest.mark.asyncio
async def test_get_recommendation_no_routes(authed_client, mock_db_session):
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[])
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/gateway/recommendations/unknown-alias")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_recommendation_no_outcome_data(authed_client, mock_db_session, mock_workspace):
    route = _make_route(alias="llm", model="gpt-4o")
    route.workspace_id = mock_workspace.id

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[route])
    routes_result = MagicMock()
    routes_result.scalars = MagicMock(return_value=scalars)
    mock_db_session.execute = AsyncMock(return_value=routes_result)

    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value={}),
    ):
        resp = await authed_client.get("/gateway/recommendations/llm")

    assert resp.status_code == 200
    data = resp.json()
    assert data["alias"] == "llm"
    assert data["total_outcomes_sampled"] == 0
    assert data["best_model"] is None
    assert "No outcome data" in data["message"]


@pytest.mark.asyncio
async def test_get_recommendation_with_data(authed_client, mock_db_session, mock_workspace):
    route_a = _make_route(alias="llm", model="gpt-4o", priority=10)
    route_b = _make_route(alias="llm", model="gpt-4o-mini", priority=20)
    route_a.workspace_id = mock_workspace.id
    route_b.workspace_id = mock_workspace.id

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[route_a, route_b])
    routes_result = MagicMock()
    routes_result.scalars = MagicMock(return_value=scalars)
    mock_db_session.execute = AsyncMock(return_value=routes_result)

    stats = {
        "gpt-4o": {"sample_count": 100, "success_rate": 0.90, "cost_per_success": 0.0030},
        "gpt-4o-mini": {"sample_count": 80, "success_rate": 0.85, "cost_per_success": 0.0018},
    }

    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value=stats),
    ):
        resp = await authed_client.get("/gateway/recommendations/llm")

    assert resp.status_code == 200
    data = resp.json()
    assert data["alias"] == "llm"
    assert data["best_model"] == "gpt-4o-mini"
    assert data["total_outcomes_sampled"] == 180
    assert len(data["models"]) == 2
    # Best model should be first (sorted by cost_per_success asc)
    assert data["models"][0]["model"] == "gpt-4o-mini"
    assert data["models"][0]["cost_per_success"] == pytest.approx(0.0018, abs=1e-6)
    # improvement_vs_current: (0.003 - 0.0018) / 0.003 ≈ 0.40
    assert data["models"][0]["improvement_vs_current"] == pytest.approx(0.40, abs=0.01)
    assert "40.0%" in data["message"] or "40" in data["message"]


@pytest.mark.asyncio
async def test_get_recommendation_message_mentions_models(
    authed_client, mock_db_session, mock_workspace
):
    route_a = _make_route(alias="chat", model="gpt-4o", priority=10)
    route_b = _make_route(alias="chat", model="claude-sonnet-4-6", priority=20)
    route_a.workspace_id = mock_workspace.id
    route_b.workspace_id = mock_workspace.id

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[route_a, route_b])
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    mock_db_session.execute = AsyncMock(return_value=result)

    stats = {
        "gpt-4o": {"sample_count": 50, "success_rate": 0.88, "cost_per_success": 0.0025},
        "claude-sonnet-4-6": {"sample_count": 40, "success_rate": 0.92, "cost_per_success": 0.0020},
    }

    with patch(
        "runledger_api.services.routing.get_outcome_stats_by_model",
        new=AsyncMock(return_value=stats),
    ):
        resp = await authed_client.get("/gateway/recommendations/chat")

    data = resp.json()
    assert data["best_model"] == "claude-sonnet-4-6"
    # Message should mention both models and the improvement
    assert "claude-sonnet-4-6" in data["message"]
    assert "gpt-4o" in data["message"]


@pytest.mark.asyncio
async def test_get_recommendation_workflow_type_param(
    authed_client, mock_db_session, mock_workspace
):
    """workflow_type query param is forwarded to get_outcome_stats_by_model."""
    route = _make_route(alias="llm", model="gpt-4o")
    route.workspace_id = mock_workspace.id

    scalars = MagicMock()
    scalars.all = MagicMock(return_value=[route])
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars)
    mock_db_session.execute = AsyncMock(return_value=result)

    mock_stats = AsyncMock(return_value={})
    with patch("runledger_api.services.routing.get_outcome_stats_by_model", new=mock_stats):
        resp = await authed_client.get(
            "/gateway/recommendations/llm?workflow_type=conversion&window_days=14"
        )

    assert resp.status_code == 200
    # Verify the helper was called with the right params
    call_kwargs = mock_stats.call_args.kwargs
    assert call_kwargs["workflow_type"] == "conversion"
    assert call_kwargs["lookback_days"] == 14
