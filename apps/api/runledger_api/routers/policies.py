"""Unified policy decision endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.policies import (
    FinopsSimulationRequest,
    FinopsSimulationResponse,
    PolicyCheckRequest,
    PolicyCheckResponse,
    ToolCostAccountingResponse,
)
from runledger_api.services.policies import (
    evaluate_policy_check,
    get_tool_cost_accounting,
    simulate_finops_policy,
)

router = APIRouter(
    prefix="/policies",
    tags=["policies"],
    dependencies=[Depends(management_rate_limit)],
)


@router.post("/check", response_model=PolicyCheckResponse)
async def check_policy(
    body: PolicyCheckRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> PolicyCheckResponse:
    return await evaluate_policy_check(
        db=db,
        redis=redis,
        workspace_id=workspace.id,
        body=body,
    )


@router.post("/simulate-finops", response_model=FinopsSimulationResponse)
async def simulate_finops(
    body: FinopsSimulationRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> FinopsSimulationResponse:
    return await simulate_finops_policy(
        db=db,
        redis=redis,
        workspace_id=workspace.id,
        body=body,
    )


@router.get("/tool-costs", response_model=ToolCostAccountingResponse)
async def tool_costs(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolCostAccountingResponse:
    now = datetime.now(UTC)
    return await get_tool_cost_accounting(
        db=db,
        workspace_id=workspace.id,
        from_dt=now - timedelta(days=7),
        to_dt=now,
    )
