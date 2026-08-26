from __future__ import annotations

import ipaddress
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.security import IpAclRule, KeyRotationEvent, OIDCProvider
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
    OIDCProviderCreate,
    OIDCProviderList,
    OIDCProviderResponse,
    OIDCProviderUpdate,
    RotateApiKeyRequest,
    RotateApiKeyResponse,
    WorkspaceSecuritySettingsResponse,
    WorkspaceSecuritySettingsUpdate,
)
from runledger_api.services.auth import generate_api_key
from runledger_api.services.security import evaluate_ip_acl, get_or_create_security_settings

router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(management_rate_limit)],
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
OrgAdminDep = Annotated[tuple[Workspace, Any, Any], Depends(require_org_admin)]


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
    if key is None or key.is_session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    visible_workspace_ids = await _visible_workspace_ids(db, workspace, membership)
    if key.workspace_id not in visible_workspace_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    return key


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
    return OIDCProviderList(items=[OIDCProviderResponse.model_validate(item) for item in items])


@router.post(
    "/oidc-providers", response_model=OIDCProviderResponse, status_code=status.HTTP_201_CREATED
)
async def create_oidc_provider(
    body: OIDCProviderCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> OIDCProviderResponse:
    workspace = auth[0]
    item = OIDCProvider(workspace_id=workspace.id, **body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return OIDCProviderResponse.model_validate(item)


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
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(item)
    return OIDCProviderResponse.model_validate(item)


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
    await db.commit()


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
    item = IpAclRule(workspace_id=workspace_id, **body.model_dump())
    db.add(item)
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
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
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
    await db.delete(item)
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
            team_name=body.team_name,
            client_ip=body.ip,
        )
        return IpAclTestResponse(ip=body.ip, allowed=True)
    except HTTPException:
        return IpAclTestResponse(ip=body.ip, allowed=False)


@router.get("/api-keys/{key_id}/rotation-history", response_model=KeyRotationEventList)
async def get_key_rotation_history(
    key_id: uuid.UUID, auth: OrgAdminDep, db: DbDep
) -> KeyRotationEventList:
    workspace, _user, membership = auth
    await _get_rotatable_key(db, key_id, workspace, membership)
    items = (
        (
            await db.execute(
                select(KeyRotationEvent)
                .where(KeyRotationEvent.api_key_id == key_id)
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
    auth: OrgAdminDep,
    db: DbDep,
) -> RotateApiKeyResponse:
    workspace, user, membership = auth
    key = await _get_rotatable_key(db, key_id, workspace, membership)
    environment = (
        EnvironmentEnum.prod if key.key_prefix.startswith("rl_live_") else EnvironmentEnum.dev
    )
    raw_key, key_hash, key_prefix = generate_api_key(environment)
    grace_expires_at = (
        datetime.now(UTC) + timedelta(hours=body.grace_hours) if body.grace_hours > 0 else None
    )

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
    )
    key.expires_at = grace_expires_at or datetime.now(UTC)
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
    await db.commit()
    return RotateApiKeyResponse(
        key_id=new_key.id,
        key_prefix=new_key.key_prefix,
        key=raw_key,
        expires_old_at=grace_expires_at,
    )
