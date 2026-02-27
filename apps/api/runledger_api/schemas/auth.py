from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from runledger_api.models.tenant import EnvironmentEnum, PlanEnum


class TenantCreate(BaseModel):
    slug: str
    name: str
    plan: PlanEnum = PlanEnum.free


class TenantResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    plan: PlanEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str
    environment: EnvironmentEnum = EnvironmentEnum.dev


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    environment: EnvironmentEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str | None = None
    environment: EnvironmentEnum = EnvironmentEnum.dev
    scopes: list[str] = []


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    key_prefix: str
    name: str | None
    scopes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned only on creation — contains the raw key (shown once)."""

    key: str
