"""Pydantic schemas for pricing intelligence: contracts and credits."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from typing import Any

from pydantic import BaseModel, Field

# ── Pricing contracts ──────────────────────────────────────────────────────────


class PricingContractCreate(BaseModel):
    provider: str
    model: str | None = None  # NULL = all models for this provider
    discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    fixed_input_per_1m: Decimal | None = None
    fixed_output_per_1m: Decimal | None = None
    effective_from: datetime
    effective_until: datetime | None = None
    notes: str | None = None


class PricingContractUpdate(BaseModel):
    discount_pct: Decimal | None = Field(default=None, ge=0, le=100)
    fixed_input_per_1m: Decimal | None = None
    fixed_output_per_1m: Decimal | None = None
    effective_until: datetime | None = None
    notes: str | None = None
    is_active: bool | None = None


class PricingContractResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: str
    model: str | None
    discount_pct: Decimal | None
    fixed_input_per_1m: Decimal | None
    fixed_output_per_1m: Decimal | None
    effective_from: datetime
    effective_until: datetime | None
    notes: str | None
    created_by: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PricingContractList(BaseModel):
    items: list[PricingContractResponse]
    total: int


# ── Pricing credits ────────────────────────────────────────────────────────────


class PricingCreditCreate(BaseModel):
    name: str
    credit_type: str = Field(..., pattern="^(prepaid_tokens|credit_bundle|minimum_commitment)$")
    amount_usd: Decimal = Field(..., gt=0)
    source: str = Field("manual", pattern="^(manual|stripe|negotiated)$")
    effective_from: datetime
    effective_until: datetime | None = None
    priority: int = Field(100, ge=1, le=9999)


class PricingCreditUpdate(BaseModel):
    name: str | None = None
    remaining_usd: Decimal | None = Field(default=None, ge=0)
    effective_until: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=9999)
    is_active: bool | None = None


class PricingCreditResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    credit_type: str
    amount_usd: Decimal
    remaining_usd: Decimal
    source: str
    effective_from: datetime
    effective_until: datetime | None
    priority: int
    is_active: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PricingCreditList(BaseModel):
    items: list[PricingCreditResponse]
    total: int


class CreditApplicationResult(BaseModel):
    applied: Decimal
    remaining_cost: Decimal
    credits_used: list[dict[str, Any]]


# ── Sync config ────────────────────────────────────────────────────────────────


class PricingSyncConfigResponse(BaseModel):
    sync_enabled: bool
    excluded_providers: list[str]
    excluded_models: list[str]
    force_update: bool
    last_sync_at: datetime | None
    last_sync_result: dict[str, Any] | None
    updated_by: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PricingSyncConfigUpdate(BaseModel):
    sync_enabled: bool | None = None
    excluded_providers: list[str] | None = None
    excluded_models: list[str] | None = None
    force_update: bool | None = None


class SyncTriggerRequest(BaseModel):
    dry_run: bool = False
    force: bool = False
    providers: list[str] | None = None
    models: list[str] | None = None
