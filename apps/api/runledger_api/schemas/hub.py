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


class HubModelCostPosture(BaseModel):
    model_id: uuid.UUID
    model_name: str
    provider: str
    input_cost_per_1k: Decimal | None
    output_cost_per_1k: Decimal | None
    active_budget_count: int
    total_budget_limit_usd: Decimal
    current_spend_usd: Decimal
    billing_period_count: int
    chargeback_cost_usd: Decimal
    budgets: list[dict]
    billing_periods: list[dict]


class HubModelGovernanceStatus(BaseModel):
    model_id: uuid.UUID
    model_name: str
    provider: str
    tags: list[str]
    approval_count: int
    recent_approvals: list[dict]
    audit_event_count: int
    recent_audit_events: list[dict]
    tool_policy_count: int
    is_deprecated: bool
    deprecation_notice: str | None
    access_request_count: int


class HubOrgSummary(BaseModel):
    total_models: int
    featured_models: int
    deprecated_models: int
    total_access_requests: int
    providers: list[str]
    workspaces: list[dict]
