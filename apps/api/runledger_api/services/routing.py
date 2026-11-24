"""
Routing policy engine for the Model Gateway.

Each policy_type implements a strategy that selects a GatewayRoute and returns
a human-readable decision_reason string explaining why that route was chosen.

All strategies fall back to priority-order selection if they cannot compute a
meaningful signal (e.g. no score data yet, no latency history).
"""

from __future__ import annotations

import logging
import math
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Float, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.budgets import Budget
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.gateway import GatewayRequest, GatewayRoute, RoutingPolicy
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.outcomes import Outcome
from runledger_api.models.scores import ScoreEvent

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _as_uuid(value: Any) -> Any:
    import uuid as _uuid  # noqa: PLC0415

    if value is None or isinstance(value, _uuid.UUID):
        return value
    try:
        return _uuid.UUID(str(value))
    except ValueError:
        return None


async def select_route_with_policy(
    db: AsyncSession,
    workspace_id: Any,
    alias: str,
    messages: list[dict[str, Any]],
) -> tuple[GatewayRoute, str]:
    """
    Return (route, decision_reason) for the given alias.

    Looks up the active RoutingPolicy for the alias, applies its strategy,
    and falls back to manual priority-order if no policy exists or the
    strategy has insufficient data.
    """
    # 1. Fetch active routes for this alias (priority order, used as fallback by all strategies)
    routes = await _fetch_active_routes(db, workspace_id, alias)
    if not routes:
        raise ValueError(f"No active gateway routes for alias '{alias}'")

    # 2. Load policy (may be None → manual)
    policy = await _fetch_policy(db, workspace_id, alias)
    policy_type = policy.policy_type if policy else "manual"
    config: dict[str, Any] = (policy.config or {}) if policy else {}

    try:
        if policy_type == "cost_optimized":
            return await _cost_optimized(db, workspace_id, routes, config)
        if policy_type == "latency_optimized":
            return await _latency_optimized(db, routes, config)
        if policy_type == "quality_optimized":
            return await _quality_optimized(db, workspace_id, routes, config)
        if policy_type == "weighted":
            return _weighted(routes, config)
        if policy_type == "canary":
            return await _canary(db, workspace_id, routes, config)
        if policy_type == "ab_test":
            return await _ab_test(db, workspace_id, routes, config)
        if policy_type == "budget_aware":
            return await _budget_aware(db, workspace_id, routes, config)
        if policy_type == "complexity_based":
            return await _complexity_based(db, workspace_id, routes, config, messages)
        if policy_type == "outcome_optimized":
            return await _outcome_optimized(db, workspace_id, routes, config)
    except Exception:
        log.exception(
            "routing_policy_error policy_type=%s alias=%s — falling back to manual",
            policy_type,
            alias,
        )

    # Default: manual priority order
    route = routes[0]
    return route, f"manual:priority-{route.priority} ({route.target_model})"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _fetch_active_routes(
    db: AsyncSession, workspace_id: Any, alias: str
) -> list[GatewayRoute]:
    # Shares the gateway's per-request memo with select_routes (review cd:gw-perf).
    from runledger_api.services.gateway_hotpath import (  # noqa: PLC0415
        is_missing,
        memo_get,
        memo_put,
    )

    memo_key = ("routes", str(workspace_id), alias)
    cached = memo_get(memo_key)
    if not is_missing(cached):
        return list(cached)
    stmt = (
        select(GatewayRoute)
        .where(
            GatewayRoute.workspace_id == workspace_id,
            GatewayRoute.alias == alias,
            GatewayRoute.is_active.is_(True),
        )
        .order_by(GatewayRoute.priority.asc())
    )
    result = await db.execute(stmt)
    routes = list(result.scalars().all())
    memo_put(memo_key, routes)
    return list(routes)


async def _fetch_active_routes_by_alias(
    db: AsyncSession, workspace_id: Any, alias: str
) -> list[GatewayRoute]:
    return await _fetch_active_routes(db, workspace_id, alias)


async def _fetch_policy(db: AsyncSession, workspace_id: Any, alias: str) -> RoutingPolicy | None:
    from runledger_api.services.gateway_hotpath import (  # noqa: PLC0415
        is_missing,
        memo_get,
        memo_put,
    )

    memo_key = ("routing_policy", str(workspace_id), alias)
    cached = memo_get(memo_key)
    if not is_missing(cached):
        return cached  # type: ignore[no-any-return]
    stmt = select(RoutingPolicy).where(
        RoutingPolicy.workspace_id == workspace_id,
        RoutingPolicy.alias == alias,
        RoutingPolicy.is_active.is_(True),
    )
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()
    memo_put(memo_key, policy)
    return policy


# ---------------------------------------------------------------------------
# Data helpers (ORM; the previous raw SQL put bind parameters inside quoted
# INTERVAL literals and compared uuid columns to text, so every data-driven
# strategy raised and silently fell back to manual — review G-01)
# ---------------------------------------------------------------------------


async def _model_scores(
    db: AsyncSession, workspace_id: Any, metric: str, lookback_days: int
) -> dict[str, float]:
    """model → average score of ``metric`` over runs in the window."""
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    rows = await db.execute(
        select(ProviderCall.model, func.avg(ScoreEvent.value))
        .join(ProviderCall, ProviderCall.run_id == ScoreEvent.run_id)
        .where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.name == metric,
            ScoreEvent.created_at >= cutoff,
        )
        .group_by(ProviderCall.model)
    )
    return {model: float(avg) for model, avg in rows.all() if avg is not None}


async def _route_p95(
    db: AsyncSession, routes: list[GatewayRoute], lookback_hours: int
) -> dict[str, float]:
    """route id → p95 latency (ms) of successful requests in the window."""
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    p95 = func.percentile_cont(0.95).within_group(GatewayRequest.latency_ms)
    rows = await db.execute(
        select(GatewayRequest.route_id, p95)
        .where(
            GatewayRequest.route_id.in_([r.id for r in routes]),
            GatewayRequest.created_at >= cutoff,
            GatewayRequest.status == "success",
            GatewayRequest.latency_ms.is_not(None),
        )
        .group_by(GatewayRequest.route_id)
    )
    return {str(rid): float(v) for rid, v in rows.all() if v is not None}


async def _combined_pricing(db: AsyncSession, workspace_id: Any) -> dict[str, float]:
    """ "provider/model" → input + output price per 1M (workspace price wins)."""
    rows = await db.execute(
        select(
            ProviderPricing.provider,
            ProviderPricing.model,
            ProviderPricing.input_cost_per_1m + ProviderPricing.output_cost_per_1m,
            ProviderPricing.workspace_id,
        ).where(
            (ProviderPricing.workspace_id == workspace_id) | ProviderPricing.workspace_id.is_(None),
            ProviderPricing.effective_to.is_(None),
        )
    )
    out: dict[str, float] = {}
    scoped: set[str] = set()
    for provider, model, combined, ws in rows.all():
        key = f"{provider}/{model}"
        if ws is not None:
            out[key] = float(combined)
            scoped.add(key)
        elif key not in scoped:
            out[key] = float(combined)
    return out


# ---------------------------------------------------------------------------
# Strategy: cost_optimized
# Filter routes to those scoring above quality_floor (from score_events),
# then pick the cheapest by provider_pricing.
# ---------------------------------------------------------------------------


async def _cost_optimized(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    quality_floor: float = float(config.get("quality_floor", 0.0))
    lookback_days: int = int(config.get("lookback_days", 7))

    quality_map = await _model_scores(db, workspace_id, "quality", lookback_days)
    cost_map = await _combined_pricing(db, workspace_id)

    # Filter routes by quality_floor, then sort by cost. Unpriced routes sort last
    # (unknown cost is not "free").
    def route_cost(r: GatewayRoute) -> float:
        key = f"{r.provider}/{r.target_model}"
        return cost_map.get(key, float("inf"))

    def route_score(r: GatewayRoute) -> float:
        return quality_map.get(r.target_model, 1.0)  # default: assume good if no data

    qualified = [r for r in routes if route_score(r) >= quality_floor] or routes
    best = min(qualified, key=route_cost)
    cost = route_cost(best)
    score = quality_map.get(best.target_model)
    score_str = f" score={score:.2f}" if score is not None else " (no score data)"
    cost_str = f"${cost:.3f}/1M combined" if cost != float("inf") else "unpriced"
    return best, (
        f"cost_optimized:cheapest-above-quality-floor-{quality_floor}"
        f" ({best.target_model}, {cost_str}{score_str})"
    )


# ---------------------------------------------------------------------------
# Strategy: latency_optimized
# Pick route with lowest p95 latency from recent gateway_requests.
# ---------------------------------------------------------------------------


async def _latency_optimized(
    db: AsyncSession,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    max_p95_ms: int = int(config.get("max_p95_ms", 999_999))
    lookback_hours: int = int(config.get("lookback_hours", 24))

    p95_map = await _route_p95(db, routes, lookback_hours)

    # Filter by max_p95_ms, sort by p95 ascending
    qualified = [r for r in routes if p95_map.get(str(r.id), 0) <= max_p95_ms] or routes
    best = min(qualified, key=lambda r: p95_map.get(str(r.id), float("inf")))
    p95 = p95_map.get(str(best.id))
    p95_str = f"p95={p95:.0f}ms" if p95 is not None else "no-latency-data"
    return best, f"latency_optimized:{p95_str} ({best.target_model})"


# ---------------------------------------------------------------------------
# Strategy: quality_optimized
# Pick route whose model has the highest average score over recent runs.
# ---------------------------------------------------------------------------


async def _quality_optimized(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    metric: str = config.get("metric", "quality")
    lookback_days: int = int(config.get("lookback_days", 7))

    score_map = await _model_scores(db, workspace_id, metric, lookback_days)

    best = max(routes, key=lambda r: score_map.get(r.target_model, -1.0))
    score = score_map.get(best.target_model)
    score_str = f"avg_{metric}={score:.3f}" if score is not None else f"no-{metric}-data"
    return best, f"quality_optimized:{score_str} ({best.target_model})"


# ---------------------------------------------------------------------------
# Strategy: weighted
# config: {"weights": {"<route_id>": 0.7, "<route_id>": 0.3}}
# ---------------------------------------------------------------------------


def _weighted(
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    weight_cfg: dict[str, float] = config.get("weights", {})
    if not weight_cfg:
        # No config: equal weighting
        route = random.choice(routes)
        return route, f"weighted:equal-split ({route.target_model})"

    id_to_route = {str(r.id): r for r in routes}
    eligible = [(rid, w) for rid, w in weight_cfg.items() if rid in id_to_route]
    if not eligible:
        route = routes[0]
        return route, f"weighted:config-mismatch-fallback ({route.target_model})"

    rids, weights = zip(*eligible, strict=False)
    chosen_id = random.choices(rids, weights=weights, k=1)[0]
    route = id_to_route[chosen_id]
    w = weight_cfg[chosen_id]
    return route, f"weighted:random-draw-p{w:.2f} ({route.target_model})"


# ---------------------------------------------------------------------------
# Strategy: canary
# config: {"canary_route_id": "<uuid>", "canary_pct": 0.10}
# ---------------------------------------------------------------------------


async def _canary(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    canary_route_id: str | None = config.get("canary_route_id")
    canary_pct: float = float(config.get("canary_pct", 0.10))
    error_spike_threshold: float = float(config.get("error_spike_threshold", 0.25))
    min_error_samples: int = int(config.get("min_error_samples", 20))

    canary_uuid = _as_uuid(canary_route_id)
    if canary_uuid is not None:
        canary = await db.get(GatewayRoute, canary_uuid)
        if canary and canary.workspace_id == workspace_id and canary.is_active:
            canary_rows = await db.execute(
                select(
                    func.count(),
                    func.avg(case((GatewayRequest.status == "error", 1.0), else_=0.0)),
                ).where(
                    GatewayRequest.workspace_id == workspace_id,
                    GatewayRequest.route_id == canary.id,
                    GatewayRequest.created_at >= datetime.now(UTC) - timedelta(days=1),
                )
            )
            total, rate = canary_rows.one()
            total_requests = int(total or 0)
            error_rate = float(rate or 0.0)
            if total_requests >= min_error_samples and error_rate >= error_spike_threshold:
                # Assign a new dict so the JSONB change is persisted.
                config = {
                    **config,
                    "canary_pct": 0.0,
                    "rollback_triggered_at": datetime.now(UTC).isoformat(),
                    "rollback_reason": f"error_spike:{error_rate:.3f}",
                }
                policy = await _fetch_policy(db, workspace_id, routes[0].alias)
                if policy is not None:
                    policy.config = config
                    await db.commit()
                baseline = next((r for r in routes if str(r.id) != canary_route_id), routes[0])
                return baseline, (
                    f"canary:auto_rollback-error-spike-{error_rate * 100:.1f}pct"
                    f" ({baseline.target_model})"
                )

    if canary_uuid is not None and random.random() < canary_pct:  # noqa: S311
        canary = await db.get(GatewayRoute, canary_uuid)
        if canary and canary.workspace_id == workspace_id and canary.is_active:
            return canary, (f"canary:canary-{canary_pct * 100:.0f}pct ({canary.target_model})")

    # Baseline: highest priority non-canary route
    baseline = next(
        (r for r in routes if str(r.id) != canary_route_id),
        routes[0],
    )
    return baseline, (f"canary:baseline-{100 - canary_pct * 100:.0f}pct ({baseline.target_model})")


async def _ab_test(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    variants = _policy_variants(routes, config, default_label_prefix="variant")
    if not variants:
        route = routes[0]
        return route, f"ab_test:no-config-fallback ({route.target_model})"
    chosen = random.choices(
        variants,
        weights=[variant["allocation_pct"] for variant in variants],
        k=1,
    )[0]
    route = chosen["route"]
    return route, (
        f"ab_test:{chosen['label']}:{int(chosen['allocation_pct'] * 100)}pct ({route.target_model})"
    )


def _policy_variants(
    routes: list[GatewayRoute],
    config: dict[str, Any],
    *,
    default_label_prefix: str,
) -> list[dict[str, Any]]:
    route_map = {str(route.id): route for route in routes}
    variants_cfg = config.get("variants")
    variants: list[dict[str, Any]] = []
    if isinstance(variants_cfg, list):
        for index, item in enumerate(variants_cfg, start=1):
            if not isinstance(item, dict):
                continue
            route_id = str(item.get("route_id") or "")
            route = route_map.get(route_id)
            if route is None:
                continue
            allocation = float(item.get("pct", item.get("weight", 0.0)) or 0.0)
            label = str(item.get("label") or f"{default_label_prefix}-{index}")
            variants.append(
                {
                    "route": route,
                    "route_id": route_id,
                    "label": label,
                    "allocation_pct": max(0.0, allocation),
                }
            )
    if variants:
        total = sum(variant["allocation_pct"] for variant in variants)
        if total > 0:
            for variant in variants:
                variant["allocation_pct"] = variant["allocation_pct"] / total
        return variants

    if config.get("weights"):
        weights = config.get("weights") or {}
        if isinstance(weights, dict):
            eligible = []
            for index, (route_id, weight) in enumerate(weights.items(), start=1):
                route = route_map.get(str(route_id))
                if route is None:
                    continue
                eligible.append(
                    {
                        "route": route,
                        "route_id": str(route_id),
                        "label": f"{default_label_prefix}-{index}",
                        "allocation_pct": float(weight or 0.0),
                    }
                )
            total = sum(variant["allocation_pct"] for variant in eligible)
            if total > 0:
                for variant in eligible:
                    variant["allocation_pct"] = variant["allocation_pct"] / total
                return eligible
    return []


def _p_value_for_two_proportion_z(z_score: float) -> float:
    return math.erfc(abs(z_score) / math.sqrt(2.0))


async def analyze_routing_policy(
    db: AsyncSession,
    workspace_id: Any,
    policy: RoutingPolicy,
) -> dict[str, Any]:
    routes = await _fetch_active_routes(db, workspace_id, policy.alias)
    if not routes:
        return {
            "policy_id": policy.id,
            "alias": policy.alias,
            "policy_type": policy.policy_type,
            "winner_route_id": None,
            "winner_label": None,
            "confidence": "insufficient_data",
            "significance_p_value": None,
            "auto_promoted": False,
            "summary": "No active routes available.",
            "variants": [],
        }

    variants = _policy_variants(routes, policy.config or {}, default_label_prefix="variant")
    if policy.policy_type == "canary":
        canary_route_id = str((policy.config or {}).get("canary_route_id") or "")
        variants = [
            {
                "route": route,
                "route_id": str(route.id),
                "label": "canary" if str(route.id) == canary_route_id else "baseline",
                "allocation_pct": float((policy.config or {}).get("canary_pct", 0.0))
                if str(route.id) == canary_route_id
                else max(0.0, 1.0 - float((policy.config or {}).get("canary_pct", 0.0))),
            }
            for route in routes
            if str(route.id) == canary_route_id or str(route.id) != canary_route_id
        ][:2]
    if not variants:
        variants = [
            {
                "route": route,
                "route_id": str(route.id),
                "label": route.target_model,
                "allocation_pct": 1.0 / max(1, len(routes)),
            }
            for route in routes
        ]

    route_uuids = [u for u in (_as_uuid(v["route_id"]) for v in variants) if u is not None]
    is_error = case((GatewayRequest.status == "error", 1.0), else_=0.0)
    rows = await db.execute(
        select(
            GatewayRequest.route_id,
            func.count().label("total_requests"),
            func.avg(1.0 - is_error).label("success_rate"),
            func.avg(is_error).label("error_rate"),
            func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
            func.avg(GatewayRequest.input_tokens).label("avg_input_tokens"),
            func.avg(GatewayRequest.output_tokens).label("avg_output_tokens"),
        )
        .where(
            GatewayRequest.workspace_id == workspace_id,
            GatewayRequest.route_id.in_(route_uuids),
            GatewayRequest.created_at >= datetime.now(UTC) - timedelta(days=14),
        )
        .group_by(GatewayRequest.route_id)
    )
    metrics_map = {str(row.route_id): row for row in rows.all()}

    metrics: list[dict[str, Any]] = []
    for variant in variants:
        row = metrics_map.get(variant["route_id"])
        metrics.append(
            {
                "route_id": variant["route"].id,
                "label": variant["label"],
                "allocation_pct": round(float(variant["allocation_pct"]), 4),
                "total_requests": int(row.total_requests or 0) if row else 0,
                "success_rate": round(float(row.success_rate or 0.0), 4) if row else 0.0,
                "error_rate": round(float(row.error_rate or 0.0), 4) if row else 0.0,
                "avg_latency_ms": round(float(row.avg_latency_ms), 2)
                if row and row.avg_latency_ms is not None
                else None,
                "avg_input_tokens": round(float(row.avg_input_tokens), 2)
                if row and row.avg_input_tokens is not None
                else None,
                "avg_output_tokens": round(float(row.avg_output_tokens), 2)
                if row and row.avg_output_tokens is not None
                else None,
            }
        )

    ranked = sorted(
        metrics,
        key=lambda item: (
            -item["success_rate"],
            item["error_rate"],
            item["avg_latency_ms"] or float("inf"),
        ),
    )
    min_sample_size = max(5, int((policy.config or {}).get("min_sample_size", 25)))
    significance_threshold = float((policy.config or {}).get("significance_threshold", 0.05))
    if (
        len(ranked) < 2
        or ranked[0]["total_requests"] < min_sample_size
        or ranked[1]["total_requests"] < min_sample_size
    ):
        return {
            "policy_id": policy.id,
            "alias": policy.alias,
            "policy_type": policy.policy_type,
            "winner_route_id": ranked[0]["route_id"] if ranked else None,
            "winner_label": ranked[0]["label"] if ranked else None,
            "confidence": "insufficient_data",
            "significance_p_value": None,
            "auto_promoted": False,
            "summary": f"Not enough variant traffic yet to determine a winner. Need at least {min_sample_size} requests per top variant.",
            "variants": metrics,
        }

    best = ranked[0]
    challenger = ranked[1]
    p1 = best["success_rate"]
    p2 = challenger["success_rate"]
    n1 = best["total_requests"]
    n2 = challenger["total_requests"]
    pooled = ((p1 * n1) + (p2 * n2)) / (n1 + n2)
    denom = math.sqrt(max(pooled * (1 - pooled) * ((1 / n1) + (1 / n2)), 1e-9))
    z_score = (p1 - p2) / denom if denom else 0.0
    p_value = _p_value_for_two_proportion_z(z_score)
    confidence = "high" if p_value < 0.01 else "medium" if p_value < 0.05 else "low"

    auto_promoted = False
    if (
        policy.policy_type == "ab_test"
        and bool((policy.config or {}).get("auto_promote"))
        and p_value < significance_threshold
        and best["route_id"] != challenger["route_id"]
    ):
        policy.policy_type = "weighted"
        policy.config = {
            "weights": {str(best["route_id"]): 1.0},
            "promoted_from": "ab_test",
            "promoted_at": datetime.now(UTC).isoformat(),
            "winner_label": best["label"],
        }
        await db.commit()
        auto_promoted = True

    return {
        "policy_id": policy.id,
        "alias": policy.alias,
        "policy_type": policy.policy_type,
        "winner_route_id": best["route_id"],
        "winner_label": best["label"],
        "confidence": confidence,
        "significance_p_value": round(p_value, 6),
        "auto_promoted": auto_promoted,
        "summary": (
            f"{best['label']} leads with {(best['success_rate'] * 100):.1f}% success "
            f"vs {(challenger['success_rate'] * 100):.1f}% for {challenger['label']}. "
            f"p={p_value:.4f} against threshold {significance_threshold:.4f}; "
            f"minimum sample per top variant is {min_sample_size}."
        ),
        "variants": metrics,
    }


# ---------------------------------------------------------------------------
# Strategy: budget_aware
# config: {"budget_id": "<uuid>", "threshold_pct": 0.80, "fallback_alias": "local"}
# Checks the workspace's budget spend from usage_daily.
# ---------------------------------------------------------------------------


async def _budget_aware(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    budget_id: str | None = config.get("budget_id")
    threshold_pct: float = float(config.get("threshold_pct", 0.80))
    fallback_alias: str | None = config.get("fallback_alias")

    consumed_pct = 0.0
    budget_uuid = _as_uuid(budget_id)
    if budget_uuid is not None:
        try:
            budget = await db.get(Budget, budget_uuid)
            if budget is not None and budget.workspace_id == workspace_id and budget.limit_usd:
                from runledger_api.core.redis import get_redis  # noqa: PLC0415
                from runledger_api.services.budgets import get_budget_spend  # noqa: PLC0415

                spent = await get_budget_spend(await get_redis(), budget.id, budget.period_type)
                consumed_pct = float(spent) / float(budget.limit_usd)
        except Exception:  # noqa: BLE001 - routing must not fail on a counter read
            log.warning("budget_aware_check_failed budget_id=%s", budget_id)

    if consumed_pct >= threshold_pct and fallback_alias:
        fallback_routes = await _fetch_active_routes(db, workspace_id, fallback_alias)
        if fallback_routes:
            route = fallback_routes[0]
            return route, (
                f"budget_aware:fallback-{consumed_pct * 100:.0f}pct-consumed"
                f" → {fallback_alias} ({route.target_model})"
            )

    route = routes[0]
    return route, (
        f"budget_aware:normal-{consumed_pct * 100:.0f}pct-consumed ({route.target_model})"
    )


# ---------------------------------------------------------------------------
# Strategy: complexity_based
# config: {"token_threshold": 500, "simple_alias": "local", "complex_alias": "gpt-4o"}
# Routes based on rough token count of the input messages.
# ---------------------------------------------------------------------------


async def _complexity_based(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
    messages: list[dict[str, Any]],
) -> tuple[GatewayRoute, str]:
    token_threshold: int = int(config.get("token_threshold", 500))
    simple_alias: str | None = config.get("simple_alias")
    complex_alias: str | None = config.get("complex_alias")

    # Rough token estimate: ~4 chars per token
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    estimated_tokens = total_chars // 4

    is_complex = estimated_tokens >= token_threshold
    target_alias = complex_alias if is_complex else simple_alias

    if target_alias:
        target_routes = await _fetch_active_routes(db, workspace_id, target_alias)
        if target_routes:
            route = target_routes[0]
            tier = "complex" if is_complex else "simple"
            return route, (
                f"complexity_based:{tier}-~{estimated_tokens}-tokens"
                f" → {target_alias} ({route.target_model})"
            )

    # Fallback: use routes passed in
    route = routes[0]
    tier = "complex" if is_complex else "simple"
    return route, (
        f"complexity_based:{tier}-~{estimated_tokens}-tokens-no-alias-fallback"
        f" ({route.target_model})"
    )


# ---------------------------------------------------------------------------
# Outcome stats helper (shared with recommendation endpoint)
# ---------------------------------------------------------------------------


async def get_outcome_stats_by_model(
    db: AsyncSession,
    workspace_id: Any,
    models: list[str],
    *,
    lookback_days: int = 30,
    workflow_type: str | None = None,
    min_sample_size: int = 1,
) -> dict[str, dict[str, Any]]:
    """
    Return per-model outcome statistics over the lookback window.

    Result shape:
        {model_name: {sample_count, success_rate, cost_per_success}}

    Only models with >= min_sample_size linked outcomes are included.
    The model for each run is determined by the first provider_call created for that run.
    """
    if not models:
        return {}

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    first_call = (
        select(ProviderCall.run_id, ProviderCall.model)
        .distinct(ProviderCall.run_id)
        .order_by(ProviderCall.run_id, ProviderCall.created_at.asc())
        .subquery()
    )
    successes = func.count(case((Outcome.success.is_(True), 1)))
    stmt = (
        select(
            first_call.c.model,
            func.count(func.distinct(Outcome.id)).label("sample_count"),
            func.avg(case((Outcome.success.is_(True), 1.0), else_=0.0)).label("success_rate"),
            (func.sum(AgentRun.total_cost_usd) / func.nullif(cast(successes, Float), 0)).label(
                "cost_per_success"
            ),
        )
        .select_from(Outcome)
        .join(AgentRun, AgentRun.id == Outcome.run_id)
        .join(first_call, first_call.c.run_id == Outcome.run_id)
        .where(
            and_(
                Outcome.workspace_id == workspace_id,
                Outcome.created_at >= cutoff,
                first_call.c.model.in_(models),
                *([Outcome.outcome_type == workflow_type] if workflow_type else []),
            )
        )
        .group_by(first_call.c.model)
        .having(func.count(func.distinct(Outcome.id)) >= min_sample_size)
    )
    rows = await db.execute(stmt)
    return {
        r.model: {
            "sample_count": int(r.sample_count),
            "success_rate": float(r.success_rate),
            "cost_per_success": float(r.cost_per_success)
            if r.cost_per_success is not None
            else None,
        }
        for r in rows.all()
    }


# ---------------------------------------------------------------------------
# Strategy: outcome_optimized
# config: {"workflow_type": "conversion", "lookback_days": 30,
#          "min_sample_size": 10, "sla_latency_ms": 5000}
# Selects the route whose model has the lowest cost-per-success over recent
# outcomes. Falls back to priority order when data is insufficient.
# ---------------------------------------------------------------------------


async def _outcome_optimized(
    db: AsyncSession,
    workspace_id: Any,
    routes: list[GatewayRoute],
    config: dict[str, Any],
) -> tuple[GatewayRoute, str]:
    lookback_days: int = int(config.get("lookback_days", 30))
    min_sample_size: int = int(config.get("min_sample_size", 10))
    workflow_type: str | None = config.get("workflow_type")
    sla_latency_ms: int | None = config.get("sla_latency_ms")

    models = [r.target_model for r in routes]
    stats = await get_outcome_stats_by_model(
        db,
        workspace_id,
        models,
        lookback_days=lookback_days,
        workflow_type=workflow_type,
        min_sample_size=min_sample_size,
    )

    if not stats:
        # No outcome data yet — fall back to priority order
        route = routes[0]
        return route, f"outcome_optimized:no-data-fallback ({route.target_model})"

    # Optionally filter by p95 SLA
    if sla_latency_ms is not None:
        p95_map = await _route_p95(db, routes, 24)
        routes = [r for r in routes if p95_map.get(str(r.id), 0) <= sla_latency_ms] or routes

    # Pick route with data; prefer lowest cost_per_success (prefer success_rate if tied)
    def _score(r: GatewayRoute) -> tuple[int, float, float]:
        s = stats.get(r.target_model)
        if s is None:
            return (1, float("inf"), 0.0)  # no data → deprioritize
        cps = s["cost_per_success"] if s["cost_per_success"] is not None else float("inf")
        return (0, cps, -s["success_rate"])

    best = min(routes, key=_score)
    s = stats.get(best.target_model)
    if s is None:
        return best, f"outcome_optimized:no-data-fallback ({best.target_model})"

    cps = s["cost_per_success"]
    cps_str = f"${cps:.4f}/success" if cps is not None else "∞"
    return best, (
        f"outcome_optimized:cost-per-success={cps_str}"
        f" success_rate={s['success_rate']:.1%}"
        f" n={s['sample_count']}"
        f" ({best.target_model})"
    )
