"""
Tests for budget CRUD, hot-path check, service functions, and Celery workers.

Uses the authed_client / mock_db_session / mock_redis_client fixtures from conftest.
No live database or Redis required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from runledger_api.services.budgets import (
    _matching_budgets,
    _period_key,
    get_budget_spend,
    incr_budget_spend,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_budget_row(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        scope_type="workspace",
        scope_id=None,
        period_type="daily",
        limit_usd=Decimal("10.00"),
        action="block",
        downgrade_to_model=None,
        is_active=True,
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


# ── _period_key ────────────────────────────────────────────────────────────────


def test_period_key_daily() -> None:
    dt = datetime(2026, 2, 27, 12, 0, tzinfo=UTC)
    assert _period_key("daily", dt) == "2026-02-27"


def test_period_key_monthly() -> None:
    dt = datetime(2026, 2, 27, 12, 0, tzinfo=UTC)
    assert _period_key("monthly", dt) == "2026-02"


def test_period_key_total() -> None:
    dt = datetime(2026, 2, 27, 12, 0, tzinfo=UTC)
    assert _period_key("total", dt) == "total"


# ── _matching_budgets ─────────────────────────────────────────────────────────


def test_matching_budgets_workspace_scope() -> None:
    """Workspace budget always matches regardless of end_user_id / feature_tag."""
    budgets = [
        {"scope_type": "workspace", "scope_id": None, "limit_usd": "10"},
    ]
    result = _matching_budgets(budgets, end_user_id="u_123", feature_tag="chat")
    assert len(result) == 1


def test_matching_budgets_end_user_scope() -> None:
    """end_user budget matches only the specific user."""
    budgets = [
        {"scope_type": "end_user", "scope_id": "u_123", "limit_usd": "5"},
        {"scope_type": "end_user", "scope_id": "u_999", "limit_usd": "5"},
    ]
    result = _matching_budgets(budgets, end_user_id="u_123", feature_tag=None)
    assert len(result) == 1
    assert result[0]["scope_id"] == "u_123"


def test_matching_budgets_feature_tag_scope() -> None:
    budgets = [
        {"scope_type": "feature_tag", "scope_id": "support-chat", "limit_usd": "5"},
        {"scope_type": "feature_tag", "scope_id": "other-feature", "limit_usd": "5"},
    ]
    result = _matching_budgets(budgets, end_user_id=None, feature_tag="support-chat")
    assert len(result) == 1


# ── incr_budget_spend ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_incr_budget_spend() -> None:
    """INCRBYFLOAT is called with the correct key and value."""
    redis = AsyncMock()
    redis.incrbyfloat = AsyncMock()
    redis.expire = AsyncMock()

    budget_id = uuid.uuid4()
    await incr_budget_spend(redis, budget_id, "daily", Decimal("0.05"))

    redis.incrbyfloat.assert_called_once()
    call_args = redis.incrbyfloat.call_args
    assert str(budget_id) in call_args[0][0]  # key contains budget_id
    assert call_args[0][1] == pytest.approx(0.05)


# ── get_budget_spend ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_budget_spend_returns_zero_when_missing() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    budget_id = uuid.uuid4()
    spend = await get_budget_spend(redis, budget_id, "daily")
    assert spend == Decimal(0)


@pytest.mark.asyncio
async def test_get_budget_spend_returns_value() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="0.123456")
    budget_id = uuid.uuid4()
    spend = await get_budget_spend(redis, budget_id, "daily")
    assert spend == Decimal("0.123456")


# ── POST /budgets ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_budget(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    budget_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def mock_refresh(obj: object) -> None:
        obj.id = budget_id  # type: ignore[attr-defined]
        obj.created_at = created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh
    mock_redis_client.delete = AsyncMock()

    response = await authed_client.post(
        "/budgets",
        json={
            "scope_type": "end_user",
            "scope_id": "u_test",
            "period_type": "daily",
            "limit_usd": "0.10",
            "action": "block",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["scope_type"] == "end_user"
    assert data["scope_id"] == "u_test"
    assert data["period_type"] == "daily"
    assert data["action"] == "block"
    assert data["current_spend_usd"] == "0"
    assert data["pct_used"] == "0"


# ── GET /budgets ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_budgets_includes_spend(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    budget = _make_budget_row(
        scope_type="workspace",
        period_type="daily",
        limit_usd=Decimal("10.00"),
        action="notify",
    )
    mock_db_session.execute = AsyncMock(return_value=_list_result([budget]))
    mock_redis_client.get = AsyncMock(return_value="2.50")

    response = await authed_client.get("/budgets")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["current_spend_usd"] == "2.50"
    assert float(item["pct_used"]) == pytest.approx(25.0)


# ── GET /budgets/check ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_budget_check_allowed(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    """Spend below limit → allowed=true."""
    mock_redis_client.get = AsyncMock(return_value=None)  # cache miss + spend = 0

    with patch(
        "runledger_api.services.budgets.get_workspace_budgets_cached",
        new=AsyncMock(return_value=[]),
    ):
        response = await authed_client.get("/budgets/check?end_user_id=u_test")

    assert response.status_code == 200
    assert response.json()["allowed"] is True


@pytest.mark.asyncio
async def test_budget_check_blocked(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    """Spend at/above limit with action=block → allowed=false."""
    budget_id = str(uuid.uuid4())
    budgets = [
        {
            "id": budget_id,
            "scope_type": "end_user",
            "scope_id": "u_test",
            "period_type": "daily",
            "limit_usd": "0.10",
            "action": "block",
            "downgrade_to_model": None,
        }
    ]

    with (
        patch(
            "runledger_api.services.budgets.get_workspace_budgets_cached",
            new=AsyncMock(return_value=budgets),
        ),
        patch(
            "runledger_api.services.budgets.get_budget_spend",
            new=AsyncMock(return_value=Decimal("0.12")),
        ),
    ):
        response = await authed_client.get("/budgets/check?end_user_id=u_test")

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert data["action"] == "block"
    assert data["budget_id"] == budget_id


@pytest.mark.asyncio
async def test_budget_check_downgrade(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    """action=downgrade returns downgrade_model."""
    budget_id = str(uuid.uuid4())
    budgets = [
        {
            "id": budget_id,
            "scope_type": "workspace",
            "scope_id": None,
            "period_type": "monthly",
            "limit_usd": "100.00",
            "action": "downgrade",
            "downgrade_to_model": "gpt-4o-mini",
        }
    ]

    with (
        patch(
            "runledger_api.services.budgets.get_workspace_budgets_cached",
            new=AsyncMock(return_value=budgets),
        ),
        patch(
            "runledger_api.services.budgets.get_budget_spend",
            new=AsyncMock(return_value=Decimal("150.00")),
        ),
    ):
        response = await authed_client.get("/budgets/check")

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    assert data["action"] == "downgrade"
    assert data["downgrade_model"] == "gpt-4o-mini"


# ── DELETE /budgets/{id} ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_budget_deactivates(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_redis_client: AsyncMock,
) -> None:
    budget = _make_budget_row()
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(budget))
    mock_redis_client.delete = AsyncMock()

    response = await authed_client.delete(f"/budgets/{budget.id}")

    assert response.status_code == 204


# ── GET /budgets/{id}/breaches ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_breach_history_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    budget = _make_budget_row()
    # First call: verify budget ownership; second: list breaches
    mock_db_session.execute = AsyncMock(side_effect=[_scalar_result(budget), _list_result([])])

    response = await authed_client.get(f"/budgets/{budget.id}/breaches")

    assert response.status_code == 200
    assert response.json()["items"] == []


# ── Runaway protection ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_runaway_protection_retry_storm() -> None:
    """Runs with >20 calls in 2 min are cancelled."""
    from runledger_api.workers.budgets import _run_runaway_protection

    run_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        status="running",
        started_at=datetime.now(UTC),
    )

    session = AsyncMock()
    session.add = MagicMock()

    # Sequence: active_runs list, call_count=25, spike_count=0, notifications list
    active_runs_result = MagicMock()
    active_runs_result.scalars = MagicMock(
        return_value=MagicMock(__iter__=MagicMock(return_value=iter([run])))
    )

    call_count_result = MagicMock()
    call_count_result.scalar_one = MagicMock(return_value=25)

    spike_count_result = MagicMock()
    spike_count_result.scalar_one = MagicMock(return_value=0)

    notif_result = MagicMock()
    notif_result.scalars = MagicMock(
        return_value=MagicMock(__iter__=MagicMock(return_value=iter([])))
    )

    update_result = MagicMock()  # result of update(AgentRun).values(status='cancelled')

    session.execute = AsyncMock(
        side_effect=[
            active_runs_result,  # select active runs
            call_count_result,  # count calls in last 2 min
            spike_count_result,  # count token spike calls
            update_result,  # update run status='cancelled'
            notif_result,  # select notifications
        ]
    )
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    # factory is a sync callable that returns the async context manager (session)
    factory_mock = MagicMock(return_value=session)

    redis = AsyncMock()
    redis.aclose = AsyncMock()

    with (
        patch(
            "runledger_api.workers.budgets._make_session_factory",
            return_value=factory_mock,
        ),
        patch(
            "runledger_api.workers.budgets._make_redis",
            return_value=redis,
        ),
    ):
        result = await _run_runaway_protection()

    assert result["cancelled"] == 1


# ── send_notification_webhook ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_notification_webhook() -> None:
    """send_notification makes an HTTP POST with HMAC signature header."""
    from runledger_api.services.budgets import send_notification

    notification = SimpleNamespace(
        id=uuid.uuid4(),
        channel="webhook",
        destination_url="https://example.com/hook",
        events=["budget.breach"],
    )
    payload = {"event": "budget.breach", "budget_id": "abc123"}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("runledger_api.services.budgets.httpx.AsyncClient", return_value=mock_client):
        await send_notification(notification, payload)  # type: ignore[arg-type]

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    headers = call_kwargs[1].get("headers") or call_kwargs.kwargs.get("headers", {})
    assert "X-RunLedger-Signature" in headers
    assert headers["X-RunLedger-Signature"].startswith("sha256=")


# ── Auth enforcement ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_budgets_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/budgets")
    assert response.status_code == 401
