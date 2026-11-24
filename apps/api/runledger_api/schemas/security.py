from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorkspaceSecuritySettingsUpdate(BaseModel):
    """Only settings with a runtime enforcement path (review S-24: residency, callback,
    brand and OIDC-session settings were stored but never read, so they were removed)."""

    required_metadata_fields: list[str] | None = None
    required_metadata_mode: str | None = Field(None, pattern="^(warn|reject)$")


class WorkspaceSecuritySettingsResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    required_metadata_fields: list[str]
    required_metadata_mode: str
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
    # Write-only: "••••••••" when a secret is stored, else null (review S-03).
    client_secret: str | None = None
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
    # Write-only: "••••••••" when a secret is stored, else null (review S-03).
    client_secret: str | None = None
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
    # Non-empty when set: an empty bind password is an unauthenticated bind (S-25).
    bind_password: str | None = Field(None, min_length=1, max_length=1024)
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

    @model_validator(mode="after")
    def _service_bind_needs_password(self) -> LDAPProviderCreate:
        if self.bind_dn and not self.bind_password:
            raise ValueError("bind_password is required when bind_dn is set")
        return self


class LDAPProviderUpdate(BaseModel):
    name: str | None = None
    server_url: str | None = None
    bind_dn: str | None = None
    # Send the mask (or omit) to keep the stored password; never empty (S-25).
    bind_password: str | None = Field(None, min_length=1, max_length=1024)
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
    # Write-only: "••••••••" when a password is stored, else null (review S-03).
    bind_password: str | None = None
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
    username: str = Field(..., min_length=1, max_length=255)
    # Non-empty: an empty password turns an LDAP bind into an anonymous bind.
    password: str = Field(..., min_length=1, max_length=1024)


class IpAclRuleCreate(BaseModel):
    # global: every workspace (platform admins only). team was replaced by access_group.
    scope_type: str = Field(..., pattern="^(global|workspace|api_key|access_group)$")
    api_key_id: uuid.UUID | None = None
    access_group_id: uuid.UUID | None = None
    cidr: str
    action: str = Field(..., pattern="^(allow|deny)$")
    priority: int = Field(100, ge=1, le=1000)
    description: str | None = None


class IpAclRuleUpdate(BaseModel):
    api_key_id: uuid.UUID | None = None
    access_group_id: uuid.UUID | None = None
    cidr: str | None = None
    action: str | None = Field(None, pattern="^(allow|deny)$")
    priority: int | None = Field(None, ge=1, le=1000)
    description: str | None = None


class IpAclRuleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID | None
    api_key_id: uuid.UUID | None
    scope_type: str
    access_group_id: uuid.UUID | None = None
    # Set only on legacy team rules that couldn't be mapped; they never match.
    team_name: str | None = None
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
    user_id: uuid.UUID | None = None


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


# ── Secret inventory (ENH: secret age, rotation, per-secret audit timeline) ──


class SecretRecordResponse(BaseModel):
    id: uuid.UUID
    kind: str
    label: str | None
    owner_table: str
    owner_id: uuid.UUID
    field: str
    key_id: str | None
    # True when the value is wrapped by the current primary key (else re-wrap).
    key_current: bool
    fingerprint: str | None
    rotation_count: int
    rotated_by_label: str | None
    created_at: datetime
    rotated_at: datetime
    age_days: int
    # fresh (< warn), aging (>= warn_days), stale (>= max_age_days)
    age_status: str
    # Secret keys inside a JSON config (rotate sends one value per key).
    fields: list[str] = Field(default_factory=list)


class SecretInventoryResponse(BaseModel):
    items: list[SecretRecordResponse]
    primary_key_id: str
    using_derived_key: bool
    max_age_days: int
    warn_days: int


class SecretRotateRequest(BaseModel):
    """New value for a plain secret, or ``values`` by key for a JSON config."""

    value: str | None = Field(None, min_length=1, max_length=8192)
    values: dict[str, str] | None = None


class SecretRewrapResponse(BaseModel):
    rewrapped: int
    primary_key_id: str
