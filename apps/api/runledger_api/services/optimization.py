"""
One optimization engine (review B-20).

Optimization opportunities come from the Flywheel: per-segment recommendations
learned from observed runs, cost and quality, each of which can be applied to a
gateway route (with audit and rollback) through ``POST
/gateway/flywheel/recommendations/{id}/apply``. This replaces the fixed 15/30/20% guesses
the analytics endpoint used and the second engine the page computed client-side.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.flywheel import FlywheelRecommendation

_TYPE_BY_KIND = {
    "switch": "route_switch",
    "explore": "route_canary",
    "guardrail": "quality_guardrail",
}


def _describe(rec: FlywheelRecommendation) -> str:
    proposed = rec.proposed_config or {}
    parts = []
    if proposed.get("model"):
        parts.append(f"switch to {proposed['model']}")
    if "semantic_cache" in proposed:
        parts.append("semantic cache " + ("on" if proposed["semantic_cache"] else "off"))
    if "context_compiler" in proposed:
        parts.append("context compiler " + ("on" if proposed["context_compiler"] else "off"))
    change = ", ".join(parts) or "config change"
    quality = ""
    if rec.proposed_quality is not None and rec.current_quality is not None:
        quality = f"; quality {float(rec.current_quality):.2f} → {float(rec.proposed_quality):.2f}"
    return (
        f"{rec.segment_by} '{rec.segment_key}': {change} "
        f"(observed on {rec.sample_size} requests, {rec.confidence} confidence{quality})"
    )


async def flywheel_opportunities(db: AsyncSession, workspace_id: uuid.UUID) -> list[dict[str, Any]]:
    """Pending Flywheel recommendations as optimization opportunities, best first."""
    recs = (
        (
            await db.execute(
                select(FlywheelRecommendation)
                .where(
                    FlywheelRecommendation.workspace_id == workspace_id,
                    FlywheelRecommendation.status == "pending",
                )
                .order_by(FlywheelRecommendation.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    items: list[dict[str, Any]] = []
    for rec in recs:
        per_req = rec.est_cost_delta_per_req
        savings = (
            max(Decimal(0), -per_req * Decimal(rec.sample_size or 0))
            if per_req is not None
            else Decimal(0)
        )
        items.append(
            {
                "optimization_type": _TYPE_BY_KIND.get(rec.kind, rec.kind),
                "potential_savings_usd": savings,
                "affected_calls": int(rec.sample_size or 0),
                "description": _describe(rec),
                "recommendation_id": rec.id,
                "segment_by": rec.segment_by,
                "segment_key": rec.segment_key,
                "kind": rec.kind,
                "confidence": rec.confidence,
                "current_config": rec.current_config or {},
                "proposed_config": rec.proposed_config or {},
                "est_cost_delta_pct": float(rec.est_cost_delta_pct)
                if rec.est_cost_delta_pct is not None
                else None,
                "applies_to_route": rec.segment_by == "alias",
            }
        )
    items.sort(key=lambda i: i["potential_savings_usd"], reverse=True)
    return items


async def price_ratio(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    usage: list[tuple[str, str, int, int]],
    proposed_model: str,
) -> tuple[Decimal | None, Decimal | None]:
    """Current and projected cost of the observed token mix using real pricing rows.

    ``usage`` is (provider, model, input_tokens, output_tokens) per current model.
    Returns (current, projected) or Nones when either side has no pricing.
    """
    from runledger_api.models.metering import ProviderPricing  # noqa: PLC0415
    from runledger_api.services.pricing import calculate_cost  # noqa: PLC0415

    target = (
        await db.execute(
            select(ProviderPricing).where(ProviderPricing.model == proposed_model).limit(1)
        )
    ).scalar_one_or_none()
    if target is None:
        return None, None
    current = Decimal(0)
    projected = Decimal(0)
    for provider, model, tin, tout in usage:
        cur = await calculate_cost(
            db,
            provider=provider,
            model=model,
            input_tokens=tin,
            output_tokens=tout,
            workspace_id=workspace_id,
        )
        new = await calculate_cost(
            db,
            provider=target.provider,
            model=proposed_model,
            input_tokens=tin,
            output_tokens=tout,
            workspace_id=workspace_id,
        )
        if cur is None or new is None:
            return None, None
        current += cur
        projected += new
    return current, projected


async def observed_rates(
    db: AsyncSession, workspace_id: uuid.UUID, since: Any
) -> dict[str, float | int | None]:
    """Cache hit rate and compression savings this workspace actually achieved.

    * ``cache_hit_rate``: share of gateway requests served from cache on routes that
      have caching enabled (exact or semantic), over the window.
    * ``compression_savings_pct``: savings / baseline cost on provider calls that
      recorded a compression or context-compiler optimization.

    Either is ``None`` when there is no observed traffic to learn from; the simulator
    then projects nothing for that lever instead of assuming a number (review B-20).
    """
    from sqlalchemy import case, func  # noqa: PLC0415

    from runledger_api.models.events import ProviderCall  # noqa: PLC0415
    from runledger_api.models.gateway import GatewayRequest, GatewayRoute  # noqa: PLC0415

    cache_routes = select(GatewayRoute.id).where(
        GatewayRoute.workspace_id == workspace_id,
        GatewayRoute.semantic_cache_enabled.is_(True),
    )
    total, hits = (
        await db.execute(
            select(
                func.count(GatewayRequest.id),
                func.coalesce(func.sum(case((GatewayRequest.cache_hit.is_(True), 1), else_=0)), 0),
            ).where(
                GatewayRequest.workspace_id == workspace_id,
                GatewayRequest.created_at >= since,
                (GatewayRequest.route_id.in_(cache_routes)) | (GatewayRequest.cache_hit.is_(True)),
            )
        )
    ).one()
    savings, baseline, comp_calls = (
        await db.execute(
            select(
                func.coalesce(func.sum(ProviderCall.savings_usd), 0),
                func.coalesce(func.sum(ProviderCall.baseline_cost_usd), 0),
                func.count(ProviderCall.id),
            ).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= since,
                ProviderCall.optimization_applied.in_(
                    ["prompt_compression", "context_compiler", "compression"]
                ),
                ProviderCall.baseline_cost_usd > 0,
            )
        )
    ).one()
    return {
        "cache_hit_rate": (float(hits) / float(total)) if total else None,
        "cache_sample": int(total or 0),
        "compression_savings_pct": (float(savings) / float(baseline)) if baseline else None,
        "compression_sample": int(comp_calls or 0),
    }
