"""Shared email utilities — recipient lookup helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.tenant import User, WorkspaceRoleEnum, WorkspaceUser

# Roles that should receive admin-level email notifications
_ADMIN_ROLES = {WorkspaceRoleEnum.workspace_admin, WorkspaceRoleEnum.workspace_editor}


async def get_workspace_admin_users(db: AsyncSession, workspace_id: uuid.UUID) -> list[User]:
    """Return active workspace admin/editor users for a given workspace."""
    result = await db.execute(
        select(User)
        .join(WorkspaceUser, WorkspaceUser.user_id == User.id)
        .where(
            WorkspaceUser.workspace_id == workspace_id,
            WorkspaceUser.role.in_(_ADMIN_ROLES),
            User.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
