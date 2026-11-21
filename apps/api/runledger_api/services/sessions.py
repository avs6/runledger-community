"""Dashboard sessions and workspace access resolution.

A dashboard session is an ``ApiKey`` row with ``is_session=True`` and
``user_id`` set to its owner. Access is re-derived from current memberships on
every request (see ``core.deps.get_current_workspace``), so suspending a member,
removing them, or deactivating the account takes effect immediately. Session
keys are also revoked eagerly on those events and on sign-out.

Workspace access rules (single source of truth for login, switch and per-request
validation):

* platform admins may enter any workspace;
* an **active** ``WorkspaceUser`` row grants access to that workspace;
* an **active** ``TenantUser`` with an org-level role (org_admin, org_manager,
  org_billing_admin, org_auditor) grants access to every workspace of that org.

Suspended or invited memberships grant nothing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.tenant import (
    ApiKey,
    EnvironmentEnum,
    MemberStatusEnum,
    TenantRoleEnum,
    TenantStatusEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceStatusEnum,
    WorkspaceUser,
)
from runledger_api.services.auth import generate_api_key

ORG_ADMIN_ROLES = frozenset({TenantRoleEnum.org_admin, TenantRoleEnum.org_manager})
# Org roles that see every workspace in the org (read access for billing/auditor).
ORG_LEVEL_ROLES = frozenset(
    {
        TenantRoleEnum.org_admin,
        TenantRoleEnum.org_manager,
        TenantRoleEnum.org_billing_admin,
        TenantRoleEnum.org_auditor,
    }
)


@dataclass
class WorkspaceAccess:
    workspace: Workspace
    tenant_user: TenantUser | None
    workspace_user: WorkspaceUser | None


async def active_tenant_user(
    db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> TenantUser | None:
    return (
        await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user_id,
                TenantUser.tenant_id == tenant_id,
                TenantUser.status == MemberStatusEnum.active,
            )
        )
    ).scalar_one_or_none()


async def active_workspace_user(
    db: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> WorkspaceUser | None:
    return (
        await db.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.user_id == user_id,
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.status == MemberStatusEnum.active,
            )
        )
    ).scalar_one_or_none()


async def has_workspace_access(db: AsyncSession, user: User, workspace: Workspace) -> bool:
    """True when ``user`` may currently act inside ``workspace``."""
    if user.is_platform_admin:
        return True
    tu = (
        await db.execute(
            select(TenantUser).where(
                TenantUser.user_id == user.id, TenantUser.tenant_id == workspace.tenant_id
            )
        )
    ).scalar_one_or_none()
    # A suspended org membership blocks every workspace in that org.
    if tu is not None and tu.status == MemberStatusEnum.suspended:
        return False
    if tu is not None and tu.status == MemberStatusEnum.active and tu.role in ORG_LEVEL_ROLES:
        return True
    return await active_workspace_user(db, user.id, workspace.id) is not None


async def accessible_workspaces(db: AsyncSession, user: User) -> list[Workspace]:
    """Every workspace the user may enter, oldest membership first (no suspended orgs).

    Platform admins get their own memberships here; they reach other orgs' workspaces
    through switch-workspace.
    """
    tenant_rows = list(
        (await db.execute(select(TenantUser).where(TenantUser.user_id == user.id))).scalars().all()
    )
    suspended_tenants = {
        tu.tenant_id for tu in tenant_rows if tu.status == MemberStatusEnum.suspended
    }
    org_level_tenants = {
        tu.tenant_id
        for tu in tenant_rows
        if tu.status == MemberStatusEnum.active and tu.role in ORG_LEVEL_ROLES
    }

    ordered: list[Workspace] = []
    seen: set[uuid.UUID] = set()
    ws_rows = (
        await db.execute(
            select(Workspace)
            .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
            .where(
                WorkspaceUser.user_id == user.id,
                WorkspaceUser.status == MemberStatusEnum.active,
            )
            .order_by(WorkspaceUser.created_at)
        )
    ).scalars()
    for ws in ws_rows:
        if ws.tenant_id in suspended_tenants or ws.id in seen:
            continue
        ordered.append(ws)
        seen.add(ws.id)
    if org_level_tenants:
        org_ws = (
            await db.execute(
                select(Workspace)
                .where(Workspace.tenant_id.in_(list(org_level_tenants)))
                .order_by(Workspace.created_at)
            )
        ).scalars()
        for ws in org_ws:
            if ws.id not in seen:
                ordered.append(ws)
                seen.add(ws.id)
    return [ws for ws in ordered if ws.status == WorkspaceStatusEnum.active]


async def tenant_is_active(db: AsyncSession, workspace: Workspace) -> bool:
    from runledger_api.models.tenant import Tenant  # noqa: PLC0415

    tenant = await db.get(Tenant, workspace.tenant_id)
    return tenant is not None and tenant.status == TenantStatusEnum.active


async def create_session_key(
    db: AsyncSession, *, user: User, workspace: Workspace, name: str = "dashboard-session"
) -> tuple[str, ApiKey]:
    """Mint a session key for ``user`` in ``workspace``. Caller commits."""
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        scopes=[],
        expires_at=datetime.now(UTC) + timedelta(days=settings.session_ttl_days),
        is_session=True,
        created_by=user.email,
        user_id=user.id,
    )
    db.add(key)
    await db.flush()
    return raw_key, key


async def revoke_user_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    workspace_ids: list[uuid.UUID] | None = None,
    except_key_id: uuid.UUID | None = None,
) -> int:
    """Revoke a user's live session keys (optionally limited to some workspaces).

    Matches on ``user_id`` and, for keys minted before owners were tracked, on the
    creator email. Caller commits. Returns the number of keys revoked.
    """
    user = await db.get(User, user_id)
    owner_match = ApiKey.user_id == user_id
    if user is not None:
        owner_match = or_(ApiKey.user_id == user_id, ApiKey.created_by == user.email)
    stmt = (
        update(ApiKey)
        .where(
            ApiKey.is_session.is_(True),
            ApiKey.revoked_at.is_(None),
            owner_match,
        )
        .values(revoked_at=datetime.now(UTC))
    )
    if workspace_ids is not None:
        if not workspace_ids:
            return 0
        stmt = stmt.where(ApiKey.workspace_id.in_(workspace_ids))
    if except_key_id is not None:
        stmt = stmt.where(ApiKey.id != except_key_id)
    result = await db.execute(stmt.execution_options(synchronize_session=False))
    return int(result.rowcount or 0)


async def tenant_workspace_ids(db: AsyncSession, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        (await db.execute(select(Workspace.id).where(Workspace.tenant_id == tenant_id)))
        .scalars()
        .all()
    )


async def is_tenant_managed_user(db: AsyncSession, user: User, tenant_id: uuid.UUID) -> bool:
    """True when the org identified by ``tenant_id`` may manage this identity.

    An org may edit global identity fields (password, active, verified) or link an
    external login to an existing account only for users that belong to that org
    alone: not platform admins, with an active (accepted) membership there, and no
    membership in any other org or in workspaces of another org.
    """
    if user.is_platform_admin:
        return False
    tenant_rows = list(
        (await db.execute(select(TenantUser).where(TenantUser.user_id == user.id))).scalars().all()
    )
    home = [tu for tu in tenant_rows if tu.tenant_id == tenant_id]
    if not home or home[0].status != MemberStatusEnum.active:
        return False
    if any(tu.tenant_id != tenant_id for tu in tenant_rows):
        return False
    foreign_ws = (
        await db.execute(
            select(Workspace.id)
            .join(WorkspaceUser, WorkspaceUser.workspace_id == Workspace.id)
            .where(WorkspaceUser.user_id == user.id, Workspace.tenant_id != tenant_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return foreign_ws is None


def can_assign_tenant_role(
    *,
    actor_is_platform_admin: bool,
    actor_role: TenantRoleEnum | None,
    target_current_role: TenantRoleEnum | None,
    new_role: TenantRoleEnum | None,
) -> bool:
    """Role hierarchy: only org admins (or platform admins) grant, revoke or modify
    org_admin; org managers manage every role below org_admin."""
    if actor_is_platform_admin or actor_role == TenantRoleEnum.org_admin:
        return True
    if actor_role != TenantRoleEnum.org_manager:
        return False
    if target_current_role == TenantRoleEnum.org_admin:
        return False
    return new_role != TenantRoleEnum.org_admin


async def resolve_principal_user_id(
    db: AsyncSession,
    *,
    api_key: ApiKey | None,
    end_user_id: str | None,
    workspace: Workspace,
) -> uuid.UUID | None:
    """Best-effort mapping of a gateway request to a RunLedger user.

    Used to apply access-group policy (guardrail profiles) in the gateway. Order:
    the session key's owner; a user-owned key's creator; an ``end_user_id`` that is
    a workspace member's user id or email.
    """
    if api_key is not None:
        if api_key.user_id is not None:
            return api_key.user_id
        if api_key.ownership_type == "user" and api_key.created_by:
            owner = (
                await db.execute(select(User.id).where(User.email == api_key.created_by))
            ).scalar_one_or_none()
            if owner is not None:
                return owner
    if end_user_id:
        candidate: User | None = None
        try:
            candidate = await db.get(User, uuid.UUID(end_user_id))
        except ValueError:
            candidate = (
                await db.execute(select(User).where(User.email == end_user_id))
            ).scalar_one_or_none()
        if candidate is not None and await has_workspace_access(db, candidate, workspace):
            return candidate.id
    return None
