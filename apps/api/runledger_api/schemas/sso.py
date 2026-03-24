from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

# ── SSO Config ────────────────────────────────────────────────────────────────


class SsoConfigCreate(BaseModel):
    provider: str  # e.g. "google", "okta", "azure"
    issuer_url: str
    client_id: str
    client_secret: str  # plaintext; encrypted at rest
    scopes: str = "openid email profile"
    default_role: str = "member"
    enabled: bool = True


class SsoConfigUpdate(BaseModel):
    issuer_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scopes: str | None = None
    default_role: str | None = None
    enabled: bool | None = None


class SsoConfigResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    provider: str
    issuer_url: str
    client_id: str
    scopes: str
    default_role: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SsoConfigList(BaseModel):
    items: list[SsoConfigResponse]
    total: int


# ── SSO auth flow ─────────────────────────────────────────────────────────────


class SsoAuthorizeResponse(BaseModel):
    authorization_url: str


class SsoExchangeRequest(BaseModel):
    token: str  # short-lived Redis token from callback redirect


# ── SCIM Token ────────────────────────────────────────────────────────────────


class ScimTokenCreate(BaseModel):
    label: str = "SCIM provisioning"


class ScimTokenResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    token_prefix: str
    label: str
    enabled: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScimTokenCreated(ScimTokenResponse):
    """Returned only at creation — includes raw token."""

    raw_token: str


class ScimTokenList(BaseModel):
    items: list[ScimTokenResponse]
    total: int


# ── SCIM 2.0 protocol schemas ─────────────────────────────────────────────────


class ScimName(BaseModel):
    formatted: str | None = None
    givenName: str | None = None
    familyName: str | None = None


class ScimEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True


class ScimUserRequest(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: ScimName | None = None
    emails: list[ScimEmail] = []
    active: bool = True
    externalId: str | None = None

    @field_validator("userName")
    @classmethod
    def username_must_have_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("SCIM userName must be an email address")
        return v


class ScimUserResponse(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: str
    userName: str
    name: ScimName
    emails: list[ScimEmail]
    active: bool
    meta: dict[str, str]


class ScimListResponse(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int
    Resources: list[ScimUserResponse]


class ScimPatchOp(BaseModel):
    op: str  # "replace", "add", "remove"
    path: str | None = None
    value: dict[str, object] | None = None


class ScimPatchRequest(BaseModel):
    schemas: list[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: list[ScimPatchOp]
