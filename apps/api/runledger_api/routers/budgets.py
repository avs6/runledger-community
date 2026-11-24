"""
Budget CRUD + hot-path check endpoints.

Prefix: /budgets
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /budgets                  Create a budget
GET    /budgets                  List budgets with current Redis spend
GET    /budgets/check            Pre-call check (budgets, model budgets, runaway holds)
POST   /budgets/simulate         Replay the last 30 days against a candidate budget
GET    /budgets/{id}/burndown    Spend this period + forecast-to-breach date
GET    /budgets/runaway-holds    Runs / sessions held by runaway protection
POST   /budgets/runaway-holds    Hold a run or session; …/{id}/release releases it
GET    /budgets/{id}/breaches    Breach history
DELETE /budgets/{id}             Soft-delete (is_active=False)
POST   /budgets/notifications    Create notification channel
GET    /budgets/notifications    List notification channels
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy import and_, literal_column, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_user,
    get_current_workspace,
    require_workspace_admin,
)
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.core.secrets import SECRET_MASK, is_mask, mask_url
from runledger_api.models.access_groups import AccessGroup
from runledger_api.models.approvals import Approval
from runledger_api.models.budget_overrides import BudgetOverride
from runledger_api.models.budgets import (
    Budget,
    BudgetBreach,
    BudgetNotification,
    BudgetNotificationDelivery,
    RunawayHold,
)
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import (
    ApiKey,
    Application,
    TenantRoleEnum,
    TenantUser,
    Workspace,
)
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
    BudgetBurndownPoint,
    BudgetBurndownResponse,
    BudgetCheckResponse,
    BudgetCreate,
    BudgetList,
    BudgetResponse,
    BudgetRollupResponse,
    BudgetRollupWorkspace,
    BudgetSimulatePeriod,
    BudgetSimulateRequest,
    BudgetSimulateResponse,
    BudgetUpdate,
    BudgetUserBreakdownEntry,
    NotificationCreate,
    NotificationDeliveryList,
    NotificationDeliveryResponse,
    NotificationList,
    NotificationResponse,
    NotificationTestResult,
    NotificationUpdate,
    RunawayHoldCreate,
    RunawayHoldList,
    RunawayHoldResponse,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.budgets import (
    UUID_SCOPES,
    budget_burndown,
    build_delivery_record,
    check_budgets,
    get_budget_spend,
    invalidate_runaway_holds_cache,
    invalidate_workspace_budgets_cache,
    send_notification,
    simulate_budget,
)
from runledger_api.services.budgets import (
    get_budget_breakdown as _svc_get_budget_breakdown,
)

# An override above this multiple of the budget's limit requires approval (F-13).
OVERRIDE_APPROVAL_RATIO = Decimal("1.5")

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
    breakdown: list[dict] | None = None,
) -> BudgetResponse:
    pct = (current_spend_usd / budget.limit_usd * 100) if budget.limit_usd > 0 else Decimal("0")
    if pct.is_zero():
        pct = Decimal("0")
    return BudgetResponse(
        id=str(budget.id),
        scope_type=budget.scope_type,
        scope_id=budget.scope_id,
        scope_display_name=scope_display_name,
        api_key_id=str(budget.api_key_id) if getattr(budget, "api_key_id", None) else None,
        period_type=budget.period_type,
        limit_usd=budget.limit_usd,
        action=budget.action,
        downgrade_to_model=budget.downgrade_to_model,
        is_active=budget.is_active,
        created_at=budget.created_at,
        current_spend_usd=current_spend_usd,
        pct_used=pct,
        breakdown=breakdown,
    )


def _validate_budget_payload(
    *,
    scope_type: str,
    scope_id: str | None,
    action: str,
    downgrade_to_model: str | None,
    api_key_id: str | None = None,
) -> None:
    """Shape checks for a budget scope (review F-12); references are checked by
    :func:`_validate_scope_reference`."""
    if scope_type == "workspace":
        if scope_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Workspace budgets take no scope_id",
            )
    elif not scope_id or not scope_id.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "scope_id is required for non-workspace budgets",
        )
    if scope_type in UUID_SCOPES and scope_id:
        try:
            uuid.UUID(scope_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"scope_id must be a valid {scope_type.replace('_', ' ')} UUID",
            ) from exc
    if scope_type == "model" and scope_id and "*" in scope_id[:-1]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Model patterns support one trailing * only (e.g. gpt-4*)",
        )
    if api_key_id is not None and scope_type != "model":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "api_key_id narrows model budgets only; use scope_type=api_key for a key budget",
        )
    if action in {"downgrade", "fallback"} and not downgrade_to_model:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "downgrade_to_model is required for downgrade or fallback actions",
        )


async def _ensure_unique_scope(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    scope_type: str,
    scope_id: str | None,
    api_key_id: uuid.UUID | None,
    period_type: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """409 when an active budget already covers this scope, key filter and period
    (backed by the unique index uq_budgets_active_scope, review F-12)."""
    stmt = select(Budget.id).where(
        Budget.workspace_id == workspace_id,
        Budget.is_active.is_(True),
        Budget.scope_type == scope_type,
        Budget.period_type == period_type,
        (Budget.scope_id == scope_id) if scope_id is not None else Budget.scope_id.is_(None),
        (Budget.api_key_id == api_key_id)
        if api_key_id is not None
        else Budget.api_key_id.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Budget.id != exclude_id)
    if (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An active budget already exists for this scope and period; edit it instead",
        )


def _parse_key_id(api_key_id: str | None) -> uuid.UUID | None:
    if api_key_id is None:
        return None
    try:
        return uuid.UUID(api_key_id)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "api_key_id must be a valid UUID"
        ) from exc


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
    if scope_type in {"end_user", "feature_tag"}:
        return scope_id
    if scope_type == "model":
        return f"Model {scope_id}"
    if scope_type == "app":
        try:
            app_id = uuid.UUID(scope_id)
        except ValueError:
            return scope_id
        name = (
            await db.execute(
                select(Application.name).where(
                    Application.id == app_id, Application.workspace_id == workspace_id
                )
            )
        ).scalar_one_or_none()
        return str(name) if name else scope_id
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
    if scope_type in {"end_user", "feature_tag", "model"}:
        return
    if scope_type == "app":
        exists = (
            await db.execute(
                select(Application.id).where(
                    Application.id == uuid.UUID(scope_id),
                    Application.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
        return
    if scope_type == "access_group":
        try:
            group_id = uuid.UUID(scope_id)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        (
            await db.execute(
                select(Approval).where(
                    Approval.workspace_id == workspace_id,
                    Approval.request_type == "budget_increase",
                )
            )
        )
        .scalars()
        .all()
    )
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
        # Write-only (review F-15): the URL path/query carries the webhook token.
        destination_url=mask_url(notification.destination_url) or "",
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
        status.HTTP_422_UNPROCESSABLE_CONTENT, "scope must be workspace, org, or platform"
    )


# ── POST /budgets ─────────────────────────────────────────────────────────────


def _check_destination(url: str) -> None:
    """Webhook/Slack destinations must resolve to public addresses (SSRF)."""
    from runledger_api.services.egress import EgressBlocked, check_url  # noqa: PLC0415

    try:
        check_url(url)
    except EgressBlocked as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


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
        api_key_id=body.api_key_id,
    )
    await _validate_scope_reference(db, workspace.id, body.scope_type, body.scope_id)
    key_filter = _parse_key_id(body.api_key_id)
    if key_filter is not None:
        await _validate_scope_reference(db, workspace.id, "api_key", str(key_filter))
    await _ensure_unique_scope(
        db,
        workspace.id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        api_key_id=key_filter,
        period_type=body.period_type,
    )
    budget = Budget(
        workspace_id=workspace.id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        api_key_id=key_filter,
        period_type=body.period_type,
        limit_usd=body.limit_usd,
        action=body.action,
        downgrade_to_model=body.downgrade_to_model,
        is_active=True,
    )
    db.add(budget)
    try:
        await db.commit()
    except IntegrityError as exc:  # concurrent create of the same scope
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An active budget already exists for this scope and period"
        ) from exc
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
    page: PageDep,
    response: Response,
    include_inactive: Annotated[bool, Query()] = False,
    scope_type: Annotated[str | None, Query()] = None,
    scope_id: Annotated[str | None, Query()] = None,
) -> BudgetList:
    """List budgets with current period spend from Redis."""

    stmt = select(Budget).where(Budget.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(Budget.is_active.is_(True))
    if scope_type:
        stmt = stmt.where(Budget.scope_type == scope_type)
    if scope_id:
        stmt = stmt.where(Budget.scope_id == scope_id)
    stmt = stmt.order_by(Budget.created_at.desc(), Budget.id)
    budgets: list[Budget] = await paginate(db, stmt, page, response)

    items = []
    for b in budgets:
        spend = await get_budget_spend(redis, b.id, b.period_type, db=db)
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


async def _monthly_billing_rows(
    db: AsyncSession, workspace_id: uuid.UUID, months: int
) -> list[Any]:
    """Per month: priced cost, billable cost, all calls, billable calls (from provider
    calls, using the shared billable-cost definition)."""
    from sqlalchemy import case as sa_case  # noqa: PLC0415
    from sqlalchemy import func as sa_func  # noqa: PLC0415

    from runledger_api.models.events import ProviderCall  # noqa: PLC0415
    from runledger_api.services.billable import billable_cost_sum, billable_filters  # noqa: PLC0415

    month = sa_func.to_char(ProviderCall.created_at, literal_column("'YYYY-MM'")).label("period")
    result = await db.execute(
        select(
            month,
            sa_func.coalesce(sa_func.sum(ProviderCall.cost_usd), 0).label("total_cost"),
            billable_cost_sum().label("billable_cost"),
            sa_func.count(ProviderCall.id).label("total_calls"),
            sa_func.count(sa_case((and_(*billable_filters()), ProviderCall.id))).label(
                "billable_calls"
            ),
        )
        .where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at >= sa_func.current_date() - months * 31,
        )
        .group_by(month)
        .order_by(month)
    )
    return list(result.all())


# ── GET /budgets/billing-summary ──────────────────────────────────────────────


@router.get("/billing-summary", response_model=BillingSummaryResponse)
async def billing_summary(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    months: Annotated[int, Query(ge=1, le=12)] = 3,
) -> BillingSummaryResponse:
    """Billing summary with billable vs non-billable cost per month (shared
    billable-cost definition: priced calls with ``is_billable`` true)."""
    periods = []
    for row in await _monthly_billing_rows(db, workspace.id, months):
        total = Decimal(str(row.total_cost))
        billable = Decimal(str(row.billable_cost))
        periods.append(
            BillingPeriodSummary(
                period=row.period,
                total_cost_usd=total,
                billable_cost_usd=billable,
                non_billable_cost_usd=total - billable,
                total_calls=int(row.total_calls),
                billable_calls=int(row.billable_calls),
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

    rows = await _monthly_billing_rows(db, workspace.id, months)
    _ = sa_func

    if fmt == "csv":
        buf = StringIO()
        buf.write(
            "period,total_cost_usd,billable_cost_usd,non_billable_cost_usd,total_calls,billable_calls\n"
        )
        for r in rows:
            total = Decimal(str(r.total_cost))
            billable = Decimal(str(r.billable_cost))
            buf.write(
                f"{r.period},{total},{billable},{total - billable},{r.total_calls},{r.billable_calls}\n"
            )
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
        periods.append(
            {
                "period": r.period,
                "total_cost_usd": total,
                "billable_cost_usd": billable,
                "non_billable_cost_usd": round(total - billable, 8),
                "total_calls": int(r.total_calls),
                "billable_calls": int(r.billable_calls),
            }
        )
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

        spend = await get_budget_spend(redis, budget.id, budget.period_type, db=db)
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
    model: Annotated[str | None, Query(max_length=255)] = None,
    run_id: Annotated[str | None, Query(max_length=255)] = None,
    session_id: Annotated[str | None, Query(max_length=255)] = None,
) -> BudgetCheckResponse:
    """
    Budget check for SDK and MCP callers before a model call.

    Reads cached budget definitions and period spend (Redis, falling back to
    Postgres). Pass ``model`` to include model budgets and ``run_id`` /
    ``session_id`` to be told when runaway protection holds the run or session.
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
        model=model,
        run_id=run_id,
        session_id=session_id,
    )


# ── GET /budgets/notifications ────────────────────────────────────────────────


@router.get("/notifications", response_model=NotificationList)
async def list_notifications(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: PageDep,
    response: Response,
) -> NotificationList:
    """List notification channels for this workspace (workspace admins; review F-15)."""
    workspace: Workspace = auth[0]
    notifications: list[BudgetNotification] = await paginate(
        db,
        select(BudgetNotification)
        .where(BudgetNotification.workspace_id == workspace.id)
        .order_by(BudgetNotification.created_at.desc(), BudgetNotification.id),
        page,
        response,
    )

    return NotificationList(items=[_notification_response(n) for n in notifications])


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
    _check_destination(body.destination_url)
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
            "destination_url": mask_url(notification.destination_url),
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
        "destination_url": mask_url(notification.destination_url),
        "events": list(notification.events or []),
        "is_active": notification.is_active,
    }

    data = body.model_dump(exclude_unset=True)
    if is_mask(data.get("destination_url")) or (data.get("destination_url") or "").endswith(
        "/" + SECRET_MASK
    ):
        data.pop("destination_url")  # masked URL sent back unchanged: keep it
    if data.get("destination_url"):
        _check_destination(data["destination_url"])
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
            "destination_url": mask_url(notification.destination_url),
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
        "destination_url": mask_url(notification.destination_url),
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


@router.get("/notifications/{notification_id}/signing-secret")
async def get_notification_signing_secret(
    notification_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """This destination's webhook signing secret. Deliveries carry
    ``X-RunLedger-Signature: sha256=<hex HMAC-SHA256 of the raw body>``."""
    from runledger_api.services.billing_signing import webhook_secret  # noqa: PLC0415

    notification = await _get_notification(db, auth[0].id, notification_id)
    version = int(notification.signing_version or 1)
    return {
        "notification_id": str(notification.id),
        "signing_version": version,
        "secret": webhook_secret(notification.id, version),
    }


@router.post("/notifications/{notification_id}/signing-secret/rotate")
async def rotate_notification_signing_secret(
    notification_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Rotate this destination's signing secret; the old one stops verifying."""
    from runledger_api.services.billing_signing import webhook_secret  # noqa: PLC0415

    workspace: Workspace = auth[0]
    notification = await _get_notification(db, workspace.id, notification_id)
    notification.signing_version = int(notification.signing_version or 1) + 1
    await emit_audit_event(
        db,
        workspace.id,
        "notification.signing_secret_rotated",
        target_type="webhook_destination",
        target_id=str(notification.id),
        after={"signing_version": notification.signing_version},
    )
    await db.commit()
    return {
        "notification_id": str(notification.id),
        "signing_version": notification.signing_version,
        "secret": webhook_secret(notification.id, notification.signing_version),
    }


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


# ── Runaway holds (review cd:B-09) ───────────────────────────────────────────


def _hold_response(hold: RunawayHold) -> RunawayHoldResponse:
    now = datetime.now(UTC)
    return RunawayHoldResponse(
        id=str(hold.id),
        subject_type=hold.subject_type,
        subject_id=hold.subject_id,
        reason=hold.reason,
        details=hold.details or {},
        created_at=hold.created_at,
        expires_at=hold.expires_at,
        released_at=hold.released_at,
        active=hold.released_at is None and hold.expires_at > now,
    )


@router.get("/runaway-holds", response_model=RunawayHoldList)
async def list_runaway_holds(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: PageDep,
    response: Response,
    active_only: Annotated[bool, Query()] = False,
) -> RunawayHoldList:
    """Runs and sessions runaway protection has held (newest first)."""
    stmt = select(RunawayHold).where(RunawayHold.workspace_id == workspace.id)
    if active_only:
        stmt = stmt.where(
            RunawayHold.released_at.is_(None), RunawayHold.expires_at > datetime.now(UTC)
        )
    holds = await paginate(
        db, stmt.order_by(RunawayHold.created_at.desc(), RunawayHold.id), page, response
    )
    return RunawayHoldList(items=[_hold_response(h) for h in holds])


@router.post(
    "/runaway-holds", response_model=RunawayHoldResponse, status_code=status.HTTP_201_CREATED
)
async def create_runaway_hold(
    body: RunawayHoldCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> RunawayHoldResponse:
    """Hold a run or session by hand: the gateway refuses its calls until released."""
    workspace: Workspace = auth[0]
    hold = RunawayHold(
        workspace_id=workspace.id,
        subject_type=body.subject_type,
        subject_id=body.subject_id.strip(),
        reason=body.reason or "manual",
        details={"source": "manual"},
        created_by=api_key.created_by,
        expires_at=datetime.now(UTC) + timedelta(minutes=body.minutes),
    )
    db.add(hold)
    await db.flush()
    await emit_audit_event(
        db,
        workspace.id,
        "runaway_hold.created",
        target_type="runaway_hold",
        target_id=str(hold.id),
        after={"subject": f"{hold.subject_type}:{hold.subject_id}", "minutes": body.minutes},
    )
    await db.commit()
    await db.refresh(hold)
    await invalidate_runaway_holds_cache(redis, workspace.id)
    return _hold_response(hold)


@router.post("/runaway-holds/{hold_id}/release", response_model=RunawayHoldResponse)
async def release_runaway_hold(
    hold_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    api_key: Annotated[ApiKey, Depends(get_current_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> RunawayHoldResponse:
    """Release a hold; the run or session can call the gateway again."""
    workspace: Workspace = auth[0]
    hold = (
        await db.execute(
            select(RunawayHold).where(
                RunawayHold.id == hold_id, RunawayHold.workspace_id == workspace.id
            )
        )
    ).scalar_one_or_none()
    if hold is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hold not found")
    if hold.released_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Hold already released")
    hold.released_at = datetime.now(UTC)
    hold.released_by = api_key.created_by
    await emit_audit_event(
        db,
        workspace.id,
        "runaway_hold.released",
        target_type="runaway_hold",
        target_id=str(hold.id),
        after={"subject": f"{hold.subject_type}:{hold.subject_id}"},
    )
    await db.commit()
    await invalidate_runaway_holds_cache(redis, workspace.id)
    return _hold_response(hold)


# ── Simulation (ENH) ─────────────────────────────────────────────────────────


@router.post("/simulate", response_model=BudgetSimulateResponse)
async def simulate(
    body: BudgetSimulateRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetSimulateResponse:
    """Replay the last N days (default 30) of real spend against a candidate budget:
    when it would have breached and how many calls its action would have affected."""
    _validate_budget_payload(
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        action=body.action,
        downgrade_to_model=body.action if body.action in {"downgrade", "fallback"} else None,
        api_key_id=body.api_key_id,
    )
    await _validate_scope_reference(db, workspace.id, body.scope_type, body.scope_id)
    key_filter = _parse_key_id(body.api_key_id)
    try:
        result = await simulate_budget(
            db,
            workspace.id,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            api_key_id=str(key_filter) if key_filter else None,
            period_type=body.period_type,
            limit_usd=body.limit_usd,
            action=body.action,
            days=body.days,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return BudgetSimulateResponse(
        **{k: v for k, v in result.items() if k != "periods"},
        periods=[BudgetSimulatePeriod(**p) for p in result["periods"]],
    )


@router.get("/{budget_id}/burndown", response_model=BudgetBurndownResponse)
async def get_budget_burndown(
    budget_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> BudgetBurndownResponse:
    """Cumulative spend this period with a run-rate forecast and forecast-to-breach date."""
    budget = await _get_workspace_budget(db=db, workspace_id=workspace.id, budget_id=budget_id)
    data = await budget_burndown(db, redis, budget)
    return BudgetBurndownResponse(
        **{k: v for k, v in data.items() if k != "points"},
        points=[BudgetBurndownPoint(**p) for p in data["points"]],
    )


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
    # Get spend breakdown by end user
    breakdown = await _svc_get_budget_breakdown(
        budget=budget,
        workspace=workspace,
        db=db,
        end_user_id=None,
    )
    spend = await get_budget_spend(redis, budget.id, budget.period_type, db=db)
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
        breakdown=breakdown,
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

    next_key = (
        data["api_key_id"]
        if "api_key_id" in data
        else (str(budget.api_key_id) if budget.api_key_id else None)
    )
    if next_scope_type != "model" and "api_key_id" not in data:
        next_key = None  # leaving model scope drops the key filter
    _validate_budget_payload(
        scope_type=next_scope_type,
        scope_id=next_scope_id,
        action=next_action,
        downgrade_to_model=next_downgrade_model,
        api_key_id=next_key,
    )
    await _validate_scope_reference(db, workspace.id, next_scope_type, next_scope_id)
    key_filter = _parse_key_id(next_key)
    if key_filter is not None:
        await _validate_scope_reference(db, workspace.id, "api_key", str(key_filter))
    if data.get("is_active", budget.is_active):
        await _ensure_unique_scope(
            db,
            workspace.id,
            scope_type=next_scope_type,
            scope_id=next_scope_id,
            api_key_id=key_filter,
            period_type=data.get("period_type", budget.period_type),
            exclude_id=budget.id,
        )

    data.pop("api_key_id", None)
    for key, value in data.items():
        setattr(budget, key, value)
    budget.api_key_id = key_filter

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An active budget already exists for this scope and period"
        ) from exc
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

    spend = await get_budget_spend(redis, budget.id, budget.period_type, db=db)
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
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "expires_at must be after starts_at",
        )

    requested_by = api_key.created_by
    # Large increases always need a second admin's approval (review F-13): the
    # requester can't skip it by leaving require_approval off.
    needs_approval = body.require_approval or (
        budget.limit_usd > 0
        and body.override_limit_usd > budget.limit_usd * OVERRIDE_APPROVAL_RATIO
    )
    if needs_approval:
        override_status = "pending"
    elif body.starts_at > datetime.now(UTC):
        override_status = "scheduled"  # activated by budgets.expire_overrides
    else:
        override_status = "active"
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
    if needs_approval:
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
    if override.status not in {"active", "scheduled", "pending"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Override is no longer active")

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


# ── GET /budgets/{id}/breakdown ────────────────────────────────────────
@router.get("/{budget_id}/breakdown", response_model=list[BudgetUserBreakdownEntry])
async def get_budget_user_breakdown(
    budget_id: uuid.UUID,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    end_user_id: Annotated[str | None, Query()] = None,
) -> list[BudgetUserBreakdownEntry]:
    """Get spend breakdown by end user for a budget."""
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

    return await _svc_get_budget_breakdown(
        budget=budget,
        workspace=workspace,
        db=db,
        end_user_id=end_user_id,
    )
