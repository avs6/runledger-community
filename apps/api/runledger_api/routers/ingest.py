from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import ingest_rate_limit
from runledger_api.models.events import AgentRun
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.events import AgentRunResponse, BatchIngestRequest, IngestEvent
from runledger_api.services.quotas import check_quota, increment_quota_usage
from runledger_api.workers.pipeline import process_events_task

log = structlog.get_logger()

router = APIRouter(prefix="/ingest/v1", tags=["ingest"], dependencies=[Depends(ingest_rate_limit)])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post("/events", status_code=202)
async def ingest_event(
    event: IngestEvent,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, int]:
    """Ingest a single event. Returns 202 immediately; processing is async."""
    await check_quota(workspace.tenant_id, db)
    process_events_task.delay(
        workspace_id=str(workspace.id),
        events=[event.model_dump(mode="json")],
    )
    await increment_quota_usage(workspace.tenant_id, 1, db)
    await db.commit()
    log.debug("event_accepted", workspace_id=str(workspace.id), event_type=event.event_type)
    return {"accepted": 1}


@router.post("/batch", status_code=202)
async def ingest_batch(
    payload: BatchIngestRequest,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, int]:
    """Ingest a batch of events. Returns 202 immediately."""
    if not payload.events:
        return {"accepted": 0}
    await check_quota(workspace.tenant_id, db)
    process_events_task.delay(
        workspace_id=str(workspace.id),
        events=[e.model_dump(mode="json") for e in payload.events],
    )
    await increment_quota_usage(workspace.tenant_id, len(payload.events), db)
    await db.commit()
    log.debug("batch_accepted", workspace_id=str(workspace.id), count=len(payload.events))
    return {"accepted": len(payload.events)}


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AgentRun]:
    """List agent runs for the authenticated workspace, newest first."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
