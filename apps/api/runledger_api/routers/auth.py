from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_admin
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import (
    ApiKey,
    Application,
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
from runledger_api.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApplicationCreate,
    ApplicationResponse,
    TenantCreate,
    TenantResponse,
    WorkspaceCreate,
    WorkspaceResponse,
)
from runledger_api.schemas.providers import (
    ProviderPricingCreate,
    ProviderPricingResponse,
    ProviderPricingUpdate,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _make_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]
    return f"{base}-{secrets.token_hex(3)}"


# ── Tenants ───────────────────────────────────────────────────────────────────


@router.post("/tenants", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(body: TenantCreate, db: DbDep) -> dict[str, Any]:
    """Atomically creates Tenant + org admin User + TenantUser + default Workspace."""
    existing = await db.execute(select(User).where(User.email == body.admin_email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.admin_email}' already exists")

    slug = _make_slug(body.name)
    tenant = Tenant(slug=slug, name=body.name, plan=body.plan)
    db.add(tenant)
    await db.flush()

    pw_hash = bcrypt.hashpw(body.admin_password.encode(), bcrypt.gensalt()).decode()
    user = User(
        email=body.admin_email,
        password_hash=pw_hash,
        full_name=body.admin_full_name or body.admin_email.split("@")[0],
        is_active=True,
    )
    db.add(user)
    await db.flush()

    tenant.owner_user_id = user.id
    db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin))

    workspace = Workspace(tenant_id=tenant.id, name=f"{body.name} Workspace")
    db.add(workspace)
    await db.flush()

    db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin))
    await db.commit()
    await db.refresh(tenant)

    log.info("tenant_created", tenant_id=str(tenant.id), admin_email=body.admin_email)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "plan": tenant.plan,
        "is_default": tenant.is_default,
        "owner_user_id": tenant.owner_user_id,
        "created_at": tenant.created_at,
        "workspace_count": 1,
        "member_count": 1,
    }


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(db: DbDep) -> list[dict[str, Any]]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = list(result.scalars().all())
    out = []
    for t in tenants:
        ws = (await db.execute(select(Workspace).where(Workspace.tenant_id == t.id))).scalars().all()
        tu = (await db.execute(select(TenantUser).where(TenantUser.tenant_id == t.id))).scalars().all()
        out.append({
            "id": t.id, "name": t.name, "plan": t.plan,
            "is_default": t.is_default, "owner_user_id": t.owner_user_id,
            "created_at": t.created_at, "workspace_count": len(ws), "member_count": len(tu),
        })
    return out


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: uuid.UUID, db: DbDep) -> None:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    if tenant.is_default:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the default tenant")
    await db.delete(tenant)
    await db.commit()


# ── Workspaces ────────────────────────────────────────────────────────────────


@router.post("/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceResponse)
async def create_workspace(body: WorkspaceCreate, db: DbDep) -> Workspace:
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    workspace = Workspace(tenant_id=body.tenant_id, name=body.name)
    db.add(workspace)
    await db.flush()
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/tenants/{tenant_id}/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(tenant_id: uuid.UUID, db: DbDep) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.tenant_id == tenant_id).order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


# ── Applications ──────────────────────────────────────────────────────────────


@router.post("/applications", status_code=status.HTTP_201_CREATED, response_model=ApplicationResponse)
async def create_application(body: ApplicationCreate, db: DbDep) -> Application:
    workspace = await db.get(Workspace, body.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    app = Application(workspace_id=body.workspace_id, name=body.name, environment=body.environment)
    db.add(app)
    await db.flush()
    await db.commit()
    await db.refresh(app)
    return app


# ── API Keys ──────────────────────────────────────────────────────────────────


@router.post("/workspaces/{workspace_id}/api-keys", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreateResponse)
async def create_api_key(workspace_id: uuid.UUID, body: ApiKeyCreate, db: DbDep) -> dict[str, Any]:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    raw_key, key_hash, key_prefix = generate_api_key(body.environment)
    api_key = ApiKey(workspace_id=workspace_id, key_hash=key_hash, key_prefix=key_prefix,
                     name=body.name, scopes=body.scopes)
    db.add(api_key)
    await db.flush()
    await db.commit()
    await db.refresh(api_key)
    await emit_audit_event(
        db, workspace_id, "api_key.created",
        target_type="api_key", target_id=str(api_key.id),
        after={"name": api_key.name, "key_prefix": api_key.key_prefix},
    )
    await db.commit()
    return {"id": api_key.id, "workspace_id": api_key.workspace_id, "key_prefix": api_key.key_prefix,
            "name": api_key.name, "scopes": api_key.scopes, "created_at": api_key.created_at,
            "created_by": api_key.created_by, "is_session": api_key.is_session, "key": raw_key}


@router.get("/workspaces/{workspace_id}/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(workspace_id: uuid.UUID, db: DbDep) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.workspace_id == workspace_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: uuid.UUID, db: DbDep) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked_at = datetime.now(UTC)
    await emit_audit_event(
        db, api_key.workspace_id, "api_key.revoked",
        target_type="api_key", target_id=str(api_key.id),
        before={"name": api_key.name, "key_prefix": api_key.key_prefix},
    )
    await db.commit()


# ── Bootstrap ────────────────────────────────────────────────────────────────


class BootstrapRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    org_name: str = "Default Organization"


class BootstrapResponse(BaseModel):
    user_id: str
    tenant_id: str
    workspace_id: str
    api_key: str
    message: str


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
async def bootstrap_platform_admin(body: BootstrapRequest, db: DbDep) -> BootstrapResponse:
    """
    One-time bootstrap: creates the platform admin user + default org.
    Protected by X-Admin-Secret. Call once after fresh deployment.
    Idempotent: if user already exists, just promotes them to platform admin.
    """
    from runledger_api.services.auth import generate_api_key as _gen_key  # noqa

    # Find or create user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        user = User(
            email=body.email,
            password_hash=pw_hash,
            full_name=body.full_name or body.email.split("@")[0],
            is_active=True,
            is_platform_admin=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.is_platform_admin = True
        if body.full_name:
            user.full_name = body.full_name

    # Find or create default tenant
    default_result = await db.execute(select(Tenant).where(Tenant.is_default == True))  # noqa: E712
    tenant = default_result.scalar_one_or_none()
    if tenant is None:
        slug = _make_slug(body.org_name)
        tenant = Tenant(slug=slug, name=body.org_name, plan=PlanEnum.enterprise, is_default=True)
        db.add(tenant)
        await db.flush()
        tenant.owner_user_id = user.id

    # Ensure TenantUser row
    tu_result = await db.execute(
        select(TenantUser).where(TenantUser.tenant_id == tenant.id, TenantUser.user_id == user.id)
    )
    if tu_result.scalar_one_or_none() is None:
        db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin))

    # Find or create workspace
    ws_result = await db.execute(select(Workspace).where(Workspace.tenant_id == tenant.id).limit(1))
    workspace = ws_result.scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(tenant_id=tenant.id, name=f"{body.org_name} Workspace")
        db.add(workspace)
        await db.flush()

    # Ensure WorkspaceUser row
    wu_result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace.id, WorkspaceUser.user_id == user.id
        )
    )
    if wu_result.scalar_one_or_none() is None:
        db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin))

    # Generate API key
    raw_key, key_hash, key_prefix = _gen_key(EnvironmentEnum.dev)
    db.add(ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="bootstrap-key",
        scopes=[],
    ))
    await db.commit()

    log.info("bootstrap_complete", email=body.email, tenant_id=str(tenant.id))
    return {
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "workspace_id": str(workspace.id),
        "api_key": raw_key,
        "message": f"Platform admin '{body.email}' ready. Use the api_key for your .env file.",
    }


# ── Global Pricing ────────────────────────────────────────────────────────────


@router.post("/global-pricing", status_code=status.HTTP_201_CREATED, response_model=ProviderPricingResponse)
async def create_global_pricing(body: ProviderPricingCreate, db: DbDep) -> ProviderPricing:
    pricing = ProviderPricing(workspace_id=None, provider=body.provider, model=body.model,
                               input_cost_per_1m=body.input_cost_per_1m,
                               output_cost_per_1m=body.output_cost_per_1m,
                               cached_input_cost_per_1m=body.cached_input_cost_per_1m,
                               effective_from=body.effective_from or datetime.now(UTC))
    db.add(pricing)
    await db.flush()
    await db.commit()
    await db.refresh(pricing)
    return pricing


@router.put("/global-pricing/{pricing_id}", response_model=ProviderPricingResponse)
async def update_global_pricing(pricing_id: uuid.UUID, body: ProviderPricingUpdate, db: DbDep) -> ProviderPricing:
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing profile not found")
    if pricing.workspace_id is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Use workspace API for workspace-scoped pricing")
    if body.input_cost_per_1m is not None:
        pricing.input_cost_per_1m = body.input_cost_per_1m
    if body.output_cost_per_1m is not None:
        pricing.output_cost_per_1m = body.output_cost_per_1m
    if body.cached_input_cost_per_1m is not None:
        pricing.cached_input_cost_per_1m = body.cached_input_cost_per_1m
    await db.commit()
    await db.refresh(pricing)
    return pricing


@router.delete("/global-pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_pricing(pricing_id: uuid.UUID, db: DbDep) -> None:
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing profile not found")
    if pricing.workspace_id is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Use workspace API for workspace-scoped pricing")
    await db.delete(pricing)
    await db.commit()
