"""
Workflow Definitions & Runs API.

Prefix: /workflows
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /workflows                              Create workflow definition
GET    /workflows                              List workflow definitions
GET    /workflows/{id}                         Get workflow definition
PUT    /workflows/{id}                         Update workflow definition
DELETE /workflows/{id}                         Archive workflow definition

POST   /workflows/{id}/runs                    Create a run for this workflow
GET    /workflows/{id}/runs                    List runs for a workflow
GET    /workflows/{id}/runs/{run_id}           Run detail with steps
PUT    /workflows/{id}/runs/{run_id}           Update run status
GET    /workflows/{id}/cost                    Cost attribution for a workflow

POST   /workflows/runs/{run_id}/steps          Add a step to a run
PUT    /workflows/runs/{run_id}/steps/{step_id}  Update step status
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.agents import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
)
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.agents import (
    StepCostBreakdown,
    WorkflowCostAttribution,
    WorkflowDefinitionCreate,
    WorkflowDefinitionListResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionUpdate,
    WorkflowRunCreate,
    WorkflowRunListResponse,
    WorkflowRunResponse,
    WorkflowRunUpdate,
    WorkflowStepCreate,
    WorkflowStepResponse,
    WorkflowStepUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/workflows", tags=["workflows"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _def_to_response(d: WorkflowDefinition) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(
        id=d.id,
        workspace_id=d.workspace_id,
        name=d.name,
        description=d.description,
        steps_schema=d.steps_schema or [],
        status=d.status,
        config=d.config or {},
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


def _step_to_response(s: WorkflowStep) -> WorkflowStepResponse:
    return WorkflowStepResponse(
        id=s.id,
        run_id=s.run_id,
        step_index=s.step_index,
        name=s.name,
        step_type=s.step_type,
        agent_id=s.agent_id,
        model=s.model,
        tool=s.tool,
        status=s.status,
        cost=s.cost,
        tokens=s.tokens,
        duration_ms=s.duration_ms,
        input_data=s.input_data,
        output_data=s.output_data,
        error=s.error,
        started_at=s.started_at,
        completed_at=s.completed_at,
        created_at=s.created_at,
    )


def _run_to_response(
    r: WorkflowRun, steps: list[WorkflowStep] | None = None
) -> WorkflowRunResponse:
    return WorkflowRunResponse(
        id=r.id,
        workspace_id=r.workspace_id,
        workflow_id=r.workflow_id,
        agent_id=r.agent_id,
        parent_run_id=r.parent_run_id,
        status=r.status,
        total_cost=r.total_cost,
        total_tokens=r.total_tokens,
        total_duration_ms=r.total_duration_ms,
        trigger=r.trigger,
        input_data=r.input_data or {},
        output_data=r.output_data,
        error=r.error,
        started_at=r.started_at,
        completed_at=r.completed_at,
        created_at=r.created_at,
        steps=[_step_to_response(s) for s in steps] if steps else [],
    )


# ── Workflow Definition CRUD ────────────────────────────────────────────────


@router.post(
    "",
    response_model=WorkflowDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_workflow(
    body: WorkflowDefinitionCreate, ws: WorkspaceDep, db: DbDep
) -> WorkflowDefinitionResponse:
    wf = WorkflowDefinition(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        steps_schema=body.steps_schema,
        status=body.status,
        config=body.config,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return _def_to_response(wf)


@router.get(
    "",
    response_model=WorkflowDefinitionListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_workflows(
    ws: WorkspaceDep,
    db: DbDep,
    wf_status: str | None = Query(None, alias="status"),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> WorkflowDefinitionListResponse:
    q = select(WorkflowDefinition).where(WorkflowDefinition.workspace_id == ws.id)
    count_q = select(func.count(WorkflowDefinition.id)).where(
        WorkflowDefinition.workspace_id == ws.id
    )
    if wf_status:
        q = q.where(WorkflowDefinition.status == wf_status)
        count_q = count_q.where(WorkflowDefinition.status == wf_status)
    if access_group_id or api_key_id:
        import uuid as _uuid
        run_sub = select(WorkflowRun.workflow_id).where(
            WorkflowRun.workspace_id == ws.id,
        )
        if access_group_id:
            run_sub = run_sub.where(WorkflowRun.access_group_id == _uuid.UUID(access_group_id))
        if api_key_id:
            run_sub = run_sub.where(WorkflowRun.api_key_id == _uuid.UUID(api_key_id))
        run_sub = run_sub.distinct()
        q = q.where(WorkflowDefinition.id.in_(run_sub))
        count_q = count_q.where(WorkflowDefinition.id.in_(run_sub))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (
            await db.execute(
                q.order_by(WorkflowDefinition.created_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return WorkflowDefinitionListResponse(
        workflows=[_def_to_response(d) for d in rows],
        total=total,
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDefinitionResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_workflow(
    workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep
) -> WorkflowDefinitionResponse:
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.workspace_id == ws.id,
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return _def_to_response(wf)


@router.put(
    "/{workflow_id}",
    response_model=WorkflowDefinitionResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowDefinitionUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowDefinitionResponse:
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.workspace_id == ws.id,
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(wf, field, val)
    wf.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(wf)
    return _def_to_response(wf)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def archive_workflow(workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.workspace_id == ws.id,
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    wf.status = "archived"
    wf.updated_at = datetime.now(UTC)
    await db.commit()


# ── Workflow Runs ───────────────────────────────────────────────────────────


@router.post(
    "/{workflow_id}/runs",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_run(
    workflow_id: uuid.UUID,
    body: WorkflowRunCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowRunResponse:
    # Verify workflow exists
    wf = (
        await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == workflow_id,
                WorkflowDefinition.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")

    run = WorkflowRun(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        workflow_id=workflow_id,
        agent_id=body.agent_id,
        parent_run_id=body.parent_run_id,
        api_key_id=body.api_key_id,
        access_group_id=body.access_group_id,
        trigger=body.trigger,
        input_data=body.input_data,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return _run_to_response(run)


@router.get(
    "/{workflow_id}/runs",
    response_model=WorkflowRunListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_runs(
    workflow_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    run_status: str | None = Query(None, alias="status"),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> WorkflowRunListResponse:
    base = select(WorkflowRun).where(
        WorkflowRun.workflow_id == workflow_id,
        WorkflowRun.workspace_id == ws.id,
    )
    count_q = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.workflow_id == workflow_id,
        WorkflowRun.workspace_id == ws.id,
    )
    if run_status:
        base = base.where(WorkflowRun.status == run_status)
        count_q = count_q.where(WorkflowRun.status == run_status)
    if access_group_id:
        import uuid as _uuid
        _ag = _uuid.UUID(access_group_id)
        base = base.where(WorkflowRun.access_group_id == _ag)
        count_q = count_q.where(WorkflowRun.access_group_id == _ag)
    if api_key_id:
        import uuid as _uuid
        _ak = _uuid.UUID(api_key_id)
        base = base.where(WorkflowRun.api_key_id == _ak)
        count_q = count_q.where(WorkflowRun.api_key_id == _ak)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (await db.execute(base.order_by(WorkflowRun.created_at.desc()).offset(offset).limit(limit)))
        .scalars()
        .all()
    )

    return WorkflowRunListResponse(
        runs=[_run_to_response(r) for r in rows],
        total=total,
    )


@router.get(
    "/{workflow_id}/runs/{run_id}",
    response_model=WorkflowRunResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowRunResponse:
    run = (
        await db.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == run_id,
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")

    steps = (
        (
            await db.execute(
                select(WorkflowStep)
                .where(WorkflowStep.run_id == run_id)
                .order_by(WorkflowStep.step_index)
            )
        )
        .scalars()
        .all()
    )

    return _run_to_response(run, list(steps))


@router.put(
    "/{workflow_id}/runs/{run_id}",
    response_model=WorkflowRunResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_run(
    workflow_id: uuid.UUID,
    run_id: uuid.UUID,
    body: WorkflowRunUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowRunResponse:
    run = (
        await db.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == run_id,
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")

    updates = body.model_dump(exclude_unset=True)
    if "status" in updates:
        new_status = updates["status"]
        if new_status == "running" and not run.started_at:
            run.started_at = datetime.now(UTC)
        elif new_status in ("completed", "failed", "cancelled"):
            run.completed_at = datetime.now(UTC)
            if run.started_at:
                run.total_duration_ms = int(
                    (run.completed_at - run.started_at).total_seconds() * 1000
                )

    for field, val in updates.items():
        setattr(run, field, val)

    await db.commit()
    await db.refresh(run)
    return _run_to_response(run)


# ── Workflow Steps ──────────────────────────────────────────────────────────


@router.post(
    "/runs/{run_id}/steps",
    response_model=WorkflowStepResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_step(
    run_id: uuid.UUID,
    body: WorkflowStepCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowStepResponse:
    run = (
        await db.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == run_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")

    step = WorkflowStep(
        id=uuid.uuid4(),
        run_id=run_id,
        step_index=body.step_index,
        name=body.name,
        step_type=body.step_type,
        agent_id=body.agent_id,
        model=body.model,
        tool=body.tool,
        input_data=body.input_data,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return _step_to_response(step)


@router.put(
    "/runs/{run_id}/steps/{step_id}",
    response_model=WorkflowStepResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_step(
    run_id: uuid.UUID,
    step_id: uuid.UUID,
    body: WorkflowStepUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowStepResponse:
    step = (
        await db.execute(
            select(WorkflowStep).where(
                WorkflowStep.id == step_id,
                WorkflowStep.run_id == run_id,
            )
        )
    ).scalar_one_or_none()
    if not step:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow step not found")

    # Verify run belongs to workspace
    run = (
        await db.execute(
            select(WorkflowRun).where(
                WorkflowRun.id == run_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")

    updates = body.model_dump(exclude_unset=True)
    if "status" in updates:
        new_status = updates["status"]
        if new_status == "running" and not step.started_at:
            step.started_at = datetime.now(UTC)
        elif new_status in ("completed", "failed", "skipped"):
            step.completed_at = datetime.now(UTC)
            if step.started_at:
                step.duration_ms = int((step.completed_at - step.started_at).total_seconds() * 1000)

    for field, val in updates.items():
        setattr(step, field, val)

    await db.commit()
    await db.refresh(step)
    return _step_to_response(step)


# ── Cost Attribution ────────────────────────────────────────────────────────


@router.get(
    "/{workflow_id}/cost",
    response_model=WorkflowCostAttribution,
    dependencies=[Depends(analytics_rate_limit)],
)
async def workflow_cost_attribution(
    workflow_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowCostAttribution:
    wf = (
        await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == workflow_id,
                WorkflowDefinition.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")

    # Run-level aggregates
    run_agg = (
        await db.execute(
            select(
                func.count(WorkflowRun.id).label("total_runs"),
                func.coalesce(func.sum(WorkflowRun.total_cost), 0).label("total_cost"),
            ).where(
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).one()

    total_runs = run_agg.total_runs or 0
    total_cost = Decimal(str(run_agg.total_cost))
    avg_cost = (total_cost / total_runs) if total_runs > 0 else Decimal("0")

    # Step-level cost breakdown
    step_rows = (
        await db.execute(
            select(
                WorkflowStep.name,
                WorkflowStep.step_type,
                func.coalesce(func.sum(WorkflowStep.cost), 0).label("total_cost"),
                func.avg(WorkflowStep.cost).label("avg_cost"),
                func.count(WorkflowStep.id).label("invocation_count"),
            )
            .join(WorkflowRun, WorkflowStep.run_id == WorkflowRun.id)
            .where(
                WorkflowRun.workflow_id == workflow_id,
                WorkflowRun.workspace_id == ws.id,
            )
            .group_by(WorkflowStep.name, WorkflowStep.step_type)
            .order_by(func.sum(WorkflowStep.cost).desc())
        )
    ).all()

    return WorkflowCostAttribution(
        workflow_id=workflow_id,
        workflow_name=wf.name,
        total_runs=total_runs,
        total_cost=total_cost,
        avg_cost_per_run=avg_cost,
        cost_by_step=[
            StepCostBreakdown(
                step_name=row.name,
                step_type=row.step_type,
                total_cost=Decimal(str(row.total_cost)),
                avg_cost=Decimal(str(row.avg_cost)) if row.avg_cost else Decimal("0"),
                invocation_count=row.invocation_count,
            )
            for row in step_rows
        ],
    )
