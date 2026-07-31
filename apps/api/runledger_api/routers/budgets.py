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
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_user, get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.budgets import Budget, BudgetBreach, BudgetNotification
from runledger_api.models.tenant import TenantRoleEnum, TenantUser, Workspace
from runledger_api.schemas.budgets import (
    BreachList,
    BreachResponse,
    BudgetCheckResponse,
    BudgetCreate,
    BudgetList,
    BudgetRollupResponse,
    BudgetRollupWorkspace,
    BudgetResponse,
    NotificationCreate,
    NotificationList,
    NotificationResponse,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.budgets import (
    check_budgets,
    get_budget_spend,
    invalidate_workspace_budgets_cache,
)

router = APIRouter(
    prefix="/budgets", tags=["budgets"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()
_ORG_BUDGET_ROLES = {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager}


async def _budget_rollup_workspace_ids(
    *,
    scope: str,
    workspace: Workspace,
    user: Any,
    db: AsyncSession,
) -> list[uuid.UUID]:
    if scope == "workspace":
        return [workspace.id]

    if user is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A dashboard user session is required for org or platform budget rollups",
        )

    if scope == "org":
        if not user.is_platform_admin:
            tenant_user = (
                await db.execute(
                    select(TenantUser).where(
                        TenantUser.user_id == user.id,
                        TenantUser.tenant_id == workspace.tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if tenant_user is None or tenant_user.role not in _ORG_BUDGET_ROLES:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Organization admin access required for org budget rollups",
                )
        result = await db.execute(select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id))
        return list(result.scalars().all())

    if scope == "platform":
        if not user.is_platform_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Platform admin access required for platform budget rollups",
            )
        result = await db.execute(select(Workspace.id))
        return list(result.scalars().all())

    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "scope must be workspace, org, or platform")


# ── POST /budgets ─────────────────────────────────────────────────────────────


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    body: BudgetCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
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
    await emit_audit_event(
        db,
        workspace.id,
        "budget.created",
        target_type="budget",
        target_id=str(budget.id),
        after={
            "scope_type": budget.scope_type,
            "period_type": budget.period_type,
            "limit_usd": str(budget.limit_usd),
        },
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


@router.get("/rollup", response_model=BudgetRollupResponse)
async def budget_rollup(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    user: Annotated[Any, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    scope: Annotated[str, Query(pattern="^(workspace|org|platform)$")] = "workspace",
    include_inactive: Annotated[bool, Query()] = False,
) -> BudgetRollupResponse:
    """Roll budget usage up across workspace, organization, or platform scope."""
    workspace_ids = await _budget_rollup_workspace_ids(
        scope=scope,
        workspace=workspace,
        user=user,
        db=db,
    )
    if not workspace_ids:
        return BudgetRollupResponse(
            scope=scope,
            workspace_count=0,
            budget_count=0,
            active_budget_count=0,
            limit_usd=Decimal(0),
            current_spend_usd=Decimal(0),
            remaining_usd=Decimal(0),
            pct_used=Decimal(0),
            exceeded_count=0,
            at_risk_count=0,
            workspaces=[],
        )

    workspace_rows = list(
        (
            await db.execute(
                select(Workspace.id, Workspace.name)
                .where(Workspace.id.in_(workspace_ids))
                .order_by(Workspace.name.asc())
            )
        ).all()
    )
    workspaces = {row.id: row.name for row in workspace_rows}

    budget_stmt = select(Budget).where(Budget.workspace_id.in_(workspace_ids))
    if not include_inactive:
        budget_stmt = budget_stmt.where(Budget.is_active.is_(True))
    budgets = list((await db.execute(budget_stmt)).scalars())

    per_workspace = {
        workspace_id: {
            "workspace_id": workspace_id,
            "workspace_name": name,
            "budget_count": 0,
            "active_budget_count": 0,
            "limit_usd": Decimal(0),
            "current_spend_usd": Decimal(0),
            "exceeded_count": 0,
            "at_risk_count": 0,
        }
        for workspace_id, name in workspaces.items()
    }

    total_budget_count = 0
    total_active_budget_count = 0
    total_limit = Decimal(0)
    total_spend = Decimal(0)
    total_exceeded = 0
    total_at_risk = 0

    for budget in budgets:
        bucket = per_workspace.get(budget.workspace_id)
        if bucket is None:
            continue
        bucket["budget_count"] += 1
        total_budget_count += 1
        if not budget.is_active:
            continue

        spend = await get_budget_spend(redis, budget.id, budget.period_type)
        pct = (spend / budget.limit_usd * 100) if budget.limit_usd > 0 else Decimal(0)
        bucket["active_budget_count"] += 1
        bucket["limit_usd"] += budget.limit_usd
        bucket["current_spend_usd"] += spend
        total_active_budget_count += 1
        total_limit += budget.limit_usd
        total_spend += spend
        if pct >= 100:
            bucket["exceeded_count"] += 1
            total_exceeded += 1
        elif pct >= 80:
            bucket["at_risk_count"] += 1
            total_at_risk += 1

    rollup_workspaces: list[BudgetRollupWorkspace] = []
    for bucket in per_workspace.values():
        limit = bucket["limit_usd"]
        spend = bucket["current_spend_usd"]
        remaining = max(limit - spend, Decimal(0))
        pct = (spend / limit * 100) if limit > 0 else Decimal(0)
        rollup_workspaces.append(
            BudgetRollupWorkspace(
                workspace_id=str(bucket["workspace_id"]),
                workspace_name=str(bucket["workspace_name"]),
                budget_count=int(bucket["budget_count"]),
                active_budget_count=int(bucket["active_budget_count"]),
                limit_usd=limit,
                current_spend_usd=spend,
                remaining_usd=remaining,
                pct_used=pct,
                exceeded_count=int(bucket["exceeded_count"]),
                at_risk_count=int(bucket["at_risk_count"]),
            )
        )

    total_remaining = max(total_limit - total_spend, Decimal(0))
    total_pct = (total_spend / total_limit * 100) if total_limit > 0 else Decimal(0)
    return BudgetRollupResponse(
        scope=scope,
        workspace_count=len(workspace_ids),
        budget_count=total_budget_count,
        active_budget_count=total_active_budget_count,
        limit_usd=total_limit,
        current_spend_usd=total_spend,
        remaining_usd=total_remaining,
        pct_used=total_pct,
        exceeded_count=total_exceeded,
        at_risk_count=total_at_risk,
        workspaces=rollup_workspaces,
    )


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
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
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
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
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
    await emit_audit_event(
        db,
        workspace.id,
        "budget.deleted",
        target_type="budget",
        target_id=str(budget_id),
        before={
            "scope_type": budget.scope_type,
            "period_type": budget.period_type,
            "limit_usd": str(budget.limit_usd),
        },
    )
    await db.commit()
    await invalidate_workspace_budgets_cache(redis, workspace.id)

    log.info("budget_deactivated", budget_id=str(budget_id))
