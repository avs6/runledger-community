from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.events import AgentRun
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.sessions import (
    SessionDetail,
    SessionItem,
    SessionList,
    SessionRunItem,
    TurnCost,
    TurnCostResponse,
)
from runledger_api.services.observe import resolve_access_group, run_access_clauses

router = APIRouter(prefix="/sessions", tags=["sessions"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _duration_ms(started: datetime, ended: datetime | None) -> int | None:
    if ended is None:
        return None
    return int((ended - started).total_seconds() * 1000)


# ── List sessions ──────────────────────────────────────────────────────────────


@dataclass
class SessionFilters:
    q: str | None
    end_user_id: str | None
    from_dt: datetime | None
    to_dt: datetime | None
    min_turns: int | None
    min_cost: Decimal | None
    max_cost: Decimal | None
    api_key_id: uuid.UUID | None
    access_group_id: uuid.UUID | None


def session_filters(
    q: str | None = Query(None, description="Substring of session id or end user"),
    end_user_id: str | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    min_turns: int | None = Query(None, ge=1),
    min_cost: Decimal | None = Query(None),
    max_cost: Decimal | None = Query(None),
    api_key_id: uuid.UUID | None = Query(None),
    access_group_id: uuid.UUID | None = Query(None),
) -> SessionFilters:
    return SessionFilters(
        q, end_user_id, from_dt, to_dt, min_turns, min_cost, max_cost, api_key_id, access_group_id
    )


SessionFiltersDep = Annotated[SessionFilters, Depends(session_filters)]


async def _grouped_sessions(f: SessionFilters, workspace: Workspace, db: AsyncSession) -> Any:
    """One GROUP BY session_id query shared by list and export (review O-23)."""
    access = await resolve_access_group(db, workspace.id, f.access_group_id)
    where: list[Any] = [
        AgentRun.workspace_id == workspace.id,
        AgentRun.session_id.isnot(None),
        *run_access_clauses(access, [workspace.id]),
    ]
    if f.api_key_id:
        where.append(AgentRun.api_key_id == f.api_key_id)
    if f.q and f.q.strip():
        q_like = f"%{f.q.strip()}%"
        where.append(
            or_(cast(AgentRun.session_id, String).ilike(q_like), AgentRun.end_user_id.ilike(q_like))
        )
    if f.end_user_id:
        where.append(AgentRun.end_user_id == f.end_user_id)
    if f.from_dt:
        where.append(AgentRun.started_at >= f.from_dt)
    if f.to_dt:
        where.append(AgentRun.started_at <= f.to_dt)
    cost = func.coalesce(func.sum(AgentRun.total_cost_usd), Decimal("0"))
    grouped = (
        select(
            AgentRun.session_id,
            func.max(AgentRun.end_user_id).label("end_user_id"),
            func.count(AgentRun.id).label("run_count"),
            cost.label("total_cost_usd"),
            func.min(AgentRun.started_at).label("started_at"),
            func.max(AgentRun.ended_at).label("ended_at"),
        )
        .where(*where)
        .group_by(AgentRun.session_id)
    )
    if f.min_turns is not None:
        grouped = grouped.having(func.count(AgentRun.id) >= f.min_turns)
    if f.min_cost is not None:
        grouped = grouped.having(cost >= f.min_cost)
    if f.max_cost is not None:
        grouped = grouped.having(cost <= f.max_cost)
    return grouped


async def _avg_scores(
    db: AsyncSession, workspace_id: uuid.UUID, session_ids: list[str]
) -> dict[str, Decimal]:
    """Mean evaluation score per session (scores recorded against the session's runs)."""
    if not session_ids:
        return {}
    rows = await db.execute(
        select(AgentRun.session_id, func.avg(ScoreEvent.value))
        .join(ScoreEvent, ScoreEvent.run_id == AgentRun.id)
        .where(
            AgentRun.workspace_id == workspace_id,
            ScoreEvent.workspace_id == workspace_id,
            AgentRun.session_id.in_(session_ids),
        )
        .group_by(AgentRun.session_id)
    )
    return {sid: Decimal(str(round(float(avg), 4))) for sid, avg in rows.all() if avg is not None}


@router.get("", response_model=SessionList)
async def list_sessions(
    workspace: WorkspaceDep,
    db: DbDep,
    filters: SessionFiltersDep,
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> SessionList:
    grouped = await _grouped_sessions(filters, workspace, db)
    total = (await db.execute(select(func.count()).select_from(grouped.subquery()))).scalar_one()
    response.headers["X-Total-Count"] = str(total)
    rows = (
        await db.execute(
            grouped.order_by(func.max(AgentRun.started_at).desc(), AgentRun.session_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    scores = await _avg_scores(db, workspace.id, [r.session_id for r in rows])
    items = [
        SessionItem(
            session_id=row.session_id,
            end_user_id=row.end_user_id,
            run_count=row.run_count,
            total_cost_usd=row.total_cost_usd,
            started_at=row.started_at,
            ended_at=row.ended_at,
            avg_score=scores.get(row.session_id),
        )
        for row in rows
    ]
    return SessionList(items=items, total=total, page=page, page_size=page_size)


@router.get("/export", response_model=None)
async def export_sessions(
    workspace: WorkspaceDep,
    db: DbDep,
    filters: SessionFiltersDep,
    limit: int = Query(5000, ge=1, le=10000),
) -> StreamingResponse:
    grouped = await _grouped_sessions(filters, workspace, db)
    rows = (
        await db.execute(grouped.order_by(func.max(AgentRun.started_at).desc()).limit(limit))
    ).all()

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "session_id",
            "end_user_id",
            "run_count",
            "total_cost_usd",
            "started_at",
            "ended_at",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "session_id": row.session_id,
                "end_user_id": row.end_user_id,
                "run_count": row.run_count,
                "total_cost_usd": str(row.total_cost_usd),
                "started_at": row.started_at.isoformat() if row.started_at else "",
                "ended_at": row.ended_at.isoformat() if row.ended_at else "",
            }
        )

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sessions.csv"'},
    )


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
