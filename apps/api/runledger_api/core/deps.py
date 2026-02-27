from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.models.tenant import Workspace
from runledger_api.services.auth import verify_api_key

_bearer = HTTPBearer()


async def get_current_workspace(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Workspace:
    """Validates Bearer API key and returns the associated Workspace."""
    api_key = await verify_api_key(credentials.credentials, db)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return workspace


async def require_admin(x_admin_secret: Annotated[str, Header()]) -> None:
    """Validates X-Admin-Secret header for admin-only endpoints."""
    if x_admin_secret != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )
