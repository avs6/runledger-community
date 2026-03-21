"""
Routing policy engine for the Model Gateway.

Each policy_type implements a strategy that selects a GatewayRoute and returns
a human-readable decision_reason string explaining why that route was chosen.

All strategies fall back to priority-order selection if they cannot compute a
meaningful signal (e.g. no score data yet, no latency history).
"""

from __future__ import annotations

import logging
import random
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.gateway import GatewayRoute, RoutingPolicy

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


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
        if policy_type == "budget_aware":
            return await _budget_aware(db, workspace_id, routes, config)
        if policy_type == "complexity_based":
            return await _complexity_based(db, workspace_id, routes, config, messages)
    except Exception:
        log.exception("routing_policy_error policy_type=%s alias=%s — falling back to manual",
                      policy_type, alias)

    # Default: manual priority order
    route = routes[0]
    return route, f"manual:priority-{route.priority} ({route.target_model})"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _fetch_active_routes(
    db: AsyncSession, workspace_id: Any, alias: str
) -> list[GatewayRoute]:
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
    return list(result.scalars().all())


async def _fetch_active_routes_by_alias(
    db: AsyncSession, workspace_id: Any, alias: str
) -> list[GatewayRoute]:
    return await _fetch_active_routes(db, workspace_id, alias)


async def _fetch_policy(
    db: AsyncSession, workspace_id: Any, alias: str
) -> RoutingPolicy | None:
    stmt = select(RoutingPolicy).where(
        RoutingPolicy.workspace_id == workspace_id,
        RoutingPolicy.alias == alias,
        RoutingPolicy.is_active.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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

    # Build model → avg_score map from score_events (via provider_calls)
    score_rows = await db.execute(text("""
        SELECT pc.model, AVG(se.value) AS avg_score
        FROM score_events se
        JOIN agent_runs ar ON ar.id = se.run_id
        JOIN provider_calls pc ON pc.run_id = ar.id
        WHERE se.workspace_id = :ws
          AND se.name = 'quality'
          AND se.created_at >= NOW() - INTERVAL ':days days'
        GROUP BY pc.model
    """).bindparams(ws=str(workspace_id), days=lookback_days))
    quality_map: dict[str, float] = {r.model: float(r.avg_score) for r in score_rows.all()}

    # Build model → cost_per_1m map from provider_pricing (cheapest effective)
    pricing_rows = await db.execute(text("""
        SELECT DISTINCT ON (provider, model)
               provider, model,
               input_cost_per_1m + output_cost_per_1m AS combined_cost
        FROM provider_pricing
        WHERE (workspace_id = :ws OR workspace_id IS NULL)
        ORDER BY provider, model, effective_from DESC
    """).bindparams(ws=str(workspace_id)))
    cost_map: dict[str, float] = {
        f"{r.provider}/{r.model}": float(r.combined_cost)
        for r in pricing_rows.all()
    }

    # Filter routes by quality_floor, then sort by cost
    def route_cost(r: GatewayRoute) -> float:
        key = f"{r.provider}/{r.target_model}"
        return cost_map.get(key, 0.0)

    def route_score(r: GatewayRoute) -> float:
        return quality_map.get(r.target_model, 1.0)  # default: assume good if no data

    qualified = [r for r in routes if route_score(r) >= quality_floor] or routes
    best = min(qualified, key=route_cost)
    cost = route_cost(best)
    score = quality_map.get(best.target_model)
    score_str = f" score={score:.2f}" if score is not None else " (no score data)"
    return best, (
        f"cost_optimized:cheapest-above-quality-floor-{quality_floor}"
        f" ({best.target_model}, ${cost:.3f}/1M combined{score_str})"
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

    route_ids = [str(r.id) for r in routes]
    lat_rows = await db.execute(text("""
        SELECT route_id,
               PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
        FROM gateway_requests
        WHERE route_id = ANY(:ids)
          AND created_at >= NOW() - INTERVAL ':h hours'
          AND status = 'success'
          AND latency_ms IS NOT NULL
        GROUP BY route_id
    """).bindparams(ids=route_ids, h=lookback_hours))
    p95_map: dict[str, float] = {
        str(r.route_id): float(r.p95) for r in lat_rows.all()
    }

    id_to_route = {str(r.id): r for r in routes}

    # Filter by max_p95_ms, sort by p95 ascending
    qualified = [r for r in routes
                 if p95_map.get(str(r.id), 0) <= max_p95_ms] or routes
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

    score_rows = await db.execute(text("""
        SELECT pc.model, AVG(se.value) AS avg_score
        FROM score_events se
        JOIN agent_runs ar ON ar.id = se.run_id
        JOIN provider_calls pc ON pc.run_id = ar.id
        WHERE se.workspace_id = :ws
          AND se.name = :metric
          AND se.created_at >= NOW() - INTERVAL ':days days'
        GROUP BY pc.model
    """).bindparams(ws=str(workspace_id), metric=metric, days=lookback_days))
    score_map: dict[str, float] = {r.model: float(r.avg_score) for r in score_rows.all()}

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

    rids, weights = zip(*eligible)
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

    if canary_route_id and random.random() < canary_pct:
        canary = await db.get(GatewayRoute, canary_route_id)
        if canary and canary.workspace_id == workspace_id and canary.is_active:
            return canary, (
                f"canary:canary-{canary_pct*100:.0f}pct ({canary.target_model})"
            )

    # Baseline: highest priority non-canary route
    baseline = next(
        (r for r in routes if str(r.id) != canary_route_id),
        routes[0],
    )
    return baseline, (
        f"canary:baseline-{100-canary_pct*100:.0f}pct ({baseline.target_model})"
    )


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
    if budget_id:
        try:
            budget_row = await db.execute(text("""
                SELECT b.amount_usd,
                       COALESCE(SUM(ud.cost_usd), 0) AS spent
                FROM budgets b
                LEFT JOIN usage_daily ud ON ud.workspace_id = b.workspace_id
                  AND ud.day >= CURRENT_DATE - INTERVAL '30 days'
                WHERE b.id = :bid AND b.workspace_id = :ws
                GROUP BY b.amount_usd
            """).bindparams(bid=budget_id, ws=str(workspace_id)))
            row = budget_row.one_or_none()
            if row and float(row.amount_usd) > 0:
                consumed_pct = float(row.spent) / float(row.amount_usd)
        except Exception:
            log.warning("budget_aware_check_failed budget_id=%s", budget_id)

    if consumed_pct >= threshold_pct and fallback_alias:
        fallback_routes = await _fetch_active_routes(db, workspace_id, fallback_alias)
        if fallback_routes:
            route = fallback_routes[0]
            return route, (
                f"budget_aware:fallback-{consumed_pct*100:.0f}pct-consumed"
                f" → {fallback_alias} ({route.target_model})"
            )

    route = routes[0]
    return route, (
        f"budget_aware:normal-{consumed_pct*100:.0f}pct-consumed ({route.target_model})"
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
