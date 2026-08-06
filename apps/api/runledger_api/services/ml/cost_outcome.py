"""Cost-per-outcome analysis with Pareto frontier computation.

Joins agent runs with outcomes to compute cost per successful outcome
by model and route, then identifies Pareto-optimal configurations on
the cost-quality frontier.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, OutcomeEvent, ProviderCall
from runledger_api.models.scores import ScoreEvent
from runledger_api.schemas.ml import CostOutcomeResponse, CostPerOutcome, ParetoPoint

log = structlog.get_logger()


async def compute_cost_per_outcome(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> CostOutcomeResponse:
    """Compute cost per outcome by model with Pareto frontier."""
    result = await db.execute(
        select(
            ProviderCall.model,
            OutcomeEvent.event_type,
            func.coalesce(func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
            func.count(func.distinct(AgentRun.id)).label("run_count"),
            func.count().filter(OutcomeEvent.success.is_(True)).label("success_count"),
        )
        .select_from(ProviderCall)
        .join(AgentRun, ProviderCall.run_id == AgentRun.id)
        .join(OutcomeEvent, OutcomeEvent.run_id == AgentRun.id)
        .where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= start,
            ProviderCall.created_at <= end,
        )
        .group_by(ProviderCall.model, OutcomeEvent.event_type)
    )
    rows = result.all()

    score_result = await db.execute(
        select(
            ProviderCall.model,
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .select_from(ScoreEvent)
        .join(AgentRun, ScoreEvent.run_id == AgentRun.id)
        .join(ProviderCall, ProviderCall.run_id == AgentRun.id)
        .where(
            ScoreEvent.workspace_id == workspace_id,
            ScoreEvent.created_at >= start,
            ScoreEvent.created_at <= end,
        )
        .group_by(ProviderCall.model)
    )
    score_map = {r.model: float(r.avg_score) for r in score_result.all()}

    items: list[CostPerOutcome] = []
    model_agg: dict[str, dict[str, Any]] = {}

    for row in rows:
        total_cost = float(row.total_cost)
        outcome_count = row.success_count or 1
        cost_per = total_cost / outcome_count if outcome_count > 0 else total_cost

        items.append(
            CostPerOutcome(
                outcome_type=row.outcome_type,
                total_cost=round(total_cost, 4),
                outcome_count=outcome_count,
                cost_per_outcome=round(cost_per, 4),
                avg_quality_score=score_map.get(row.model),
                model=row.model,
            )
        )

        if row.model not in model_agg:
            model_agg[row.model] = {"cost": 0.0, "outcomes": 0}
        model_agg[row.model]["cost"] += total_cost
        model_agg[row.model]["outcomes"] += outcome_count

    pareto_points: list[ParetoPoint] = []
    for model, agg in model_agg.items():
        cost_per = agg["cost"] / agg["outcomes"] if agg["outcomes"] > 0 else agg["cost"]
        quality = score_map.get(model, 0.5)
        pareto_points.append(
            ParetoPoint(
                key=model,
                cost=round(cost_per, 4),
                quality=round(quality, 4),
                is_optimal=False,
            )
        )

    _mark_pareto_optimal(pareto_points)

    return CostOutcomeResponse(items=items, pareto_frontier=pareto_points)


def _mark_pareto_optimal(points: list[ParetoPoint]) -> None:
    """Mark non-dominated points on the cost-quality frontier.

    A point is Pareto-optimal if no other point has both lower cost AND
    higher quality.
    """
    if not points:
        return

    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            if (
                q.cost <= p.cost
                and q.quality >= p.quality
                and (q.cost < p.cost or q.quality > p.quality)
            ):
                dominated = True
                break
        p.is_optimal = not dominated
