"""
Budget CRUD + hot-path check endpoints.

Prefix: /budgets
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /budgets                  Create a budget
GET    /budgets                  List budgets with current Redis spend
GET    /budgets/check            Hot-path check (Redis only, target <5ms)
GET    /budgets/{id}/breaches    Breach history
DELETE /budgets/{id}             Soft-delete (is_active=False)
POST   /budgets/notifications    Create notification channel
GET    /budgets/notifications    List notification channels
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.budgets import Budget, BudgetBreach, BudgetNotification
from runledger_api.models.tenant import Workspace, WorkspaceUser
from runledger_api.schemas.budgets import (
    BreachList,
    BreachResponse,
    BudgetCheckResponse,
    BudgetCreate,
    BudgetList,
    BudgetResponse,
    NotificationCreate,
    NotificationList,
    NotificationResponse,
)
from runledger_api.services.budgets import (
    check_budgets,
    get_budget_spend,
    invalidate_workspace_budgets_cache,
)

router = APIRouter(
    prefix="/budgets", tags=["budgets"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()


# ── POST /budgets ─────────────────────────────────────────────────────────────


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    body: BudgetCreate,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetResponse:
    workspace: Workspace = auth[0]
    """Create a new budget for this workspace."""
    budget = Budget(
        workspace_id=workspace.id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        period_type=body.period_type,
        limit_usd=body.limit_usd,
        action=body.action,
        downgrade_to_model=body.downgrade_to_model,
        is_active=True,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    await invalidate_workspace_budgets_cache(redis, workspace.id)

    log.info(
        "budget_created",
        budget_id=str(budget.id),
        workspace_id=str(workspace.id),
        scope_type=budget.scope_type,
        period_type=budget.period_type,
        limit_usd=str(budget.limit_usd),
    )

    from decimal import Decimal  # noqa: PLC0415

    return BudgetResponse(
        id=str(budget.id),
        scope_type=budget.scope_type,
        scope_id=budget.scope_id,
        period_type=budget.period_type,
        limit_usd=budget.limit_usd,
        action=budget.action,
        downgrade_to_model=budget.downgrade_to_model,
        is_active=budget.is_active,
        created_at=budget.created_at,
        current_spend_usd=Decimal(0),
        pct_used=Decimal(0),
    )


# ── GET /budgets ──────────────────────────────────────────────────────────────


@router.get("", response_model=BudgetList)
async def list_budgets(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    include_inactive: Annotated[bool, Query()] = False,
) -> BudgetList:
    """List budgets with current period spend from Redis."""
    from decimal import Decimal  # noqa: PLC0415

    stmt = select(Budget).where(Budget.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(Budget.is_active.is_(True))
    stmt = stmt.order_by(Budget.created_at.desc())

    result = await db.execute(stmt)
    budgets: list[Budget] = list(result.scalars())

    items = []
    for b in budgets:
        spend = await get_budget_spend(redis, b.id, b.period_type)
        pct = (spend / b.limit_usd * 100) if b.limit_usd > 0 else Decimal(0)
        items.append(
            BudgetResponse(
                id=str(b.id),
                scope_type=b.scope_type,
                scope_id=b.scope_id,
                period_type=b.period_type,
                limit_usd=b.limit_usd,
                action=b.action,
                downgrade_to_model=b.downgrade_to_model,
                is_active=b.is_active,
                created_at=b.created_at,
                current_spend_usd=spend,
                pct_used=pct,
            )
        )

    return BudgetList(items=items)


# ── GET /budgets/check ────────────────────────────────────────────────────────
# IMPORTANT: this route must be defined BEFORE /budgets/{id}/... routes
# so FastAPI doesn't treat "check" as a budget ID.


@router.get("/check", response_model=BudgetCheckResponse)
async def budget_check(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    end_user_id: Annotated[str | None, Query()] = None,
    feature_tag: Annotated[str | None, Query()] = None,
) -> BudgetCheckResponse:
    """
    Hot-path budget check.

    Reads from Redis cache + spend counters only.
    Target latency: <5ms p99.
    """
    return await check_budgets(
        redis=redis,
        db=db,
        workspace_id=workspace.id,
        end_user_id=end_user_id,
        feature_tag=feature_tag,
    )


# ── GET /budgets/notifications ────────────────────────────────────────────────


@router.get("/notifications", response_model=NotificationList)
async def list_notifications(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationList:
    """List notification channels for this workspace."""
    result = await db.execute(
        select(BudgetNotification)
        .where(BudgetNotification.workspace_id == workspace.id)
        .order_by(BudgetNotification.created_at.desc())
    )
    notifications: list[BudgetNotification] = list(result.scalars())

    return NotificationList(
        items=[
            NotificationResponse(
                id=str(n.id),
                channel=n.channel,
                destination_url=n.destination_url,
                events=n.events,
                is_active=n.is_active,
                created_at=n.created_at,
            )
            for n in notifications
        ]
    )


# ── POST /budgets/notifications ───────────────────────────────────────────────


@router.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification(
    body: NotificationCreate,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationResponse:
    workspace: Workspace = auth[0]
    """Create a webhook or Slack notification channel."""
    notification = BudgetNotification(
        workspace_id=workspace.id,
        channel=body.channel,
        destination_url=body.destination_url,
        events=body.events,
        is_active=True,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    log.info(
        "notification_created",
        notification_id=str(notification.id),
        channel=notification.channel,
    )

    return NotificationResponse(
        id=str(notification.id),
        channel=notification.channel,
        destination_url=notification.destination_url,
        events=notification.events,
        is_active=notification.is_active,
        created_at=notification.created_at,
    )


# ── GET /budgets/{id}/breaches ────────────────────────────────────────────────


@router.get("/{budget_id}/breaches", response_model=BreachList)
async def get_breaches(
    budget_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> BreachList:
    """List breach history for a budget (most recent first)."""
    # Verify budget belongs to this workspace
    budget_result = await db.execute(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.workspace_id == workspace.id,
        )
    )
    budget = budget_result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    result = await db.execute(
        select(BudgetBreach)
        .where(BudgetBreach.budget_id == budget_id)
        .order_by(BudgetBreach.occurred_at.desc())
        .limit(limit)
    )
    breaches: list[BudgetBreach] = list(result.scalars())

    return BreachList(
        items=[
            BreachResponse(
                id=str(b.id),
                budget_id=str(b.budget_id),
                occurred_at=b.occurred_at,
                spend_at_breach_usd=b.spend_at_breach_usd,
                action_taken=b.action_taken,
                notified_at=b.notified_at,
            )
            for b in breaches
        ]
    )


# ── DELETE /budgets/{id} ──────────────────────────────────────────────────────


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    workspace: Workspace = auth[0]
    """Soft-delete a budget (sets is_active=False)."""
    result = await db.execute(
        select(Budget).where(
            Budget.id == budget_id,
            Budget.workspace_id == workspace.id,
        )
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    await db.execute(update(Budget).where(Budget.id == budget_id).values(is_active=False))
    await db.commit()
    await invalidate_workspace_budgets_cache(redis, workspace.id)

    log.info("budget_deactivated", budget_id=str(budget_id))
