"""SaaS Foundation routes.

POST /auth/signup      — self-service signup (no admin required)
GET  /billing/subscription — current plan + quota usage
POST /billing/checkout — create Stripe checkout session
POST /billing/portal   — Stripe customer portal session
POST /webhooks/stripe  — Stripe webhook handler
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

import bcrypt
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.saas import PLAN_QUOTAS, Subscription, UsageQuota
from runledger_api.models.tenant import (
    ApiKey,
    EnvironmentEnum,
    PlanEnum,
    Tenant,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceUser,
)
from runledger_api.schemas.saas import (
    CheckoutRequest,
    CheckoutResponse,
    PortalRequest,
    PortalResponse,
    SignupRequest,
    SignupResponse,
    SubscriptionResponse,
)
from runledger_api.services.auth import generate_api_key
from runledger_api.services.email import send_welcome_email

log = structlog.get_logger()

router = APIRouter(tags=["saas"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]

_STRIPE_PRICE_MAP = {
    "starter": lambda: settings.stripe_price_starter,
    "growth": lambda: settings.stripe_price_growth,
    "enterprise": lambda: settings.stripe_price_enterprise,
}


def _make_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    suffix = secrets.token_hex(3)
    return f"{slug}-{suffix}"


# ── Signup ────────────────────────────────────────────────────────────────────

@router.post("/auth/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: DbDep) -> SignupResponse:
    """
    Self-service signup. Creates user + tenant + workspace + free plan quota in one
    transaction. Returns an API key. No admin secret required.
    """
    # Reject duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Create user
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    verify_token = secrets.token_urlsafe(32)
    user = User(
        email=body.email,
        password_hash=pw_hash,
        full_name=body.full_name,
        is_active=True,
        is_platform_admin=False,
        email_verified=False,
        email_verify_token=verify_token,
    )
    db.add(user)
    await db.flush()

    # Create tenant on free plan
    slug = _make_slug(body.org_name)
    tenant = Tenant(slug=slug, name=body.org_name, plan=PlanEnum.free, is_default=False)
    db.add(tenant)
    await db.flush()
    tenant.owner_user_id = user.id

    # TenantUser — org_admin
    db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin))

    # Default workspace
    workspace = Workspace(tenant_id=tenant.id, name=f"{body.org_name} Workspace")
    db.add(workspace)
    await db.flush()

    # WorkspaceUser — workspace_admin
    db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin))

    # Free-tier subscription row
    db.add(Subscription(
        tenant_id=tenant.id,
        plan="free",
        status="active",
        current_period_start=datetime.now(UTC),
    ))

    # Usage quota — free tier limit
    db.add(UsageQuota(
        tenant_id=tenant.id,
        events_limit=PLAN_QUOTAS["free"],
        events_used=0,
        period_start=datetime.now(UTC),
    ))

    # API key
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    db.add(ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="default",
        scopes=[],
    ))

    await db.commit()
    log.info("signup_complete", email=body.email, tenant_id=str(tenant.id))

    # Send welcome email with credentials + verification link (non-blocking)
    verify_url = f"{settings.app_base_url}/verify-email?token={verify_token}"
    await send_welcome_email(
        to_email=body.email,
        full_name=body.full_name,
        password=body.password,
        api_key=raw_key,
        verify_url=verify_url,
    )

    return SignupResponse(
        user_id=user.id,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        api_key=raw_key,
        message="Account created. Check your email to verify your address.",
    )


# ── Email verification ────────────────────────────────────────────────────────

@router.get("/auth/verify-email")
async def verify_email(token: str, db: DbDep) -> dict[str, str]:
    """Verify email address using the token sent on signup."""
    result = await db.execute(select(User).where(User.email_verify_token == token))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link")
    user.email_verified = True
    user.email_verify_token = None
    await db.commit()
    log.info("email_verified", user_id=str(user.id), email=user.email)
    return {"status": "verified", "email": user.email}


# ── Subscription / quota ──────────────────────────────────────────────────────

@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(workspace: WorkspaceDep, db: DbDep) -> SubscriptionResponse:
    """Return the current plan and quota usage for the authenticated workspace's tenant."""
    tenant_id = workspace.tenant_id

    sub_result = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
    sub = sub_result.scalar_one_or_none()

    quota_result = await db.execute(select(UsageQuota).where(UsageQuota.tenant_id == tenant_id))
    quota = quota_result.scalar_one_or_none()

    plan = sub.plan if sub else "free"
    events_limit = quota.events_limit if quota else PLAN_QUOTAS["free"]
    events_used = quota.events_used if quota else 0
    usage_pct = round(events_used / events_limit * 100, 2) if events_limit > 0 else 0.0

    return SubscriptionResponse(
        tenant_id=tenant_id,
        plan=plan,
        status=sub.status if sub else "active",
        stripe_customer_id=sub.stripe_customer_id if sub else None,
        stripe_subscription_id=sub.stripe_subscription_id if sub else None,
        current_period_start=sub.current_period_start if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        events_limit=events_limit,
        events_used=events_used,
        usage_pct=usage_pct,
    )


# ── Stripe checkout ───────────────────────────────────────────────────────────

@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(body: CheckoutRequest, workspace: WorkspaceDep, db: DbDep) -> CheckoutResponse:
    """Create a Stripe checkout session for plan upgrade."""
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stripe not configured")

    price_id_fn = _STRIPE_PRICE_MAP.get(body.plan)
    if price_id_fn is None or not price_id_fn():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown plan: {body.plan}")

    try:
        import stripe  # noqa: PLC0415
        stripe.api_key = settings.stripe_secret_key
    except ImportError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "stripe package not installed")

    # Get or create Stripe customer
    sub_result = await db.execute(select(Subscription).where(Subscription.tenant_id == workspace.tenant_id))
    sub = sub_result.scalar_one_or_none()

    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == workspace.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        customer = stripe.Customer.create(name=tenant.name if tenant else str(workspace.tenant_id))
        customer_id = customer.id
        if sub:
            await db.execute(
                update(Subscription)
                .where(Subscription.tenant_id == workspace.tenant_id)
                .values(stripe_customer_id=customer_id)
            )
            await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id_fn(), "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"tenant_id": str(workspace.tenant_id)},
    )
    return CheckoutResponse(checkout_url=session.url)


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal(body: PortalRequest, workspace: WorkspaceDep, db: DbDep) -> PortalResponse:
    """Create a Stripe customer portal session for subscription management."""
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stripe not configured")

    try:
        import stripe  # noqa: PLC0415
        stripe.api_key = settings.stripe_secret_key
    except ImportError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "stripe package not installed")

    sub_result = await db.execute(select(Subscription).where(Subscription.tenant_id == workspace.tenant_id))
    sub = sub_result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Stripe subscription found. Upgrade first.")

    portal = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=body.return_url,
    )
    return PortalResponse(portal_url=portal.url)


# ── Stripe webhook ────────────────────────────────────────────────────────────

_PLAN_FROM_STRIPE: dict[str, str] = {}  # populated at runtime from STRIPE_PRICE_* env


@router.post("/webhooks/stripe", status_code=200)
async def stripe_webhook(request: Request, db: DbDep) -> dict[str, str]:
    """
    Handle Stripe webhook events:
    - invoice.paid                      → confirm subscription active
    - customer.subscription.updated     → update plan + quota
    - customer.subscription.deleted     → downgrade to free
    """
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stripe not configured")

    try:
        import stripe  # noqa: PLC0415
        stripe.api_key = settings.stripe_secret_key
    except ImportError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "stripe package not installed")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Stripe signature")

    await _handle_stripe_event(event, db)
    return {"status": "ok"}


async def _handle_stripe_event(event: object, db: AsyncSession) -> None:
    """Dispatch Stripe event to the appropriate handler."""
    event_type = getattr(event, "type", "")
    data_obj = getattr(getattr(event, "data", None), "object", None)
    if data_obj is None:
        return

    if event_type == "customer.subscription.updated":
        await _sync_subscription(data_obj, db)
    elif event_type == "customer.subscription.deleted":
        await _downgrade_to_free(data_obj, db)
    elif event_type == "invoice.paid":
        # Ensure subscription row is active after successful payment
        stripe_sub_id = getattr(data_obj, "subscription", None)
        if stripe_sub_id:
            await db.execute(
                update(Subscription)
                .where(Subscription.stripe_subscription_id == stripe_sub_id)
                .values(status="active")
            )
            await db.commit()


async def _sync_subscription(stripe_sub: object, db: AsyncSession) -> None:
    """Sync plan and period from a Stripe subscription object."""
    stripe_sub_id = getattr(stripe_sub, "id", None)
    customer_id = getattr(stripe_sub, "customer", None)
    status_val = getattr(stripe_sub, "status", "active")

    period_start = datetime.fromtimestamp(getattr(stripe_sub, "current_period_start", 0), tz=UTC)
    period_end = datetime.fromtimestamp(getattr(stripe_sub, "current_period_end", 0), tz=UTC)

    # Determine plan from price ID
    items = getattr(stripe_sub, "items", None)
    plan_name = "starter"
    if items:
        price_id = None
        for item in getattr(items, "data", []):
            price_id = getattr(getattr(item, "price", None), "id", None)
            break
        price_plan_map = {
            settings.stripe_price_starter: "starter",
            settings.stripe_price_growth: "growth",
            settings.stripe_price_enterprise: "enterprise",
        }
        plan_name = price_plan_map.get(price_id or "", "starter")

    sub_result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = sub_result.scalar_one_or_none()
    if sub is None:
        return

    await db.execute(
        update(Subscription)
        .where(Subscription.id == sub.id)
        .values(
            stripe_subscription_id=stripe_sub_id,
            plan=plan_name,
            status=status_val,
            current_period_start=period_start,
            current_period_end=period_end,
        )
    )
    # Update plan on tenant + bump quota limit
    await db.execute(
        update(Tenant)
        .where(Tenant.id == sub.tenant_id)
        .values(plan=plan_name)
    )
    await db.execute(
        update(UsageQuota)
        .where(UsageQuota.tenant_id == sub.tenant_id)
        .values(events_limit=PLAN_QUOTAS.get(plan_name, PLAN_QUOTAS["free"]))
    )
    await db.commit()
    log.info("stripe_subscription_synced", plan=plan_name, tenant_id=str(sub.tenant_id))


async def _downgrade_to_free(stripe_sub: object, db: AsyncSession) -> None:
    """Downgrade tenant to free plan when subscription is cancelled."""
    customer_id = getattr(stripe_sub, "customer", None)
    sub_result = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    )
    sub = sub_result.scalar_one_or_none()
    if sub is None:
        return

    await db.execute(
        update(Subscription)
        .where(Subscription.id == sub.id)
        .values(plan="free", status="canceled", stripe_subscription_id=None)
    )
    await db.execute(
        update(Tenant)
        .where(Tenant.id == sub.tenant_id)
        .values(plan="free")
    )
    await db.execute(
        update(UsageQuota)
        .where(UsageQuota.tenant_id == sub.tenant_id)
        .values(events_limit=PLAN_QUOTAS["free"])
    )
    await db.commit()
    log.info("stripe_subscription_cancelled", tenant_id=str(sub.tenant_id))
