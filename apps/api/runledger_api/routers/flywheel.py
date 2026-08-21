"""
Optimization Flywheel API (Phase 7).

Prefix: /gateway/flywheel
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET  /gateway/flywheel/settings                 Current flywheel settings (creates defaults)
PUT  /gateway/flywheel/settings                 Update SLA / metric / mode / segmentation
GET  /gateway/flywheel/recommendations          List recommendations (filter by status)
POST /gateway/flywheel/recommendations/{id}/apply    Apply a pending recommendation
POST /gateway/flywheel/recommendations/{id}/dismiss  Dismiss a pending recommendation
POST /gateway/flywheel/run                      Run the analysis loop now (manual trigger)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.flywheel import FlywheelRecommendation
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.flywheel import (
    FlywheelRecommendationList,
    FlywheelRecommendationResponse,
    FlywheelRunResponse,
    FlywheelSettingsResponse,
    FlywheelSettingsUpdate,
)
from runledger_api.services import flywheel

router = APIRouter(
    prefix="/gateway/flywheel",
    tags=["flywheel"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]

_VALID_APPLY_MODES = {"approval", "auto", "off"}
_VALID_SEGMENT_BY = {"outcome_type", "task_class", "alias"}


@router.get("/settings", response_model=FlywheelSettingsResponse)
async def get_flywheel_settings(db: DbDep, workspace: WorkspaceDep) -> FlywheelSettingsResponse:
    s = await flywheel.get_settings(db, workspace.id)
    return FlywheelSettingsResponse.model_validate(s)


@router.put("/settings", response_model=FlywheelSettingsResponse)
async def update_flywheel_settings(
    body: FlywheelSettingsUpdate, db: DbDep, workspace: WorkspaceDep
) -> FlywheelSettingsResponse:
    s = await flywheel.get_settings(db, workspace.id)
    data = body.model_dump(exclude_unset=True)
    if "apply_mode" in data and data["apply_mode"] not in _VALID_APPLY_MODES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "apply_mode must be approval|auto|off"
        )
    if "segment_by" in data and data["segment_by"] not in _VALID_SEGMENT_BY:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "segment_by must be outcome_type|task_class|alias"
        )
    for k, v in data.items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return FlywheelSettingsResponse.model_validate(s)


@router.get("/recommendations", response_model=FlywheelRecommendationList)
async def list_recommendations(
    db: DbDep,
    workspace: WorkspaceDep,
    status_filter: str | None = Query(default="pending", alias="status"),
    access_group_id: str | None = Query(default=None),
    api_key_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> FlywheelRecommendationList:
    stmt = select(FlywheelRecommendation).where(FlywheelRecommendation.workspace_id == workspace.id)
    count_stmt = (
        select(func.count())
        .select_from(FlywheelRecommendation)
        .where(FlywheelRecommendation.workspace_id == workspace.id)
    )
    if status_filter and status_filter != "all":
        stmt = stmt.where(FlywheelRecommendation.status == status_filter)
        count_stmt = count_stmt.where(FlywheelRecommendation.status == status_filter)
    if access_group_id:
        stmt = stmt.where(FlywheelRecommendation.segment_key == access_group_id)
        count_stmt = count_stmt.where(FlywheelRecommendation.segment_key == access_group_id)
    if api_key_id:
        stmt = stmt.where(FlywheelRecommendation.segment_key == api_key_id)
        count_stmt = count_stmt.where(FlywheelRecommendation.segment_key == api_key_id)
    stmt = stmt.order_by(FlywheelRecommendation.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return FlywheelRecommendationList(
        items=[FlywheelRecommendationResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.post("/recommendations/{rec_id}/apply", response_model=FlywheelRecommendationResponse)
async def apply_recommendation(
    rec_id: str, db: DbDep, workspace: WorkspaceDep
) -> FlywheelRecommendationResponse:
    ok = await flywheel.apply_recommendation(db, workspace.id, rec_id, mode="approval")
    rec = await db.get(FlywheelRecommendation, rec_id)
    if rec is None or rec.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation not found")
    if rec.status not in ("applied",) and not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, "recommendation not in a pending state")
    return FlywheelRecommendationResponse.model_validate(rec)


@router.post("/recommendations/{rec_id}/dismiss", response_model=FlywheelRecommendationResponse)
async def dismiss_recommendation(
    rec_id: str, db: DbDep, workspace: WorkspaceDep
) -> FlywheelRecommendationResponse:
    ok = await flywheel.dismiss_recommendation(db, workspace.id, rec_id)
    rec = await db.get(FlywheelRecommendation, rec_id)
    if rec is None or rec.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation not found")
    if not ok and rec.status != "dismissed":
        raise HTTPException(status.HTTP_409_CONFLICT, "recommendation not in a pending state")
    return FlywheelRecommendationResponse.model_validate(rec)


@router.post("/run", response_model=FlywheelRunResponse)
async def run_flywheel(db: DbDep, workspace: WorkspaceDep) -> FlywheelRunResponse:
    if not flywheel.enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "flywheel service not configured")
    result = await flywheel.run_analysis(db, workspace.id)
    return FlywheelRunResponse(
        status=result["status"],
        recommendations=result.get("recommendations", 0),
        auto_applied=result.get("auto_applied", 0),
    )
