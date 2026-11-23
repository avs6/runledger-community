"""
Scoped budget enforcement and spend counting.

Covers the single spend write path (``record_budget_spend``), scope resolution
(access groups, provider profiles), the gateway preflight enforcement
(block / downgrade / throttle / provider-profile), and the metering + ingest
callers. No live database or Redis required.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from runledger_api.services import budgets as budgets_svc
from runledger_api.services.budgets import (
    BudgetScope,
    _matching_budgets,
    build_budget_scope,
    check_provider_profile_budgets,
    check_request_budgets,
    get_budget_spend,
    record_budget_spend,
)

from tests.budget_fakes import FakeRedis, spend_store

WS = uuid.uuid4()


_FakeRedis = FakeRedis


@pytest.fixture(autouse=True)
def _store() -> Any:
    """Durable spend in memory; no budget tier for the request checks."""
    with (
        spend_store() as store,
        patch(
            "runledger_api.services.gateway_controls.key_tier_breach",
            AsyncMock(return_value=None),
        ),
    ):
        yield store


def _budget(
    scope_type: str = "workspace",
    scope_id: str | None = None,
    limit: str = "10",
    action: str = "block",
    period: str = "monthly",
    downgrade: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "workspace_id": str(WS),
        "scope_type": scope_type,
        "scope_id": scope_id,
        "period_type": period,
        "limit_usd": limit,
        "action": action,
        "downgrade_to_model": downgrade,
    }


def _patch_budgets(budgets: list[dict[str, Any]]) -> Any:
    return patch.object(
        budgets_svc, "get_workspace_budgets_cached", AsyncMock(return_value=budgets)
    )


# ── Scope matching ────────────────────────────────────────────────────────────


def test_matching_budgets_access_group_ids() -> None:
    g1, g2 = str(uuid.uuid4()), str(uuid.uuid4())
    budgets = [_budget("access_group", g1), _budget("access_group", g2), _budget()]
    matched = _matching_budgets(budgets, access_group_ids=(g2,))
    assert {b["scope_id"] for b in matched} == {g2, None}


def test_matching_budgets_keyword_only_call_no_longer_raises() -> None:
    """Regression: metering called this with two keyword args and got a TypeError."""
    budgets = [_budget("end_user", "u1"), _budget("feature_tag", "chat")]
    matched = _matching_budgets(budgets, end_user_id="u1", feature_tag="chat")
    assert len(matched) == 2


# ── Scope resolution ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_budget_scope_skips_lookups_without_scoped_budgets() -> None:
    db = AsyncMock()
    with (
        patch.object(budgets_svc, "resolve_access_group_ids", AsyncMock()) as groups,
        patch.object(budgets_svc, "resolve_provider_profile_id", AsyncMock()) as profile,
    ):
        scope = await build_budget_scope(
            db, [_budget()], workspace_id=WS, end_user_id="u1", feature_tag="chat"
        )
    groups.assert_not_awaited()
    profile.assert_not_awaited()
    assert scope == BudgetScope(end_user_id="u1", feature_tag="chat")


@pytest.mark.asyncio
async def test_build_budget_scope_resolves_groups_from_principal() -> None:
    user_id, group_id = uuid.uuid4(), str(uuid.uuid4())
    with patch.object(
        budgets_svc, "resolve_access_group_ids", AsyncMock(return_value=(group_id,))
    ) as groups:
        scope = await build_budget_scope(
            AsyncMock(),
            [_budget("access_group", group_id)],
            workspace_id=WS,
            principal_user_id=user_id,
        )
    groups.assert_awaited_once()
    assert scope.access_group_ids == (group_id,)


@pytest.mark.asyncio
async def test_build_budget_scope_maps_end_user_to_member() -> None:
    """Without a principal, the end_user_id / key owner is mapped to a workspace user."""
    user_id, group_id = uuid.uuid4(), str(uuid.uuid4())
    db = AsyncMock()
    db.get = AsyncMock(return_value=SimpleNamespace(id=WS))
    with (
        patch(
            "runledger_api.services.sessions.resolve_principal_user_id",
            AsyncMock(return_value=user_id),
        ) as principal,
        patch.object(
            budgets_svc, "resolve_access_group_ids", AsyncMock(return_value=(group_id,))
        ) as groups,
    ):
        scope = await build_budget_scope(
            db,
            [_budget("access_group", group_id)],
            workspace_id=WS,
            end_user_id="alice@example.com",
        )
    principal.assert_awaited_once()
    assert groups.await_args.args[2] == user_id
    assert scope.access_group_ids == (group_id,)


# ── record_budget_spend ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_spend_counts_matching_budgets_once_per_call() -> None:
    redis = _FakeRedis()
    ws_budget = _budget(limit="100")
    user_budget = _budget("end_user", "u1", limit="100")
    other_user = _budget("end_user", "u2", limit="100")
    pc_id = uuid.uuid4()
    with _patch_budgets([ws_budget, user_budget, other_user]):
        n = await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=pc_id,
            cost_usd=Decimal("2.5"),
            end_user_id="u1",
        )
        again = await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=pc_id,
            cost_usd=Decimal("2.5"),
            end_user_id="u1",
        )
    assert n == 2
    assert again == 0  # idempotent per provider call (retries, replay_backfill)
    for b, expected in ((ws_budget, "2.5"), (user_budget, "2.5"), (other_user, "0")):
        spend = await get_budget_spend(redis, uuid.UUID(b["id"]), "monthly")  # type: ignore[arg-type]
        assert spend == Decimal(expected)


@pytest.mark.asyncio
async def test_record_spend_ignores_zero_or_missing_cost() -> None:
    redis = _FakeRedis()
    with _patch_budgets([_budget()]):
        for cost in (None, Decimal(0)):
            assert (
                await record_budget_spend(
                    AsyncMock(),
                    redis,  # type: ignore[arg-type]
                    workspace_id=WS,
                    provider_call_id=uuid.uuid4(),
                    cost_usd=cost,
                )
                == 0
            )
    assert redis.store == {}


@pytest.mark.asyncio
async def test_record_spend_threshold_and_breach_fire_once_per_period() -> None:
    redis = _FakeRedis()
    budget = _budget(limit="10", action="notify")
    with (
        _patch_budgets([budget]),
        patch.object(budgets_svc.kafka_export, "publish_event", AsyncMock()) as publish,
        patch.object(budgets_svc, "fire_breach", AsyncMock()) as breach,
    ):
        for cost in ("8.5", "0.5", "2", "3"):  # 8.5 → 80%, 9.0, 11 → breach, 14
            await record_budget_spend(
                AsyncMock(),
                redis,  # type: ignore[arg-type]
                workspace_id=WS,
                provider_call_id=uuid.uuid4(),
                cost_usd=Decimal(cost),
            )
    thresholds = [
        c for c in publish.await_args_list if c.kwargs["event_type"] == "budget.threshold_crossed"
    ]
    assert len(thresholds) == 1
    breach.assert_awaited_once()
    # notify-only budgets still record the breach (that is what sends the notification)
    assert breach.await_args.args[4] == "notify"
    assert breach.await_args.kwargs == {"commit": False}


@pytest.mark.asyncio
async def test_record_spend_failure_propagates_to_caller_transaction() -> None:
    """A failed write raises, so the caller's transaction (which also holds the
    budget_spend_calls claim) rolls back and a retry counts the call."""
    redis = _FakeRedis()
    with (
        _patch_budgets([_budget()]),
        patch.object(budgets_svc, "_db_add_spend", AsyncMock(side_effect=RuntimeError)),
        pytest.raises(RuntimeError),
    ):
        await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=uuid.uuid4(),
            cost_usd=Decimal("1"),
        )


@pytest.mark.asyncio
async def test_spend_survives_redis_loss(_store: Any) -> None:
    """cd:B-05: losing the Redis cache (eviction / restart) doesn't reset spend."""
    redis = _FakeRedis()
    budget = _budget(limit="5")
    with _patch_budgets([budget]), patch.object(budgets_svc, "fire_breach", AsyncMock()):
        await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=uuid.uuid4(),
            cost_usd=Decimal("6"),
        )
        redis.store.clear()  # everything evicted
        result = await check_request_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            api_key_id=None,
            end_user_id=None,
            feature_tag=None,
        )
    assert result.allowed is False and result.action == "block"
    assert _store.total(budget["id"]) == Decimal(6)


@pytest.mark.asyncio
async def test_model_budget_counts_and_blocks_matching_route(_store: Any) -> None:
    """G-01: a model budget (scope_type=model) accrues spend and blocks the route."""
    redis = _FakeRedis()
    key_id = uuid.uuid4()
    budget = _budget("model", "gpt-4*", limit="1")
    budget["api_key_id"] = str(key_id)
    with _patch_budgets([budget]), patch.object(budgets_svc, "fire_breach", AsyncMock()):
        n = await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=uuid.uuid4(),
            cost_usd=Decimal("2"),
            api_key_id=key_id,
            model="gpt-4o",
        )
        other_key = await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=uuid.uuid4(),
            cost_usd=Decimal("2"),
            api_key_id=uuid.uuid4(),
            model="gpt-4o",
        )
        blocked = await check_provider_profile_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            provider="openai",
            model="gpt-4o-mini",
            api_key_id=key_id,
        )
        other_model = await check_provider_profile_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            provider="anthropic",
            model="claude-sonnet-4",
            api_key_id=key_id,
        )
    assert n == 1 and other_key == 0
    assert blocked.allowed is False and blocked.budget_id == budget["id"]
    assert other_model.allowed is True


@pytest.mark.asyncio
async def test_request_check_blocks_on_key_tier() -> None:
    """cd:B-06: the key's tier spend limit blocks in preflight, with no route caps."""
    with (
        patch(
            "runledger_api.services.gateway_controls.key_tier_breach",
            AsyncMock(return_value="budget_tier:starter"),
        ),
        _patch_budgets([]),
    ):
        result = await check_request_budgets(
            _FakeRedis(),  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            api_key_id=uuid.uuid4(),
            end_user_id=None,
            feature_tag=None,
        )
    assert result.allowed is False and result.reason == "budget_tier:starter"


@pytest.mark.asyncio
async def test_record_spend_counts_access_group_budget_for_member() -> None:
    redis = _FakeRedis()
    group_id = str(uuid.uuid4())
    budget = _budget("access_group", group_id, limit="50")
    with (
        _patch_budgets([budget]),
        patch.object(budgets_svc, "resolve_access_group_ids", AsyncMock(return_value=(group_id,))),
    ):
        n = await record_budget_spend(
            AsyncMock(),
            redis,  # type: ignore[arg-type]
            workspace_id=WS,
            provider_call_id=uuid.uuid4(),
            cost_usd=Decimal("4"),
            principal_user_id=uuid.uuid4(),
        )
    assert n == 1
    assert await get_budget_spend(redis, uuid.UUID(budget["id"]), "monthly") == Decimal(4)  # type: ignore[arg-type]


# ── Request-level checks ──────────────────────────────────────────────────────


async def _exhaust(redis: _FakeRedis, budget: dict[str, Any], amount: str = "999") -> None:
    await budgets_svc._cache_spend(
        redis,  # type: ignore[arg-type]
        uuid.UUID(budget["id"]),
        budgets_svc._period_key(budget["period_type"], datetime.now(UTC)),
        Decimal(amount),
    )


@pytest.mark.asyncio
async def test_check_request_budgets_blocks_exhausted_api_key_budget() -> None:
    redis = _FakeRedis()
    key_id = uuid.uuid4()
    budget = _budget("api_key", str(key_id))
    await _exhaust(redis, budget)
    with _patch_budgets([budget]):
        result = await check_request_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            api_key_id=key_id,
            end_user_id=None,
            feature_tag=None,
        )
        other = await check_request_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            api_key_id=uuid.uuid4(),
            end_user_id=None,
            feature_tag=None,
        )
    assert result.allowed is False and result.action == "block"
    assert result.budget_id == budget["id"]
    assert other.allowed is True


@pytest.mark.asyncio
async def test_check_request_budgets_ignores_provider_profile_budgets() -> None:
    redis = _FakeRedis()
    budget = _budget("provider_profile", str(uuid.uuid4()))
    await _exhaust(redis, budget)
    with _patch_budgets([budget]):
        result = await check_request_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            api_key_id=None,
            end_user_id=None,
            feature_tag=None,
        )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_check_provider_profile_budgets_matches_route_profile() -> None:
    redis = _FakeRedis()
    profile_id = str(uuid.uuid4())
    budget = _budget("provider_profile", profile_id)
    await _exhaust(redis, budget)
    with (
        _patch_budgets([budget]),
        patch.object(
            budgets_svc, "resolve_provider_profile_id", AsyncMock(return_value=profile_id)
        ),
    ):
        blocked = await check_provider_profile_budgets(
            redis,  # type: ignore[arg-type]
            AsyncMock(),
            workspace_id=WS,
            provider="openai",
            model="gpt-4o",
        )
    assert blocked.allowed is False


# ── Gateway preflight enforcement ─────────────────────────────────────────────


def _enforce_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(
        workspace_id=WS,
        api_key_id=None,
        end_user_id="u1",
        feature_tag="support",
        principal_user_id=None,
        route_alias="smart",
        request_tags=[],
        preferred_region=None,
    )
    kwargs.update(overrides)
    return kwargs


def _check(**fields: Any) -> Any:
    from runledger_api.schemas.budgets import BudgetCheckResponse

    return BudgetCheckResponse(**fields)


@pytest.mark.asyncio
async def test_gateway_block_budget_returns_429() -> None:
    from runledger_api.routers import gateway_runtime as gr

    with (
        patch.object(gr, "get_redis", AsyncMock(return_value=_FakeRedis())),
        patch.object(
            gr,
            "check_request_budgets",
            AsyncMock(return_value=_check(allowed=False, action="block", budget_id="b1")),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
    assert exc.value.status_code == 429
    assert exc.value.headers is not None
    assert exc.value.headers["X-Budget-Id"] == "b1"
    assert exc.value.headers["X-Cost-Cap-Reason"] == "budget_exceeded"


@pytest.mark.asyncio
async def test_gateway_downgrade_budget_reroutes_alias() -> None:
    from runledger_api.routers import gateway_runtime as gr

    with (
        patch.object(gr, "get_redis", AsyncMock(return_value=_FakeRedis())),
        patch.object(
            gr,
            "check_request_budgets",
            AsyncMock(
                return_value=_check(
                    allowed=False, action="downgrade", budget_id="b2", downgrade_model="cheap"
                )
            ),
        ),
        patch.object(gr, "_route_alias_for_model", AsyncMock(return_value="cheap")),
    ):
        alias, note = await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
    assert alias == "cheap"
    assert note == "budget_downgrade:b2"


@pytest.mark.asyncio
async def test_gateway_downgrade_without_route_blocks() -> None:
    from runledger_api.routers import gateway_runtime as gr

    with (
        patch.object(gr, "get_redis", AsyncMock(return_value=_FakeRedis())),
        patch.object(
            gr,
            "check_request_budgets",
            AsyncMock(
                return_value=_check(
                    allowed=False, action="downgrade", budget_id="b2", downgrade_model="missing"
                )
            ),
        ),
        patch.object(gr, "_route_alias_for_model", AsyncMock(return_value=None)),
        pytest.raises(HTTPException) as exc,
    ):
        await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_gateway_throttle_budget_admits_up_to_rpm_then_429() -> None:
    from runledger_api.routers import gateway_runtime as gr

    redis = _FakeRedis()
    throttled = _check(allowed=True, action="throttle", budget_id="b3", throttled=True)
    with (
        patch.object(gr, "get_redis", AsyncMock(return_value=redis)),
        patch.object(gr, "check_request_budgets", AsyncMock(return_value=throttled)),
        patch.object(gr.settings, "budget_throttle_rpm", 2),
    ):
        for _ in range(2):
            alias, note = await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
            assert alias == "smart" and note == "budget_throttle:b3"
        with pytest.raises(HTTPException) as exc:
            await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
    assert exc.value.status_code == 429
    assert exc.value.headers is not None and exc.value.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_gateway_budget_check_fails_open_when_redis_down() -> None:
    from runledger_api.routers import gateway_runtime as gr

    with (
        patch.object(gr, "get_redis", AsyncMock(return_value=_FakeRedis())),
        patch.object(gr, "check_request_budgets", AsyncMock(side_effect=ConnectionError)),
    ):
        alias, note = await gr._enforce_request_budgets(AsyncMock(), **_enforce_kwargs())
    assert (alias, note) == ("smart", None)


def test_feature_tag_from_metadata_and_tags() -> None:
    from runledger_api.routers.gateway_runtime import _feature_tag_from

    assert _feature_tag_from({"workflow": "triage"}, ["x"]) == "triage"
    assert _feature_tag_from({}, ["billing", "y"]) == "billing"
    assert _feature_tag_from({}, []) is None


# ── Callers: metering + ingest ────────────────────────────────────────────────


@asynccontextmanager
async def _nested() -> Any:
    yield


@pytest.mark.asyncio
async def test_metering_enrichment_counts_priced_call_against_budgets() -> None:
    """Regression: the enrichment worker used to crash (silently) before counting."""
    from runledger_api.workers import metering

    run_id, key_id = uuid.uuid4(), uuid.uuid4()
    pc = SimpleNamespace(
        id=uuid.uuid4(),
        run_id=run_id,
        workspace_id=WS,
        api_key_id=None,
        end_user_id=None,
        provider="openai",
        model="gpt-4o",
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        span_id=None,
    )
    run = SimpleNamespace(
        api_key_id=key_id, end_user_id="u9", feature_tag="support", application_id=None
    )
    select_result = MagicMock()
    select_result.scalars = MagicMock(return_value=[pc])
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[select_result, MagicMock()])
    session.get = AsyncMock(return_value=run)
    session.begin_nested = MagicMock(return_value=_nested())

    @asynccontextmanager
    async def _session_cm() -> Any:
        yield session

    fake_redis = AsyncMock()
    with (
        patch.object(metering, "_make_session_factory", return_value=_session_cm),
        patch("redis.asyncio.Redis.from_url", return_value=fake_redis),
        patch.object(metering, "_provider_call_cost", AsyncMock(return_value=Decimal("0.42"))),
        patch.object(metering, "_rollup_span_and_run_costs", AsyncMock()),
        patch.object(metering, "record_budget_spend", AsyncMock(return_value=1)) as record,
    ):
        result = await metering._run_cost_enrichment()

    assert result == {"enriched": 1}
    record.assert_awaited_once()
    kwargs = record.await_args.kwargs
    assert kwargs["provider_call_id"] == pc.id
    assert kwargs["cost_usd"] == Decimal("0.42")
    assert kwargs["api_key_id"] == key_id  # falls back to the run's key
    assert kwargs["end_user_id"] == "u9"
    assert kwargs["feature_tag"] == "support"
    assert kwargs["model"] == "gpt-4o"
    # Spend lands in the period of the call, not of the enrichment run (B-07).
    assert kwargs["occurred_at"] == pc.created_at


@pytest.mark.asyncio
async def test_pipeline_collects_priced_provider_calls() -> None:
    from runledger_api.workers.pipeline import _handle_provider_call

    session = AsyncMock()
    run_id = str(uuid.uuid4())
    priced: list[dict[str, Any]] = []
    base = {
        "run_id": run_id,
        "provider": "anthropic",
        "model": "claude-x",
        "status": "success",
        "end_user_id": "u1",
    }
    await _handle_provider_call(session, str(WS), {**base, "cost_usd": "0.10"}, priced)
    await _handle_provider_call(session, str(WS), {**base, "span_id": None}, priced)  # no cost
    await _handle_provider_call(
        session, str(WS), {**base, "cost_usd": "0.10", "status": "error"}, priced
    )
    assert len(priced) == 1
    assert priced[0]["cost_usd"] == Decimal("0.10")
    assert priced[0]["end_user_id"] == "u1"
