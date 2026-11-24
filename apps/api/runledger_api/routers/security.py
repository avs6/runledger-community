from __future__ import annotations

import ipaddress
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core import secrets
from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin, require_workspace_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.security import (
    IpAclRule,
    KeyRotationEvent,
    LDAPProvider,
    OAuth2Provider,
    OIDCProvider,
)
from runledger_api.models.tenant import ApiKey, EnvironmentEnum, Workspace, WorkspaceUser
from runledger_api.schemas.security import (
    IpAclRuleCreate,
    IpAclRuleList,
    IpAclRuleResponse,
    IpAclRuleUpdate,
    IpAclTestRequest,
    IpAclTestResponse,
    KeyRotationEventList,
    KeyRotationEventResponse,
    LDAPProviderCreate,
    LDAPProviderList,
    LDAPProviderResponse,
    LDAPProviderUpdate,
    OAuth2ProviderCreate,
    OAuth2ProviderList,
    OAuth2ProviderResponse,
    OAuth2ProviderUpdate,
    OIDCProviderCreate,
    OIDCProviderList,
    OIDCProviderResponse,
    OIDCProviderUpdate,
    RotateApiKeyRequest,
    RotateApiKeyResponse,
    SecretInventoryResponse,
    SecretRecordResponse,
    SecretRewrapResponse,
    SecretRotateRequest,
    WorkspaceSecuritySettingsResponse,
    WorkspaceSecuritySettingsUpdate,
)
from runledger_api.services import secrets_inventory
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.auth import generate_api_key
from runledger_api.services.security import (
    evaluate_ip_acl,
    get_or_create_security_settings,
)

router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple[Workspace, Any, Any], Depends(require_org_admin)]
# Key rotation follows API-key management: workspace admins rotate keys in their
# workspace, org admins (membership None) across the org.
WorkspaceAdminDep = Annotated[tuple[Workspace, Any, Any], Depends(require_workspace_admin)]


async def _visible_workspace_ids(
    db: AsyncSession,
    workspace: Workspace,
    membership: WorkspaceUser | None,
) -> set[uuid.UUID]:
    if membership is not None:
        return {workspace.id}
    result = await db.execute(
        select(Workspace.id).where(Workspace.tenant_id == workspace.tenant_id)
    )
    return set(result.scalars().all())


async def _get_rotatable_key(
    db: AsyncSession,
    key_id: uuid.UUID,
    workspace: Workspace,
    membership: WorkspaceUser | None,
) -> ApiKey:
    key = await db.get(ApiKey, key_id)
    if key is None or key.is_session or key.revoked_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    visible_workspace_ids = await _visible_workspace_ids(db, workspace, membership)
    if key.workspace_id not in visible_workspace_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    return key


def _oidc_out(item: OIDCProvider) -> OIDCProviderResponse:
    out = OIDCProviderResponse.model_validate(item)
    out.client_secret = secrets.mask(item.client_secret_encrypted)
    return out


def _oauth2_out(item: OAuth2Provider) -> OAuth2ProviderResponse:
    out = OAuth2ProviderResponse.model_validate(item)
    out.client_secret = secrets.mask(item.client_secret_encrypted)
    return out


def _ldap_out(item: LDAPProvider) -> LDAPProviderResponse:
    out = LDAPProviderResponse.model_validate(item)
    out.bind_password = secrets.mask(item.bind_password_encrypted)
    return out


@router.get("/settings", response_model=WorkspaceSecuritySettingsResponse)
async def get_security_settings(auth: OrgAdminDep, db: DbDep) -> WorkspaceSecuritySettingsResponse:
    workspace = auth[0]
    return WorkspaceSecuritySettingsResponse.model_validate(
        await get_or_create_security_settings(db, workspace.id)
    )


@router.put("/settings", response_model=WorkspaceSecuritySettingsResponse)
async def update_security_settings(
    body: WorkspaceSecuritySettingsUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> WorkspaceSecuritySettingsResponse:
    workspace = auth[0]
    settings = await get_or_create_security_settings(db, workspace.id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.now(UTC)
    await emit_audit_event(
        db,
        auth[0].id,
        "security.settings_updated",
        actor_user_id=auth[1].id,
        target_type="security_settings",
        target_id=str(workspace.id),
    )
    await db.commit()
    await db.refresh(settings)
    return WorkspaceSecuritySettingsResponse.model_validate(settings)


@router.get("/oidc-providers", response_model=OIDCProviderList)
async def list_oidc_providers(auth: OrgAdminDep, db: DbDep) -> OIDCProviderList:
    workspace = auth[0]
    items = (
        (await db.execute(select(OIDCProvider).where(OIDCProvider.workspace_id == workspace.id)))
        .scalars()
        .all()
    )
    return OIDCProviderList(items=[_oidc_out(item) for item in items])


@router.post(
    "/oidc-providers", response_model=OIDCProviderResponse, status_code=status.HTTP_201_CREATED
)
async def create_oidc_provider(
    body: OIDCProviderCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> OIDCProviderResponse:
    workspace = auth[0]
    data = body.model_dump(exclude={"client_secret"})
    if body.client_secret and not secrets.is_mask(body.client_secret):
        data["client_secret_encrypted"] = body.client_secret  # encrypted by the column type
    data["tenant_id"] = workspace.tenant_id
    item = OIDCProvider(workspace_id=workspace.id, **data)
    db.add(item)
    await db.flush()
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.created",
        actor_user_id=auth[1].id,
        target_type="oidc_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _oidc_out(item)


@router.put("/oidc-providers/{provider_id}", response_model=OIDCProviderResponse)
async def update_oidc_provider(
    provider_id: uuid.UUID,
    body: OIDCProviderUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> OIDCProviderResponse:
    workspace = auth[0]
    item = await db.get(OIDCProvider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OIDC provider not found")
    updates = body.model_dump(exclude_none=True, exclude={"client_secret"})
    for field, value in updates.items():
        setattr(item, field, value)
    if body.client_secret is not None and not secrets.is_mask(body.client_secret):
        item.client_secret_encrypted = (
            body.client_secret
        )  # encrypted by the column type; mask = keep
    item.updated_at = datetime.now(UTC)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.updated",
        actor_user_id=auth[1].id,
        target_type="oidc_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _oidc_out(item)


@router.delete("/oidc-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_oidc_provider(
    provider_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    item = await db.get(OIDCProvider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OIDC provider not found")
    await db.delete(item)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.deleted",
        actor_user_id=auth[1].id,
        target_type="oidc_provider",
        target_id=str(item.id),
    )
    await db.commit()


# ── OAuth2 Providers ──────────────────────────────────────────────────────────


@router.get("/oauth2-providers", response_model=OAuth2ProviderList)
async def list_oauth2_providers(auth: OrgAdminDep, db: DbDep) -> OAuth2ProviderList:
    workspace = auth[0]
    items = (
        (
            await db.execute(
                select(OAuth2Provider).where(OAuth2Provider.workspace_id == workspace.id)
            )
        )
        .scalars()
        .all()
    )
    return OAuth2ProviderList(items=[_oauth2_out(item) for item in items])


@router.post(
    "/oauth2-providers", response_model=OAuth2ProviderResponse, status_code=status.HTTP_201_CREATED
)
async def create_oauth2_provider(
    body: OAuth2ProviderCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> OAuth2ProviderResponse:
    workspace = auth[0]
    data = body.model_dump(exclude={"client_secret"})
    if body.client_secret and not secrets.is_mask(body.client_secret):
        data["client_secret_encrypted"] = body.client_secret  # encrypted by the column type
    data["tenant_id"] = workspace.tenant_id
    item = OAuth2Provider(workspace_id=workspace.id, **data)
    db.add(item)
    await db.flush()
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.created",
        actor_user_id=auth[1].id,
        target_type="oauth2_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _oauth2_out(item)


@router.put("/oauth2-providers/{provider_id}", response_model=OAuth2ProviderResponse)
async def update_oauth2_provider(
    provider_id: uuid.UUID,
    body: OAuth2ProviderUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> OAuth2ProviderResponse:
    workspace = auth[0]
    item = await db.get(OAuth2Provider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")
    updates = body.model_dump(exclude_none=True, exclude={"client_secret"})
    for field, value in updates.items():
        setattr(item, field, value)
    if body.client_secret is not None and not secrets.is_mask(body.client_secret):
        item.client_secret_encrypted = (
            body.client_secret
        )  # encrypted by the column type; mask = keep
    item.updated_at = datetime.now(UTC)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.updated",
        actor_user_id=auth[1].id,
        target_type="oauth2_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _oauth2_out(item)


@router.delete("/oauth2-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_oauth2_provider(
    provider_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    item = await db.get(OAuth2Provider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "OAuth2 provider not found")
    await db.delete(item)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.deleted",
        actor_user_id=auth[1].id,
        target_type="oauth2_provider",
        target_id=str(item.id),
    )
    await db.commit()


# ── LDAP Providers ────────────────────────────────────────────────────────────


@router.get("/ldap-providers", response_model=LDAPProviderList)
async def list_ldap_providers(auth: OrgAdminDep, db: DbDep) -> LDAPProviderList:
    workspace = auth[0]
    items = (
        (await db.execute(select(LDAPProvider).where(LDAPProvider.workspace_id == workspace.id)))
        .scalars()
        .all()
    )
    return LDAPProviderList(items=[_ldap_out(item) for item in items])


@router.post(
    "/ldap-providers", response_model=LDAPProviderResponse, status_code=status.HTTP_201_CREATED
)
async def create_ldap_provider(
    body: LDAPProviderCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> LDAPProviderResponse:
    workspace = auth[0]
    data = body.model_dump(exclude={"bind_password"})
    if body.bind_password and not secrets.is_mask(body.bind_password):
        data["bind_password_encrypted"] = body.bind_password  # encrypted by the column type
    data["tenant_id"] = workspace.tenant_id
    item = LDAPProvider(workspace_id=workspace.id, **data)
    db.add(item)
    await db.flush()
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.created",
        actor_user_id=auth[1].id,
        target_type="ldap_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _ldap_out(item)


@router.put("/ldap-providers/{provider_id}", response_model=LDAPProviderResponse)
async def update_ldap_provider(
    provider_id: uuid.UUID,
    body: LDAPProviderUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> LDAPProviderResponse:
    workspace = auth[0]
    item = await db.get(LDAPProvider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LDAP provider not found")
    updates = body.model_dump(exclude_none=True, exclude={"bind_password"})
    for field, value in updates.items():
        setattr(item, field, value)
    if body.bind_password is not None and not secrets.is_mask(body.bind_password):
        item.bind_password_encrypted = (
            body.bind_password
        )  # encrypted by the column type; mask = keep
    item.updated_at = datetime.now(UTC)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.updated",
        actor_user_id=auth[1].id,
        target_type="ldap_provider",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return _ldap_out(item)


@router.delete("/ldap-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ldap_provider(
    provider_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    item = await db.get(LDAPProvider, provider_id)
    if item is None or item.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LDAP provider not found")
    await db.delete(item)
    await emit_audit_event(
        db,
        auth[0].id,
        "identity_provider.deleted",
        actor_user_id=auth[1].id,
        target_type="ldap_provider",
        target_id=str(item.id),
    )
    await db.commit()


async def _check_acl_rule(
    db: AsyncSession,
    workspace: Workspace,
    *,
    scope_type: str,
    cidr: str | None,
    api_key_id: uuid.UUID | None,
    access_group_id: uuid.UUID | None,
) -> None:
    """Validate an IP ACL rule before saving (review G-18): a real CIDR, and the key or
    access group it names must belong to this workspace."""
    if cidr is not None:
        try:
            ipaddress.ip_network(cidr.strip(), strict=False)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid CIDR") from exc
    if scope_type == "api_key" and api_key_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "api_key_id is required")
    if scope_type == "access_group" and access_group_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "access_group_id is required")
    if api_key_id is not None:
        key = await db.get(ApiKey, api_key_id)
        if key is None or key.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    if access_group_id is not None:
        from runledger_api.models.access_groups import AccessGroup  # noqa: PLC0415

        group = await db.get(AccessGroup, access_group_id)
        if group is None or group.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Access group not found")


def _require_platform_admin_for_global(auth: Any, workspace_id: uuid.UUID | None) -> None:
    """Global rules apply to every workspace and tenant, so only platform admins may
    create, change or delete them (review G-18)."""
    if workspace_id is None and not getattr(auth[1], "is_platform_admin", False):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only platform admins can manage global IP ACL rules"
        )


@router.get("/ip-acl", response_model=IpAclRuleList)
async def list_ip_acl_rules(auth: OrgAdminDep, db: DbDep) -> IpAclRuleList:
    workspace = auth[0]
    items = (
        (
            await db.execute(
                select(IpAclRule).where(
                    (IpAclRule.workspace_id == workspace.id) | (IpAclRule.workspace_id.is_(None))
                )
            )
        )
        .scalars()
        .all()
    )
    return IpAclRuleList(items=[IpAclRuleResponse.model_validate(item) for item in items])


@router.post("/ip-acl", response_model=IpAclRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_ip_acl_rule(
    body: IpAclRuleCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> IpAclRuleResponse:
    workspace = auth[0]
    workspace_id = None if body.scope_type == "global" else workspace.id
    _require_platform_admin_for_global(auth, workspace_id)
    await _check_acl_rule(
        db,
        workspace,
        scope_type=body.scope_type,
        cidr=body.cidr,
        api_key_id=body.api_key_id,
        access_group_id=body.access_group_id,
    )
    item = IpAclRule(workspace_id=workspace_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await emit_audit_event(
        db,
        auth[0].id,
        "ip_acl.created",
        actor_user_id=auth[1].id,
        target_type="ip_acl_rule",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return IpAclRuleResponse.model_validate(item)


@router.put("/ip-acl/{rule_id}", response_model=IpAclRuleResponse)
async def update_ip_acl_rule(
    rule_id: uuid.UUID,
    body: IpAclRuleUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> IpAclRuleResponse:
    workspace = auth[0]
    item = await db.get(IpAclRule, rule_id)
    if item is None or (item.workspace_id not in (None, workspace.id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IP ACL rule not found")
    _require_platform_admin_for_global(auth, item.workspace_id)
    changes = body.model_dump(exclude_none=True)
    await _check_acl_rule(
        db,
        workspace,
        scope_type=item.scope_type,
        cidr=changes.get("cidr"),
        api_key_id=changes.get("api_key_id", item.api_key_id),
        access_group_id=changes.get("access_group_id", item.access_group_id),
    )
    for field, value in changes.items():
        setattr(item, field, value)
    if "access_group_id" in changes:
        # Reassigning a legacy team rule to an access group (review G-18).
        item.scope_type = "access_group"
        item.team_name = None
    await emit_audit_event(
        db,
        auth[0].id,
        "ip_acl.updated",
        actor_user_id=auth[1].id,
        target_type="ip_acl_rule",
        target_id=str(item.id),
    )
    await db.commit()
    await db.refresh(item)
    return IpAclRuleResponse.model_validate(item)


@router.delete("/ip-acl/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ip_acl_rule(
    rule_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    item = await db.get(IpAclRule, rule_id)
    if item is None or (item.workspace_id not in (None, workspace.id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "IP ACL rule not found")
    _require_platform_admin_for_global(auth, item.workspace_id)
    await db.delete(item)
    await emit_audit_event(
        db,
        auth[0].id,
        "ip_acl.deleted",
        actor_user_id=auth[1].id,
        target_type="ip_acl_rule",
        target_id=str(item.id),
    )
    await db.commit()


@router.post("/ip-acl/test", response_model=IpAclTestResponse)
async def test_ip_acl(body: IpAclTestRequest, auth: OrgAdminDep, db: DbDep) -> IpAclTestResponse:
    workspace = auth[0]
    try:
        ipaddress.ip_address(body.ip)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid IP address") from exc
    try:
        await evaluate_ip_acl(
            db,
            workspace_id=workspace.id,
            api_key_id=body.api_key_id,
            client_ip=body.ip,
            principal_user_id=body.user_id,
        )
        return IpAclTestResponse(ip=body.ip, allowed=True)
    except HTTPException:
        return IpAclTestResponse(ip=body.ip, allowed=False)


@router.get("/api-keys/{key_id}/rotation-history", response_model=KeyRotationEventList)
async def get_key_rotation_history(
    key_id: uuid.UUID, auth: WorkspaceAdminDep, db: DbDep
) -> KeyRotationEventList:
    workspace, _user, membership = auth
    key = await _get_rotatable_key(db, key_id, workspace, membership)
    # Events are stored on the key a rotation produced; match both sides by prefix
    # so the history is visible from the old and the new key.
    items = (
        (
            await db.execute(
                select(KeyRotationEvent)
                .where(
                    (KeyRotationEvent.api_key_id == key_id)
                    | (KeyRotationEvent.rotated_from_prefix == key.key_prefix)
                    | (KeyRotationEvent.rotated_to_prefix == key.key_prefix)
                )
                .order_by(KeyRotationEvent.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return KeyRotationEventList(
        items=[KeyRotationEventResponse.model_validate(item) for item in items]
    )


@router.post("/api-keys/{key_id}/rotate", response_model=RotateApiKeyResponse)
async def rotate_api_key(
    key_id: uuid.UUID,
    body: RotateApiKeyRequest,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> RotateApiKeyResponse:
    workspace, user, membership = auth
    key = await _get_rotatable_key(db, key_id, workspace, membership)
    environment = (
        EnvironmentEnum.prod if key.key_prefix.startswith("rl_live_") else EnvironmentEnum.dev
    )
    raw_key, key_hash, key_prefix = generate_api_key(environment)
    now = datetime.now(UTC)
    grace_expires_at = now + timedelta(hours=body.grace_hours) if body.grace_hours > 0 else None
    # The replacement keeps the original key's expiry policy (if it had one).
    inherited_expiry = key.expires_at if key.expires_at and key.expires_at > now else None

    new_key = ApiKey(
        workspace_id=key.workspace_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key.name,
        scopes=list(key.scopes or []),
        created_by=getattr(user, "email", None),
        ownership_type=key.ownership_type,
        owner_reference=key.owner_reference,
        guardrail_config=key.guardrail_config,
        budget_tier_id=key.budget_tier_id,
        expires_at=inherited_expiry,
    )
    old_expiry = grace_expires_at or now
    key.expires_at = min(old_expiry, inherited_expiry) if inherited_expiry else old_expiry
    db.add(new_key)
    await db.flush()
    db.add(
        KeyRotationEvent(
            api_key_id=new_key.id,
            rotated_from_prefix=key.key_prefix,
            rotated_to_prefix=key_prefix,
            triggered_by=getattr(user, "email", None),
            grace_expires_at=grace_expires_at,
        )
    )
    await emit_audit_event(
        db,
        key.workspace_id,
        "api_key.rotated",
        actor_user_id=user.id,
        target_type="api_key",
        target_id=str(new_key.id),
        before={"key_prefix": key.key_prefix},
        after={
            "key_prefix": key_prefix,
            "grace_expires_at": grace_expires_at.isoformat() if grace_expires_at else None,
        },
    )
    await db.commit()
    return RotateApiKeyResponse(
        key_id=new_key.id,
        key_prefix=new_key.key_prefix,
        key=raw_key,
        expires_old_at=grace_expires_at,
    )


# ── Secret inventory (ENH) ────────────────────────────────────────────────────
#
# Every stored credential, its age, the key that wraps it, a "rotate" action
# (replace the value) and "re-wrap" (re-encrypt with the current master key).
# The per-secret timeline is GET /audit/events?target_type=secret&target_id=<id>.

SECRET_MAX_AGE_DAYS = 90
SECRET_WARN_DAYS = 60


def _secret_out(record: Any, fields: list[str]) -> SecretRecordResponse:
    age = secrets_inventory.age_days(record)
    if age >= SECRET_MAX_AGE_DAYS:
        age_status = "stale"
    elif age >= SECRET_WARN_DAYS:
        age_status = "aging"
    else:
        age_status = "fresh"
    return SecretRecordResponse(
        id=record.id,
        kind=record.kind,
        label=record.label,
        owner_table=record.owner_table,
        owner_id=record.owner_id,
        field=record.field,
        key_id=record.key_id,
        key_current=record.key_id == secrets.primary_key_id(),
        fingerprint=record.fingerprint,
        rotation_count=int(record.rotation_count or 0),
        rotated_by_label=record.rotated_by_label,
        created_at=record.created_at,
        rotated_at=record.rotated_at,
        age_days=age,
        age_status=age_status,
        fields=fields,
    )


async def _secret_fields(db: AsyncSession, record: Any) -> list[str]:
    entry = secrets_inventory.KINDS.get(record.kind)
    if entry is None or not entry.is_json:
        return []
    owner = await db.get(entry.model(), record.owner_id)
    config = getattr(owner, entry.field, None) or {}
    return sorted(k for k, v in config.items() if secrets.is_secret_key(k) and v)


@router.get("/secrets", response_model=SecretInventoryResponse)
async def list_secrets(auth: WorkspaceAdminDep, db: DbDep) -> SecretInventoryResponse:
    """All stored secrets in this workspace, oldest rotation first."""
    workspace = auth[0]
    records = await secrets_inventory.list_records(db, workspace.id)
    items = [_secret_out(r, await _secret_fields(db, r)) for r in records]
    return SecretInventoryResponse(
        items=items,
        primary_key_id=secrets.primary_key_id(),
        using_derived_key=secrets.using_derived_key(),
        max_age_days=SECRET_MAX_AGE_DAYS,
        warn_days=SECRET_WARN_DAYS,
    )


@router.get("/secrets/{secret_id}", response_model=SecretRecordResponse)
async def get_secret(
    secret_id: uuid.UUID, auth: WorkspaceAdminDep, db: DbDep
) -> SecretRecordResponse:
    record = await secrets_inventory.get_record(db, auth[0].id, secret_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Secret not found")
    return _secret_out(record, await _secret_fields(db, record))


@router.post("/secrets/{secret_id}/rotate", response_model=SecretRecordResponse)
async def rotate_secret(
    secret_id: uuid.UUID,
    body: SecretRotateRequest,
    auth: WorkspaceAdminDep,
    db: DbDep,
) -> SecretRecordResponse:
    """Replace a secret's value. The session hook records ``secret.rotated``."""
    workspace = auth[0]
    record = await secrets_inventory.get_record(db, workspace.id, secret_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Secret not found")
    try:
        await secrets_inventory.rotate_secret(db, record, value=body.value, values=body.values)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    await db.flush()
    await db.commit()
    await db.refresh(record)
    return _secret_out(record, await _secret_fields(db, record))


@router.post("/secrets/{secret_id}/rewrap", response_model=SecretRecordResponse)
async def rewrap_secret(
    secret_id: uuid.UUID, auth: WorkspaceAdminDep, db: DbDep
) -> SecretRecordResponse:
    """Re-encrypt one secret with the current master key (value unchanged)."""
    workspace = auth[0]
    record = await secrets_inventory.get_record(db, workspace.id, secret_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Secret not found")
    old_key = record.key_id
    if await secrets_inventory.rewrap_secret(db, record):
        await emit_audit_event(
            db,
            workspace.id,
            "secret.rewrapped",
            target_type="secret",
            target_id=str(record.id),
            before={"key_id": old_key},
            after={"key_id": record.key_id, "kind": record.kind, "label": record.label},
        )
    await db.commit()
    await db.refresh(record)
    return _secret_out(record, await _secret_fields(db, record))


@router.post("/secrets/rewrap", response_model=SecretRewrapResponse)
async def rewrap_all_secrets(auth: WorkspaceAdminDep, db: DbDep) -> SecretRewrapResponse:
    """Re-encrypt every secret in this workspace not yet on the primary key."""
    workspace = auth[0]
    count = 0
    for record in await secrets_inventory.list_records(db, workspace.id):
        old_key = record.key_id
        if await secrets_inventory.rewrap_secret(db, record):
            count += 1
            await emit_audit_event(
                db,
                workspace.id,
                "secret.rewrapped",
                target_type="secret",
                target_id=str(record.id),
                before={"key_id": old_key},
                after={"key_id": record.key_id, "kind": record.kind, "label": record.label},
            )
    await db.commit()
    return SecretRewrapResponse(rewrapped=count, primary_key_id=secrets.primary_key_id())
