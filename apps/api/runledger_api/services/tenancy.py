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
) -> None:
    """Add an AuditEvent to the session. Caller must commit."""
    before = {"value": old_value} if old_value else None
    after = {"value": new_value} if new_value else None
    db.add(
        AuditEvent(
            workspace_id=scope_id,
            actor_user_id=actor_user_id,
            action=f"{scope_type}.{action}",
            target_type=scope_type if target_user_id else None,
            target_id=str(target_user_id) if target_user_id else None,
            before=before,
            after=after,
        )
    )
