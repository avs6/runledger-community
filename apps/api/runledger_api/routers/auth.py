from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_admin
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import ApiKey, Application, Tenant, Workspace
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
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Tenants ───────────────────────────────────────────────────────────────────


@router.post("/tenants", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(body: TenantCreate, db: DbDep) -> Tenant:
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Slug '{body.slug}' already taken")
    tenant = Tenant(slug=body.slug, name=body.name, plan=body.plan)
    db.add(tenant)
    await db.flush()
    await db.commit()
    await db.refresh(tenant)
    log.info("tenant_created", tenant_id=str(tenant.id), slug=tenant.slug)
    return tenant


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(db: DbDep) -> list[Tenant]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


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
    log.info("workspace_created", workspace_id=str(workspace.id), tenant_id=str(body.tenant_id))
    return workspace


@router.get("/tenants/{tenant_id}/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(tenant_id: uuid.UUID, db: DbDep) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.tenant_id == tenant_id).order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


# ── Applications ──────────────────────────────────────────────────────────────


@router.post(
    "/applications", status_code=status.HTTP_201_CREATED, response_model=ApplicationResponse
)
async def create_application(body: ApplicationCreate, db: DbDep) -> Application:
    workspace = await db.get(Workspace, body.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    application = Application(
        workspace_id=body.workspace_id, name=body.name, environment=body.environment
    )
    db.add(application)
    await db.flush()
    await db.commit()
    await db.refresh(application)
    return application


# ── API Keys ──────────────────────────────────────────────────────────────────


@router.post(
    "/workspaces/{workspace_id}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreateResponse,
)
async def create_api_key(workspace_id: uuid.UUID, body: ApiKeyCreate, db: DbDep) -> dict[str, Any]:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    raw_key, key_hash, key_prefix = generate_api_key(body.environment)
    api_key = ApiKey(
        workspace_id=workspace_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        scopes=body.scopes,
    )
    db.add(api_key)
    await db.flush()
    await db.commit()
    await db.refresh(api_key)
    log.info("api_key_created", key_id=str(api_key.id), workspace_id=str(workspace_id))
    return {
        "id": api_key.id,
        "workspace_id": api_key.workspace_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "key": raw_key,
    }


@router.get("/workspaces/{workspace_id}/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(workspace_id: uuid.UUID, db: DbDep) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.workspace_id == workspace_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: uuid.UUID, db: DbDep) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    api_key.revoked_at = datetime.now(UTC)
    await db.commit()
    log.info("api_key_revoked", key_id=str(key_id))


# ── Global Pricing (admin-only) ────────────────────────────────────────────────


@router.post(
    "/global-pricing", status_code=status.HTTP_201_CREATED, response_model=ProviderPricingResponse
)
async def create_global_pricing(body: ProviderPricingCreate, db: DbDep) -> ProviderPricing:
    pricing = ProviderPricing(
        workspace_id=None,
        provider=body.provider,
        model=body.model,
        input_cost_per_1m=body.input_cost_per_1m,
        output_cost_per_1m=body.output_cost_per_1m,
        cached_input_cost_per_1m=body.cached_input_cost_per_1m,
        effective_from=body.effective_from or datetime.now(UTC),
    )
    db.add(pricing)
    await db.flush()
    await db.commit()
    await db.refresh(pricing)
    log.info("global_pricing_created", pricing_id=str(pricing.id), provider=pricing.provider)
    return pricing


@router.put("/global-pricing/{pricing_id}", response_model=ProviderPricingResponse)
async def update_global_pricing(
    pricing_id: uuid.UUID, body: ProviderPricingUpdate, db: DbDep
) -> ProviderPricing:
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing profile not found")
    if pricing.workspace_id is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Use workspace API for workspace-scoped pricing"
        )
    if body.input_cost_per_1m is not None:
        pricing.input_cost_per_1m = body.input_cost_per_1m
    if body.output_cost_per_1m is not None:
        pricing.output_cost_per_1m = body.output_cost_per_1m
    if body.cached_input_cost_per_1m is not None:
        pricing.cached_input_cost_per_1m = body.cached_input_cost_per_1m
    await db.commit()
    await db.refresh(pricing)
    log.info("global_pricing_updated", pricing_id=str(pricing_id))
    return pricing


@router.delete("/global-pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_pricing(pricing_id: uuid.UUID, db: DbDep) -> None:
    pricing = await db.get(ProviderPricing, pricing_id)
    if pricing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pricing profile not found")
    if pricing.workspace_id is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Use workspace API for workspace-scoped pricing"
        )
    await db.delete(pricing)
    await db.commit()
    log.info("global_pricing_deleted", pricing_id=str(pricing_id))
