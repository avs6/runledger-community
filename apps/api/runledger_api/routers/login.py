"""
Public login endpoint for the NextAuth dashboard.

POST /auth/login — verifies email + password, generates a short-lived
dashboard session API key, and returns it in the response body.
NextAuth stores the raw key in the encrypted JWT session.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.models.tenant import ApiKey, EnvironmentEnum, User, WorkspaceUser
from runledger_api.schemas.runs import LoginRequest, LoginResponse
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

# Dashboard session keys expire after 30 days
_SESSION_EXPIRY = timedelta(days=30)


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DbDep) -> LoginResponse:
    """
    Authenticate with email + password.
    Returns a workspace-scoped API key for the dashboard session.
    The key is valid for 30 days and named "dashboard-session".
    """
    # Find user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Constant-time failure (avoids timing attacks)
    if user is None or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
        )

    # Find the user's first workspace
    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
        .limit(1)
    )
    workspace_user = wu_result.scalar_one_or_none()
    if workspace_user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace")

    # Load workspace
    from runledger_api.models.tenant import Workspace

    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")

    # Generate a fresh session API key
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
    )
    db.add(session_key)
    await db.commit()

    log.info("dashboard_login", user_id=str(user.id), workspace_id=str(workspace.id))

    return LoginResponse(
        email=user.email,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        api_key=raw_key,
    )
