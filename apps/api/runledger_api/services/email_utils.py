"""Shared email utilities — recipient lookup helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tenant import User, WorkspaceRoleEnum, WorkspaceUser

# Roles that should receive admin-level email notifications
_ADMIN_ROLES = {WorkspaceRoleEnum.workspace_admin, WorkspaceRoleEnum.workspace_editor}


async def get_workspace_admin_users(db: AsyncSession, workspace_id: uuid.UUID) -> list[User]:
    """Return active workspace admin/editor users for a given workspace who have not unsubscribed."""
    result = await db.execute(
        select(User)
        .join(WorkspaceUser, WorkspaceUser.user_id == User.id)
        .where(
            WorkspaceUser.workspace_id == workspace_id,
            WorkspaceUser.role.in_(_ADMIN_ROLES),
            User.is_active.is_(True),
            User.email_notifications_enabled.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_email_preference(
    db: AsyncSession, workspace_id: uuid.UUID
) -> "EmailPreference | None":  # noqa: F821
    """Return workspace email preferences, or None if not yet configured."""
    from runledger_api.models.email_prefs import EmailPreference

    result = await db.execute(
        select(EmailPreference).where(EmailPreference.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()
