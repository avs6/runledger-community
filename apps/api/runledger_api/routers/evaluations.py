"""
Evaluations API — quality score CRUD.

Prefix: /evaluations
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST /evaluations/scores   Submit a quality score (run, span, session, or end-user)
GET  /evaluations/scores   List scores with optional filters
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.scores import ScoreCreate, ScoreList, ScoreResponse

router = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/scores", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def create_score(
    body: ScoreCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> ScoreResponse:
    """Submit a quality score for a run, span, session, or end-user."""
    score = ScoreEvent(
        workspace_id=workspace.id,
        run_id=body.run_id,
        span_id=body.span_id,
        session_id=body.session_id,
        end_user_id=body.end_user_id,
        name=body.name,
        value=body.value,
        label=body.label,
        source=body.source,
        confidence=body.confidence,
        evidence=body.evidence,
    )
    db.add(score)
    await db.flush()
    await db.commit()
    await db.refresh(score)
    log.info("score_created", workspace_id=str(workspace.id), name=body.name, value=str(body.value))
    return ScoreResponse.model_validate(score)


@router.get("/scores", response_model=ScoreList)
async def list_scores(
    workspace: WorkspaceDep,
    db: DbDep,
    run_id: Annotated[uuid.UUID | None, Query()] = None,
    name: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(le=200)] = 50,
) -> ScoreList:
    """List quality scores for the workspace with optional filters."""
    from datetime import UTC, datetime

    stmt = select(ScoreEvent).where(ScoreEvent.workspace_id == workspace.id)

    if run_id is not None:
        stmt = stmt.where(ScoreEvent.run_id == run_id)
    if name is not None:
        stmt = stmt.where(ScoreEvent.name == name)
    if source is not None:
        stmt = stmt.where(ScoreEvent.source == source)
    if from_dt is not None:
        try:
            t_from = datetime.fromisoformat(from_dt)
        except ValueError:
            t_from = datetime.now(UTC)
        stmt = stmt.where(ScoreEvent.created_at >= t_from)
    if to_dt is not None:
        try:
            t_to = datetime.fromisoformat(to_dt)
        except ValueError:
            t_to = datetime.now(UTC)
        stmt = stmt.where(ScoreEvent.created_at < t_to)

    stmt = stmt.order_by(ScoreEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return ScoreList(items=[ScoreResponse.model_validate(s) for s in items])
