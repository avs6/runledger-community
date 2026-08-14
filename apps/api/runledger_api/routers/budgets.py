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
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_user,
    get_current_workspace,
    require_workspace_admin,
)
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.access_groups import AccessGroup
from runledger_api.models.approvals import Approval
from runledger_api.models.budget_overrides import BudgetOverride
from runledger_api.models.budgets import (
    Budget,
    BudgetBreach,
    BudgetNotification,
    BudgetNotificationDelivery,
)
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import ApiKey, TenantRoleEnum, TenantUser, User, Workspace
from runledger_api.schemas.budget_overrides import (
    BudgetOverrideCreate,
    BudgetOverrideList,
    BudgetOverrideResponse,
)
from runledger_api.schemas.budgets import (
    BillingPeriodSummary,
    BillingSummaryResponse,
    BreachList,
    BreachResponse,
    BudgetCheckResponse,
    BudgetCreate,
    BudgetList,
    BudgetResponse,
    BudgetRollupResponse,
    BudgetRollupWorkspace,
    BudgetUpdate,
    NotificationCreate,
    NotificationDeliveryList,
    NotificationDeliveryResponse,
    NotificationList,
    NotificationResponse,
    NotificationTestResult,
    NotificationUpdate,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.budgets import (
    build_delivery_record,
    check_budgets,
    get_budget_spend,
    invalidate_workspace_budgets_cache,
    send_notification,
)

router = APIRouter(
    prefix="/budgets", tags=["budgets"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()
_ORG_BUDGET_ROLES = {TenantRoleEnum.org_admin, TenantRoleEnum.org_manager}


def _budget_response(
    budget: Budget,
    *,
    current_spend_usd: Decimal,
    scope_display_name: str | None = None,
) -> BudgetResponse:
    pct = (
        (current_spend_usd / budget.limit_usd * 100)
        if budget.limit_usd > 0
        else Decimal(0)
    )
    return BudgetResponse(
        id=str(budget.id),
        scope_type=budget.scope_type,
        scope_id=budget.scope_id,
        scope_display_name=scope_display_name,
        period_type=budget.period_type,
        limit_usd=budget.limit_usd,
        action=budget.action,
        downgrade_to_model=budget.downgrade_to_model,
        is_active=budget.is_active,
        created_at=budget.created_at,
        current_spend_usd=current_spend_usd,
        pct_used=pct,
    )


def _validate_budget_payload(
    *,
    scope_type: str,
    scope_id: str | None,
    action: str,
    downgrade_to_model: str | None,
) -> None:
    if scope_type == "workspace":
        return
    if scope_type in {
        "end_user",
        "feature_tag",
        "app",
        "access_group",
        "api_key",
        "provider_profile",
    } and not scope_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "scope_id is required for non-workspace budgets",
        )
    if action in {"downgrade", "fallback"} and not downgrade_to_model:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "downgrade_to_model is required for downgrade or fallback actions",
        )


async def _resolve_scope_display_name(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    scope_type: str,
    scope_id: str | None,
) -> str | None:
    if scope_type == "workspace":
        return "All workspace traffic"
    if not scope_id:
        return None
    if scope_type in {"end_user", "feature_tag", "app"}:
        return scope_id
    if scope_type == "access_group":
        try:
            group_id = uuid.UUID(scope_id)
        except ValueError:
            return scope_id
        group = (
            await db.execute(
                select(AccessGroup.name).where(
                    AccessGroup.id == group_id,
                    AccessGroup.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        return group or scope_id
    if scope_type == "api_key":
        try:
            key_id = uuid.UUID(scope_id)
        except ValueError:
            return scope_id
        api_key = (
            await db.execute(
                select(ApiKey.name, ApiKey.key_prefix).where(
                    ApiKey.id == key_id,
                    ApiKey.workspace_id == workspace_id,
                )
            )
        ).one_or_none()
        if api_key is None:
            return scope_id
        name, key_prefix = api_key
        return str(name or key_prefix)
    if scope_type == "provider_profile":
        try:
            pricing_id = uuid.UUID(scope_id)
        except ValueError:
            return scope_id
        pricing = (
            await db.execute(
                select(
                    ProviderPricing.provider,
                    ProviderPricing.model,
                    ProviderPricing.display_name,
                ).where(
                    ProviderPricing.id == pricing_id,
                    (ProviderPricing.workspace_id == workspace_id)
                    | (ProviderPricing.workspace_id.is_(None)),
                )
            )
        ).one_or_none()
        if pricing is None:
            return scope_id
        provider, model, display_name = pricing
        return str(display_name or f"{provider} / {model}")
    return scope_id


async def _validate_scope_reference(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    scope_type: str,
    scope_id: str | None,
) -> None:
    if scope_type == "workspace" or not scope_id:
        return
    if scope_type in {"end_user", "feature_tag", "app"}:
        return
    if scope_type == "access_group":
        try:
            group_id = uuid.UUID(scope_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "scope_id must be a valid access-group UUID",
            ) from exc
        exists = (
            await db.execute(
                select(AccessGroup.id).where(
                    AccessGroup.id == group_id,
                    AccessGroup.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Access group not found")
        return
    if scope_type == "api_key":
        try:
            key_id = uuid.UUID(scope_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "scope_id must be a valid API key UUID",
            ) from exc
        exists = (
            await db.execute(
                select(ApiKey.id).where(
                    ApiKey.id == key_id,
                    ApiKey.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
        return
    if scope_type == "provider_profile":
        try:
            pricing_id = uuid.UUID(scope_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "scope_id must be a valid provider-profile UUID",
            ) from exc
        exists = (
            await db.execute(
                select(ProviderPricing.id).where(
                    ProviderPricing.id == pricing_id,
                    (ProviderPricing.workspace_id == workspace_id)
                    | (ProviderPricing.workspace_id.is_(None)),
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider profile not found")


async def _get_workspace_budget(
    *,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Budget:
    budget = (
        await db.execute(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return budget


async def _override_approval_map(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    override_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Approval]:
    if not override_ids:
        return {}
    approvals = (
        await db.execute(
            select(Approval).where(
                Approval.workspace_id == workspace_id,
                Approval.request_type == "budget_increase",
            )
        )
    ).scalars().all()
    mapped: dict[uuid.UUID, Approval] = {}
    for approval in approvals:
        if not approval.request:
            continue
        override_id = approval.request.get("budget_override_id")
        if not override_id:
            continue
        try:
            parsed = uuid.UUID(str(override_id))
        except ValueError:
            continue
        if parsed in override_ids:
            mapped[parsed] = approval
    return mapped


def _override_response(
    override: BudgetOverride,
    approval: Approval | None = None,
) -> BudgetOverrideResponse:
    return BudgetOverrideResponse(
        id=str(override.id),
        budget_id=str(override.budget_id),
        original_limit_usd=override.original_limit_usd,
        override_limit_usd=override.override_limit_usd,
        starts_at=override.starts_at,
        expires_at=override.expires_at,
        reason=override.reason,
        approved_by=str(override.approved_by) if override.approved_by else None,
        status=override.status,
        approval_id=str(approval.id) if approval else None,
        approval_status=approval.status if approval else None,
        created_at=override.created_at,
    )


def _notification_response(notification: BudgetNotification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        channel=notification.channel,
        destination_url=notification.destination_url,
        events=notification.events,
        is_active=notification.is_active,
        created_at=notification.created_at,
    )


async def _get_notification(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> BudgetNotification:
    notification = await db.get(BudgetNotification, notification_id)
    if notification is None or notification.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook destination not found")
    return notification


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
        result = await db.execute(
            select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)
        )
        return list(result.scalars().all())

    if scope == "platform":
        if not user.is_platform_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Platform admin access required for platform budget rollups",
            )
        result = await db.execute(select(Workspace.id))
        return list(result.scalars().all())

    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY, "scope must be workspace, org, or platform"
    )


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
    _validate_budget_payload(
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        action=body.action,
        downgrade_to_model=body.downgrade_to_model,
    )
    await _validate_scope_reference(db, workspace.id, body.scope_type, body.scope_id)
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

    scope_display_name = await _resolve_scope_display_name(
        db,
        workspace.id,
        budget.scope_type,
        budget.scope_id,
    )
    return _budget_response(
        budget,
        current_spend_usd=Decimal(0),
        scope_display_name=scope_display_name,
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
        scope_display_name = await _resolve_scope_display_name(
            db,
            workspace.id,
            b.scope_type,
            b.scope_id,
        )
        items.append(
            _budget_response(
                b,
                current_spend_usd=spend,
                scope_display_name=scope_display_name,
            )
        )

    return BudgetList(items=items)


# ── GET /budgets/billing-summary ──────────────────────────────────────────────


@router.get("/billing-summary", response_model=BillingSummaryResponse)
async def billing_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=12)] = 3,
) -> BillingSummaryResponse:
    """Billing summary with billable vs non-billable cost per period."""
    from sqlalchemy import func as sa_func  # noqa: PLC0415

    from runledger_api.models.metering import UsageDaily  # noqa: PLC0415

    result = await db.execute(
        select(
            sa_func.to_char(UsageDaily.day, "YYYY-MM").label("period"),
            sa_func.coalesce(sa_func.sum(UsageDaily.cost_usd), 0).label("total_cost"),
            sa_func.coalesce(sa_func.sum(UsageDaily.billable_cost_usd), 0).label("billable_cost"),
            sa_func.coalesce(sa_func.sum(UsageDaily.call_count), 0).label("total_calls"),
        )
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= sa_func.current_date() - months * 31,
        )
        .group_by("period")
        .order_by("period")
    )
    periods = []
    for row in result.all():
        total = Decimal(str(row.total_cost))
        billable = Decimal(str(row.billable_cost))
        periods.append(
            BillingPeriodSummary(
                period=row.period,
                total_cost_usd=total,
                billable_cost_usd=billable,
                non_billable_cost_usd=total - billable,
                total_calls=int(row.total_calls),
                billable_calls=int(row.total_calls),
            )
        )
    return BillingSummaryResponse(
        workspace_id=str(workspace.id),
        periods=periods,
    )


# ── GET /budgets/billing-export ──────────────────────────────────────────────


@router.get("/billing-export")
async def billing_export(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=12)] = 3,
    fmt: Annotated[str, Query(alias="format", pattern="^(csv|json)$")] = "json",
):
    """Export billing summary as CSV or JSON."""
    from io import StringIO  # noqa: PLC0415

    from fastapi.responses import Response  # noqa: PLC0415
    from sqlalchemy import func as sa_func  # noqa: PLC0415

    from runledger_api.models.metering import UsageDaily  # noqa: PLC0415

    result = await db.execute(
        select(
            sa_func.to_char(UsageDaily.day, "YYYY-MM").label("period"),
            sa_func.coalesce(sa_func.sum(UsageDaily.cost_usd), 0).label("total_cost"),
            sa_func.coalesce(sa_func.sum(UsageDaily.billable_cost_usd), 0).label("billable_cost"),
            sa_func.coalesce(sa_func.sum(UsageDaily.call_count), 0).label("total_calls"),
        )
        .where(
            UsageDaily.workspace_id == workspace.id,
            UsageDaily.day >= sa_func.current_date() - months * 31,
        )
        .group_by("period")
        .order_by("period")
    )
    rows = result.all()

    if fmt == "csv":
        buf = StringIO()
        buf.write("period,total_cost_usd,billable_cost_usd,non_billable_cost_usd,total_calls\n")
        for r in rows:
            total = Decimal(str(r.total_cost))
            billable = Decimal(str(r.billable_cost))
            buf.write(f"{r.period},{total},{billable},{total - billable},{r.total_calls}\n")
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=billing-export.csv"},
        )

    import json as _json  # noqa: PLC0415

    periods = []
    for r in rows:
        total = float(Decimal(str(r.total_cost)))
        billable = float(Decimal(str(r.billable_cost)))
        periods.append({
            "period": r.period,
            "total_cost_usd": total,
            "billable_cost_usd": billable,
            "non_billable_cost_usd": round(total - billable, 8),
            "total_calls": int(r.total_calls),
        })
    return Response(
        content=_json.dumps({"workspace_id": str(workspace.id), "periods": periods}),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=billing-export.json"},
    )


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
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    end_user_id: Annotated[str | None, Query()] = None,
    feature_tag: Annotated[str | None, Query()] = None,
    app_id: Annotated[str | None, Query()] = None,
    access_group_id: Annotated[str | None, Query()] = None,
    provider_profile_id: Annotated[str | None, Query()] = None,
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
        app_id=app_id,
        api_key_id=str(api_key.id),
        access_group_id=access_group_id,
        provider_profile_id=provider_profile_id,
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
        items=[_notification_response(n) for n in notifications]
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
    await emit_audit_event(
        db,
        workspace.id,
        "notification.created",
        target_type="webhook_destination",
        target_id=str(notification.id),
        after={
            "channel": notification.channel,
            "destination_url": notification.destination_url,
            "events": notification.events,
            "is_active": notification.is_active,
        },
    )
    await db.commit()

    return _notification_response(notification)


@router.put("/notifications/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: uuid.UUID,
    body: NotificationUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationResponse:
    workspace: Workspace = auth[0]
    notification = await _get_notification(db, workspace.id, notification_id)
    before = {
        "destination_url": notification.destination_url,
        "events": list(notification.events or []),
        "is_active": notification.is_active,
    }

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(notification, key, value)

    await db.commit()
    await db.refresh(notification)
    await emit_audit_event(
        db,
        workspace.id,
        "notification.updated",
        target_type="webhook_destination",
        target_id=str(notification.id),
        before=before,
        after={
            "destination_url": notification.destination_url,
            "events": list(notification.events or []),
            "is_active": notification.is_active,
        },
    )
    await db.commit()

    return _notification_response(notification)


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace: Workspace = auth[0]
    notification = await _get_notification(db, workspace.id, notification_id)
    before = {
        "channel": notification.channel,
        "destination_url": notification.destination_url,
        "events": list(notification.events or []),
    }
    await db.delete(notification)
    await db.commit()
    await emit_audit_event(
        db,
        workspace.id,
        "notification.deleted",
        target_type="webhook_destination",
        target_id=str(notification_id),
        before=before,
    )
    await db.commit()


@router.post("/notifications/{notification_id}/test", response_model=NotificationTestResult)
async def test_notification(
    notification_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationTestResult:
    workspace: Workspace = auth[0]
    notification = await _get_notification(db, workspace.id, notification_id)
    payload = {
        "event": "webhook.test",
        "workspace_id": str(workspace.id),
        "workspace_name": workspace.name,
        "sent_at": datetime.now(UTC).isoformat(),
        "source": "runledger.webhooks",
        "message": "RunLedger webhook destination test event",
    }
    try:
        result = await send_notification(notification, payload)
        db.add(
            build_delivery_record(
                notification,
                event_type="webhook.test",
                status=str(result["status"]),
                response_status=result.get("response_status"),
                error_detail=result.get("error_detail"),
                delivered_at=result.get("delivered_at"),
            )
        )
        await emit_audit_event(
            db,
            workspace.id,
            "notification.tested",
            target_type="webhook_destination",
            target_id=str(notification.id),
            after={"ok": True, "channel": notification.channel},
        )
        await db.commit()
        return NotificationTestResult(ok=True)
    except Exception as exc:
        db.add(
            build_delivery_record(
                notification,
                event_type="webhook.test",
                status="failed",
                error_detail=str(exc),
            )
        )
        await emit_audit_event(
            db,
            workspace.id,
            "notification.tested",
            target_type="webhook_destination",
            target_id=str(notification.id),
            after={"ok": False, "channel": notification.channel, "error": str(exc)},
        )
        await db.commit()
        return NotificationTestResult(ok=False, error=str(exc))


@router.get("/notifications/{notification_id}/deliveries", response_model=NotificationDeliveryList)
async def list_notification_deliveries(
    notification_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> NotificationDeliveryList:
    workspace: Workspace = auth[0]
    notification = await _get_notification(db, workspace.id, notification_id)
    rows = (
        (
            await db.execute(
                select(BudgetNotificationDelivery)
                .where(BudgetNotificationDelivery.notification_id == notification.id)
                .order_by(BudgetNotificationDelivery.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return NotificationDeliveryList(
        items=[
            NotificationDeliveryResponse(
                id=str(row.id),
                notification_id=str(row.notification_id),
                event_type=row.event_type,
                attempt=row.attempt,
                status=row.status,
                response_status=row.response_status,
                error_detail=row.error_detail,
                delivered_at=row.delivered_at,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


# ── GET /budgets/{id}/breaches ────────────────────────────────────────────────


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetResponse:
    """Return a single budget with live spend state."""
    budget = await _get_workspace_budget(
        db=db,
        workspace_id=workspace.id,
        budget_id=budget_id,
    )
    spend = await get_budget_spend(redis, budget.id, budget.period_type)
    scope_display_name = await _resolve_scope_display_name(
        db,
        workspace.id,
        budget.scope_type,
        budget.scope_id,
    )
    return _budget_response(
        budget,
        current_spend_usd=spend,
        scope_display_name=scope_display_name,
    )


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    body: BudgetUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetResponse:
    """Update a budget policy in place."""
    workspace: Workspace = auth[0]
    budget = await _get_workspace_budget(
        db=db,
        workspace_id=workspace.id,
        budget_id=budget_id,
    )
    before = {
        "scope_type": budget.scope_type,
        "scope_id": budget.scope_id,
        "period_type": budget.period_type,
        "limit_usd": str(budget.limit_usd),
        "action": budget.action,
        "downgrade_to_model": budget.downgrade_to_model,
        "is_active": budget.is_active,
    }

    data = body.model_dump(exclude_unset=True)
    next_scope_type = data.get("scope_type", budget.scope_type)
    next_scope_id = data.get("scope_id", budget.scope_id)
    next_action = data.get("action", budget.action)
    next_downgrade_model = data.get(
        "downgrade_to_model",
        budget.downgrade_to_model,
    )

    _validate_budget_payload(
        scope_type=next_scope_type,
        scope_id=next_scope_id,
        action=next_action,
        downgrade_to_model=next_downgrade_model,
    )
    await _validate_scope_reference(db, workspace.id, next_scope_type, next_scope_id)

    for key, value in data.items():
        setattr(budget, key, value)

    await db.commit()
    await db.refresh(budget)
    await invalidate_workspace_budgets_cache(redis, workspace.id)

    await emit_audit_event(
        db,
        workspace.id,
        "budget.updated",
        target_type="budget",
        target_id=str(budget.id),
        before=before,
        after={
            "scope_type": budget.scope_type,
            "scope_id": budget.scope_id,
            "period_type": budget.period_type,
            "limit_usd": str(budget.limit_usd),
            "action": budget.action,
            "downgrade_to_model": budget.downgrade_to_model,
            "is_active": budget.is_active,
        },
    )
    await db.commit()

    spend = await get_budget_spend(redis, budget.id, budget.period_type)
    scope_display_name = await _resolve_scope_display_name(
        db,
        workspace.id,
        budget.scope_type,
        budget.scope_id,
    )
    return _budget_response(
        budget,
        current_spend_usd=spend,
        scope_display_name=scope_display_name,
    )


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


# ── POST /budgets/{id}/override ──────────────────────────────────────────────


@router.post(
    "/{budget_id}/override",
    response_model=BudgetOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_override(
    budget_id: uuid.UUID,
    body: BudgetOverrideCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetOverrideResponse:
    """Create a time-boxed budget increase."""
    workspace: Workspace = auth[0]

    budget_result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.workspace_id == workspace.id)
    )
    budget = budget_result.scalar_one_or_none()
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")

    if body.expires_at <= body.starts_at:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "expires_at must be after starts_at",
        )

    requested_by = api_key.created_by
    override_status = "pending" if body.require_approval or body.starts_at > datetime.now(UTC) else "active"
    override = BudgetOverride(
        budget_id=budget_id,
        original_limit_usd=budget.limit_usd,
        override_limit_usd=body.override_limit_usd,
        starts_at=body.starts_at,
        expires_at=body.expires_at,
        reason=body.reason,
        status=override_status,
    )
    db.add(override)
    await db.flush()

    approval: Approval | None = None
    if body.require_approval:
        approval = Approval(
            workspace_id=workspace.id,
            request_type="budget_increase",
            request={
                "budget_id": str(budget.id),
                "budget_override_id": str(override.id),
                "current_limit": str(budget.limit_usd),
                "requested_limit": str(body.override_limit_usd),
                "scope_type": budget.scope_type,
                "scope_id": budget.scope_id,
                "starts_at": body.starts_at.isoformat(),
                "expires_at": body.expires_at.isoformat(),
                "_reason": body.reason,
            },
            status="pending",
            requested_by=requested_by,
        )
        db.add(approval)

    await db.commit()
    await db.refresh(override)
    await invalidate_workspace_budgets_cache(redis, workspace.id)

    log.info(
        "budget_override_created",
        override_id=str(override.id),
        budget_id=str(budget_id),
        override_limit=str(override.override_limit_usd),
    )
    await emit_audit_event(
        db,
        workspace.id,
        "budget_override.created",
        target_type="budget_override",
        target_id=str(override.id),
        after={
            "budget_id": str(budget.id),
            "override_limit_usd": str(override.override_limit_usd),
            "status": override.status,
            "approval_id": str(approval.id) if approval else None,
        },
    )
    if approval is not None:
        await emit_audit_event(
            db,
            workspace.id,
            "approval.requested",
            target_type="approval",
            target_id=str(approval.id),
            after={
                "request_type": approval.request_type,
                "budget_override_id": str(override.id),
            },
        )
    await db.commit()
    return _override_response(override, approval)


# ── GET /budgets/{id}/overrides ──────────────────────────────────────────────


@router.get("/{budget_id}/overrides", response_model=BudgetOverrideList)
async def list_overrides(
    budget_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BudgetOverrideList:
    """List overrides for a budget."""
    budget_result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.workspace_id == workspace.id)
    )
    if budget_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")

    result = await db.execute(
        select(BudgetOverride)
        .where(BudgetOverride.budget_id == budget_id)
        .order_by(BudgetOverride.created_at.desc())
        .limit(limit)
    )
    overrides = list(result.scalars())
    approvals = await _override_approval_map(
        db,
        workspace.id,
        [override.id for override in overrides],
    )
    return BudgetOverrideList(
        items=[_override_response(override, approvals.get(override.id)) for override in overrides]
    )


# ── POST /budgets/{id}/override/{oid}/revoke ─────────────────────────────────


@router.post("/{budget_id}/override/{override_id}/revoke", response_model=BudgetOverrideResponse)
async def revoke_override(
    budget_id: uuid.UUID,
    override_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetOverrideResponse:
    """Revoke an active budget override."""
    workspace: Workspace = auth[0]

    budget_result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.workspace_id == workspace.id)
    )
    if budget_result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget not found")

    result = await db.execute(
        select(BudgetOverride).where(
            BudgetOverride.id == override_id,
            BudgetOverride.budget_id == budget_id,
        )
    )
    override = result.scalar_one_or_none()
    if override is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Override not found")
    if override.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Override is not active")

    await db.execute(
        update(BudgetOverride).where(BudgetOverride.id == override_id).values(status="revoked")
    )
    approvals = await _override_approval_map(db, workspace.id, [override.id])
    await db.commit()
    await invalidate_workspace_budgets_cache(redis, workspace.id)
    override.status = "revoked"

    log.info("budget_override_revoked", override_id=str(override_id))
    await emit_audit_event(
        db,
        workspace.id,
        "budget_override.revoked",
        target_type="budget_override",
        target_id=str(override.id),
        after={"status": override.status},
    )
    await db.commit()
    return _override_response(override, approvals.get(override.id))
