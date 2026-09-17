from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkspaceSecuritySettingsUpdate(BaseModel):
    required_metadata_fields: list[str] | None = None
    required_metadata_mode: str | None = Field(None, pattern="^(warn|reject)$")
    data_residency_regions: list[str] | None = None
    callback_config: dict[str, Any] | None = None
    brand_config: dict[str, Any] | None = None
    oidc_session_config: dict[str, Any] | None = None


class WorkspaceSecuritySettingsResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    required_metadata_fields: list[str]
    required_metadata_mode: str
    data_residency_regions: list[str]
    callback_config: dict[str, Any]
    brand_config: dict[str, Any]
    oidc_session_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OIDCProviderCreate(BaseModel):
    name: str
    issuer_url: str
    audience: str | None = None
    discovery_url: str | None = None
    jwks_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: str = "openid email profile"
    auto_provision: bool = False
    default_workspace_role: str = "viewer"
    default_tenant_role: str = "org_member"
    claim_mappings: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class OIDCProviderUpdate(BaseModel):
    name: str | None = None
    issuer_url: str | None = None
    audience: str | None = None
    discovery_url: str | None = None
    jwks_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: str | None = None
    auto_provision: bool | None = None
    default_workspace_role: str | None = None
    default_tenant_role: str | None = None
    claim_mappings: dict[str, Any] | None = None
    is_active: bool | None = None


class OIDCProviderResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    name: str
    issuer_url: str
    audience: str | None
    discovery_url: str | None
    jwks_uri: str | None
    client_id: str | None = None
    scopes: str
    auto_provision: bool
    default_workspace_role: str
    default_tenant_role: str
    claim_mappings: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OIDCProviderList(BaseModel):
    items: list[OIDCProviderResponse]


class OIDCAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class OIDCCallbackRequest(BaseModel):
    code: str
    state: str
    provider_id: uuid.UUID


class AuthProviderInfo(BaseModel):
    id: uuid.UUID
    name: str
    type: str = "oidc"

    model_config = {"from_attributes": True}


class AuthProvidersResponse(BaseModel):
    providers: list[AuthProviderInfo]


class ExternalIdentityResponse(BaseModel):
    id: uuid.UUID
    provider_type: str
    provider_id: uuid.UUID
    external_subject: str
    external_email: str | None
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


# ── OAuth2 Provider schemas ──────────────────────────────────────────────────


class OAuth2ProviderCreate(BaseModel):
    name: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    client_id: str
    client_secret: str | None = None
    scopes: str = "openid email profile"
    userinfo_id_field: str = "sub"
    userinfo_email_field: str = "email"
    userinfo_name_field: str = "name"
    auto_provision: bool = False
    default_workspace_role: str = "viewer"
    default_tenant_role: str = "org_member"
    is_active: bool = True


class OAuth2ProviderUpdate(BaseModel):
    name: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: str | None = None
    userinfo_id_field: str | None = None
    userinfo_email_field: str | None = None
    userinfo_name_field: str | None = None
    auto_provision: bool | None = None
    default_workspace_role: str | None = None
    default_tenant_role: str | None = None
    is_active: bool | None = None


class OAuth2ProviderResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    name: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    client_id: str
    scopes: str
    userinfo_id_field: str
    userinfo_email_field: str
    userinfo_name_field: str
    auto_provision: bool
    default_workspace_role: str
    default_tenant_role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OAuth2ProviderList(BaseModel):
    items: list[OAuth2ProviderResponse]


class OAuth2AuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class OAuth2CallbackRequest(BaseModel):
    code: str
    state: str
    provider_id: uuid.UUID


# ── LDAP Provider schemas ────────────────────────────────────────────────────


class LDAPProviderCreate(BaseModel):
    name: str
    server_url: str
    bind_dn: str | None = None
    bind_password: str | None = None
    use_ssl: bool = False
    start_tls: bool = False
    user_search_base: str
    user_search_filter: str = "(uid={username})"
    email_attribute: str = "mail"
    name_attribute: str = "cn"
    uid_attribute: str = "uid"
    group_search_base: str | None = None
    group_search_filter: str | None = None
    auto_provision: bool = False
    default_workspace_role: str = "viewer"
    default_tenant_role: str = "org_member"
    is_active: bool = True


class LDAPProviderUpdate(BaseModel):
    name: str | None = None
    server_url: str | None = None
    bind_dn: str | None = None
    bind_password: str | None = None
    use_ssl: bool | None = None
    start_tls: bool | None = None
    user_search_base: str | None = None
    user_search_filter: str | None = None
    email_attribute: str | None = None
    name_attribute: str | None = None
    uid_attribute: str | None = None
    group_search_base: str | None = None
    group_search_filter: str | None = None
    auto_provision: bool | None = None
    default_workspace_role: str | None = None
    default_tenant_role: str | None = None
    is_active: bool | None = None


class LDAPProviderResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    name: str
    server_url: str
    bind_dn: str | None
    use_ssl: bool
    start_tls: bool
    user_search_base: str
    user_search_filter: str
    email_attribute: str
    name_attribute: str
    uid_attribute: str
    group_search_base: str | None
    group_search_filter: str | None
    auto_provision: bool
    default_workspace_role: str
    default_tenant_role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LDAPProviderList(BaseModel):
    items: list[LDAPProviderResponse]


class LDAPLoginRequest(BaseModel):
    provider_id: uuid.UUID
    username: str
    password: str


class IpAclRuleCreate(BaseModel):
    scope_type: str = Field(..., pattern="^(global|workspace|api_key|team)$")
    api_key_id: uuid.UUID | None = None
    team_name: str | None = None
    cidr: str
    action: str = Field(..., pattern="^(allow|deny)$")
    priority: int = Field(100, ge=1, le=1000)
    description: str | None = None


class IpAclRuleUpdate(BaseModel):
    api_key_id: uuid.UUID | None = None
    team_name: str | None = None
    cidr: str | None = None
    action: str | None = Field(None, pattern="^(allow|deny)$")
    priority: int | None = Field(None, ge=1, le=1000)
    description: str | None = None


class IpAclRuleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID | None
    api_key_id: uuid.UUID | None
    scope_type: str
    team_name: str | None
    cidr: str
    action: str
    priority: int
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IpAclRuleList(BaseModel):
    items: list[IpAclRuleResponse]


class IpAclTestRequest(BaseModel):
    ip: str
    api_key_id: uuid.UUID | None = None
    team_name: str | None = None


class IpAclTestResponse(BaseModel):
    ip: str
    allowed: bool


class KeyRotationEventResponse(BaseModel):
    id: uuid.UUID
    api_key_id: uuid.UUID
    rotated_from_prefix: str
    rotated_to_prefix: str
    triggered_by: str | None
    grace_expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KeyRotationEventList(BaseModel):
    items: list[KeyRotationEventResponse]


class RotateApiKeyRequest(BaseModel):
    grace_hours: int = Field(24, ge=0, le=168)


class RotateApiKeyResponse(BaseModel):
    key_id: uuid.UUID
    key_prefix: str
    key: str
    expires_old_at: datetime | None
