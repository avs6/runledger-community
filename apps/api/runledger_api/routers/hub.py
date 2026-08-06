"""
AI Hub Model Catalog API.

Prefix: /hub
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /hub/models                 Add model to catalog
GET    /hub/models                 List catalog models
GET    /hub/models/{id}            Get model card
PUT    /hub/models/{id}            Update model card
DELETE /hub/models/{id}            Remove from catalog
POST   /hub/models/{id}/request-access   Request access to a model
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.hub import HubModel
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.hub import (
    HubModelCreate,
    HubModelList,
    HubModelResponse,
    HubModelUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/hub", tags=["hub"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _to_response(m: HubModel) -> HubModelResponse:
    return HubModelResponse(
        id=m.id, workspace_id=m.workspace_id, name=m.name, provider=m.provider,
        description=m.description, capabilities=m.capabilities or [],
        context_window=m.context_window, input_cost_per_1k=m.input_cost_per_1k,
        output_cost_per_1k=m.output_cost_per_1k, tags=m.tags or [],
        is_featured=m.is_featured, is_deprecated=m.is_deprecated,
        deprecation_notice=m.deprecation_notice, is_public=m.is_public,
        access_request_count=m.access_request_count, created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.post("/models", response_model=HubModelResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(management_rate_limit)])
async def add_model(body: HubModelCreate, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = HubModel(
        id=uuid.uuid4(), workspace_id=ws.id, name=body.name, provider=body.provider,
        description=body.description, capabilities=body.capabilities,
        context_window=body.context_window, input_cost_per_1k=body.input_cost_per_1k,
        output_cost_per_1k=body.output_cost_per_1k, tags=body.tags,
        is_featured=body.is_featured, is_public=body.is_public,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _to_response(m)


@router.get("/models", response_model=HubModelList, dependencies=[Depends(analytics_rate_limit)])
async def list_models(
    ws: WorkspaceDep, db: DbDep,
    featured_only: bool = False,
    provider: str | None = None,
    tag: str | None = None,
) -> HubModelList:
    q = select(HubModel).where(HubModel.workspace_id == ws.id, HubModel.is_public.is_(True))
    if featured_only:
        q = q.where(HubModel.is_featured.is_(True))
    if provider:
        q = q.where(HubModel.provider == provider)
    q = q.order_by(HubModel.is_featured.desc(), HubModel.name)
    rows = (await db.execute(q)).scalars().all()
    items = [_to_response(m) for m in rows]
    if tag:
        items = [i for i in items if tag in (i.tags or [])]
    return HubModelList(items=items)


@router.get("/models/{model_id}", response_model=HubModelResponse,
            dependencies=[Depends(analytics_rate_limit)])
async def get_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    return _to_response(m)


@router.put("/models/{model_id}", response_model=HubModelResponse,
            dependencies=[Depends(management_rate_limit)])
async def update_model(model_id: uuid.UUID, body: HubModelUpdate, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    m.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(m)
    return _to_response(m)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(management_rate_limit)])
async def remove_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    await db.delete(m)
    await db.commit()


@router.post("/models/{model_id}/request-access", dependencies=[Depends(management_rate_limit)])
async def request_access(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> dict:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    m.access_request_count = (m.access_request_count or 0) + 1
    await db.commit()
    return {"status": "requested", "model_id": str(model_id), "total_requests": m.access_request_count}
