"""
Agent Registry, Lifecycle & Memory API.

Prefix: /agents
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /agents                              Register an agent
GET    /agents                              List agents
GET    /agents/{id}                         Get agent detail
PUT    /agents/{id}                         Update agent
DELETE /agents/{id}                         Retire agent
GET    /agents/{id}/runs                    List agent runs
GET    /agents/{id}/stats                   Agent cost/performance summary

POST   /agents/{id}/memory                  Store a memory
GET    /agents/{id}/memory                  List memories
GET    /agents/{id}/memory/stats            Memory usage stats
POST   /agents/{id}/memory/search           Search memories
GET    /agents/{id}/memory/audit            Memory audit log
PUT    /agents/{id}/memory/{key}            Update a memory
DELETE /agents/{id}/memory/{key}            Delete a memory
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

import sqlalchemy as sa
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.agents import (
    Agent,
    AgentMemory,
    AgentMemoryAudit,
    WorkflowRun,
    WorkflowStep,
)
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.agents import (
    AgentCreate,
    AgentListResponse,
    AgentMemoryAuditListResponse,
    AgentMemoryAuditResponse,
    AgentMemoryCreate,
    AgentMemoryListResponse,
    AgentMemoryResponse,
    AgentMemorySearchRequest,
    AgentMemoryStats,
    AgentMemoryUpdate,
    AgentResponse,
    AgentStats,
    AgentUpdate,
    WorkflowRunSummary,
    WorkflowRunSummaryListResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/agents", tags=["agents"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _agent_to_response(a: Agent) -> AgentResponse:
    return AgentResponse(
        id=a.id,
        workspace_id=a.workspace_id,
        name=a.name,
        description=a.description,
        agent_type=a.agent_type,
        owner=a.owner,
        default_model=a.default_model,
        default_tools=a.default_tools or [],
        budget_envelope=a.budget_envelope,
        policy_profile=a.policy_profile,
        status=a.status,
        config=a.config or {},
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


# ── CRUD ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def create_agent(body: AgentCreate, ws: WorkspaceDep, db: DbDep) -> AgentResponse:
    agent = Agent(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        agent_type=body.agent_type,
        owner=body.owner,
        default_model=body.default_model,
        default_tools=body.default_tools,
        budget_envelope=body.budget_envelope,
        policy_profile=body.policy_profile,
        status=body.status,
        config=body.config,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_to_response(agent)


@router.get(
    "",
    response_model=AgentListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_agents(
    ws: WorkspaceDep,
    db: DbDep,
    agent_status: str | None = Query(None, alias="status"),
    agent_type: str | None = Query(None),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AgentListResponse:
    q = select(Agent).where(Agent.workspace_id == ws.id)
    count_q = select(func.count(Agent.id)).where(Agent.workspace_id == ws.id)

    if agent_status:
        q = q.where(Agent.status == agent_status)
        count_q = count_q.where(Agent.status == agent_status)
    if agent_type:
        q = q.where(Agent.agent_type == agent_type)
        count_q = count_q.where(Agent.agent_type == agent_type)
    if access_group_id or api_key_id:
        import uuid as _uuid

        run_sub = select(WorkflowRun.agent_id).where(
            WorkflowRun.workspace_id == ws.id,
            WorkflowRun.agent_id.isnot(None),
        )
        if access_group_id:
            run_sub = run_sub.where(WorkflowRun.access_group_id == _uuid.UUID(access_group_id))
        if api_key_id:
            run_sub = run_sub.where(WorkflowRun.api_key_id == _uuid.UUID(api_key_id))
        run_sub = run_sub.distinct()
        q = q.where(Agent.id.in_(run_sub))
        count_q = count_q.where(Agent.id.in_(run_sub))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (await db.execute(q.order_by(Agent.created_at.desc()).offset(offset).limit(limit)))
        .scalars()
        .all()
    )

    return AgentListResponse(
        agents=[_agent_to_response(a) for a in rows],
        total=total,
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_agent(agent_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> AgentResponse:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    return _agent_to_response(agent)


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_agent(
    agent_id: uuid.UUID, body: AgentUpdate, ws: WorkspaceDep, db: DbDep
) -> AgentResponse:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, val)
    agent.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(agent)
    return _agent_to_response(agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def retire_agent(agent_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    agent.status = "retired"
    agent.updated_at = datetime.now(UTC)
    await db.commit()


# ── Agent Runs ──────────────────────────────────────────────────────────────


@router.get(
    "/{agent_id}/runs",
    response_model=WorkflowRunSummaryListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_agent_runs(
    agent_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    run_status: str | None = Query(None, alias="status"),
    access_group_id: str | None = Query(None),
    api_key_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> WorkflowRunSummaryListResponse:
    base = select(WorkflowRun).where(
        WorkflowRun.agent_id == agent_id,
        WorkflowRun.workspace_id == ws.id,
    )
    count_q = select(func.count(WorkflowRun.id)).where(
        WorkflowRun.agent_id == agent_id,
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

    return WorkflowRunSummaryListResponse(
        runs=[
            WorkflowRunSummary(
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
                error=r.error,
                started_at=r.started_at,
                completed_at=r.completed_at,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
    )


# ── Agent Stats ─────────────────────────────────────────────────────────────


@router.get(
    "/{agent_id}/stats",
    response_model=AgentStats,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_agent_stats(agent_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> AgentStats:
    # Verify agent exists
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")

    # Aggregate run stats
    agg = (
        await db.execute(
            select(
                func.count(WorkflowRun.id).label("total_runs"),
                func.count(WorkflowRun.id)
                .filter(WorkflowRun.status == "completed")
                .label("completed"),
                func.count(WorkflowRun.id).filter(WorkflowRun.status == "failed").label("failed"),
                func.coalesce(func.sum(WorkflowRun.total_cost), 0).label("total_cost"),
                func.coalesce(func.sum(WorkflowRun.total_tokens), 0).label("total_tokens"),
                func.avg(WorkflowRun.total_duration_ms).label("avg_duration"),
                func.max(WorkflowRun.created_at).label("last_run"),
            ).where(
                WorkflowRun.agent_id == agent_id,
                WorkflowRun.workspace_id == ws.id,
            )
        )
    ).one()

    total_runs: int = agg.total_runs or 0
    completed: int = agg.completed or 0

    # Models used (from steps)
    models_q = (
        (
            await db.execute(
                select(distinct(WorkflowStep.model))
                .join(WorkflowRun, WorkflowStep.run_id == WorkflowRun.id)
                .where(
                    WorkflowRun.agent_id == agent_id,
                    WorkflowRun.workspace_id == ws.id,
                    WorkflowStep.model.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )

    tools_q = (
        (
            await db.execute(
                select(distinct(WorkflowStep.tool))
                .join(WorkflowRun, WorkflowStep.run_id == WorkflowRun.id)
                .where(
                    WorkflowRun.agent_id == agent_id,
                    WorkflowRun.workspace_id == ws.id,
                    WorkflowStep.tool.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )

    return AgentStats(
        agent_id=agent_id,
        total_runs=total_runs,
        completed_runs=completed,
        failed_runs=agg.failed or 0,
        total_cost=Decimal(str(agg.total_cost)),
        total_tokens=agg.total_tokens or 0,
        avg_duration_ms=float(agg.avg_duration) if agg.avg_duration else None,
        success_rate=round(completed / total_runs, 4) if total_runs > 0 else None,
        last_run_at=agg.last_run,
        models_used=list(models_q),
        tools_used=list(tools_q),
    )


# ── Agent Memory ────────────────────────────────────────────────────────────

_PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
]

import re  # noqa: E402

_PII_RE = [re.compile(p) for p in _PII_PATTERNS]


def _detect_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_RE)


def _memory_to_response(m: AgentMemory) -> AgentMemoryResponse:
    return AgentMemoryResponse(
        id=m.id,
        workspace_id=m.workspace_id,
        agent_id=m.agent_id,
        key=m.key,
        value=m.value,
        memory_type=m.memory_type,
        metadata=m.metadata_ or {},
        size_bytes=m.size_bytes,
        access_count=m.access_count,
        has_pii=m.has_pii,
        retention_days=m.retention_days,
        expires_at=m.expires_at,
        last_accessed_at=m.last_accessed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


async def _audit_log(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    agent_id: uuid.UUID,
    action: str,
    *,
    memory_id: uuid.UUID | None = None,
    key: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AgentMemoryAudit(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            agent_id=agent_id,
            memory_id=memory_id,
            action=action,
            key=key,
            details=details or {},
        )
    )


@router.post(
    "/{agent_id}/memory",
    response_model=AgentMemoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit)],
)
async def store_memory(
    agent_id: uuid.UUID,
    body: AgentMemoryCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AgentMemoryResponse:
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")

    has_pii = _detect_pii(body.value) or _detect_pii(body.key)
    size_bytes = len(body.value.encode("utf-8"))

    expires_at = None
    if body.retention_days:
        from datetime import timedelta  # noqa: PLC0415

        expires_at = datetime.now(UTC) + timedelta(days=body.retention_days)

    mem = AgentMemory(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        agent_id=agent_id,
        key=body.key,
        value=body.value,
        memory_type=body.memory_type,
        metadata_=body.metadata,
        size_bytes=size_bytes,
        has_pii=has_pii,
        retention_days=body.retention_days,
        expires_at=expires_at,
    )
    db.add(mem)
    await _audit_log(
        db,
        ws.id,
        agent_id,
        "store",
        memory_id=mem.id,
        key=body.key,
        details={"memory_type": body.memory_type, "size_bytes": size_bytes, "has_pii": has_pii},
    )
    await db.commit()
    await db.refresh(mem)
    return _memory_to_response(mem)


@router.get(
    "/{agent_id}/memory",
    response_model=AgentMemoryListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_memories(
    agent_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    memory_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AgentMemoryListResponse:
    q = select(AgentMemory).where(
        AgentMemory.agent_id == agent_id, AgentMemory.workspace_id == ws.id
    )
    count_q = select(func.count(AgentMemory.id)).where(
        AgentMemory.agent_id == agent_id, AgentMemory.workspace_id == ws.id
    )
    if memory_type:
        q = q.where(AgentMemory.memory_type == memory_type)
        count_q = count_q.where(AgentMemory.memory_type == memory_type)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (await db.execute(q.order_by(AgentMemory.updated_at.desc()).offset(offset).limit(limit)))
        .scalars()
        .all()
    )
    return AgentMemoryListResponse(
        memories=[_memory_to_response(m) for m in rows],
        total=total,
    )


@router.put(
    "/{agent_id}/memory/{key:path}",
    response_model=AgentMemoryResponse,
    dependencies=[Depends(management_rate_limit)],
)
async def update_memory(
    agent_id: uuid.UUID,
    key: str,
    body: AgentMemoryUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AgentMemoryResponse:
    mem = (
        await db.execute(
            select(AgentMemory).where(
                AgentMemory.agent_id == agent_id,
                AgentMemory.workspace_id == ws.id,
                AgentMemory.key == key,
            )
        )
    ).scalar_one_or_none()
    if not mem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory not found")

    updates = body.model_dump(exclude_unset=True)
    if "value" in updates and updates["value"] is not None:
        mem.value = updates["value"]
        mem.size_bytes = len(updates["value"].encode("utf-8"))
        mem.has_pii = _detect_pii(updates["value"])
    if "memory_type" in updates and updates["memory_type"] is not None:
        mem.memory_type = updates["memory_type"]
    if "metadata" in updates and updates["metadata"] is not None:
        mem.metadata_ = updates["metadata"]
    if "retention_days" in updates:
        mem.retention_days = updates["retention_days"]
        if updates["retention_days"]:
            from datetime import timedelta  # noqa: PLC0415

            mem.expires_at = datetime.now(UTC) + timedelta(days=updates["retention_days"])
        else:
            mem.expires_at = None

    mem.updated_at = datetime.now(UTC)
    await _audit_log(
        db,
        ws.id,
        agent_id,
        "update",
        memory_id=mem.id,
        key=key,
        details={k: str(v) for k, v in updates.items()},
    )
    await db.commit()
    await db.refresh(mem)
    return _memory_to_response(mem)


@router.delete(
    "/{agent_id}/memory/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit)],
)
async def delete_memory(
    agent_id: uuid.UUID,
    key: str,
    ws: WorkspaceDep,
    db: DbDep,
) -> None:
    mem = (
        await db.execute(
            select(AgentMemory).where(
                AgentMemory.agent_id == agent_id,
                AgentMemory.workspace_id == ws.id,
                AgentMemory.key == key,
            )
        )
    ).scalar_one_or_none()
    if not mem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory not found")

    await _audit_log(
        db,
        ws.id,
        agent_id,
        "delete",
        memory_id=mem.id,
        key=key,
        details={"memory_type": mem.memory_type, "size_bytes": mem.size_bytes},
    )
    await db.delete(mem)
    await db.commit()


@router.post(
    "/{agent_id}/memory/search",
    response_model=AgentMemoryListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def search_memories(
    agent_id: uuid.UUID,
    body: AgentMemorySearchRequest,
    ws: WorkspaceDep,
    db: DbDep,
) -> AgentMemoryListResponse:
    q = select(AgentMemory).where(
        AgentMemory.agent_id == agent_id,
        AgentMemory.workspace_id == ws.id,
    )
    if body.memory_type:
        q = q.where(AgentMemory.memory_type == body.memory_type)

    pattern = f"%{body.query}%"
    q = q.where(
        sa.or_(
            AgentMemory.key.ilike(pattern),
            AgentMemory.value.ilike(pattern),
        )
    )
    rows = (
        (await db.execute(q.order_by(AgentMemory.access_count.desc()).limit(body.limit)))
        .scalars()
        .all()
    )

    # Bump access counts
    for m in rows:
        m.access_count += 1
        m.last_accessed_at = datetime.now(UTC)
    if rows:
        await db.commit()

    return AgentMemoryListResponse(
        memories=[_memory_to_response(m) for m in rows],
        total=len(rows),
    )


@router.get(
    "/{agent_id}/memory/stats",
    response_model=AgentMemoryStats,
    dependencies=[Depends(analytics_rate_limit)],
)
async def memory_stats(
    agent_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> AgentMemoryStats:
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id, Agent.workspace_id == ws.id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")

    # Totals
    agg = (
        await db.execute(
            select(
                func.count(AgentMemory.id).label("total"),
                func.coalesce(func.sum(AgentMemory.size_bytes), 0).label("total_size"),
                func.count(AgentMemory.id).filter(AgentMemory.has_pii.is_(True)).label("pii_count"),
                func.count(AgentMemory.id)
                .filter(AgentMemory.expires_at < func.now())
                .label("expired"),
            ).where(AgentMemory.agent_id == agent_id, AgentMemory.workspace_id == ws.id)
        )
    ).one()

    # By type
    type_rows = (
        await db.execute(
            select(AgentMemory.memory_type, func.count(AgentMemory.id))
            .where(AgentMemory.agent_id == agent_id, AgentMemory.workspace_id == ws.id)
            .group_by(AgentMemory.memory_type)
        )
    ).all()
    by_type = {row[0]: row[1] for row in type_rows}

    # Most accessed
    top = (
        (
            await db.execute(
                select(AgentMemory)
                .where(AgentMemory.agent_id == agent_id, AgentMemory.workspace_id == ws.id)
                .order_by(AgentMemory.access_count.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    return AgentMemoryStats(
        agent_id=agent_id,
        total_memories=agg.total or 0,
        total_size_bytes=agg.total_size or 0,
        by_type=by_type,
        pii_count=agg.pii_count or 0,
        expired_count=agg.expired or 0,
        most_accessed=[_memory_to_response(m) for m in top],
    )


@router.get(
    "/{agent_id}/memory/audit",
    response_model=AgentMemoryAuditListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def memory_audit_log(
    agent_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AgentMemoryAuditListResponse:
    count_q = select(func.count(AgentMemoryAudit.id)).where(
        AgentMemoryAudit.agent_id == agent_id, AgentMemoryAudit.workspace_id == ws.id
    )
    total = (await db.execute(count_q)).scalar() or 0

    rows = (
        (
            await db.execute(
                select(AgentMemoryAudit)
                .where(
                    AgentMemoryAudit.agent_id == agent_id, AgentMemoryAudit.workspace_id == ws.id
                )
                .order_by(AgentMemoryAudit.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return AgentMemoryAuditListResponse(
        events=[
            AgentMemoryAuditResponse(
                id=e.id,
                workspace_id=e.workspace_id,
                agent_id=e.agent_id,
                memory_id=e.memory_id,
                action=e.action,
                key=e.key,
                details=e.details or {},
                actor=e.actor,
                created_at=e.created_at,
            )
            for e in rows
        ],
        total=total,
    )
