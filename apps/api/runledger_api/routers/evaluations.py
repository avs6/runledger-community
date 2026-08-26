"""
Evaluations API — quality score CRUD + evaluator management.

Prefix: /evaluations
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST /evaluations/scores               Submit a quality score
GET  /evaluations/scores               List scores with optional filters
POST /evaluations/evaluators           Create an evaluator
GET  /evaluations/evaluators           List evaluators
GET  /evaluations/evaluators/{id}      Get a single evaluator
PUT  /evaluations/evaluators/{id}      Update an evaluator
DELETE /evaluations/evaluators/{id}    Delete an evaluator
POST /evaluations/evaluators/{id}/run  Trigger a batch evaluation run
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.evaluators import Evaluator
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.evaluators import (
    EvaluatorCreate,
    EvaluatorList,
    EvaluatorResponse,
    EvaluatorRunRequest,
    EvaluatorRunResult,
    EvaluatorUpdate,
)
from runledger_api.schemas.scores import ScoreCreate, ScoreList, ScoreResponse

router = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Scores ────────────────────────────────────────────────────────────────────


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
    access_group_id: Annotated[str | None, Query()] = None,
    api_key_id: Annotated[str | None, Query()] = None,
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
    if access_group_id:
        import uuid as _uuid

        from runledger_api.models.access_groups import AccessGroupMember

        member_rows = (
            (
                await db.execute(
                    select(AccessGroupMember.user_id).where(
                        AccessGroupMember.group_id == _uuid.UUID(access_group_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = [str(uid) for uid in member_rows]
        stmt = stmt.where(ScoreEvent.end_user_id.in_(member_ids))
    if api_key_id:
        import uuid as _uuid

        from runledger_api.models.events import AgentRun

        run_ids_sub = select(AgentRun.id).where(
            AgentRun.workspace_id == workspace.id,
            AgentRun.api_key_id == _uuid.UUID(api_key_id),
        )
        stmt = stmt.where(ScoreEvent.run_id.in_(run_ids_sub))

    stmt = stmt.order_by(ScoreEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return ScoreList(items=[ScoreResponse.model_validate(s) for s in items])


# ── Evaluators ────────────────────────────────────────────────────────────────


@router.post("/evaluators", response_model=EvaluatorResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluator(
    body: EvaluatorCreate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> EvaluatorResponse:
    """Create a new evaluator (llm_judge or rule)."""
    ev = Evaluator(
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
        type=body.type,
        config=body.config,
    )
    db.add(ev)
    await db.flush()
    await db.commit()
    await db.refresh(ev)
    log.info("evaluator_created", workspace_id=str(workspace.id), name=body.name, type=body.type)
    return EvaluatorResponse.model_validate(ev)


@router.get("/evaluators", response_model=EvaluatorList)
async def list_evaluators(
    workspace: WorkspaceDep,
    db: DbDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> EvaluatorList:
    """List evaluators for the workspace."""
    stmt = select(Evaluator).where(Evaluator.workspace_id == workspace.id)
    if status_filter:
        stmt = stmt.where(Evaluator.status == status_filter)
    stmt = stmt.order_by(Evaluator.created_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    return EvaluatorList(items=[EvaluatorResponse.model_validate(e) for e in items])


@router.get("/evaluators/{evaluator_id}", response_model=EvaluatorResponse)
async def get_evaluator(
    evaluator_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> EvaluatorResponse:
    """Get a single evaluator."""
    result = await db.execute(
        select(Evaluator).where(
            Evaluator.id == evaluator_id,
            Evaluator.workspace_id == workspace.id,
        )
    )
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return EvaluatorResponse.model_validate(ev)


@router.put("/evaluators/{evaluator_id}", response_model=EvaluatorResponse)
async def update_evaluator(
    evaluator_id: uuid.UUID,
    body: EvaluatorUpdate,
    workspace: WorkspaceDep,
    db: DbDep,
) -> EvaluatorResponse:
    """Update an evaluator's name, description, config, or status."""
    result = await db.execute(
        select(Evaluator).where(
            Evaluator.id == evaluator_id,
            Evaluator.workspace_id == workspace.id,
        )
    )
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")

    if body.name is not None:
        ev.name = body.name
    if body.description is not None:
        ev.description = body.description
    if body.config is not None:
        ev.config = body.config
    if body.status is not None:
        ev.status = body.status

    await db.commit()
    await db.refresh(ev)
    return EvaluatorResponse.model_validate(ev)


@router.delete("/evaluators/{evaluator_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluator(
    evaluator_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> None:
    """Delete an evaluator."""
    result = await db.execute(
        select(Evaluator).where(
            Evaluator.id == evaluator_id,
            Evaluator.workspace_id == workspace.id,
        )
    )
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    await db.delete(ev)
    await db.commit()


@router.post("/evaluators/{evaluator_id}/run", response_model=EvaluatorRunResult)
async def run_evaluator(
    evaluator_id: uuid.UUID,
    body: EvaluatorRunRequest,
    workspace: WorkspaceDep,
    db: DbDep,
) -> EvaluatorRunResult:
    """
    Trigger a batch evaluation run.

    Dispatches a Celery task asynchronously and returns immediately with a
    placeholder result. The task processes runs in the background.
    """
    # Verify evaluator belongs to this workspace
    result = await db.execute(
        select(Evaluator).where(
            Evaluator.id == evaluator_id,
            Evaluator.workspace_id == workspace.id,
        )
    )
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")

    from runledger_api.workers.evaluators import batch_evaluate

    run_id_strs = [str(r) for r in body.run_ids] if body.run_ids else None
    batch_evaluate.delay(str(evaluator_id), run_id_strs, body.limit)

    log.info(
        "evaluator_run_queued",
        evaluator_id=str(evaluator_id),
        workspace_id=str(workspace.id),
        run_ids=run_id_strs,
    )
    return EvaluatorRunResult(
        evaluator_id=evaluator_id,
        evaluated=0,
        scores_created=0,
        errors=0,
    )
