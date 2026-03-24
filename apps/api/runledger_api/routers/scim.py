"""
SCIM 2.0 provisioning endpoints — used by IdPs (Okta, Azure AD, etc.)
to automatically sync users.

Auth: Bearer <scim_token>  (validated via SHA256 hash in scim_tokens table)

  GET    /scim/v2/Users                   — list users
  POST   /scim/v2/Users                   — provision new user
  GET    /scim/v2/Users/{id}              — get user
  PUT    /scim/v2/Users/{id}              — replace user
  PATCH  /scim/v2/Users/{id}             — partial update (activate/deactivate)
  DELETE /scim/v2/Users/{id}             — deprovision user
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.models.sso import ScimToken
from runledger_api.models.tenant import (
    Tenant,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceUser,
)
from runledger_api.schemas.sso import (
    ScimEmail,
    ScimListResponse,
    ScimName,
    ScimPatchRequest,
    ScimUserRequest,
    ScimUserResponse,
)

log = structlog.get_logger()
router = APIRouter(tags=["scim"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


# ── SCIM Bearer auth ──────────────────────────────────────────────────────────


async def _get_scim_tenant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbDep,
) -> tuple[ScimToken, Tenant]:
    """Validate SCIM Bearer token → return (ScimToken, Tenant)."""
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "SCIM Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    result = await db.execute(
        select(ScimToken).where(
            ScimToken.token_hash == token_hash,
            ScimToken.enabled == True,  # noqa: E712
        )
    )
    scim_token = result.scalar_one_or_none()
    if scim_token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or revoked SCIM token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at
    scim_token.last_used_at = datetime.now(UTC)
    await db.flush()

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == scim_token.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant not found")

    return scim_token, tenant


ScimAuthDep = Annotated[tuple[ScimToken, Tenant], Depends(_get_scim_tenant)]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _user_to_scim(user: User, request_base: str = "/scim/v2") -> ScimUserResponse:
    name_parts = (user.full_name or "").split(" ", 1)
    return ScimUserResponse(
        id=str(user.id),
        userName=user.email,
        name=ScimName(
            formatted=user.full_name,
            givenName=name_parts[0] if name_parts else "",
            familyName=name_parts[1] if len(name_parts) > 1 else "",
        ),
        emails=[ScimEmail(value=user.email, type="work", primary=True)],
        active=user.is_active,
        meta={
            "resourceType": "User",
            "location": f"{request_base}/Users/{user.id}",
        },
    )


async def _get_user_in_tenant(db: AsyncSession, user_id: uuid.UUID, tenant: Tenant) -> User | None:
    """Return user only if they belong to the tenant."""
    result = await db.execute(
        select(User)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(User.id == user_id, TenantUser.tenant_id == tenant.id)
    )
    return result.scalar_one_or_none()


async def _get_primary_workspace(db: AsyncSession, tenant_id: uuid.UUID) -> Workspace | None:
    result = await db.execute(
        select(Workspace)
        .where(Workspace.tenant_id == tenant_id)
        .order_by(Workspace.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/scim/v2/Users", response_model=ScimListResponse)
async def scim_list_users(
    auth: ScimAuthDep,
    db: DbDep,
    startIndex: int = Query(default=1, ge=1),
    count: int = Query(default=100, ge=1, le=200),
    filter: str | None = Query(default=None),
) -> ScimListResponse:
    _, tenant = auth
    stmt = (
        select(User)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == tenant.id)
        .order_by(User.email)
    )

    # Basic filter support: filter=userName eq "email@example.com"
    if filter and "userName eq" in filter.lower():
        try:
            email_val = filter.split('"')[1]
            stmt = stmt.where(User.email == email_val)
        except IndexError:
            pass

    result = await db.execute(stmt)
    all_users = list(result.scalars().all())
    total = len(all_users)

    page = all_users[startIndex - 1 : startIndex - 1 + count]
    return ScimListResponse(
        totalResults=total,
        startIndex=startIndex,
        itemsPerPage=len(page),
        Resources=[_user_to_scim(u) for u in page],
    )


@router.post("/scim/v2/Users", response_model=ScimUserResponse, status_code=201)
async def scim_create_user(body: ScimUserRequest, auth: ScimAuthDep, db: DbDep) -> ScimUserResponse:
    _, tenant = auth
    email = body.userName.lower()

    # Check if user already exists in this tenant
    existing = await db.execute(select(User).where(User.email == email))
    user = existing.scalar_one_or_none()

    if user is None:
        full_name = ""
        if body.name:
            parts = [p for p in [body.name.givenName, body.name.familyName] if p]
            full_name = " ".join(parts) or body.name.formatted or email.split("@")[0]

        user = User(
            email=email,
            password_hash=None,
            full_name=full_name,
            is_active=body.active,
            is_platform_admin=False,
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_member))

        workspace = await _get_primary_workspace(db, tenant.id)
        if workspace:
            db.add(
                WorkspaceUser(
                    workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.member
                )
            )
    else:
        # Ensure membership in this tenant
        tu_result = await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id
            )
        )
        if tu_result.scalar_one_or_none() is None:
            db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_member))

    await db.commit()
    await db.refresh(user)
    log.info("scim_user_provisioned", email=email, tenant_id=str(tenant.id))
    return _user_to_scim(user)


@router.get("/scim/v2/Users/{user_id}", response_model=ScimUserResponse)
async def scim_get_user(user_id: uuid.UUID, auth: ScimAuthDep, db: DbDep) -> ScimUserResponse:
    _, tenant = auth
    user = await _get_user_in_tenant(db, user_id, tenant)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _user_to_scim(user)


@router.put("/scim/v2/Users/{user_id}", response_model=ScimUserResponse)
async def scim_replace_user(
    user_id: uuid.UUID, body: ScimUserRequest, auth: ScimAuthDep, db: DbDep
) -> ScimUserResponse:
    _, tenant = auth
    user = await _get_user_in_tenant(db, user_id, tenant)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if body.name:
        parts = [p for p in [body.name.givenName, body.name.familyName] if p]
        user.full_name = " ".join(parts) or body.name.formatted or user.full_name
    user.is_active = body.active

    await db.commit()
    await db.refresh(user)
    return _user_to_scim(user)


@router.patch("/scim/v2/Users/{user_id}", response_model=ScimUserResponse)
async def scim_patch_user(
    user_id: uuid.UUID, body: ScimPatchRequest, auth: ScimAuthDep, db: DbDep
) -> ScimUserResponse:
    _, tenant = auth
    user = await _get_user_in_tenant(db, user_id, tenant)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    for op in body.Operations:
        if op.op.lower() == "replace" and op.value:
            if "active" in op.value:
                user.is_active = bool(op.value["active"])
            if "displayName" in op.value:
                user.full_name = str(op.value["displayName"])

    await db.commit()
    await db.refresh(user)
    log.info("scim_user_patched", user_id=str(user_id), is_active=user.is_active)
    return _user_to_scim(user)


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
async def scim_delete_user(user_id: uuid.UUID, auth: ScimAuthDep, db: DbDep) -> None:
    """Deprovision user: deactivate (soft delete) and remove from tenant."""
    _, tenant = auth
    user = await _get_user_in_tenant(db, user_id, tenant)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.is_active = False

    # Remove tenant membership
    tu_result = await db.execute(
        select(TenantUser).where(TenantUser.user_id == user_id, TenantUser.tenant_id == tenant.id)
    )
    tu = tu_result.scalar_one_or_none()
    if tu:
        await db.delete(tu)

    await db.commit()
    log.info("scim_user_deprovisioned", user_id=str(user_id), tenant_id=str(tenant.id))
