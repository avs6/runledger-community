"""
Settings router — workspace-scoped API key management + email preferences.

Prefix: /settings
Auth: Bearer API key via get_current_workspace
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings as app_settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_platform_admin,
    require_workspace_admin,
)
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.email_prefs import EmailLog, EmailPreference
from runledger_api.models.tenant import ApiKey, Tenant, Workspace, WorkspaceUser
from runledger_api.schemas.auth import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from runledger_api.schemas.email_prefs import (
    EmailLogList,
    EmailPreferenceResponse,
    EmailPreferenceUpdate,
)
from runledger_api.services.auth import generate_api_key
from runledger_api.services.email import send_email

log = structlog.get_logger()

router = APIRouter(
    prefix="/settings", tags=["settings"], dependencies=[Depends(management_rate_limit)]
)

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
# API-key management is an **org-admin** function performed by a logged-in user
# (a session), not by a bare API key — a key can no longer mint or revoke keys.
WorkspaceAdminDep = Annotated[
    tuple[Workspace, Any, WorkspaceUser | None], Depends(require_workspace_admin)
]
PlatformAdminDep = Annotated[tuple[Any, ...], Depends(require_platform_admin)]


async def _org_workspaces(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """All workspaces in an org, as {id: name} — the org's key-visibility boundary."""
    rows = (
        (await db.execute(select(Workspace).where(Workspace.tenant_id == tenant_id)))
        .scalars()
        .all()
    )
    return {w.id: w.name for w in rows}


async def _key_visible_workspaces(
    db: AsyncSession,
    workspace: Workspace,
    workspace_membership: WorkspaceUser | None,
) -> dict[uuid.UUID, str]:
    if workspace_membership is None:
        return await _org_workspaces(db, workspace.tenant_id)
    return {workspace.id: workspace.name}


@router.get("/ops/status")
async def get_ops_feature_status(auth: PlatformAdminDep) -> dict[str, bool]:
    """Expose platform-wide optional feature flags for the Settings UI."""
    _workspace = auth[0]
    smtp_configured = bool(app_settings.smtp_user and app_settings.smtp_password)
    return {
        "email_enabled": app_settings.email_enabled,
        "email_reports_enabled": app_settings.email_reports_enabled,
        "backup_enabled": app_settings.backup_enabled,
        "smtp_configured": smtp_configured,
    }


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(auth: WorkspaceAdminDep, db: DbDep) -> list[dict[str, Any]]:
    """List keys across ALL workspaces in the caller's org (org-admin only)."""
    workspace, _user, workspace_membership = auth
    ws = await _key_visible_workspaces(db, workspace, workspace_membership)
    result = await db.execute(
        select(ApiKey)
        .where(
            ApiKey.workspace_id.in_(list(ws.keys())),
            ApiKey.revoked_at.is_(None),
            ApiKey.is_session.is_(False),
        )
        .order_by(ApiKey.created_at.desc())
    )
    return [
        {
            "id": k.id,
            "workspace_id": k.workspace_id,
            "workspace_name": ws.get(k.workspace_id),
            "key_prefix": k.key_prefix,
            "name": k.name,
            "scopes": k.scopes,
            "created_at": k.created_at,
            "created_by": k.created_by,
            "is_session": k.is_session,
        }
        for k in result.scalars().all()
    ]


@router.post(
    "/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreateResponse,
)
async def create_api_key(body: ApiKeyCreate, auth: WorkspaceAdminDep, db: DbDep) -> dict[str, Any]:
    """Mint a key for a workspace in the caller's org (org-admin only)."""
    workspace, user, workspace_membership = auth
    ws = await _key_visible_workspaces(db, workspace, workspace_membership)
    target_id = body.workspace_id or workspace.id
    if target_id not in ws:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Workspace is outside your API key scope")
    raw_key, key_hash, key_prefix = generate_api_key(body.environment)
    api_key = ApiKey(
        workspace_id=target_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        scopes=body.scopes,
        created_by=user.email,
    )
    db.add(api_key)
    await db.flush()
    await db.commit()
    await db.refresh(api_key)
    log.info(
        "api_key_created",
        key_id=str(api_key.id),
        workspace_id=str(target_id),
        by=user.email,
    )
    return {
        "id": api_key.id,
        "workspace_id": api_key.workspace_id,
        "workspace_name": ws.get(target_id),
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "created_by": api_key.created_by,
        "key": raw_key,
    }


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: uuid.UUID, auth: WorkspaceAdminDep, db: DbDep) -> None:
    """Revoke a key belonging to the caller's org (org-admin only)."""
    workspace, _user, workspace_membership = auth
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    ws = await _key_visible_workspaces(db, workspace, workspace_membership)
    if api_key.workspace_id not in ws:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key is outside your API key scope")
    api_key.revoked_at = datetime.now(UTC)
    await db.commit()
    log.info("api_key_revoked", key_id=str(key_id))


# ── Email Preferences ─────────────────────────────────────────────────────────


@router.get("/email/preferences", response_model=EmailPreferenceResponse)
async def get_email_preferences(auth: PlatformAdminDep, db: DbDep) -> EmailPreference:
    """Get or create default email preferences for this workspace."""
    workspace = auth[0]
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.workspace_id == workspace.id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = EmailPreference(workspace_id=workspace.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.put("/email/preferences", response_model=EmailPreferenceResponse)
async def update_email_preferences(
    body: EmailPreferenceUpdate, auth: PlatformAdminDep, db: DbDep
) -> EmailPreference:
    workspace = auth[0]
    """Update email preferences (PATCH semantics — only provided fields are changed)."""
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.workspace_id == workspace.id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = EmailPreference(workspace_id=workspace.id)
        db.add(prefs)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)

    prefs.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(prefs)
    log.info("email_preferences_updated", workspace_id=str(workspace.id))
    return prefs


@router.get("/email/log", response_model=EmailLogList)
async def get_email_log(auth: PlatformAdminDep, db: DbDep) -> EmailLogList:
    workspace = auth[0]
    """List the 50 most recent email log entries for this workspace."""
    result = await db.execute(
        select(EmailLog)
        .where(EmailLog.workspace_id == workspace.id)
        .order_by(EmailLog.sent_at.desc())
        .limit(50)
    )
    items = list(result.scalars().all())

    count_result = await db.execute(select(EmailLog).where(EmailLog.workspace_id == workspace.id))
    total = len(list(count_result.scalars().all()))

    return EmailLogList(items=items, total=total)  # type: ignore[arg-type]


@router.post("/email/test")
async def test_email_send(
    auth: PlatformAdminDep,
    db: DbDep,
) -> dict[str, Any]:
    workspace = auth[0]
    """Send a test email to the workspace's API key owner (created_by field)."""
    if not app_settings.email_enabled:
        return {"ok": False, "error": "Email delivery is disabled (EMAIL_ENABLED=false)"}
    if not app_settings.smtp_user or not app_settings.smtp_password:
        return {"ok": False, "error": "SMTP credentials are not configured"}

    # Find a session key to get the user's email
    key_result = await db.execute(
        select(ApiKey)
        .where(
            ApiKey.workspace_id == workspace.id,
            ApiKey.revoked_at.is_(None),
            ApiKey.is_session.is_(True),
            ApiKey.created_by.isnot(None),
        )
        .order_by(ApiKey.created_at.desc())
        .limit(1)
    )
    session_key = key_result.scalar_one_or_none()

    # Fall back: try any key with a created_by email
    if session_key is None or not session_key.created_by:
        key_result2 = await db.execute(
            select(ApiKey)
            .where(
                ApiKey.workspace_id == workspace.id,
                ApiKey.revoked_at.is_(None),
                ApiKey.created_by.isnot(None),
            )
            .order_by(ApiKey.created_at.desc())
            .limit(1)
        )
        session_key = key_result2.scalar_one_or_none()

    if session_key is None or not session_key.created_by:
        return {"ok": False, "error": "No user email found for this workspace"}

    to_email = session_key.created_by
    try:
        await send_email(
            to_email=to_email,
            subject="RunLedger email test",
            html="<p>This is a test email from RunLedger. Your email notifications are working correctly.</p>",
            text="This is a test email from RunLedger. Your email notifications are working correctly.",
            event_type="test",
            workspace_id=workspace.id,
            background=False,
        )
        return {"ok": True, "error": None}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Onboarding ───────────────────────────────────────────────────────────────


@router.get("/onboarding-status")
async def onboarding_status(
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, Any]:
    """Return setup completion checklist for onboarding wizard."""
    from runledger_api.models.alerts import AlertRule  # noqa: PLC0415
    from runledger_api.models.budgets import Budget  # noqa: PLC0415
    from runledger_api.models.events import AgentRun  # noqa: PLC0415
    from runledger_api.models.gateway import GatewayRoute  # noqa: PLC0415

    has_org = (
        await db.execute(select(Tenant.id).where(Tenant.id == workspace.tenant_id).limit(1))
    ).scalar_one_or_none() is not None

    has_workspace = True  # they're authenticated with a workspace key

    has_api_key = (
        await db.execute(
            select(ApiKey.id)
            .where(ApiKey.workspace_id == workspace.id, ApiKey.revoked_at.is_(None))
            .limit(1)
        )
    ).scalar_one_or_none() is not None

    has_first_run = (
        await db.execute(select(AgentRun.id).where(AgentRun.workspace_id == workspace.id).limit(1))
    ).scalar_one_or_none() is not None

    has_gateway_route = (
        await db.execute(
            select(GatewayRoute.id)
            .where(GatewayRoute.workspace_id == workspace.id, GatewayRoute.is_active.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none() is not None

    has_budget = (
        await db.execute(select(Budget.id).where(Budget.workspace_id == workspace.id).limit(1))
    ).scalar_one_or_none() is not None

    has_alert_rule = (
        await db.execute(
            select(AlertRule.id).where(AlertRule.workspace_id == workspace.id).limit(1)
        )
    ).scalar_one_or_none() is not None

    steps = [
        has_org,
        has_workspace,
        has_api_key,
        has_first_run,
        has_gateway_route,
        has_budget,
        has_alert_rule,
    ]
    completed = sum(1 for s in steps if s)

    return {
        "has_org": has_org,
        "has_workspace": has_workspace,
        "has_api_key": has_api_key,
        "has_first_run": has_first_run,
        "has_gateway_route": has_gateway_route,
        "has_budget": has_budget,
        "has_alert_rule": has_alert_rule,
        "completed": completed,
        "total": len(steps),
        "pct": round(completed / len(steps) * 100),
    }


# ── Demo seed ────────────────────────────────────────────────────────────────


@router.post("/demo-seed")
async def trigger_demo_seed(
    auth: PlatformAdminDep,
) -> dict[str, str]:
    """Trigger the demo data seeder (platform admin only)."""
    import subprocess  # noqa: PLC0415, S404
    import sys  # noqa: PLC0415

    try:
        subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "scripts.seed_demo"],
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]),
        )
        return {"status": "started", "message": "Demo seed started in background"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
