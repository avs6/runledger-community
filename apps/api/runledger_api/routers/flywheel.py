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
POST /gateway/flywheel/recommendations/{id}/rollback Restore the route an applied rec changed
POST /gateway/flywheel/run                      Run the analysis loop now (manual trigger)

Roles (core/role_matrix.py, review G-03/G-17): reads need any member; run and dismiss a
workspace admin; apply, rollback and settings (which can enable auto-apply) an org admin.
Every mutation writes an audit event (review G-10).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.role_matrix import gateway_role
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
from runledger_api.services.admin_audit import audit_change, changed_only, snapshot

router = APIRouter(
    prefix="/gateway/flywheel",
    tags=["flywheel"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]

_VALID_APPLY_MODES = {"approval", "auto", "off"}
_VALID_SEGMENT_BY = {"outcome_type", "task_class", "alias"}
_SETTINGS_FIELDS = (
    "enabled",
    "apply_mode",
    "quality_metric",
    "min_quality",
    "segment_by",
    "action_space",
    "min_sample_size",
    "lookback_days",
)
_REC_FIELDS = ("status", "segment_by", "segment_key", "proposed_config", "applied_route_id")

ApplyDep = Annotated[tuple, Depends(gateway_role("flywheel", "apply"))]
WriteDep = Annotated[tuple, Depends(gateway_role("flywheel", "write"))]


@router.get("/settings", response_model=FlywheelSettingsResponse)
async def get_flywheel_settings(db: DbDep, workspace: WorkspaceDep) -> FlywheelSettingsResponse:
    s = await flywheel.get_settings(db, workspace.id)
    return FlywheelSettingsResponse.model_validate(s)


@router.put("/settings", response_model=FlywheelSettingsResponse)
async def update_flywheel_settings(
    body: FlywheelSettingsUpdate, db: DbDep, auth: ApplyDep
) -> FlywheelSettingsResponse:
    workspace = auth[0]
    s = await flywheel.get_settings(db, workspace.id)
    before = snapshot(s, _SETTINGS_FIELDS)
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
    b, a = changed_only(before, snapshot(s, _SETTINGS_FIELDS))
    await audit_change(
        db,
        workspace.id,
        "flywheel.settings_updated",
        auth=auth,
        target_type="flywheel_settings",
        target_id=workspace.id,
        before=b,
        after=a,
    )
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


async def _own_rec(db: AsyncSession, workspace_id: object, rec_id: str) -> FlywheelRecommendation:
    rec = await db.get(FlywheelRecommendation, rec_id)
    if rec is None or rec.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation not found")
    return rec


@router.post("/recommendations/{rec_id}/apply", response_model=FlywheelRecommendationResponse)
async def apply_recommendation(
    rec_id: str, db: DbDep, auth: ApplyDep
) -> FlywheelRecommendationResponse:
    """Apply a pending recommendation (org admin). Snapshots the route for rollback."""
    workspace = auth[0]
    rec = await _own_rec(db, workspace.id, rec_id)
    if rec.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "recommendation not in a pending state")
    mutated = await flywheel.apply_recommendation(
        db, workspace.id, rec_id, mode="approval", commit=False
    )
    await audit_change(
        db,
        workspace.id,
        "flywheel.recommendation_applied",
        auth=auth,
        target_type="flywheel_recommendation",
        target_id=rec.id,
        before=(rec.current_config or {}).get("_route_snapshot"),
        after={**snapshot(rec, _REC_FIELDS), "route_mutated": mutated},
    )
    await db.commit()
    await db.refresh(rec)
    return FlywheelRecommendationResponse.model_validate(rec)


@router.post("/recommendations/{rec_id}/rollback", response_model=FlywheelRecommendationResponse)
async def rollback_recommendation(
    rec_id: str, db: DbDep, auth: ApplyDep
) -> FlywheelRecommendationResponse:
    """Undo an applied recommendation (org admin): the route gets its pre-apply config back."""
    workspace = auth[0]
    rec = await _own_rec(db, workspace.id, rec_id)
    if rec.status != "applied":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "only an applied recommendation can be rolled back"
        )
    applied = snapshot(rec, _REC_FIELDS)
    await flywheel.rollback_recommendation(db, workspace.id, rec_id, reason="manual")
    await audit_change(
        db,
        workspace.id,
        "flywheel.recommendation_rolled_back",
        auth=auth,
        target_type="flywheel_recommendation",
        target_id=rec.id,
        before=applied,
        after={
            **snapshot(rec, _REC_FIELDS),
            "restored": (rec.current_config or {}).get("_route_snapshot"),
        },
    )
    await db.commit()
    await db.refresh(rec)
    return FlywheelRecommendationResponse.model_validate(rec)


@router.post("/recommendations/{rec_id}/dismiss", response_model=FlywheelRecommendationResponse)
async def dismiss_recommendation(
    rec_id: str, db: DbDep, auth: WriteDep
) -> FlywheelRecommendationResponse:
    workspace = auth[0]
    rec = await _own_rec(db, workspace.id, rec_id)
    if rec.status == "dismissed":
        return FlywheelRecommendationResponse.model_validate(rec)
    if rec.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "recommendation not in a pending state")
    rec.status = "dismissed"
    rec.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "flywheel.recommendation_dismissed",
        auth=auth,
        target_type="flywheel_recommendation",
        target_id=rec.id,
        after={"status": "dismissed"},
    )
    await db.commit()
    await db.refresh(rec)
    return FlywheelRecommendationResponse.model_validate(rec)


@router.post("/run", response_model=FlywheelRunResponse)
async def run_flywheel(db: DbDep, auth: WriteDep) -> FlywheelRunResponse:
    workspace = auth[0]
    if not flywheel.enabled():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "flywheel service not configured")
    result = await flywheel.run_analysis(db, workspace.id)
    await audit_change(
        db,
        workspace.id,
        "flywheel.run",
        auth=auth,
        target_type="flywheel_settings",
        target_id=workspace.id,
        after={
            "recommendations": result.get("recommendations", 0),
            "auto_applied": result.get("auto_applied", 0),
        },
    )
    await db.commit()
    return FlywheelRunResponse(
        status=result["status"],
        recommendations=result.get("recommendations", 0),
        auto_applied=result.get("auto_applied", 0),
    )
