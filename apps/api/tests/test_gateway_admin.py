"""Gateway admin (stream W1-C): role matrix, audit, invariants, tiers, flywheel, partners."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from runledger_api.core import deps, role_matrix
from runledger_api.routers import gateway_routing
from runledger_api.schemas.gateway import GatewayRouteUpdate, RoutingPolicyUpdate
from runledger_api.services import budget_tier_enforcement as bte
from runledger_api.services import flywheel as flywheel_svc
from runledger_api.services.admin_audit import actor_of, changed_only, snapshot

# ── Role matrix (G-17) ──────────────────────────────────────────────────────────


def test_role_matrix_maps_to_shared_dependencies() -> None:
    assert role_matrix.gateway_role("routes", "write") is deps.require_org_admin
    assert role_matrix.gateway_role("routes", "read") is deps.require_workspace_admin
    assert role_matrix.gateway_role("flywheel", "apply") is deps.require_org_admin
    assert role_matrix.gateway_role("budget_tiers", "write") is deps.require_workspace_admin
    assert role_matrix.gateway_role("pricing", "global") is deps.require_platform_admin


def test_capabilities_follow_levels() -> None:
    ws_admin = role_matrix.capabilities("workspace_admin")
    assert ws_admin["budget_tiers"]["write"] is True
    assert ws_admin["routes"]["write"] is False
    assert ws_admin["flywheel"]["apply"] is False
    org = role_matrix.capabilities("org_admin")
    assert org["flywheel"]["apply"] is True
    assert org["pricing"]["global"] is False
    workload = role_matrix.capabilities("workload")
    assert workload["guardrails"]["read"] is True
    assert workload["guardrails"]["write"] is False


# ── Audit helpers (G-10) ────────────────────────────────────────────────────────


def test_snapshot_masks_credentials_and_serializes() -> None:
    obj = SimpleNamespace(
        credentials={"api_key": "sk-secret", "region": "us"},
        price=Decimal("1.50"),
        when=datetime(2026, 1, 1, tzinfo=UTC),
        rid=uuid.UUID(int=1),
    )
    snap = snapshot(obj, ("credentials", "price", "when", "rid"))
    assert snap["credentials"] == ["api_key", "region"]
    assert "sk-secret" not in str(snap)
    assert snap["price"] == "1.50"
    assert snap["rid"] == str(uuid.UUID(int=1))


def test_changed_only_and_actor() -> None:
    b, a = changed_only({"x": 1, "y": 2}, {"x": 1, "y": 3})
    assert (b, a) == ({"y": 2}, {"y": 3})
    user_id = uuid.uuid4()
    assert actor_of((object(), SimpleNamespace(id=user_id))) == user_id
    assert actor_of(None) is None


# ── Policy type validator (G-13) ────────────────────────────────────────────────


def test_policy_update_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        RoutingPolicyUpdate(policy_type="random_pick")
    assert RoutingPolicyUpdate(policy_type="canary").policy_type == "canary"


# ── Route update merge (G-16) ───────────────────────────────────────────────────


def _route(**kw: Any) -> SimpleNamespace:
    base = {f: None for f in gateway_routing.ROUTE_FIELDS}
    base.update(
        id=uuid.uuid4(),
        alias="chat",
        provider="openai",
        target_model="gpt-4o",
        priority=10,
        is_active=True,
        fallback_config={"aliases": ["backup"], "fallbacks": [{"alias": "big", "on": ["x"]}]},
        routing_config={"threshold": 0.5, "tiers": {"simple": "mini"}},
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_merge_mode_keeps_untouched_config_keys() -> None:
    route = _route()
    body = GatewayRouteUpdate(
        merge_configs=True,
        fallback_config={"aliases": ["other"]},
        routing_config={"tiers": {"complex": "big"}},
    )
    planned = gateway_routing._planned_route_changes(route, body)  # type: ignore[arg-type]
    assert planned["fallback_config"]["fallbacks"] == [{"alias": "big", "on": ["x"]}]
    assert planned["fallback_config"]["aliases"] == ["other"]
    assert planned["routing_config"] == {
        "threshold": 0.5,
        "tiers": {"simple": "mini", "complex": "big"},
    }


def test_merge_null_removes_key_and_replace_mode_replaces() -> None:
    route = _route()
    merged = gateway_routing._planned_route_changes(  # type: ignore[arg-type]
        route, GatewayRouteUpdate(merge_configs=True, routing_config={"threshold": None})
    )
    assert merged["routing_config"] == {"tiers": {"simple": "mini"}}
    replaced = gateway_routing._planned_route_changes(  # type: ignore[arg-type]
        route, GatewayRouteUpdate(routing_config={"threshold": 0.9})
    )
    assert replaced["routing_config"] == {"threshold": 0.9}


def test_unchanged_fields_are_not_planned() -> None:
    route = _route()
    planned = gateway_routing._planned_route_changes(  # type: ignore[arg-type]
        route, GatewayRouteUpdate(alias="chat", priority=10, target_model="gpt-4o-mini")
    )
    assert planned == {"target_model": "gpt-4o-mini"}


# ── Alias invariant (G-11) and policy ownership (G-12) ──────────────────────────


async def test_route_alias_must_match_its_group() -> None:
    group = SimpleNamespace(id=uuid.uuid4(), alias="chat", workspace_id=uuid.uuid4())
    route = _route(routing_group_id=group.id)
    db = AsyncMock()
    db.get = AsyncMock(return_value=group)
    ws = SimpleNamespace(id=group.workspace_id)
    body = GatewayRouteUpdate(alias="renamed")
    planned = gateway_routing._planned_route_changes(route, body)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as exc:
        await gateway_routing._resolve_route_group(db, ws, route, body, planned)  # type: ignore[arg-type]
    assert exc.value.status_code == 400
    # Leaving the group while renaming is allowed.
    body = GatewayRouteUpdate(alias="renamed", routing_group_id=None)
    assert (
        await gateway_routing._resolve_route_group(db, ws, route, body, planned)  # type: ignore[arg-type]
        is None
    )


def _rows(rows: list[Any]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


async def test_policy_refuses_route_for_another_alias() -> None:
    rid = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_rows([SimpleNamespace(id=rid, alias="other")]))
    with pytest.raises(HTTPException) as exc:
        await gateway_routing._validate_policy_routes(
            db, uuid.uuid4(), "chat", {"weights": {str(rid): 1}}
        )
    assert exc.value.status_code == 422


async def test_policy_refuses_foreign_route() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_rows([]))
    with pytest.raises(HTTPException) as exc:
        await gateway_routing._validate_policy_routes(
            db, uuid.uuid4(), "chat", {"canary_route_id": str(uuid.uuid4())}
        )
    assert exc.value.status_code == 404


async def test_policy_accepts_own_route() -> None:
    rid = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_rows([SimpleNamespace(id=rid, alias="chat")]))
    await gateway_routing._validate_policy_routes(
        db, uuid.uuid4(), "chat", {"variants": [{"route_id": str(rid), "pct": 1}]}
    )


# ── Per-key tier enforcement (G-02) ─────────────────────────────────────────────


def _tier(**kw: Any) -> SimpleNamespace:
    base = dict(
        id=uuid.uuid4(), name="starter", rpm_limit=None, tpm_limit=None, allowed_models=None
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _key() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), budget_tier_id=uuid.uuid4())


async def test_tier_refuses_model_outside_allow_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bte, "resolve_key_tier", AsyncMock(return_value=_tier(allowed_models=["fast"]))
    )
    with pytest.raises(HTTPException) as exc:
        await bte.enforce_key_tier(
            AsyncMock(),
            AsyncMock(),
            workspace_id=uuid.uuid4(),
            api_key=_key(),
            model="smart",
            messages=[],
        )
    assert exc.value.status_code == 403


async def test_tier_rpm_breach_is_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bte, "resolve_key_tier", AsyncMock(return_value=_tier(rpm_limit=2)))
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=[0, 2, 12_000])
    with pytest.raises(HTTPException) as exc:
        await bte.enforce_key_tier(
            AsyncMock(), redis, workspace_id=uuid.uuid4(), api_key=_key(), model="m", messages=[]
        )
    assert exc.value.status_code == 429
    assert exc.value.headers["X-RunLedger-Limit-Reason"] == "tier_rpm"
    assert exc.value.headers["Retry-After"] == "12"


async def test_tier_tpm_counts_estimated_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bte, "resolve_key_tier", AsyncMock(return_value=_tier(tpm_limit=1000)))
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=[1, 300, 0])
    messages = [{"role": "user", "content": "x" * 400}]
    await bte.enforce_key_tier(
        AsyncMock(),
        redis,
        workspace_id=uuid.uuid4(),
        api_key=_key(),
        model="m",
        messages=messages,
        max_tokens=200,
    )
    weight = redis.eval.call_args.args[6]
    assert weight == 100 + 200


async def test_tier_redis_down_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bte, "resolve_key_tier", AsyncMock(return_value=_tier(rpm_limit=1)))
    redis = AsyncMock()
    redis.eval = AsyncMock(side_effect=ConnectionError("down"))
    tier = await bte.enforce_key_tier(
        AsyncMock(), redis, workspace_id=uuid.uuid4(), api_key=_key(), model="m", messages=[]
    )
    assert tier is not None


async def test_keyless_caller_has_no_tier() -> None:
    assert (
        await bte.enforce_key_tier(
            AsyncMock(),
            AsyncMock(),
            workspace_id=uuid.uuid4(),
            api_key=None,
            model="m",
            messages=[],
        )
        is None
    )


# ── Flywheel rollback (G-03) ────────────────────────────────────────────────────


async def test_flywheel_rollback_restores_route_snapshot() -> None:
    ws_id = uuid.uuid4()
    route = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        target_model="cheap",
        semantic_cache_enabled=True,
        context_compiler_enabled=True,
        context_compiler_config={"stages": {"a": True}},
    )
    rec = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        status="applied",
        applied_route_id=route.id,
        rationale="cheaper",
        updated_at=None,
        current_config={
            "_route_snapshot": {
                "target_model": "premium",
                "semantic_cache_enabled": False,
                "context_compiler_enabled": False,
                "context_compiler_config": None,
            }
        },
    )
    db = AsyncMock()
    db.get = AsyncMock(
        side_effect=lambda model, _id: rec if model.__name__ == "FlywheelRecommendation" else route
    )
    out = await flywheel_svc.rollback_recommendation(db, ws_id, rec.id)
    assert out is rec
    assert rec.status == "rolled_back"
    assert route.target_model == "premium"
    assert route.semantic_cache_enabled is False
    assert route.context_compiler_config is None


async def test_flywheel_rollback_refuses_unapplied() -> None:
    rec = SimpleNamespace(workspace_id=uuid.uuid4(), status="pending")
    db = AsyncMock()
    db.get = AsyncMock(return_value=rec)
    assert await flywheel_svc.rollback_recommendation(db, rec.workspace_id, uuid.uuid4()) is None


# ── HTTP: partner credentials (G-06), tier soft delete (G-20), flywheel apply ───


def _scalar(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = []
    return result


async def test_partner_edit_keeps_untouched_credentials(
    authed_client: Any, mock_db_session: AsyncMock, mock_workspace: Any
) -> None:
    now = datetime.now(UTC)
    pg = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        provider="lakera",
        name="p",
        mode="pre_call",
        endpoint_url="https://x",
        credentials={"api_key": "old", "org": "o1"},
        config={},
        timeout_ms=2000,
        fallback_action="allow",
        priority=200,
        status="active",
        last_health_check=None,
        health_status=None,
        total_calls=0,
        total_cost_usd=0.0,
        created_at=now,
        updated_at=now,
    )
    mock_db_session.execute = AsyncMock(return_value=_scalar(pg))
    resp = await authed_client.put(
        f"/guardrails/partners/{pg.id}",
        json={"name": "renamed", "credentials": {"api_key": "", "org": "o2"}},
    )
    assert resp.status_code == 200, resp.text
    assert pg.credentials == {"api_key": "old", "org": "o2"}
    body = resp.json()
    assert body["credential_keys"] == ["api_key", "org"]
    assert "old" not in resp.text


async def test_tier_delete_clears_default(
    authed_client: Any, mock_db_session: AsyncMock, mock_workspace: Any
) -> None:
    tier = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=mock_workspace.id,
        name="t",
        max_spend_usd=None,
        period_type="monthly",
        rpm_limit=10,
        tpm_limit=None,
        allowed_models=None,
        is_default=True,
        is_active=True,
    )
    mock_db_session.execute = AsyncMock(return_value=_scalar(tier))
    resp = await authed_client.delete(f"/budget-tiers/{tier.id}")
    assert resp.status_code == 204
    assert tier.is_active is False
    assert tier.is_default is False
    actions = [c.args[0].action for c in mock_db_session.add.call_args_list]
    assert "budget_tier.deleted" in actions


async def test_flywheel_apply_conflicts_when_not_pending(
    authed_client: Any, mock_db_session: AsyncMock, mock_workspace: Any
) -> None:
    rec = SimpleNamespace(id=uuid.uuid4(), workspace_id=mock_workspace.id, status="dismissed")
    mock_db_session.get = AsyncMock(return_value=rec)
    resp = await authed_client.post(f"/gateway/flywheel/recommendations/{rec.id}/apply")
    assert resp.status_code == 409


async def test_role_matrix_endpoint(authed_client: Any) -> None:
    resp = await authed_client.get("/gateway/role-matrix")
    assert resp.status_code == 200
    body = resp.json()
    assert body["matrix"]["flywheel"]["apply"] == "org_admin"
    assert set(body["capabilities"]) == set(role_matrix.GATEWAY_ROLE_MATRIX)
