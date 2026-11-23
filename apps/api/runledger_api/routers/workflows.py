"""
Workflows API: the product's top-level object (review top#4, B-11, B-17, B-18).

Prefix: /workflows
Auth: Bearer API key (workspace-scoped)

A workflow is a named unit of AI work linked to a ``feature_tag`` and/or a gateway
alias. Runs are attributed to it at ingest (``agent_runs.workflow_id``; see
``services/workflow_attribution.py``), so a workflow's runs, cost and quality are
read from the one metering stream instead of hand-written run records.

Endpoints
---------
POST   /workflows                     Create a workflow (links existing runs by tag/alias)
GET    /workflows                     List workflows with 30-day stats
GET    /workflows/{id}                Get a workflow
PUT    /workflows/{id}                Update / re-link / archive / restore
DELETE /workflows/{id}                Archive (runs keep their history)
GET    /workflows/{id}/overview       Workflow page: health, budgets, evals, policies, agents
GET    /workflows/{id}/runs           Runs attributed to the workflow (view over agent_runs)
GET    /workflows/{id}/cost           Cost by step (span) and by model, rolled up from calls

Workflows are archived, not hard-deleted: runs reference them and archived workflows
stop matching new traffic, which is the behaviour a delete needs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_writer
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.agents import Agent, WorkflowDefinition
from runledger_api.models.budgets import Budget
from runledger_api.models.events import AgentRun, ProviderCall, RunStatusEnum, Span
from runledger_api.models.gateway import GatewayRoute, RoutingPolicy
from runledger_api.models.guardrails import GuardrailRule
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.tenant import Workspace
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.schemas.agents import (
    ModelCostBreakdown,
    RunSummary,
    RunSummaryListResponse,
    StepCostBreakdown,
    TrendPoint,
    WorkflowAgentUsage,
    WorkflowBudget,
    WorkflowCostAttribution,
    WorkflowDefinitionCreate,
    WorkflowDefinitionListResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionUpdate,
    WorkflowEval,
    WorkflowHealth,
    WorkflowOverview,
    WorkflowPolicy,
    WorkflowStats,
)
from runledger_api.services.workflow_attribution import link_existing_runs

log = structlog.get_logger()
router = APIRouter(prefix="/workflows", tags=["workflows"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
WindowDep = Annotated[int, Query(ge=1, le=365, description="Look-back window in days")]

RUN_STATUSES = {s.value for s in RunStatusEnum}
SORTS = {"created_at", "name", "updated_at"}


def _duration_ms() -> Any:
    return func.extract("epoch", AgentRun.ended_at - AgentRun.started_at) * 1000


def _def_to_response(
    d: WorkflowDefinition,
    stats: WorkflowStats | None = None,
    linked_runs: int | None = None,
) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(
        id=d.id,
        workspace_id=d.workspace_id,
        name=d.name,
        description=d.description,
        feature_tag=d.feature_tag,
        gateway_alias=d.gateway_alias,
        owner=d.owner,
        steps_schema=d.steps_schema or [],
        status=d.status,
        config=d.config or {},
        created_at=d.created_at,
        updated_at=d.updated_at,
        stats=stats,
        linked_runs=linked_runs,
    )


def _run_summary(r: AgentRun) -> RunSummary:
    duration = (
        int((r.ended_at - r.started_at).total_seconds() * 1000)
        if r.ended_at and r.started_at
        else None
    )
    status_value = r.status.value if isinstance(r.status, RunStatusEnum) else str(r.status)
    return RunSummary(
        id=r.id,
        workflow_id=r.workflow_id,
        agent_id=r.agent_id,
        status=status_value,
        feature_tag=r.feature_tag,
        end_user_id=r.end_user_id,
        api_key_id=r.api_key_id,
        source_type=r.source_type,
        total_cost_usd=r.total_cost_usd or Decimal("0"),
        total_tokens=(r.total_input_tokens or 0) + (r.total_output_tokens or 0),
        duration_ms=duration,
        started_at=r.started_at,
        ended_at=r.ended_at,
    )


async def _get_or_404(
    db: AsyncSession, ws: Workspace, workflow_id: uuid.UUID
) -> WorkflowDefinition:
    wf = (
        await db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == workflow_id,
                WorkflowDefinition.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if wf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return wf


async def _validate_links(
    db: AsyncSession,
    ws: Workspace,
    *,
    feature_tag: str | None,
    gateway_alias: str | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """A tag belongs to one live workflow; an alias must be a route in this workspace."""
    if feature_tag:
        q = select(WorkflowDefinition.id, WorkflowDefinition.name).where(
            WorkflowDefinition.workspace_id == ws.id,
            WorkflowDefinition.feature_tag == feature_tag,
            WorkflowDefinition.status != "archived",
        )
        if exclude_id is not None:
            q = q.where(WorkflowDefinition.id != exclude_id)
        clash = (await db.execute(q)).first()
        if clash is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"feature_tag '{feature_tag}' is already linked to workflow '{clash[1]}'",
            )
    if gateway_alias:
        exists = (
            await db.execute(
                select(GatewayRoute.id)
                .where(GatewayRoute.workspace_id == ws.id, GatewayRoute.alias == gateway_alias)
                .limit(1)
            )
        ).scalar_one_or_none()
        if exists is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"No gateway route with alias '{gateway_alias}' in this workspace",
            )


async def _stats_for(
    db: AsyncSession, ws_id: uuid.UUID, workflow_ids: list[uuid.UUID], days: int
) -> dict[uuid.UUID, WorkflowStats]:
    if not workflow_ids:
        return {}
    since = datetime.now(UTC) - timedelta(days=days)
    succeeded = func.count(AgentRun.id).filter(AgentRun.status == RunStatusEnum.succeeded)
    rows = (
        await db.execute(
            select(
                AgentRun.workflow_id,
                func.count(AgentRun.id),
                succeeded,
                func.count(AgentRun.id).filter(AgentRun.status == RunStatusEnum.failed),
                func.coalesce(func.sum(AgentRun.total_cost_usd), 0),
                func.percentile_cont(0.95).within_group(_duration_ms()),
                func.max(AgentRun.started_at),
            )
            .where(
                AgentRun.workspace_id == ws_id,
                AgentRun.workflow_id.in_(workflow_ids),
                AgentRun.started_at >= since,
            )
            .group_by(AgentRun.workflow_id)
        )
    ).all()
    out: dict[uuid.UUID, WorkflowStats] = {}
    for wf_id, runs, ok, failed, cost, p95, last in rows:
        cost_d = Decimal(str(cost or 0))
        out[wf_id] = WorkflowStats(
            window_days=days,
            runs=int(runs or 0),
            succeeded=int(ok or 0),
            failed=int(failed or 0),
            success_rate=round(ok / runs, 4) if runs else None,
            total_cost_usd=cost_d,
            cost_per_success=(cost_d / ok) if ok else None,
            p95_latency_ms=float(p95) if p95 is not None else None,
            last_run_at=last,
        )
    return out


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=WorkflowDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def create_workflow(
    body: WorkflowDefinitionCreate, ws: WorkspaceDep, db: DbDep
) -> WorkflowDefinitionResponse:
    await _validate_links(db, ws, feature_tag=body.feature_tag, gateway_alias=body.gateway_alias)
    wf = WorkflowDefinition(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name.strip(),
        description=body.description,
        feature_tag=body.feature_tag,
        gateway_alias=body.gateway_alias,
        owner=body.owner,
        steps_schema=body.steps_schema,
        status="active",
        config=body.config,
    )
    db.add(wf)
    try:
        await db.flush()
        linked = await link_existing_runs(db, wf)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "feature_tag already linked") from exc
    await db.refresh(wf)
    log.info("workflow_created", workflow_id=str(wf.id), linked_runs=linked)
    return _def_to_response(wf, linked_runs=linked)


@router.get(
    "",
    response_model=WorkflowDefinitionListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_workflows(
    ws: WorkspaceDep,
    db: DbDep,
    response: Response,
    wf_status: Annotated[str | None, Query(alias="status", pattern="^(active|archived)$")] = None,
    q: Annotated[str | None, Query(max_length=200, description="Name or tag contains")] = None,
    feature_tag: Annotated[str | None, Query(max_length=255)] = None,
    api_key_id: uuid.UUID | None = None,
    days: WindowDep = 30,
    sort: Annotated[str, Query(pattern="^(created_at|name|updated_at)$")] = "created_at",
    dir: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",  # noqa: A002
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkflowDefinitionListResponse:
    conds: list[Any] = [WorkflowDefinition.workspace_id == ws.id]
    if wf_status:
        conds.append(WorkflowDefinition.status == wf_status)
    if q:
        like = f"%{q.strip()}%"
        conds.append(
            or_(WorkflowDefinition.name.ilike(like), WorkflowDefinition.feature_tag.ilike(like))
        )
    if feature_tag:
        conds.append(WorkflowDefinition.feature_tag == feature_tag)
    if api_key_id:
        conds.append(
            WorkflowDefinition.id.in_(
                select(AgentRun.workflow_id)
                .where(AgentRun.workspace_id == ws.id, AgentRun.api_key_id == api_key_id)
                .distinct()
            )
        )
    total = int(
        (await db.execute(select(func.count(WorkflowDefinition.id)).where(*conds))).scalar() or 0
    )
    col = getattr(WorkflowDefinition, sort if sort in SORTS else "created_at")
    order = col.asc() if dir == "asc" else col.desc()
    rows = list(
        (
            await db.execute(
                select(WorkflowDefinition)
                .where(*conds)
                .order_by(order, WorkflowDefinition.id)
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    stats = await _stats_for(db, ws.id, [w.id for w in rows], days)
    response.headers["X-Total-Count"] = str(total)
    return WorkflowDefinitionListResponse(
        workflows=[
            _def_to_response(w, stats.get(w.id) or WorkflowStats(window_days=days)) for w in rows
        ],
        total=total,
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDefinitionResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_workflow(
    workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep, days: WindowDep = 30
) -> WorkflowDefinitionResponse:
    wf = await _get_or_404(db, ws, workflow_id)
    stats = await _stats_for(db, ws.id, [wf.id], days)
    return _def_to_response(wf, stats.get(wf.id) or WorkflowStats(window_days=days))


@router.put(
    "/{workflow_id}",
    response_model=WorkflowDefinitionResponse,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def update_workflow(
    workflow_id: uuid.UUID,
    body: WorkflowDefinitionUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> WorkflowDefinitionResponse:
    wf = await _get_or_404(db, ws, workflow_id)
    updates = body.model_dump(exclude_unset=True)
    if "name" in updates and not updates["name"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name cannot be empty")
    new_status = updates.get("status", wf.status)
    new_tag = updates.get("feature_tag", wf.feature_tag)
    new_alias = updates.get("gateway_alias", wf.gateway_alias)
    if new_status != "archived":
        await _validate_links(
            db,
            ws,
            # Re-check the tag when it changes or when an archived workflow is restored.
            feature_tag=new_tag if (new_tag != wf.feature_tag or wf.status == "archived") else None,
            gateway_alias=new_alias if new_alias != wf.gateway_alias else None,
            exclude_id=wf.id,
        )
    relink = (
        new_tag != wf.feature_tag
        or new_alias != wf.gateway_alias
        or (wf.status == "archived" and new_status == "active")
    )
    for field, val in updates.items():
        setattr(wf, field, val)
    wf.updated_at = datetime.now(UTC)
    linked: int | None = None
    try:
        await db.flush()
        if relink:
            linked = await link_existing_runs(db, wf)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "feature_tag already linked") from exc
    await db.refresh(wf)
    return _def_to_response(wf, linked_runs=linked)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def archive_workflow(workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    """Archive: the workflow stops matching new traffic; its runs keep their history."""
    wf = await _get_or_404(db, ws, workflow_id)
    wf.status = "archived"
    wf.updated_at = datetime.now(UTC)
    await db.commit()


# ── Runs (view over agent_runs) ─────────────────────────────────────────────


@router.get(
    "/{workflow_id}/runs",
    response_model=RunSummaryListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_runs(
    workflow_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    response: Response,
    run_status: Annotated[str | None, Query(alias="status")] = None,
    api_key_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    days: Annotated[int | None, Query(ge=1, le=365)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunSummaryListResponse:
    await _get_or_404(db, ws, workflow_id)
    conds: list[Any] = [AgentRun.workspace_id == ws.id, AgentRun.workflow_id == workflow_id]
    if run_status:
        if run_status not in RUN_STATUSES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"status must be one of {sorted(RUN_STATUSES)}",
            )
        conds.append(AgentRun.status == RunStatusEnum(run_status))
    if api_key_id:
        conds.append(AgentRun.api_key_id == api_key_id)
    if agent_id:
        conds.append(AgentRun.agent_id == agent_id)
    if days:
        conds.append(AgentRun.started_at >= datetime.now(UTC) - timedelta(days=days))
    total = int((await db.execute(select(func.count(AgentRun.id)).where(*conds))).scalar() or 0)
    rows = (
        (
            await db.execute(
                select(AgentRun)
                .where(*conds)
                .order_by(AgentRun.started_at.desc(), AgentRun.id)
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    response.headers["X-Total-Count"] = str(total)
    return RunSummaryListResponse(runs=[_run_summary(r) for r in rows], total=total)


# ── Cost attribution ────────────────────────────────────────────────────────


@router.get(
    "/{workflow_id}/cost",
    response_model=WorkflowCostAttribution,
    dependencies=[Depends(analytics_rate_limit)],
)
async def workflow_cost_attribution(
    workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep, days: WindowDep = 30
) -> WorkflowCostAttribution:
    """Cost by step and by model, rolled up from provider calls (B-18).

    A step is a span name within the workflow's runs. Its cost is the sum of the
    provider calls made under it, so steps always add up to what metering priced.
    """
    wf = await _get_or_404(db, ws, workflow_id)
    since = datetime.now(UTC) - timedelta(days=days)
    run_filter = (
        AgentRun.workspace_id == ws.id,
        AgentRun.workflow_id == workflow_id,
        AgentRun.started_at >= since,
    )
    runs, total_cost = (
        await db.execute(
            select(
                func.count(AgentRun.id), func.coalesce(func.sum(AgentRun.total_cost_usd), 0)
            ).where(*run_filter)
        )
    ).one()
    runs = int(runs or 0)
    total = Decimal(str(total_cost or 0))

    call_cost = func.coalesce(func.sum(ProviderCall.cost_usd), 0)
    call_tokens = func.coalesce(
        func.sum(
            func.coalesce(ProviderCall.input_tokens, 0)
            + func.coalesce(ProviderCall.output_tokens, 0)
        ),
        0,
    )
    step_rows = (
        await db.execute(
            select(
                func.coalesce(Span.name, "(no span)"),
                func.min(cast(Span.span_type, String)),
                call_cost,
                func.count(ProviderCall.id),
                call_tokens,
            )
            .select_from(ProviderCall)
            .join(AgentRun, AgentRun.id == ProviderCall.run_id)
            .outerjoin(Span, Span.id == ProviderCall.span_id)
            .where(*run_filter)
            .group_by(Span.name)
            .order_by(call_cost.desc())
            .limit(50)
        )
    ).all()
    steps: list[StepCostBreakdown] = []
    steps_cost = Decimal("0")
    for name, span_type, cost, calls, tokens in step_rows:
        cost_d = Decimal(str(cost or 0))
        steps_cost += cost_d
        steps.append(
            StepCostBreakdown(
                step_name=str(name),
                step_type=str(span_type or "llm"),
                total_cost=cost_d,
                avg_cost=(cost_d / calls) if calls else Decimal("0"),
                invocation_count=int(calls or 0),
                total_tokens=int(tokens or 0),
            )
        )
    model_rows = (
        await db.execute(
            select(
                ProviderCall.provider,
                ProviderCall.model,
                func.count(ProviderCall.id),
                call_cost,
                call_tokens,
            )
            .join(AgentRun, AgentRun.id == ProviderCall.run_id)
            .where(*run_filter)
            .group_by(ProviderCall.provider, ProviderCall.model)
            .order_by(call_cost.desc())
            .limit(25)
        )
    ).all()
    return WorkflowCostAttribution(
        workflow_id=wf.id,
        workflow_name=wf.name,
        window_days=days,
        total_runs=runs,
        total_cost=total,
        avg_cost_per_run=(total / runs) if runs else Decimal("0"),
        steps_cost=steps_cost,
        cost_by_step=steps,
        cost_by_model=[
            ModelCostBreakdown(
                provider=str(p),
                model=str(m),
                calls=int(c or 0),
                total_cost=Decimal(str(cost or 0)),
                total_tokens=int(t or 0),
            )
            for p, m, c, cost, t in model_rows
        ],
    )


# ── Overview (Workflow page + health card) ──────────────────────────────────


def _period_start(period_type: str, now: datetime) -> datetime | None:
    if period_type == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_type == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None  # total


async def _health(
    db: AsyncSession, ws_id: uuid.UUID, wf_id: uuid.UUID, days: int
) -> WorkflowHealth:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    base = (
        AgentRun.workspace_id == ws_id,
        AgentRun.workflow_id == wf_id,
        AgentRun.started_at >= since,
    )
    dur = _duration_ms()
    runs, ok, failed, cost, p50, p95 = (
        await db.execute(
            select(
                func.count(AgentRun.id),
                func.count(AgentRun.id).filter(AgentRun.status == RunStatusEnum.succeeded),
                func.count(AgentRun.id).filter(AgentRun.status == RunStatusEnum.failed),
                func.coalesce(func.sum(AgentRun.total_cost_usd), 0),
                func.percentile_cont(0.5).within_group(dur),
                func.percentile_cont(0.95).within_group(dur),
            ).where(*base)
        )
    ).one()
    runs, ok, failed = int(runs or 0), int(ok or 0), int(failed or 0)
    cost_d = Decimal(str(cost or 0))

    day = func.date_trunc("day", AgentRun.started_at)
    run_trend = {
        d.date().isoformat(): (int(n or 0), Decimal(str(c or 0)))
        for d, n, c in (
            await db.execute(
                select(
                    day,
                    func.count(AgentRun.id),
                    func.coalesce(func.sum(AgentRun.total_cost_usd), 0),
                )
                .where(*base)
                .group_by(day)
            )
        ).all()
        if d is not None
    }
    score_day = func.date_trunc("day", ScoreEvent.created_at)
    score_trend = {
        d.date().isoformat(): (float(avg), int(n or 0))
        for d, avg, n in (
            await db.execute(
                select(score_day, func.avg(ScoreEvent.value), func.count(ScoreEvent.id))
                .join(AgentRun, AgentRun.id == ScoreEvent.run_id)
                .where(*base, ScoreEvent.workspace_id == ws_id)
                .group_by(score_day)
            )
        ).all()
        if d is not None and avg is not None
    }
    trend: list[TrendPoint] = []
    start: date = since.date()
    for i in range(days + 1):
        key = (start + timedelta(days=i)).isoformat()
        n, c = run_trend.get(key, (0, Decimal("0")))
        avg, sn = score_trend.get(key, (None, 0))
        trend.append(TrendPoint(day=key, runs=n, cost_usd=c, avg_score=avg, scores=sn))

    total_scores = sum(n for _, n in score_trend.values())
    avg_score = sum(a * n for a, n in score_trend.values()) / total_scores if total_scores else None
    half = len(trend) // 2

    def _avg(points: list[TrendPoint]) -> float | None:
        n = sum(p.scores for p in points)
        return sum((p.avg_score or 0) * p.scores for p in points) / n if n else None

    first, second = _avg(trend[:half]), _avg(trend[half:])
    return WorkflowHealth(
        window_days=days,
        runs=runs,
        succeeded=ok,
        failed=failed,
        success_rate=round(ok / runs, 4) if runs else None,
        total_cost_usd=cost_d,
        cost_per_success=(cost_d / ok) if ok else None,
        p50_latency_ms=float(p50) if p50 is not None else None,
        p95_latency_ms=float(p95) if p95 is not None else None,
        avg_eval_score=round(avg_score, 4) if avg_score is not None else None,
        eval_score_delta=round(second - first, 4)
        if first is not None and second is not None
        else None,
        trend=trend,
    )


@router.get(
    "/{workflow_id}/overview",
    response_model=WorkflowOverview,
    dependencies=[Depends(analytics_rate_limit)],
)
async def workflow_overview(
    workflow_id: uuid.UUID, ws: WorkspaceDep, db: DbDep, days: WindowDep = 30
) -> WorkflowOverview:
    """The Workflow page in one call: health, budgets, evals, policies and agents."""
    wf = await _get_or_404(db, ws, workflow_id)
    health = await _health(db, ws.id, wf.id, days)
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    budgets: list[WorkflowBudget] = []
    if wf.feature_tag:
        rows = (
            (
                await db.execute(
                    select(Budget).where(
                        Budget.workspace_id == ws.id,
                        Budget.is_active.is_(True),
                        Budget.scope_type == "feature_tag",
                        Budget.scope_id == wf.feature_tag,
                    )
                )
            )
            .scalars()
            .all()
        )
        for b in rows:
            start = _period_start(b.period_type, now)
            spent_q = select(func.coalesce(func.sum(AgentRun.total_cost_usd), 0)).where(
                AgentRun.workspace_id == ws.id, AgentRun.workflow_id == wf.id
            )
            if start is not None:
                spent_q = spent_q.where(AgentRun.started_at >= start)
            spent = Decimal(str((await db.execute(spent_q)).scalar() or 0))
            budgets.append(
                WorkflowBudget(
                    id=b.id,
                    scope_type=b.scope_type,
                    scope_id=b.scope_id,
                    period_type=b.period_type,
                    limit_usd=b.limit_usd,
                    action=b.action,
                    spent_usd=spent,
                )
            )

    evals = [
        WorkflowEval(name=str(name), avg_score=round(float(avg), 4), count=int(n))
        for name, avg, n in (
            await db.execute(
                select(ScoreEvent.name, func.avg(ScoreEvent.value), func.count(ScoreEvent.id))
                .join(AgentRun, AgentRun.id == ScoreEvent.run_id)
                .where(
                    ScoreEvent.workspace_id == ws.id,
                    AgentRun.workflow_id == wf.id,
                    AgentRun.started_at >= since,
                )
                .group_by(ScoreEvent.name)
                .order_by(func.count(ScoreEvent.id).desc())
                .limit(20)
            )
        ).all()
        if avg is not None
    ]

    policies: list[WorkflowPolicy] = []
    if wf.gateway_alias:
        routes = (
            (
                await db.execute(
                    select(GatewayRoute).where(
                        GatewayRoute.workspace_id == ws.id,
                        GatewayRoute.alias == wf.gateway_alias,
                        GatewayRoute.is_active.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        for r in routes:
            flags = [
                label
                for label, on in (
                    ("PII redaction", r.pii_redaction_enabled),
                    ("semantic cache", r.semantic_cache_enabled),
                    ("intelligent routing", r.intelligent_routing_enabled),
                    ("daily cap", r.daily_cost_limit_usd is not None),
                    ("monthly cap", r.monthly_cost_limit_usd is not None),
                )
                if on
            ]
            policies.append(
                WorkflowPolicy(
                    kind="route",
                    name=f"{r.alias} → {r.provider}/{r.target_model}",
                    detail=", ".join(flags) or "no route controls",
                    href="/gateway?tab=routes",
                )
            )
        rp = (
            await db.execute(
                select(RoutingPolicy).where(
                    RoutingPolicy.workspace_id == ws.id,
                    RoutingPolicy.alias == wf.gateway_alias,
                    RoutingPolicy.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if rp is not None:
            policies.append(
                WorkflowPolicy(
                    kind="routing_policy",
                    name=f"Routing policy on {rp.alias}",
                    detail=rp.policy_type,
                    href="/gateway?tab=policies",
                )
            )
    guardrails = int(
        (
            await db.execute(
                select(func.count(GuardrailRule.id)).where(
                    GuardrailRule.workspace_id == ws.id, GuardrailRule.status == "active"
                )
            )
        ).scalar()
        or 0
    )
    if guardrails:
        policies.append(
            WorkflowPolicy(
                kind="guardrails",
                name="Workspace guardrail rules",
                detail=f"{guardrails} active, applied to gateway traffic",
                href="/guardrails",
            )
        )
    tool_policies = int(
        (
            await db.execute(
                select(func.count(ToolPolicy.id)).where(
                    ToolPolicy.workspace_id == ws.id, ToolPolicy.is_active.is_(True)
                )
            )
        ).scalar()
        or 0
    )
    if tool_policies:
        policies.append(
            WorkflowPolicy(
                kind="tool_policies",
                name="Tool policies",
                detail=f"{tool_policies} active in this workspace",
                href="/tool-registry",
            )
        )

    agents = [
        WorkflowAgentUsage(
            id=aid, name=str(name), runs=int(n or 0), total_cost_usd=Decimal(str(c or 0))
        )
        for aid, name, n, c in (
            await db.execute(
                select(
                    Agent.id,
                    Agent.name,
                    func.count(AgentRun.id),
                    func.coalesce(func.sum(AgentRun.total_cost_usd), 0),
                )
                .join(AgentRun, AgentRun.agent_id == Agent.id)
                .where(
                    AgentRun.workspace_id == ws.id,
                    AgentRun.workflow_id == wf.id,
                    AgentRun.started_at >= since,
                )
                .group_by(Agent.id, Agent.name)
                .order_by(func.count(AgentRun.id).desc())
                .limit(20)
            )
        ).all()
    ]

    stats = WorkflowStats(
        window_days=days,
        runs=health.runs,
        succeeded=health.succeeded,
        failed=health.failed,
        success_rate=health.success_rate,
        total_cost_usd=health.total_cost_usd,
        cost_per_success=health.cost_per_success,
        p95_latency_ms=health.p95_latency_ms,
    )
    return WorkflowOverview(
        workflow=_def_to_response(wf, stats),
        health=health,
        budgets=budgets,
        evals=evals,
        policies=policies,
        agents=agents,
    )
