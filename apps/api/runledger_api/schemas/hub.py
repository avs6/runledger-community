"""Pydantic schemas for the AI Hub model catalog."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class HubModelCreate(BaseModel):
    name: str
    provider: str
    description: str | None = None
    capabilities: list[str] = []
    context_window: int | None = None
    input_cost_per_1k: Decimal | None = None
    output_cost_per_1k: Decimal | None = None
    tags: list[str] = []
    is_featured: bool = False
    is_public: bool = True


class HubModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None
    context_window: int | None = None
    input_cost_per_1k: Decimal | None = None
    output_cost_per_1k: Decimal | None = None
    tags: list[str] | None = None
    is_featured: bool | None = None
    is_deprecated: bool | None = None
    deprecation_notice: str | None = None
    is_public: bool | None = None


class HubModelResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    context_window: int | None
    input_cost_per_1k: Decimal | None
    output_cost_per_1k: Decimal | None
    tags: list[str]
    is_featured: bool
    is_deprecated: bool
    deprecation_notice: str | None
    is_public: bool
    access_request_count: int
    created_at: datetime
    updated_at: datetime


class HubModelList(BaseModel):
    items: list[HubModelResponse]
