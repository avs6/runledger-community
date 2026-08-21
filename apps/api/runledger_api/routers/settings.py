"""
Settings router — workspace-scoped API key management + email preferences.

Prefix: /settings
Auth: Bearer API key via get_current_workspace
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings as app_settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_org_admin,
    require_platform_admin,
    require_workspace_admin,
)
from runledger_api.core.redis import get_redis
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.email_prefs import EmailLog, EmailPreference
from runledger_api.models.ledger import CapturePolicyScope
from runledger_api.models.platform_settings import PlatformWebhookSettings
from runledger_api.models.tenant import ApiKey, Tenant, Workspace, WorkspaceUser
from runledger_api.schemas.auth import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse, ApiKeyUpdate
from runledger_api.schemas.backup_ops import (
    BackupActionResult,
    BackupRunList,
    BackupRunResponse,
    BackupSnapshotList,
    BackupSnapshotResponse,
    BackupTargetConfigResponse,
    BackupTargetConfigUpdate,
)
from runledger_api.schemas.email_prefs import (
    EmailLogList,
    EmailPreferenceResponse,
    EmailPreferenceUpdate,
)
from runledger_api.schemas.platform_settings import (
    PlatformWebhookSettingsResponse,
    PlatformWebhookSettingsTestResult,
    PlatformWebhookSettingsTestStatus,
    PlatformWebhookSettingsUpdate,
)
from runledger_api.schemas.privacy import (
    CapturePolicyScopeList,
    CapturePolicyScopeResponse,
    CapturePolicyScopeUpsert,
    PiiDetectionResponse,
    PiiTestRequest,
    PiiTestResultResponse,
    RetentionPreviewResponse,
)
from runledger_api.services import backup_ops
from runledger_api.services.auth import generate_api_key
from runledger_api.services.demo_mode import launch_demo_process, read_demo_state
from runledger_api.services.email import send_email
from runledger_api.services.email_utils import get_workspace_admin_users
from runledger_api.services.ops import get_queue_depths
from runledger_api.services.ops_policy import evaluate_infra_posture
from runledger_api.services.gateway_redact import redact_text
from runledger_api.services.notifications import build_test_blocks, send_slack_message
import httpx

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = object  # type: ignore[misc,assignment]

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
OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]
PlatformAdminDep = Annotated[tuple[Any, ...], Depends(require_platform_admin)]


async def _get_or_create_platform_webhook_settings(
    db: AsyncSession,
) -> PlatformWebhookSettings:
    settings_row = await db.get(PlatformWebhookSettings, 1)
    if settings_row is None:
        settings_row = PlatformWebhookSettings(
            id=1,
            generic_webhook_url=app_settings.platform_webhook_url or None,
            slack_webhook_url=app_settings.platform_slack_webhook_url or None,
            events=[
                item.strip()
                for item in app_settings.platform_webhook_events.split(",")
                if item.strip()
            ],
        )
        db.add(settings_row)
        await db.commit()
        await db.refresh(settings_row)
    return settings_row


def _platform_webhook_settings_response(
    settings_row: PlatformWebhookSettings,
) -> PlatformWebhookSettingsResponse:
    return PlatformWebhookSettingsResponse(
        generic_webhook_configured=bool(settings_row.generic_webhook_url),
        slack_webhook_configured=bool(settings_row.slack_webhook_url),
        events=list(settings_row.events or []),
        generic_webhook_url=settings_row.generic_webhook_url,
        slack_webhook_url=settings_row.slack_webhook_url,
        created_at=settings_row.created_at,
        updated_at=settings_row.updated_at,
    )

_PII_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("email", "high", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    (
        "phone",
        "medium",
        re.compile(
            r"(?<!\d)(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)"
        ),
    ),
    ("ssn", "high", re.compile(r"\b\d{3}[\-\s]\d{2}[\-\s]\d{4}\b")),
    (
        "credit_card",
        "medium",
        re.compile(
            r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{0,4}\b"
        ),
    ),
]


def _capture_policy_scope_to_response(scope: CapturePolicyScope) -> CapturePolicyScopeResponse:
    return CapturePolicyScopeResponse(
        scope_type=scope.scope_type,
        scope_id=scope.scope_id,
        privacy_mode=scope.privacy_mode,
        sampled_rate=scope.sampled_rate,
    )


def _retention_preview(privacy_mode: str) -> RetentionPreviewResponse:
    normalized = privacy_mode.upper()
    previews: dict[str, RetentionPreviewResponse] = {
        "METADATA_ONLY": RetentionPreviewResponse(
            privacy_mode=normalized,
            estimated_storage_mb_per_month="25",
            fields_captured=["timings", "token counts", "status", "provider and model metadata"],
            fields_redacted=["prompt bodies", "response bodies", "tool payloads", "span metadata"],
            compliance_notes=[
                "Strongest default for GDPR data minimization.",
                "Suitable for low-retention enterprise deployments.",
            ],
        ),
        "ERRORS_ONLY": RetentionPreviewResponse(
            privacy_mode=normalized,
            estimated_storage_mb_per_month="120",
            fields_captured=["error payload excerpts", "timings", "token counts", "failure metadata"],
            fields_redacted=["successful prompt and response payloads"],
            compliance_notes=[
                "Limits sensitive capture to failed requests only.",
                "Review incident retention windows with security teams.",
            ],
        ),
        "SAMPLED": RetentionPreviewResponse(
            privacy_mode=normalized,
            estimated_storage_mb_per_month="350",
            fields_captured=["sampled prompt/response excerpts", "timings", "token counts", "metadata"],
            fields_redacted=["non-sampled payloads"],
            compliance_notes=[
                "Use with a documented sampling policy.",
                "Sampled payloads may still be in regulatory scope.",
            ],
        ),
        "FULL": RetentionPreviewResponse(
            privacy_mode=normalized,
            estimated_storage_mb_per_month="1200",
            fields_captured=["full prompts", "full responses", "tool payloads", "metadata", "timings"],
            fields_redacted=[],
            compliance_notes=[
                "Highest observability, highest compliance burden.",
                "Requires clear retention and consent posture for many teams.",
            ],
        ),
    }
    return previews.get(normalized, previews["METADATA_ONLY"])


def _detect_pii_spans(text: str) -> list[PiiDetectionResponse]:
    found: list[PiiDetectionResponse] = []
    for pii_type, confidence, pattern in _PII_PATTERNS:
        for match in pattern.finditer(text):
            found.append(
                PiiDetectionResponse(
                    type=pii_type,
                    value=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                )
            )
    found.sort(key=lambda item: (item.start, item.end))
    return found


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


async def _get_visible_api_key(
    db: AsyncSession,
    key_id: uuid.UUID,
    workspace: Workspace,
    workspace_membership: WorkspaceUser | None,
) -> tuple[ApiKey, dict[uuid.UUID, str]]:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None or api_key.is_session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    visible_workspaces = await _key_visible_workspaces(db, workspace, workspace_membership)
    if api_key.workspace_id not in visible_workspaces:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key is outside your API key scope")
    return api_key, visible_workspaces


@router.get("/ops/status")
async def get_ops_feature_status(auth: PlatformAdminDep) -> dict[str, Any]:
    """Expose platform-wide optional feature flags for the Settings UI."""
    _workspace = auth[0]
    smtp_configured = bool(app_settings.smtp_user and app_settings.smtp_password)
    return {
        "email_enabled": app_settings.email_enabled,
        "email_reports_enabled": app_settings.email_reports_enabled,
        "backup_enabled": app_settings.backup_enabled,
        "smtp_configured": smtp_configured,
        "redis_durable": app_settings.redis_durability_mode != "ephemeral",
        "redis_durability_mode": app_settings.redis_durability_mode,
        "compliance_export_enabled": app_settings.compliance_export_enabled,
        "compliance_export_configured": bool(app_settings.compliance_export_bucket),
        "object_lifecycle_enabled": app_settings.object_lifecycle_enabled,
        "abuse_protection_enabled": app_settings.abuse_protection_enabled,
        "local_tls_enabled": app_settings.local_tls_enabled,
        "deployment_profile": app_settings.deployment_profile,
        "feature_flags": sorted(app_settings.enabled_feature_flags),
    }


@router.get("/ops/queues")
async def get_ops_queue_status(
    auth: PlatformAdminDep,
    redis: Annotated[Redis, Depends(get_redis)],
) -> dict[str, Any]:
    """Expose worker queue depth and role hints for the operator UI."""
    _workspace = auth[0]
    items = await get_queue_depths(redis)
    return {
        "items": items,
        "total_depth": sum(int(item["depth"]) for item in items),
        "busy_queues": sum(1 for item in items if int(item["depth"]) > 0),
    }


@router.get("/ops/storage")
async def get_ops_storage_status(auth: PlatformAdminDep) -> dict[str, Any]:
    _workspace = auth[0]
    return {
        "backup": {
            "bucket": app_settings.runledger_localai_s3_bucket if hasattr(app_settings, "runledger_localai_s3_bucket") else None,
            "lifecycle_enabled": app_settings.object_lifecycle_enabled,
            "retention_days": app_settings.object_lifecycle_days,
            "noncurrent_retention_days": app_settings.object_lifecycle_noncurrent_days,
        },
        "compliance_exports": {
            "enabled": app_settings.compliance_export_enabled,
            "bucket": app_settings.compliance_export_bucket or None,
            "prefix": app_settings.compliance_export_prefix,
            "storage_class": app_settings.compliance_export_storage_class,
            "retention_days": app_settings.compliance_export_retention_days,
        },
    }


@router.get("/webhooks/defaults", response_model=PlatformWebhookSettingsResponse)
async def get_platform_webhook_defaults(
    auth: PlatformAdminDep,
    db: DbDep,
) -> PlatformWebhookSettingsResponse:
    _workspace = auth[0]
    settings_row = await _get_or_create_platform_webhook_settings(db)
    return _platform_webhook_settings_response(settings_row)


@router.put("/webhooks/defaults", response_model=PlatformWebhookSettingsResponse)
async def update_platform_webhook_defaults(
    payload: PlatformWebhookSettingsUpdate,
    auth: PlatformAdminDep,
    db: DbDep,
) -> PlatformWebhookSettingsResponse:
    _workspace = auth[0]
    settings_row = await _get_or_create_platform_webhook_settings(db)
    settings_row.generic_webhook_url = payload.generic_webhook_url or None
    settings_row.slack_webhook_url = payload.slack_webhook_url or None
    settings_row.events = list(payload.events)
    settings_row.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(settings_row)
    return _platform_webhook_settings_response(settings_row)


@router.post("/webhooks/defaults/test", response_model=PlatformWebhookSettingsTestResult)
async def test_platform_webhook_defaults(
    auth: PlatformAdminDep,
    db: DbDep,
) -> PlatformWebhookSettingsTestResult:
    _workspace = auth[0]
    settings_row = await _get_or_create_platform_webhook_settings(db)
    results: list[PlatformWebhookSettingsTestStatus] = []

    if settings_row.generic_webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings_row.generic_webhook_url,
                    json={
                        "event": "platform.webhook.test",
                        "source": "runledger.platform",
                        "message": "RunLedger platform webhook default test event",
                    },
                )
                response.raise_for_status()
            results.append(PlatformWebhookSettingsTestStatus(channel="webhook", ok=True, error=None))
        except Exception as exc:
            results.append(PlatformWebhookSettingsTestStatus(channel="webhook", ok=False, error=str(exc)))

    if settings_row.slack_webhook_url:
        try:
            await send_slack_message(
                settings_row.slack_webhook_url,
                build_test_blocks(),
                "RunLedger platform webhook test",
            )
            results.append(PlatformWebhookSettingsTestStatus(channel="slack", ok=True, error=None))
        except Exception as exc:
            results.append(PlatformWebhookSettingsTestStatus(channel="slack", ok=False, error=str(exc)))

    return PlatformWebhookSettingsTestResult(
        ok=all(item.ok for item in results) if results else False,
        results=results,
        message="No platform defaults configured." if not results else "Platform webhook default test completed.",
    )


@router.get("/ops/feature-flags")
async def get_ops_feature_flags(auth: PlatformAdminDep) -> dict[str, Any]:
    _workspace = auth[0]
    known_flags = [
        "gateway_pass_through",
        "kafka_exports",
        "backup_operations",
        "policy_dry_run",
        "otlp_insights",
        "demo_mode",
    ]
    return {
        "enabled": sorted(app_settings.enabled_feature_flags),
        "items": [
            {
                "name": flag,
                "enabled": app_settings.is_feature_enabled(flag),
            }
            for flag in known_flags
        ],
    }


@router.get("/ops/policy-evaluation")
async def get_ops_policy_evaluation(auth: PlatformAdminDep) -> dict[str, Any]:
    _workspace = auth[0]
    return evaluate_infra_posture()


@router.get("/capture-policy/retention-preview", response_model=RetentionPreviewResponse)
async def get_capture_policy_retention_preview(
    auth: WorkspaceAdminDep,
    privacy_mode: str = Query("METADATA_ONLY"),
) -> RetentionPreviewResponse:
    _workspace, _user, _workspace_membership = auth
    return _retention_preview(privacy_mode)


@router.post("/capture-policy/test-pii", response_model=PiiTestResultResponse)
async def test_capture_policy_pii(
    body: PiiTestRequest,
    auth: WorkspaceAdminDep,
) -> PiiTestResultResponse:
    _workspace, _user, _workspace_membership = auth
    return PiiTestResultResponse(
        input_text=body.text,
        detected_pii=_detect_pii_spans(body.text),
        redacted_text=redact_text(body.text),
    )


@router.get("/capture-policy/scopes", response_model=CapturePolicyScopeList)
async def list_capture_policy_scopes(
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> CapturePolicyScopeList:
    workspace, _user, _workspace_membership = auth
    items = list(
        (
            await db.execute(
                select(CapturePolicyScope)
                .where(CapturePolicyScope.workspace_id == workspace.id)
                .order_by(CapturePolicyScope.scope_type.asc(), CapturePolicyScope.scope_id.asc())
            )
        )
        .scalars()
        .all()
    )
    return CapturePolicyScopeList(
        items=[_capture_policy_scope_to_response(item) for item in items]
    )


@router.put("/capture-policy/scopes", response_model=CapturePolicyScopeResponse)
async def upsert_capture_policy_scope(
    body: CapturePolicyScopeUpsert,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> CapturePolicyScopeResponse:
    workspace, _user, _workspace_membership = auth
    existing = (
        await db.execute(
            select(CapturePolicyScope).where(
                CapturePolicyScope.workspace_id == workspace.id,
                CapturePolicyScope.scope_type == body.scope_type,
                CapturePolicyScope.scope_id == body.scope_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = CapturePolicyScope(
            workspace_id=workspace.id,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            privacy_mode=body.privacy_mode,
            sampled_rate=body.sampled_rate,
        )
        db.add(existing)
    else:
        existing.privacy_mode = body.privacy_mode
        existing.sampled_rate = body.sampled_rate
        existing.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(existing)
    return _capture_policy_scope_to_response(existing)


@router.delete("/capture-policy/scopes", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capture_policy_scope(
    scope_type: str,
    scope_id: str,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> None:
    workspace, _user, _workspace_membership = auth
    existing = (
        await db.execute(
            select(CapturePolicyScope).where(
                CapturePolicyScope.workspace_id == workspace.id,
                CapturePolicyScope.scope_type == scope_type,
                CapturePolicyScope.scope_id == scope_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scoped capture policy not found")
    await db.delete(existing)
    await db.commit()


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
            "budget_tier_id": k.budget_tier_id,
            "key_prefix": k.key_prefix,
            "name": k.name,
            "scopes": k.scopes,
            "created_at": k.created_at,
            "created_by": k.created_by,
            "is_session": k.is_session,
            "ownership_type": k.ownership_type,
            "owner_reference": k.owner_reference,
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
        ownership_type=body.ownership_type,
        owner_reference=body.owner_reference,
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
        "budget_tier_id": api_key.budget_tier_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "created_by": api_key.created_by,
        "ownership_type": api_key.ownership_type,
        "owner_reference": api_key.owner_reference,
        "key": raw_key,
    }


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> dict[str, Any]:
    workspace, _user, workspace_membership = auth
    api_key, visible_workspaces = await _get_visible_api_key(
        db, key_id, workspace, workspace_membership
    )
    if api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    return {
        "id": api_key.id,
        "workspace_id": api_key.workspace_id,
        "workspace_name": visible_workspaces.get(api_key.workspace_id),
        "budget_tier_id": api_key.budget_tier_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "created_by": api_key.created_by,
        "is_session": api_key.is_session,
        "ownership_type": api_key.ownership_type,
        "owner_reference": api_key.owner_reference,
    }


@router.put("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    body: ApiKeyUpdate,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> dict[str, Any]:
    workspace, _user, workspace_membership = auth
    api_key, visible_workspaces = await _get_visible_api_key(
        db, key_id, workspace, workspace_membership
    )
    if api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(api_key, field, value)

    await db.commit()
    await db.refresh(api_key)
    return {
        "id": api_key.id,
        "workspace_id": api_key.workspace_id,
        "workspace_name": visible_workspaces.get(api_key.workspace_id),
        "budget_tier_id": api_key.budget_tier_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "created_by": api_key.created_by,
        "is_session": api_key.is_session,
        "ownership_type": api_key.ownership_type,
        "owner_reference": api_key.owner_reference,
    }


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: uuid.UUID, auth: WorkspaceAdminDep, db: DbDep) -> None:
    """Revoke a key belonging to the caller's org (org-admin only)."""
    workspace, _user, workspace_membership = auth
    api_key, _visible_workspaces = await _get_visible_api_key(
        db, key_id, workspace, workspace_membership
    )
    api_key.revoked_at = datetime.now(UTC)
    await db.commit()
    log.info("api_key_revoked", key_id=str(key_id))


# ── Email Preferences ─────────────────────────────────────────────────────────


@router.get("/email/preferences", response_model=EmailPreferenceResponse)
async def get_email_preferences(auth: OrgAdminDep, db: DbDep) -> EmailPreference:
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


@router.get("/email/status")
async def get_email_feature_status(auth: OrgAdminDep) -> dict[str, bool]:
    """Expose org-safe email delivery flags for the org console."""
    _workspace = auth[0]
    return {
        "email_enabled": app_settings.email_enabled,
        "email_reports_enabled": app_settings.email_reports_enabled,
        "smtp_configured": bool(app_settings.smtp_user and app_settings.smtp_password),
    }


@router.put("/email/preferences", response_model=EmailPreferenceResponse)
async def update_email_preferences(
    body: EmailPreferenceUpdate, auth: OrgAdminDep, db: DbDep
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
async def get_email_log(auth: OrgAdminDep, db: DbDep) -> EmailLogList:
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


@router.get("/email/history", response_model=EmailLogList)
async def get_email_history(auth: OrgAdminDep, db: DbDep) -> EmailLogList:
    return await get_email_log(auth=auth, db=db)


@router.post("/email/test")
async def test_email_send(
    auth: OrgAdminDep,
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


@router.post("/email/test-report")
async def test_email_report(
    auth: OrgAdminDep,
    db: DbDep,
) -> dict[str, Any]:
    workspace = auth[0]
    if not app_settings.email_enabled:
        return {"ok": False, "error": "Email delivery is disabled (EMAIL_ENABLED=false)"}
    if not app_settings.smtp_user or not app_settings.smtp_password:
        return {"ok": False, "error": "SMTP credentials are not configured"}

    prefs = (
        await db.execute(select(EmailPreference).where(EmailPreference.workspace_id == workspace.id))
    ).scalar_one_or_none()
    admins = await get_workspace_admin_users(db, workspace.id)
    recipient = admins[0] if admins else None
    if recipient is None:
        return {"ok": False, "error": "No workspace admin email found"}

    from runledger_api.services.email import send_analytics_report_email  # noqa: PLC0415

    await send_analytics_report_email(
        to_email=recipient.email,
        full_name=recipient.full_name,
        period_label="Test report",
        rows=[
            {
                "date": datetime.now(UTC).date().isoformat(),
                "provider": "openai",
                "model": "gpt-5",
                "cost_usd": "12.340000",
                "input_tokens": 12345,
                "output_tokens": 2345,
                "call_count": 42,
            }
        ],
        total_cost="12.340000",
        workspace_name=workspace.name,
        template=getattr(prefs, "report_template", "detailed"),
    )
    return {"ok": True, "recipient": recipient.email}


@router.get("/backups/history", response_model=BackupRunList)
async def get_backup_history(
    auth: OrgAdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> BackupRunList:
    workspace = auth[0]
    items, total = await backup_ops.list_backup_runs(db, workspace.id, limit=limit)
    return BackupRunList(
        items=[BackupRunResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/backups/config", response_model=BackupTargetConfigResponse | None)
async def get_backup_config(
    auth: OrgAdminDep,
    db: DbDep,
) -> BackupTargetConfigResponse | None:
    workspace = auth[0]
    config = await backup_ops.get_backup_config(db, workspace.id)
    if config is None:
        return None
    return BackupTargetConfigResponse.model_validate(config)


@router.put("/backups/config", response_model=BackupTargetConfigResponse)
async def update_backup_config(
    payload: BackupTargetConfigUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> BackupTargetConfigResponse:
    workspace = auth[0]
    config = await backup_ops.upsert_backup_config(
        db, workspace.id, payload.model_dump()
    )
    return BackupTargetConfigResponse.model_validate(config)


@router.get("/backups/snapshots", response_model=BackupSnapshotList)
async def get_backup_snapshots(
    auth: OrgAdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> BackupSnapshotList:
    workspace = auth[0]
    items, total = await backup_ops.list_backup_snapshots(db, workspace.id, limit=limit)
    return BackupSnapshotList(
        items=[BackupSnapshotResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("/backups/run", response_model=BackupRunResponse)
async def run_backup_now(auth: OrgAdminDep, db: DbDep) -> BackupRunResponse:
    workspace = auth[0]
    if not app_settings.backup_enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Backup execution is disabled for this deployment (BACKUP_ENABLED=false).",
        )
    actor = None
    if len(auth) > 1 and getattr(auth[1], "email", None):
        actor = auth[1].email
    backup = await backup_ops.queue_backup_run(db, workspace.id, triggered_by=actor)
    return BackupRunResponse.model_validate(backup)


@router.post("/backups/test", response_model=BackupActionResult)
async def test_backup_connection(auth: OrgAdminDep, db: DbDep) -> BackupActionResult:
    workspace = auth[0]
    config = await backup_ops.get_backup_config(db, workspace.id)
    result = await backup_ops.test_backup_connection(config)
    return BackupActionResult(
        ok=bool(result["ok"]),
        message=str(result["message"]),
        details=result.get("details"),
    )


@router.post("/backups/restore-drill", response_model=BackupRunResponse)
async def run_restore_drill(auth: OrgAdminDep, db: DbDep) -> BackupRunResponse:
    workspace = auth[0]
    actor = None
    if len(auth) > 1 and getattr(auth[1], "email", None):
        actor = auth[1].email
    backup = await backup_ops.queue_restore_drill(db, workspace.id, triggered_by=actor)
    return BackupRunResponse.model_validate(backup)


@router.get("/backups/status", response_model=BackupActionResult)
async def get_backup_status(auth: OrgAdminDep, db: DbDep) -> BackupActionResult:
    workspace = auth[0]
    status_payload = await backup_ops.backup_alert_status(db, workspace.id)
    return BackupActionResult(
        ok=not status_payload["has_alert"],
        message=status_payload["message"],
        details=status_payload,
    )


# ── Onboarding ───────────────────────────────────────────────────────────────


@router.get("/onboarding-status")
async def onboarding_status(
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, Any]:
    """Return setup completion checklist for onboarding wizard."""
    from runledger_api.models.alerts import AlertRule  # noqa: PLC0415
    from runledger_api.models.approvals import Approval  # noqa: PLC0415
    from runledger_api.models.billing import BillingPeriod  # noqa: PLC0415
    from runledger_api.models.budgets import Budget, BudgetNotification  # noqa: PLC0415
    from runledger_api.models.events import AgentRun  # noqa: PLC0415
    from runledger_api.models.gateway import GatewayRoute  # noqa: PLC0415
    from runledger_api.models.guardrails import GuardrailRule  # noqa: PLC0415
    from runledger_api.models.ledger import CapturePolicy  # noqa: PLC0415
    from runledger_api.models.mcp_registry import McpServer  # noqa: PLC0415
    from runledger_api.models.search_tools import SearchTool  # noqa: PLC0415
    from runledger_api.models.security import WorkspaceSecuritySettings  # noqa: PLC0415
    from runledger_api.models.tags import Tag  # noqa: PLC0415
    from runledger_api.models.tool_policies import ToolPolicy  # noqa: PLC0415

    ws = workspace.id

    async def _exists(stmt: Any) -> bool:
        return (await db.execute(stmt)).scalar_one_or_none() is not None

    has_org = await _exists(
        select(Tenant.id).where(Tenant.id == workspace.tenant_id).limit(1)
    )
    has_workspace = True
    has_api_key = await _exists(
        select(ApiKey.id).where(ApiKey.workspace_id == ws, ApiKey.revoked_at.is_(None)).limit(1)
    )
    has_first_run = await _exists(
        select(AgentRun.id).where(AgentRun.workspace_id == ws).limit(1)
    )
    has_gateway_route = await _exists(
        select(GatewayRoute.id).where(GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)).limit(1)
    )
    has_budget = await _exists(
        select(Budget.id).where(Budget.workspace_id == ws).limit(1)
    )
    has_alert_rule = await _exists(
        select(AlertRule.id).where(AlertRule.workspace_id == ws).limit(1)
    )
    has_budget_notification = await _exists(
        select(BudgetNotification.id).where(BudgetNotification.workspace_id == ws).limit(1)
    )
    has_billing_period = await _exists(
        select(BillingPeriod.id).where(BillingPeriod.workspace_id == ws).limit(1)
    )
    has_provider_profile = await _exists(
        select(GatewayRoute.provider).where(GatewayRoute.workspace_id == ws, GatewayRoute.is_active.is_(True)).limit(1)
    )
    has_guardrail = await _exists(
        select(GuardrailRule.id).where(GuardrailRule.workspace_id == ws, GuardrailRule.status == "active").limit(1)
    )
    has_rate_limit = await _exists(
        select(GatewayRoute.id).where(GatewayRoute.workspace_id == ws, GatewayRoute.per_user_rpm_limit.is_not(None)).limit(1)
    )
    has_mcp_server = await _exists(
        select(McpServer.id).where(McpServer.workspace_id == ws).limit(1)
    )
    has_search_tool = await _exists(
        select(SearchTool.id).where(SearchTool.workspace_id == ws).limit(1)
    )
    has_tool_policy = await _exists(
        select(ToolPolicy.id).where(ToolPolicy.workspace_id == ws, ToolPolicy.is_active.is_(True)).limit(1)
    )
    has_approval_config = await _exists(
        select(Approval.id).where(Approval.workspace_id == ws).limit(1)
    )
    has_data_capture = await _exists(
        select(CapturePolicy.id).where(CapturePolicy.workspace_id == ws).limit(1)
    )
    has_security_config = await _exists(
        select(WorkspaceSecuritySettings.id).where(WorkspaceSecuritySettings.workspace_id == ws).limit(1)
    )
    has_tag = await _exists(
        select(Tag.id).where(Tag.workspace_id == ws).limit(1)
    )

    steps = [
        has_org, has_workspace, has_api_key, has_first_run,
        has_gateway_route, has_budget, has_alert_rule,
        has_budget_notification, has_billing_period,
        has_provider_profile, has_guardrail, has_rate_limit,
        has_mcp_server, has_search_tool, has_tool_policy,
        has_approval_config, has_data_capture, has_security_config,
        has_tag,
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
        "has_budget_notification": has_budget_notification,
        "has_billing_period": has_billing_period,
        "has_provider_profile": has_provider_profile,
        "has_guardrail": has_guardrail,
        "has_rate_limit": has_rate_limit,
        "has_mcp_server": has_mcp_server,
        "has_search_tool": has_search_tool,
        "has_tool_policy": has_tool_policy,
        "has_approval_config": has_approval_config,
        "has_data_capture": has_data_capture,
        "has_security_config": has_security_config,
        "has_tag": has_tag,
        "completed": completed,
        "total": len(steps),
        "pct": round(completed / len(steps) * 100),
    }


# ── Demo seed ────────────────────────────────────────────────────────────────


@router.get("/demo-status")
async def get_demo_status(auth: PlatformAdminDep) -> dict[str, Any]:
    """Return the most recent demo-mode task state."""
    _workspace = auth[0]
    return read_demo_state()


@router.post("/demo-seed")
async def trigger_demo_seed(
    auth: PlatformAdminDep,
    profile: str = Query(default="full"),
) -> dict[str, Any]:
    """Trigger the demo data seeder (platform admin only)."""
    _workspace = auth[0]
    return launch_demo_process("seed", profile=profile)


@router.post("/demo-reset")
async def trigger_demo_reset(auth: PlatformAdminDep) -> dict[str, Any]:
    """Reset demo data to a clean slate (platform admin only)."""
    _workspace = auth[0]
    return launch_demo_process("reset")
