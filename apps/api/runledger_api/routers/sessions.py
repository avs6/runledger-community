from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.events import AgentRun
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.sessions import (
    SessionDetail,
    SessionItem,
    SessionList,
    SessionRunItem,
    TurnCost,
    TurnCostResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _duration_ms(started: datetime, ended: datetime | None) -> int | None:
    if ended is None:
        return None
    return int((ended - started).total_seconds() * 1000)


# ── List sessions ──────────────────────────────────────────────────────────────


@router.get("", response_model=SessionList)
async def list_sessions(
    workspace: WorkspaceDep,
    db: DbDep,
    end_user_id: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
) -> SessionList:
    base_where = [
        AgentRun.workspace_id == workspace.id,
        AgentRun.session_id.isnot(None),
    ]
    if end_user_id:
        base_where.append(AgentRun.end_user_id == end_user_id)
    if from_dt:
        base_where.append(AgentRun.started_at >= from_dt)
    if to_dt:
        base_where.append(AgentRun.started_at <= to_dt)

    stmt = (
        select(
            AgentRun.session_id,
            func.max(AgentRun.end_user_id).label("end_user_id"),
            func.count(AgentRun.id).label("run_count"),
            func.sum(AgentRun.total_cost_usd).label("total_cost_usd"),
            func.min(AgentRun.started_at).label("started_at"),
            func.max(AgentRun.ended_at).label("ended_at"),
        )
        .where(*base_where)
        .group_by(AgentRun.session_id)
        .order_by(func.max(AgentRun.started_at).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Total distinct session count
    count_stmt = (
        select(func.count(AgentRun.session_id.distinct()))
        .where(*base_where)
    )
    total = (await db.execute(count_stmt)).scalar_one()

    items = [
        SessionItem(
            session_id=row.session_id,
            end_user_id=row.end_user_id,
            run_count=row.run_count,
            total_cost_usd=row.total_cost_usd,
            started_at=row.started_at,
            ended_at=row.ended_at,
            avg_score=None,
        )
        for row in rows
    ]
    return SessionList(items=items, total=total)


# ── Session detail ─────────────────────────────────────────────────────────────


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> SessionDetail:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.started_at)
    )
    runs = list(result.scalars().all())

    if not runs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    total_cost: Decimal = sum(
        ((r.total_cost_usd or Decimal("0")) for r in runs),
        start=Decimal("0"),
    )

    run_items = [
        SessionRunItem(
            id=r.id,
            status=r.status,
            feature_tag=r.feature_tag,
            deployment_version=r.deployment_version,
            total_cost_usd=r.total_cost_usd,
            started_at=r.started_at,
            ended_at=r.ended_at,
            duration_ms=_duration_ms(r.started_at, r.ended_at),
            turn_number=i + 1,
        )
        for i, r in enumerate(runs)
    ]

    return SessionDetail(
        session_id=session_id,
        end_user_id=runs[0].end_user_id,
        run_count=len(runs),
        total_cost_usd=total_cost if total_cost else None,
        started_at=runs[0].started_at,
        ended_at=runs[-1].ended_at,
        runs=run_items,
    )


# ── Cost over turns ────────────────────────────────────────────────────────────


@router.get("/{session_id}/cost-over-turns", response_model=TurnCostResponse)
async def cost_over_turns(
    session_id: str,
    workspace: WorkspaceDep,
    db: DbDep,
) -> TurnCostResponse:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.started_at)
    )
    runs = list(result.scalars().all())

    if not runs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    cumulative = Decimal("0")
    turns: list[TurnCost] = []
    for i, r in enumerate(runs):
        cost = r.total_cost_usd or Decimal("0")
        cumulative += cost
        turns.append(
            TurnCost(
                turn_number=i + 1,
                run_id=r.id,
                cost_usd=r.total_cost_usd,
                cumulative_cost_usd=cumulative,
            )
        )

    return TurnCostResponse(session_id=session_id, turns=turns)
