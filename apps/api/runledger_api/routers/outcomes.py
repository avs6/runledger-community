"""
Outcome & ROI Ledger API.

Prefix: /outcomes
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST /outcomes                     Submit a business outcome
GET  /outcomes                     List outcomes with filters
GET  /outcomes/summary             Cost-per-outcome + ROI by type (window)
GET  /outcomes/trend               Daily cost-per-success + success-rate trend
GET  /outcomes/workflows           Most profitable workflows (feature_tag × outcome_type)
GET  /outcomes/quality-correlation Quality score ↔ success-rate correlation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.outcomes import Outcome, OutcomeRollupDaily
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.outcomes import (
    OutcomeCreate,
    OutcomeList,
    OutcomeResponse,
    OutcomeSummary,
    OutcomeSummaryItem,
    OutcomeTrend,
    OutcomeTrendPoint,
    OutcomeUpdate,
    QualityOutcomeCorrelation,
    WorkflowROIItem,
    WorkflowROIList,
)

router = APIRouter(prefix="/outcomes", tags=["outcomes"])
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _parse_dt(val: str | None, default: datetime) -> datetime:
    if not val:
        return default
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        return default


def _default_from(days: int = 30) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def _default_to() -> datetime:
    return datetime.now(UTC)


# ── Submit outcome ─────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_outcome(
    body: OutcomeCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> OutcomeResponse:
    """Record a business outcome linked to a run/session/end-user."""
    outcome = Outcome(
        workspace_id=workspace.id,
        run_id=body.run_id,
        session_id=body.session_id,
        end_user_id=body.end_user_id,
        outcome_type=body.outcome_type,
        success=body.success,
        value_usd=body.value_usd,
        labels=body.labels,
    )
    db.add(outcome)
    await db.flush()
    await db.commit()
    await db.refresh(outcome)
    log.info(
        "outcome_created",
        workspace_id=str(workspace.id),
        outcome_type=body.outcome_type,
        success=body.success,
    )
    return OutcomeResponse.model_validate(outcome)


async def _load_outcome_or_404(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    outcome_id: uuid.UUID,
) -> Outcome:
    result = await db.execute(
        select(Outcome).where(
            Outcome.id == outcome_id,
            Outcome.workspace_id == workspace_id,
        )
    )
    outcome = result.scalar_one_or_none()
    if outcome is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outcome not found")
    return outcome


# ── List outcomes ──────────────────────────────────────────────────────────────


@router.get("", response_model=OutcomeList, dependencies=[Depends(analytics_rate_limit)])
async def list_outcomes(
    workspace: WorkspaceDep,
    db: DbDep,
    outcome_type: Annotated[str | None, Query()] = None,
    success: Annotated[bool | None, Query()] = None,
    run_id: Annotated[uuid.UUID | None, Query()] = None,
    end_user_id: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OutcomeList:
    """List outcomes with optional filters."""
    t_from = _parse_dt(from_dt, _default_from())
    t_to = _parse_dt(to_dt, _default_to())

    stmt = select(Outcome).where(
        Outcome.workspace_id == workspace.id,
        Outcome.created_at >= t_from,
        Outcome.created_at < t_to,
    )
    if outcome_type:
        stmt = stmt.where(Outcome.outcome_type == outcome_type)
    if success is not None:
        stmt = stmt.where(Outcome.success == success)
    if run_id is not None:
        stmt = stmt.where(Outcome.run_id == run_id)
    if end_user_id:
        stmt = stmt.where(Outcome.end_user_id == end_user_id)

    count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = int(count_result.scalar() or 0)

    stmt = stmt.order_by(Outcome.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return OutcomeList(
        items=[OutcomeResponse.model_validate(o) for o in items],
        total=total,
    )


@router.get(
    "/{outcome_id}",
    response_model=OutcomeResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_outcome(
    outcome_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> OutcomeResponse:
    outcome = await _load_outcome_or_404(db, workspace.id, outcome_id)
    return OutcomeResponse.model_validate(outcome)


@router.put(
    "/{outcome_id}",
    response_model=OutcomeResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_outcome(
    outcome_id: uuid.UUID,
    body: OutcomeUpdate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> OutcomeResponse:
    outcome = await _load_outcome_or_404(db, workspace.id, outcome_id)
    outcome.outcome_type = body.outcome_type
    outcome.success = body.success
    outcome.run_id = body.run_id
    outcome.session_id = body.session_id
    outcome.end_user_id = body.end_user_id
    outcome.value_usd = body.value_usd
    outcome.labels = body.labels
    await db.commit()
    await db.refresh(outcome)
    log.info("outcome_updated", workspace_id=str(workspace.id), outcome_id=str(outcome.id))
    return OutcomeResponse.model_validate(outcome)


@router.delete(
    "/{outcome_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_outcome(
    outcome_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> Response:
    outcome = await _load_outcome_or_404(db, workspace.id, outcome_id)
    await db.delete(outcome)
    await db.commit()
    log.info("outcome_deleted", workspace_id=str(workspace.id), outcome_id=str(outcome_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Summary: cost-per-outcome + ROI ───────────────────────────────────────────


@router.get("/summary", response_model=OutcomeSummary, dependencies=[Depends(analytics_rate_limit)])
async def outcome_summary(
    workspace: WorkspaceDep,
    db: DbDep,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    window_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> OutcomeSummary:
    """
    Aggregate cost, success rate, and ROI per outcome type.

    Cost is derived from provider_calls linked to the same run_id.
    """
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, t_to - timedelta(days=window_days))

    # Step 1: aggregate outcomes by type
    agg_result = await db.execute(
        select(
            Outcome.outcome_type,
            func.count(Outcome.id).label("count"),
            func.coalesce(func.sum(Outcome.value_usd), Decimal("0")).label("total_value"),
        )
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
        .order_by(func.count(Outcome.id).desc())
    )
    agg_rows = agg_result.all()

    if not agg_rows:
        return OutcomeSummary(items=[], window_days=window_days)

    # Step 2: success count per type (separate query — bool sum is dialect-dependent)
    success_result = await db.execute(
        select(
            Outcome.outcome_type,
            func.count(Outcome.id).label("success_count"),
        )
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.outcome_type.in_([r.outcome_type for r in agg_rows]),
            Outcome.success.is_(True),
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
    )
    success_map: dict[str, int] = {
        r.outcome_type: int(r.success_count) for r in success_result.all()
    }

    # Step 3: total cost per type via run_id join
    cost_sq = (
        select(
            Outcome.outcome_type,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal("0")).label("total_cost"),
        )
        .join(ProviderCall, ProviderCall.run_id == Outcome.run_id)
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.run_id.isnot(None),
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
    )
    cost_result = await db.execute(cost_sq)
    cost_map: dict[str, Decimal] = {
        r.outcome_type: Decimal(str(r.total_cost)) for r in cost_result.all()
    }

    items: list[OutcomeSummaryItem] = []
    for row in agg_rows:
        count = int(row.count)  # type: ignore[call-overload]
        sc = success_map.get(row.outcome_type, 0)
        total_cost = cost_map.get(row.outcome_type, Decimal("0"))
        total_value = Decimal(str(row.total_value or 0))
        sr = Decimal(str(round(sc / count, 4))) if count else Decimal("0")
        cps = Decimal(str(round(float(total_cost) / sc, 6))) if sc > 0 else None
        roi = (
            Decimal(
                str(round((float(total_value) - float(total_cost)) / float(total_cost) * 100, 4))
            )
            if total_cost > 0 and total_value > 0
            else None
        )
        items.append(
            OutcomeSummaryItem(
                outcome_type=row.outcome_type,
                count=count,
                success_count=sc,
                success_rate=sr,
                total_cost_usd=total_cost,
                cost_per_success_usd=cps,
                total_value_usd=total_value if total_value > 0 else None,
                roi=roi,
            )
        )

    return OutcomeSummary(items=items, window_days=window_days)


# ── Trend: daily cost-per-success + success rate ──────────────────────────────


@router.get("/trend", response_model=OutcomeTrend, dependencies=[Depends(analytics_rate_limit)])
async def outcome_trend(
    workspace: WorkspaceDep,
    db: DbDep,
    outcome_type: Annotated[str | None, Query()] = None,
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> OutcomeTrend:
    """
    Return daily success rate and cost-per-success from rollup table.
    Falls back to live query if rollups haven't been computed yet.
    """
    from datetime import date

    cutoff = date.today() - timedelta(days=days)

    stmt = select(OutcomeRollupDaily).where(
        OutcomeRollupDaily.workspace_id == workspace.id,
        OutcomeRollupDaily.day >= cutoff,
    )
    if outcome_type:
        stmt = stmt.where(OutcomeRollupDaily.outcome_type == outcome_type)
    stmt = stmt.order_by(OutcomeRollupDaily.day, OutcomeRollupDaily.outcome_type)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        OutcomeTrendPoint(
            day=r.day,
            outcome_type=r.outcome_type,
            success_rate=r.success_rate,
            cost_per_success_usd=r.cost_per_success_usd if r.cost_per_success_usd > 0 else None,
            count=r.count,
            roi=r.roi,
        )
        for r in rows
    ]
    return OutcomeTrend(items=items)


# ── Workflow ROI ───────────────────────────────────────────────────────────────


@router.get(
    "/workflows", response_model=WorkflowROIList, dependencies=[Depends(analytics_rate_limit)]
)
async def workflow_roi(
    workspace: WorkspaceDep,
    db: DbDep,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(le=50)] = 20,
) -> WorkflowROIList:
    """
    Most profitable workflows: feature_tag × outcome_type ranked by ROI.
    Joins agent_runs → outcomes → provider_calls.
    """
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, t_to - timedelta(days=30))

    # Outcomes with feature_tag from agent_runs
    stmt = (
        select(
            AgentRun.feature_tag,
            Outcome.outcome_type,
            func.count(Outcome.id).label("run_count"),
            func.coalesce(func.sum(Outcome.value_usd), Decimal("0")).label("total_value"),
        )
        .join(Outcome, Outcome.run_id == AgentRun.id)
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
            AgentRun.feature_tag.isnot(None),
        )
        .group_by(AgentRun.feature_tag, Outcome.outcome_type)
        .order_by(func.count(Outcome.id).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return WorkflowROIList(items=[])

    # Success counts per (feature_tag, outcome_type)
    success_stmt = (
        select(
            AgentRun.feature_tag,
            Outcome.outcome_type,
            func.count(Outcome.id).label("success_count"),
        )
        .join(Outcome, Outcome.run_id == AgentRun.id)
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.success.is_(True),
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
            AgentRun.feature_tag.in_([r.feature_tag for r in rows]),
        )
        .group_by(AgentRun.feature_tag, Outcome.outcome_type)
    )
    success_result = await db.execute(success_stmt)
    success_map: dict[tuple[str | None, str], int] = {
        (r.feature_tag, r.outcome_type): int(r.success_count) for r in success_result.all()
    }

    # Cost per (feature_tag, outcome_type)
    cost_stmt = (
        select(
            AgentRun.feature_tag,
            Outcome.outcome_type,
            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal("0")).label("total_cost"),
        )
        .join(Outcome, Outcome.run_id == AgentRun.id)
        .join(ProviderCall, ProviderCall.run_id == AgentRun.id)
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
            AgentRun.feature_tag.in_([r.feature_tag for r in rows]),
        )
        .group_by(AgentRun.feature_tag, Outcome.outcome_type)
    )
    cost_result = await db.execute(cost_stmt)
    cost_map: dict[tuple[str | None, str], Decimal] = {
        (r.feature_tag, r.outcome_type): Decimal(str(r.total_cost)) for r in cost_result.all()
    }

    items: list[WorkflowROIItem] = []
    for row in rows:
        count = int(row.run_count)
        sc = success_map.get((row.feature_tag, row.outcome_type), 0)
        tc = cost_map.get((row.feature_tag, row.outcome_type), Decimal("0"))
        tv = Decimal(str(row.total_value or 0))
        sr = Decimal(str(round(sc / count, 4))) if count else Decimal("0")
        cps = Decimal(str(round(float(tc) / sc, 6))) if sc > 0 else None
        roi = (
            Decimal(str(round((float(tv) - float(tc)) / float(tc) * 100, 4)))
            if tc > 0 and tv > 0
            else None
        )
        items.append(
            WorkflowROIItem(
                feature_tag=row.feature_tag,
                outcome_type=row.outcome_type,
                run_count=count,
                success_count=sc,
                success_rate=sr,
                total_cost_usd=tc,
                total_value_usd=tv if tv > 0 else None,
                roi=roi,
                cost_per_success_usd=cps,
            )
        )

    # Sort by ROI desc, then by run_count desc
    items.sort(key=lambda x: (float(x.roi or -9999), x.run_count), reverse=True)
    return WorkflowROIList(items=items)


# ── Quality ↔ outcome correlation ─────────────────────────────────────────────


@router.get(
    "/quality-correlation",
    response_model=list[QualityOutcomeCorrelation],
    dependencies=[Depends(analytics_rate_limit)],
)
async def quality_outcome_correlation(
    workspace: WorkspaceDep,
    db: DbDep,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
) -> list[QualityOutcomeCorrelation]:
    """
    Correlate avg quality score with success rate per outcome type.
    Joins outcomes → agent_runs → score_events on run_id.
    """
    t_to = _parse_dt(to_dt, _default_to())
    t_from = _parse_dt(from_dt, t_to - timedelta(days=30))

    # Success rate per outcome type
    sr_result = await db.execute(
        select(
            Outcome.outcome_type,
            func.count(Outcome.id).label("total"),
        )
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
    )
    total_map = {r.outcome_type: int(r.total) for r in sr_result.all()}

    success_result = await db.execute(
        select(
            Outcome.outcome_type,
            func.count(Outcome.id).label("sc"),
        )
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.success.is_(True),
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
    )
    success_map = {r.outcome_type: int(r.sc) for r in success_result.all()}

    # Avg score per outcome type (via run_id)
    score_result = await db.execute(
        select(
            Outcome.outcome_type,
            func.avg(ScoreEvent.value).label("avg_score"),
        )
        .join(ScoreEvent, ScoreEvent.run_id == Outcome.run_id)
        .where(
            Outcome.workspace_id == workspace.id,
            Outcome.run_id.isnot(None),
            Outcome.created_at >= t_from,
            Outcome.created_at < t_to,
        )
        .group_by(Outcome.outcome_type)
    )
    score_map: dict[str, Decimal | None] = {
        r.outcome_type: Decimal(str(round(float(r.avg_score), 4)))
        if r.avg_score is not None
        else None
        for r in score_result.all()
    }

    correlations: list[QualityOutcomeCorrelation] = []
    for outcome_type, total in total_map.items():
        sc = success_map.get(outcome_type, 0)
        sr = Decimal(str(round(sc / total, 4))) if total else Decimal("0")
        correlations.append(
            QualityOutcomeCorrelation(
                outcome_type=outcome_type,
                avg_score=score_map.get(outcome_type),
                success_rate=sr,
                sample_count=total,
            )
        )

    correlations.sort(key=lambda x: x.sample_count, reverse=True)
    return correlations
