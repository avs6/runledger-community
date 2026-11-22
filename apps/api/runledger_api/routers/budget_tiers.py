"""
Budget tier CRUD + assign to API keys.

Prefix: /budget-tiers
Auth: Bearer API key (workspace-scoped)
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.budget_tiers import BudgetTier
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.budget_tiers import (
    BudgetTierCreate,
    BudgetTierList,
    BudgetTierResponse,
    BudgetTierUpdate,
)

router = APIRouter(
    prefix="/budget-tiers",
    tags=["budget-tiers"],
    dependencies=[Depends(management_rate_limit)],
)
log = structlog.get_logger()


async def _key_counts(db: AsyncSession, tier_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """API keys per tier in one grouped query (review G-26; was one query per tier)."""
    if not tier_ids:
        return {}
    rows = await db.execute(
        select(ApiKey.budget_tier_id, func.count())
        .where(ApiKey.budget_tier_id.in_(tier_ids))
        .group_by(ApiKey.budget_tier_id)
    )
    return {tier_id: int(n) for tier_id, n in rows.all() if tier_id is not None}


async def _tier_response(
    db: AsyncSession, tier: BudgetTier, key_count: int | None = None
) -> BudgetTierResponse:
    if key_count is None:
        key_count = (await _key_counts(db, [tier.id])).get(tier.id, 0)
    return BudgetTierResponse(
        id=str(tier.id),
        name=tier.name,
        max_spend_usd=tier.max_spend_usd,
        period_type=tier.period_type,
        rpm_limit=tier.rpm_limit,
        tpm_limit=tier.tpm_limit,
        allowed_models=tier.allowed_models,
        is_default=tier.is_default,
        is_active=tier.is_active,
        created_at=tier.created_at,
        key_count=key_count,
    )


@router.post("", response_model=BudgetTierResponse, status_code=status.HTTP_201_CREATED)
async def create_tier(
    body: BudgetTierCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetTierResponse:
    workspace: Workspace = auth[0]

    if body.is_default:
        await db.execute(
            update(BudgetTier)
            .where(BudgetTier.workspace_id == workspace.id, BudgetTier.is_default.is_(True))
            .values(is_default=False)
        )

    tier = BudgetTier(
        workspace_id=workspace.id,
        name=body.name,
        max_spend_usd=body.max_spend_usd,
        period_type=body.period_type,
        rpm_limit=body.rpm_limit,
        tpm_limit=body.tpm_limit,
        allowed_models=body.allowed_models,
        is_default=body.is_default,
    )
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    log.info("budget_tier_created", tier_id=str(tier.id), name=tier.name)
    return await _tier_response(db, tier)


_TIER_SORTS = {
    "name": BudgetTier.name,
    "max_spend_usd": BudgetTier.max_spend_usd,
    "created_at": BudgetTier.created_at,
}


@router.get("", response_model=BudgetTierList)
async def list_tiers(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: PageDep,
    response: Response,
    include_inactive: Annotated[bool, Query()] = False,
    q: Annotated[str | None, Query(max_length=200, description="Search by name")] = None,
    sort: Annotated[str, Query(pattern="^-?(name|max_spend_usd|created_at)$")] = "name",
) -> BudgetTierList:
    """Tiers with search, sort (prefix ``-`` for descending) and paging (G-26)."""
    stmt = select(BudgetTier).where(BudgetTier.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(BudgetTier.is_active.is_(True))
    if q:
        stmt = stmt.where(BudgetTier.name.ilike(f"%{q.strip()}%"))
    column = _TIER_SORTS[sort.lstrip("-")]
    order = column.desc().nulls_last() if sort.startswith("-") else column.asc().nulls_last()
    stmt = stmt.order_by(order, BudgetTier.id)
    tiers = await paginate(db, stmt, page, response)
    counts = await _key_counts(db, [t.id for t in tiers])
    items = [await _tier_response(db, t, counts.get(t.id, 0)) for t in tiers]
    return BudgetTierList(items=items)


@router.get("/{tier_id}", response_model=BudgetTierResponse)
async def get_tier(
    tier_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetTierResponse:
    result = await db.execute(
        select(BudgetTier).where(
            BudgetTier.id == tier_id,
            BudgetTier.workspace_id == workspace.id,
        )
    )
    tier = result.scalar_one_or_none()
    if tier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget tier not found")
    return await _tier_response(db, tier)


@router.put("/{tier_id}", response_model=BudgetTierResponse)
async def update_tier(
    tier_id: uuid.UUID,
    body: BudgetTierUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetTierResponse:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(BudgetTier).where(
            BudgetTier.id == tier_id,
            BudgetTier.workspace_id == workspace.id,
        )
    )
    tier = result.scalar_one_or_none()
    if tier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget tier not found")

    updates = body.model_dump(exclude_unset=True)
    if updates.get("is_default"):
        await db.execute(
            update(BudgetTier)
            .where(BudgetTier.workspace_id == workspace.id, BudgetTier.is_default.is_(True))
            .values(is_default=False)
        )

    for field, value in updates.items():
        setattr(tier, field, value)
    await db.commit()
    await db.refresh(tier)
    return await _tier_response(db, tier)


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tier(
    tier_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    result = await db.execute(
        select(BudgetTier).where(
            BudgetTier.id == tier_id,
            BudgetTier.workspace_id == workspace.id,
        )
    )
    tier = result.scalar_one_or_none()
    if tier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget tier not found")

    await db.execute(
        update(ApiKey).where(ApiKey.budget_tier_id == tier_id).values(budget_tier_id=None)
    )
    await db.execute(update(BudgetTier).where(BudgetTier.id == tier_id).values(is_active=False))
    await db.commit()
    log.info("budget_tier_deleted", tier_id=str(tier_id))


@router.put("/assign/{key_id}", response_model=dict[str, Any])
async def assign_tier_to_key(
    key_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tier_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict[str, Any]:
    """Assign a budget tier to an API key, or pass tier_id=null to unassign."""
    workspace: Workspace = auth[0]

    key_result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace.id)
    )
    api_key = key_result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")

    if tier_id is not None:
        tier_result = await db.execute(
            select(BudgetTier).where(
                BudgetTier.id == tier_id,
                BudgetTier.workspace_id == workspace.id,
                BudgetTier.is_active.is_(True),
            )
        )
        if tier_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget tier not found")

    await db.execute(update(ApiKey).where(ApiKey.id == key_id).values(budget_tier_id=tier_id))
    await db.commit()
    log.info("tier_assigned", key_id=str(key_id), tier_id=str(tier_id))
    return {"key_id": str(key_id), "budget_tier_id": str(tier_id) if tier_id else None}
