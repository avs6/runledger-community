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
    claim_mappings: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class OIDCProviderUpdate(BaseModel):
    name: str | None = None
    issuer_url: str | None = None
    audience: str | None = None
    discovery_url: str | None = None
    jwks_uri: str | None = None
    claim_mappings: dict[str, Any] | None = None
    is_active: bool | None = None


class OIDCProviderResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    issuer_url: str
    audience: str | None
    discovery_url: str | None
    jwks_uri: str | None
    claim_mappings: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OIDCProviderList(BaseModel):
    items: list[OIDCProviderResponse]


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
