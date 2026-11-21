"""Tenancy business rules: last-admin guard and audit logging."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.audit import AuditEvent
from runledger_api.models.tenant import MemberStatusEnum, TenantRoleEnum, TenantUser

# ── Last-admin guard ───────────────────────────────────────────────────────────


async def count_active_org_admins(tenant_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(TenantUser)
        .where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role == TenantRoleEnum.org_admin,
            TenantUser.status == MemberStatusEnum.active,
        )
    )
    return result.scalar() or 0


async def assert_not_last_admin(
    tenant_id: uuid.UUID, exclude_user_id: uuid.UUID, db: AsyncSession
) -> None:
    """Raise 400 if removing/demoting exclude_user_id would leave the org with no active org_admin."""
    result = await db.execute(
        select(func.count())
        .select_from(TenantUser)
        .where(
            TenantUser.tenant_id == tenant_id,
            TenantUser.role == TenantRoleEnum.org_admin,
            TenantUser.status == MemberStatusEnum.active,
            TenantUser.user_id != exclude_user_id,
        )
    )
    remaining = result.scalar() or 0
    if remaining == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove or demote the last active Org Admin. Assign another Org Admin first.",
        )


# ── Audit logging ──────────────────────────────────────────────────────────────


def log_audit(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    scope_type: str,
    scope_id: uuid.UUID,
    action: str,
    target_user_id: uuid.UUID | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    tenant_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> None:
    """Add an AuditEvent to the session (caller commits, in the same transaction).

    ``action`` is stored as given (e.g. ``org.member.role_changed``). ``scope_type``
    is ``tenant`` or ``workspace``; tenant-scoped events carry ``tenant_id`` so the
    org audit view can list them even though they have no workspace.
    """
    before = {"value": old_value} if old_value else None
    after = {"value": new_value} if new_value else None
    # workspace_id is an FK to workspaces; only a workspace-scoped event has a real
    # workspace id in scope_id.
    workspace_id = scope_id if scope_type == "workspace" else None
    if tenant_id is None and scope_type == "tenant":
        tenant_id = scope_id
    if target_user_id is not None and target_type is None:
        target_type, target_id = "user", str(target_user_id)
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=before,
            after=after,
        )
    )
