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

from sqlalchemy import select, text
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


async def _fetch_policy(db: AsyncSession, workspace_id: Any, alias: str) -> RoutingPolicy | None:
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
    score_rows = await db.execute(
        text("""
        SELECT pc.model, AVG(se.value) AS avg_score
        FROM score_events se
        JOIN agent_runs ar ON ar.id = se.run_id
        JOIN provider_calls pc ON pc.run_id = ar.id
        WHERE se.workspace_id = :ws
          AND se.name = 'quality'
          AND se.created_at >= NOW() - INTERVAL ':days days'
        GROUP BY pc.model
    """).bindparams(ws=str(workspace_id), days=lookback_days)
    )
    quality_map: dict[str, float] = {r.model: float(r.avg_score) for r in score_rows.all()}

    # Build model → cost_per_1m map from provider_pricing (cheapest effective)
    pricing_rows = await db.execute(
        text("""
        SELECT DISTINCT ON (provider, model)
               provider, model,
               input_cost_per_1m + output_cost_per_1m AS combined_cost
        FROM provider_pricing
        WHERE (workspace_id = :ws OR workspace_id IS NULL)
        ORDER BY provider, model, effective_from DESC
    """).bindparams(ws=str(workspace_id))
    )
    cost_map: dict[str, float] = {
        f"{r.provider}/{r.model}": float(r.combined_cost) for r in pricing_rows.all()
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
    lat_rows = await db.execute(
        text("""
        SELECT route_id,
               PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
        FROM gateway_requests
        WHERE route_id = ANY(:ids)
          AND created_at >= NOW() - INTERVAL ':h hours'
          AND status = 'success'
          AND latency_ms IS NOT NULL
        GROUP BY route_id
    """).bindparams(ids=route_ids, h=lookback_hours)
    )
    p95_map: dict[str, float] = {str(r.route_id): float(r.p95) for r in lat_rows.all()}

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

    score_rows = await db.execute(
        text("""
        SELECT pc.model, AVG(se.value) AS avg_score
        FROM score_events se
        JOIN agent_runs ar ON ar.id = se.run_id
        JOIN provider_calls pc ON pc.run_id = ar.id
        WHERE se.workspace_id = :ws
          AND se.name = :metric
          AND se.created_at >= NOW() - INTERVAL ':days days'
        GROUP BY pc.model
    """).bindparams(ws=str(workspace_id), metric=metric, days=lookback_days)
    )
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

    if canary_route_id:
        canary = await db.get(GatewayRoute, canary_route_id)
        if canary and canary.workspace_id == workspace_id and canary.is_active:
            canary_rows = await db.execute(
                text("""
                SELECT
                    COUNT(*) AS total_requests,
                    AVG(CASE WHEN status = 'error' THEN 1.0 ELSE 0.0 END) AS error_rate
                FROM gateway_requests
                WHERE workspace_id = :ws
                  AND route_id = :route_id
                  AND created_at >= NOW() - INTERVAL '1 day'
                """).bindparams(ws=str(workspace_id), route_id=str(canary.id))
            )
            row = canary_rows.one_or_none()
            total_requests = int(row.total_requests or 0) if row else 0
            error_rate = float(row.error_rate or 0.0) if row else 0.0
            if total_requests >= min_error_samples and error_rate >= error_spike_threshold:
                config["canary_pct"] = 0.0
                config["rollback_triggered_at"] = datetime.now(UTC).isoformat()
                config["rollback_reason"] = f"error_spike:{error_rate:.3f}"
                policy = await _fetch_policy(db, workspace_id, routes[0].alias)
                if policy is not None:
                    policy.config = config
                    await db.commit()
                baseline = next((r for r in routes if str(r.id) != canary_route_id), routes[0])
                return baseline, (
                    f"canary:auto_rollback-error-spike-{error_rate * 100:.1f}pct"
                    f" ({baseline.target_model})"
                )

    if canary_route_id and random.random() < canary_pct:
        canary = await db.get(GatewayRoute, canary_route_id)
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
        f"ab_test:{chosen['label']}:{int(chosen['allocation_pct'] * 100)}pct"
        f" ({route.target_model})"
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

    route_ids = [variant["route_id"] for variant in variants]
    rows = await db.execute(
        text("""
        SELECT
            route_id,
            COUNT(*) AS total_requests,
            AVG(CASE WHEN status <> 'error' THEN 1.0 ELSE 0.0 END) AS success_rate,
            AVG(CASE WHEN status = 'error' THEN 1.0 ELSE 0.0 END) AS error_rate,
            AVG(latency_ms) AS avg_latency_ms,
            AVG(input_tokens) AS avg_input_tokens,
            AVG(output_tokens) AS avg_output_tokens
        FROM gateway_requests
        WHERE workspace_id = :ws
          AND route_id = ANY(:route_ids)
          AND created_at >= NOW() - INTERVAL '14 days'
        GROUP BY route_id
        """).bindparams(ws=str(workspace_id), route_ids=route_ids)
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
                "avg_latency_ms": round(float(row.avg_latency_ms), 2) if row and row.avg_latency_ms is not None else None,
                "avg_input_tokens": round(float(row.avg_input_tokens), 2) if row and row.avg_input_tokens is not None else None,
                "avg_output_tokens": round(float(row.avg_output_tokens), 2) if row and row.avg_output_tokens is not None else None,
            }
        )

    ranked = sorted(
        metrics,
        key=lambda item: (-item["success_rate"], item["error_rate"], item["avg_latency_ms"] or float("inf")),
    )
    min_sample_size = max(5, int((policy.config or {}).get("min_sample_size", 25)))
    significance_threshold = float((policy.config or {}).get("significance_threshold", 0.05))
    if len(ranked) < 2 or ranked[0]["total_requests"] < min_sample_size or ranked[1]["total_requests"] < min_sample_size:
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
    if budget_id:
        try:
            budget_row = await db.execute(
                text("""
                SELECT b.amount_usd,
                       COALESCE(SUM(ud.cost_usd), 0) AS spent
                FROM budgets b
                LEFT JOIN usage_daily ud ON ud.workspace_id = b.workspace_id
                  AND ud.day >= CURRENT_DATE - INTERVAL '30 days'
                WHERE b.id = :bid AND b.workspace_id = :ws
                GROUP BY b.amount_usd
            """).bindparams(bid=budget_id, ws=str(workspace_id))
            )
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
    type_clause = "AND o.outcome_type = :wf_type" if workflow_type else ""

    stmt = text(f"""
        SELECT
            pc_first.model,
            COUNT(DISTINCT o.id)                                              AS sample_count,
            AVG(CASE WHEN o.success THEN 1.0 ELSE 0.0 END)                   AS success_rate,
            SUM(ar.cost_usd) /
                NULLIF(COUNT(CASE WHEN o.success THEN 1 END)::float, 0)      AS cost_per_success
        FROM outcomes o
        JOIN agent_runs ar ON ar.id = o.run_id
        JOIN (
            SELECT DISTINCT ON (run_id) run_id, model
            FROM provider_calls
            ORDER BY run_id, created_at ASC
        ) pc_first ON pc_first.run_id = o.run_id
        WHERE o.workspace_id = :ws
          AND o.created_at >= :cutoff
          AND pc_first.model = ANY(:models)
          {type_clause}
        GROUP BY pc_first.model
        HAVING COUNT(DISTINCT o.id) >= :min_n
    """)

    bind: dict[str, Any] = {
        "ws": str(workspace_id),
        "cutoff": cutoff,
        "models": models,
        "min_n": min_sample_size,
    }
    if workflow_type:
        bind["wf_type"] = workflow_type

    rows = await db.execute(stmt.bindparams(**bind))
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
        route_ids = [str(r.id) for r in routes]
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        lat_rows = await db.execute(
            text("""
            SELECT route_id,
                   PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
            FROM gateway_requests
            WHERE route_id = ANY(:ids)
              AND created_at >= :cutoff
              AND status = 'success'
              AND latency_ms IS NOT NULL
            GROUP BY route_id
            """).bindparams(ids=route_ids, cutoff=cutoff)
        )
        p95_map: dict[str, float] = {str(r.route_id): float(r.p95) for r in lat_rows.all()}
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
