"""Top-K analysis engine with period-over-period change detection.

Supports ranking across model, user, intent, feature_tag, and provider
dimensions by cost, tokens, call count, latency P95, or error rate.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.schemas.ml import TopKChange, TopKItem, TopKResponse

log = structlog.get_logger()

_DIMENSION_COL = {
    "model": ProviderCall.model,
    "user": ProviderCall.end_user_id,
    "provider": ProviderCall.provider,
    "intent": AgentRun.intent,
    "feature_tag": AgentRun.feature_tag,
}

_NEEDS_AGENT_RUN = {"intent", "feature_tag"}


def _metric_expr(metric: str) -> tuple:
    if metric == "cost":
        return (func.coalesce(func.sum(ProviderCall.cost_usd), 0),)
    if metric == "tokens":
        return (func.coalesce(func.sum(ProviderCall.input_tokens), 0) + func.coalesce(func.sum(ProviderCall.output_tokens), 0),)
    if metric == "call_count":
        return (func.count(),)
    if metric == "latency_p95":
        return (func.percentile_cont(0.95).within_group(ProviderCall.latency_ms),)
    if metric == "error_rate":
        return (
            func.count().filter(ProviderCall.status != "succeeded").cast(float)
            / func.nullif(func.count(), 0),
        )
    raise ValueError(f"Unknown metric: {metric}")


async def compute_top_k(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimension: str,
    metric: str,
    k: int,
    start: datetime,
    end: datetime,
) -> TopKResponse:
    """Compute Top-K ranking with change detection vs the prior period."""
    period_length = end - start
    prev_start = start - period_length
    prev_end = start

    current_items = await _query_top_k(db, workspace_id, dimension, metric, k, start, end)
    previous_items = await _query_top_k(db, workspace_id, dimension, metric, k, prev_start, prev_end)

    prev_map = {item.key: item for item in previous_items}
    prev_rank_map = {item.key: item.rank for item in previous_items}

    result_items: list[TopKItem] = []
    for item in current_items:
        prev = prev_map.get(item.key)
        prev_value = prev.current_value if prev else None
        prev_rank = prev_rank_map.get(item.key)
        rank_change = (prev_rank - item.rank) if prev_rank else None
        pct_change = None
        if prev_value and prev_value != 0:
            pct_change = round(((item.current_value - prev_value) / abs(prev_value)) * 100, 1)

        result_items.append(TopKItem(
            rank=item.rank,
            key=item.key,
            current_value=item.current_value,
            previous_value=prev_value,
            rank_change=rank_change,
            pct_change=pct_change,
        ))

    changes = _detect_changes(result_items, previous_items, threshold_pct=50.0)

    return TopKResponse(
        dimension=dimension,
        metric=metric,
        k=k,
        period={"from": start.isoformat(), "to": end.isoformat()},
        items=result_items,
        significant_changes=changes,
    )


async def _query_top_k(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    dimension: str,
    metric: str,
    k: int,
    start: datetime,
    end: datetime,
) -> list[TopKItem]:
    dim_col = _DIMENSION_COL.get(dimension)
    if dim_col is None:
        raise ValueError(f"Unknown dimension: {dimension}")

    (metric_agg,) = _metric_expr(metric)

    if dimension in _NEEDS_AGENT_RUN:
        q = (
            select(dim_col.label("key_val"), metric_agg.label("metric_val"))
            .select_from(ProviderCall)
            .join(AgentRun, ProviderCall.run_id == AgentRun.id)
            .where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= start,
                ProviderCall.created_at <= end,
                dim_col.isnot(None),
            )
            .group_by(dim_col)
            .order_by(metric_agg.desc())
            .limit(k)
        )
    else:
        q = (
            select(dim_col.label("key_val"), metric_agg.label("metric_val"))
            .where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at >= start,
                ProviderCall.created_at <= end,
                dim_col.isnot(None),
            )
            .group_by(dim_col)
            .order_by(metric_agg.desc())
            .limit(k)
        )

    result = await db.execute(q)
    items = []
    for rank, row in enumerate(result.all(), start=1):
        items.append(TopKItem(
            rank=rank,
            key=str(row.key_val),
            current_value=round(float(row.metric_val or 0), 4),
            previous_value=None,
            rank_change=None,
            pct_change=None,
        ))
    return items


def _detect_changes(
    current: list[TopKItem],
    previous: list[TopKItem],
    threshold_pct: float = 50.0,
) -> list[TopKChange]:
    changes: list[TopKChange] = []
    current_keys = {item.key for item in current}
    previous_keys = {item.key for item in previous}

    for item in current:
        if item.key not in previous_keys:
            changes.append(TopKChange(
                key=item.key,
                change_type="new_entrant",
                detail=f"{item.key} entered top-K at rank {item.rank}",
            ))
        elif item.pct_change and abs(item.pct_change) >= threshold_pct:
            direction = "increased" if item.pct_change > 0 else "decreased"
            changes.append(TopKChange(
                key=item.key,
                change_type="magnitude_spike",
                detail=f"{item.key} {direction} by {abs(item.pct_change):.1f}%",
            ))

    for prev_item in previous:
        if prev_item.key not in current_keys:
            changes.append(TopKChange(
                key=prev_item.key,
                change_type="exited",
                detail=f"{prev_item.key} exited top-K (was rank {prev_item.rank})",
            ))

    return changes
