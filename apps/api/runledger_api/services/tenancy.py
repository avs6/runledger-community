"""Tenancy business rules: last-admin guard and audit logging."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tenant import AuditEvent, MemberStatusEnum, TenantRoleEnum, TenantUser


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
    db.add(AuditEvent(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        scope_type=scope_type,
        scope_id=scope_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    ))
