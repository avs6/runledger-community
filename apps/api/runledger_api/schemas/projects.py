"""Pydantic schemas for projects and team-managed models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    owner: str | None = None
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    config: dict[str, Any] = {}


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    owner: str | None
    budget_usd: Decimal | None
    budget_period: str | None
    is_active: bool
    config: dict[str, Any]
    key_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectList(BaseModel):
    items: list[ProjectResponse]


class ProjectKeyAssign(BaseModel):
    api_key_id: uuid.UUID


class ProjectKeyResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    api_key_id: uuid.UUID
    created_at: datetime


class ProjectKeyList(BaseModel):
    items: list[ProjectKeyResponse]


class TeamModelCreate(BaseModel):
    team_name: str
    model_name: str
    provider: str | None = None
    api_base_url: str | None = None
    description: str | None = None
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    logging_opt_out: bool = False
    config: dict[str, Any] = {}


class TeamModelUpdate(BaseModel):
    model_name: str | None = None
    provider: str | None = None
    api_base_url: str | None = None
    description: str | None = None
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    is_active: bool | None = None
    logging_opt_out: bool | None = None
    config: dict[str, Any] | None = None


class TeamModelResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    team_name: str
    model_name: str
    provider: str | None
    api_base_url: str | None
    description: str | None
    budget_usd: Decimal | None
    budget_period: str | None
    is_active: bool
    logging_opt_out: bool
    health_status: str
    last_health_check: datetime | None
    total_calls: int
    total_cost_usd: Decimal
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TeamModelList(BaseModel):
    items: list[TeamModelResponse]
