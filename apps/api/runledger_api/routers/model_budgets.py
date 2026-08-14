"""
Per-model budget CRUD for API keys.

Prefix: /api-keys/{key_id}/model-budgets
Auth: Bearer API key (workspace-scoped, admin required)
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.model_budgets import ModelBudget
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.model_budgets import (
    ModelBudgetCreate,
    ModelBudgetList,
    ModelBudgetResponse,
    ModelBudgetUpdate,
)

router = APIRouter(
    prefix="/api-keys/{key_id}/model-budgets",
    tags=["model-budgets"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()


def _to_response(mb: ModelBudget) -> ModelBudgetResponse:
    return ModelBudgetResponse(
        id=str(mb.id),
        api_key_id=str(mb.api_key_id),
        model_pattern=mb.model_pattern,
        max_spend_usd=mb.max_spend_usd,
        period_type=mb.period_type,
        rpm_limit=mb.rpm_limit,
        tpm_limit=mb.tpm_limit,
        action=mb.action,
        is_active=mb.is_active,
        created_at=mb.created_at,
    )


async def _verify_key(key_id: uuid.UUID, workspace: Workspace, db: AsyncSession) -> ApiKey:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace.id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    return api_key


@router.post("", response_model=ModelBudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_model_budget(
    key_id: uuid.UUID,
    body: ModelBudgetCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelBudgetResponse:
    workspace: Workspace = auth[0]
    await _verify_key(key_id, workspace, db)

    mb = ModelBudget(
        api_key_id=key_id,
        model_pattern=body.model_pattern,
        max_spend_usd=body.max_spend_usd,
        period_type=body.period_type,
        rpm_limit=body.rpm_limit,
        tpm_limit=body.tpm_limit,
        action=body.action,
    )
    db.add(mb)
    await db.commit()
    await db.refresh(mb)
    log.info("model_budget_created", id=str(mb.id), pattern=mb.model_pattern)
    return _to_response(mb)


@router.get("", response_model=ModelBudgetList)
async def list_model_budgets(
    key_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelBudgetList:
    workspace: Workspace = auth[0]
    await _verify_key(key_id, workspace, db)

    result = await db.execute(
        select(ModelBudget)
        .where(ModelBudget.api_key_id == key_id, ModelBudget.is_active.is_(True))
        .order_by(ModelBudget.model_pattern)
    )
    items = [_to_response(mb) for mb in result.scalars()]
    return ModelBudgetList(items=items)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_budget(
    key_id: uuid.UUID,
    budget_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    await _verify_key(key_id, workspace, db)

    result = await db.execute(
        select(ModelBudget).where(ModelBudget.id == budget_id, ModelBudget.api_key_id == key_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model budget not found")

    await db.execute(update(ModelBudget).where(ModelBudget.id == budget_id).values(is_active=False))
    await db.commit()
    log.info("model_budget_deleted", id=str(budget_id))


@router.put("/{budget_id}", response_model=ModelBudgetResponse)
async def update_model_budget(
    key_id: uuid.UUID,
    budget_id: uuid.UUID,
    body: ModelBudgetUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ModelBudgetResponse:
    workspace: Workspace = auth[0]
    await _verify_key(key_id, workspace, db)

    result = await db.execute(
        select(ModelBudget).where(ModelBudget.id == budget_id, ModelBudget.api_key_id == key_id)
    )
    mb = result.scalar_one_or_none()
    if mb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model budget not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(mb, field, value)

    await db.commit()
    await db.refresh(mb)
    log.info("model_budget_updated", id=str(budget_id), pattern=mb.model_pattern)
    return _to_response(mb)
