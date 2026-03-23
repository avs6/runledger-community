"""
Public login endpoints for the NextAuth dashboard.

POST /auth/login          — email + password
POST /auth/firebase-login — Firebase ID token (social login)
POST /auth/switch-workspace

POST /auth/login — verifies email + password, generates a short-lived
dashboard session API key, and returns it in the response body.
NextAuth stores the raw key in the encrypted JWT session.
"""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import require_user
from runledger_api.models.tenant import (
    ApiKey,
    EnvironmentEnum,
    PlanEnum,
    Tenant,
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
    WorkspaceUser,
)
from runledger_api.schemas.runs import LoginRequest, LoginResponse
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_SESSION_EXPIRY = timedelta(days=30)


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DbDep) -> LoginResponse:
    """
    Authenticate with email + password.
    Returns a workspace-scoped API key for the dashboard session.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please verify your email before signing in")

    # Load all workspace memberships
    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())

    if not workspace_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    # Pick requested workspace or default to first
    workspace_user = workspace_users[0]
    if body.workspace_id:
        for wu in workspace_users:
            if str(wu.workspace_id) == body.workspace_id:
                workspace_user = wu
                break

    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")

    # Load tenant role
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value

    # All workspaces this user can access
    workspace_ids = [str(wu.workspace_id) for wu in workspace_users]

    # Update last login
    user.last_login_at = datetime.now(UTC)

    # Generate session key
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

    log.info(
        "dashboard_login",
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        tenant_id=str(workspace.tenant_id),
        is_platform_admin=user.is_platform_admin,
    )

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        tenant_id=str(workspace.tenant_id),
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: str


@router.post("/auth/switch-workspace", response_model=LoginResponse)
async def switch_workspace(
    body: SwitchWorkspaceRequest,
    auth: Annotated[tuple, Depends(require_user)],
    db: DbDep,
) -> LoginResponse:
    """
    Switch to a different workspace without re-entering credentials.
    Validates the user has access, issues a new session API key, returns full session data.
    """
    _, user = auth
    target_ws_id = uuid.UUID(body.workspace_id)

    # Verify user has access to the target workspace
    wu_result = await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == target_ws_id,
            WorkspaceUser.user_id == user.id,
        )
    )
    workspace_user = wu_result.scalar_one_or_none()
    if workspace_user is None and not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this workspace")

    target_workspace = await db.get(Workspace, target_ws_id)
    if target_workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    # Load tenant role
    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == target_workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value if workspace_user else None

    # All workspaces this user can access
    wu_all = await db.execute(
        select(WorkspaceUser).where(WorkspaceUser.user_id == user.id).order_by(WorkspaceUser.created_at)
    )
    workspace_ids = [str(wu.workspace_id) for wu in wu_all.scalars().all()]

    # Generate new session key for target workspace
    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    session_key = ApiKey(
        workspace_id=target_workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    )
    db.add(session_key)
    await db.commit()

    log.info("workspace_switch", user_id=str(user.id), workspace_id=str(target_workspace.id))

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(target_workspace.id),
        workspace_name=target_workspace.name,
        tenant_id=str(target_workspace.tenant_id),
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )


# ── Firebase social login ─────────────────────────────────────────────────────

_firebase_app: object = None


def _get_firebase_app() -> object:
    """Lazy-initialize the Firebase Admin SDK app."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if not settings.firebase_project_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Firebase not configured")

    import firebase_admin  # noqa: PLC0415
    from firebase_admin import credentials  # noqa: PLC0415

    try:
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": settings.firebase_private_key.replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        _firebase_app = firebase_admin.initialize_app(cred)

    return _firebase_app


class FirebaseLoginRequest(BaseModel):
    id_token: str


def _make_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{secrets.token_hex(3)}"


@router.post("/auth/firebase-login", response_model=LoginResponse)
async def firebase_login(body: FirebaseLoginRequest, db: DbDep) -> LoginResponse:
    """
    Verify a Firebase ID token and return a RunLedger session.
    Creates a new user + tenant + workspace on first sign-in.
    """
    _get_firebase_app()

    try:
        from firebase_admin import auth as fb_auth  # noqa: PLC0415
        decoded = fb_auth.verify_id_token(body.id_token)
    except Exception as exc:
        log.warning("firebase_token_invalid", error=str(exc))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Firebase token") from exc

    uid: str = decoded["uid"]
    email: str = decoded.get("email", "")
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Firebase account has no email")

    full_name: str = decoded.get("name") or email.split("@")[0]

    # Look up existing user by firebase_uid first, then by email
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        # ── New user: provision full account ─────────────────────────────────
        user = User(
            email=email,
            password_hash=None,
            full_name=full_name,
            firebase_uid=uid,
            is_active=True,
            is_platform_admin=False,
            email_verified=True,  # Firebase already verified the email
        )
        db.add(user)
        await db.flush()

        org_name = full_name or email.split("@")[0]
        slug = _make_slug(org_name)
        tenant = Tenant(slug=slug, name=f"{org_name}'s Org", plan=PlanEnum.free, is_default=False)
        db.add(tenant)
        await db.flush()
        tenant.owner_user_id = user.id

        db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin))

        workspace = Workspace(tenant_id=tenant.id, name=f"{org_name} Workspace")
        db.add(workspace)
        await db.flush()

        db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin))

        # Free-tier subscription + quota rows (mirror signup flow)
        from runledger_api.models.saas import PLAN_QUOTAS, Subscription, UsageQuota  # noqa: PLC0415
        db.add(Subscription(
            tenant_id=tenant.id,
            plan="free",
            status="active",
            current_period_start=datetime.now(UTC),
        ))
        db.add(UsageQuota(
            tenant_id=tenant.id,
            events_limit=PLAN_QUOTAS["free"],
            events_used=0,
            period_start=datetime.now(UTC),
        ))
        await db.flush()
        log.info("firebase_signup", email=email, uid=uid, tenant_id=str(tenant.id))
    else:
        # ── Existing user: update firebase_uid if needed ──────────────────────
        if user.firebase_uid is None:
            user.firebase_uid = uid
        if not user.email_verified:
            user.email_verified = True
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

    # Load workspace memberships for response
    wu_result = await db.execute(
        select(WorkspaceUser)
        .where(WorkspaceUser.user_id == user.id)
        .order_by(WorkspaceUser.created_at)
    )
    workspace_users = list(wu_result.scalars().all())
    if not workspace_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User has no workspace access")

    workspace_user = workspace_users[0]
    workspace = await db.get(Workspace, workspace_user.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace not found")

    tu_result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == workspace.tenant_id,
        )
    )
    tenant_user = tu_result.scalar_one_or_none()
    tenant_role = tenant_user.role.value if tenant_user else None
    workspace_role = workspace_user.role.value
    workspace_ids = [str(wu.workspace_id) for wu in workspace_users]

    user.last_login_at = datetime.now(UTC)

    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    db.add(ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dashboard-session",
        scopes=[],
        expires_at=datetime.now(UTC) + _SESSION_EXPIRY,
        is_session=True,
        created_by=user.email,
    ))
    await db.commit()

    log.info("firebase_login", user_id=str(user.id), workspace_id=str(workspace.id))

    return LoginResponse(
        email=user.email,
        full_name=user.full_name,
        user_id=str(user.id),
        workspace_id=str(workspace.id),
        workspace_name=workspace.name,
        tenant_id=str(workspace.tenant_id),
        api_key=raw_key,
        is_platform_admin=user.is_platform_admin,
        tenant_role=tenant_role,
        workspace_role=workspace_role,
        workspace_ids=workspace_ids,
    )
