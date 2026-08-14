"""
Pydantic schemas for per-model budget CRUD.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ModelBudgetCreate(BaseModel):
    model_pattern: str = Field(..., min_length=1, max_length=255)
    max_spend_usd: Decimal | None = Field(None, gt=0)
    period_type: str = Field("monthly", pattern="^(daily|monthly|total)$")
    rpm_limit: int | None = Field(None, gt=0)
    tpm_limit: int | None = Field(None, gt=0)
    action: str = Field("block", pattern="^(notify|block|downgrade|throttle|fallback)$")


class ModelBudgetUpdate(BaseModel):
    model_pattern: str | None = Field(None, min_length=1, max_length=255)
    max_spend_usd: Decimal | None = Field(None, gt=0)
    period_type: str | None = Field(None, pattern="^(daily|monthly|total)$")
    rpm_limit: int | None = Field(None, gt=0)
    tpm_limit: int | None = Field(None, gt=0)
    action: str | None = Field(None, pattern="^(notify|block|downgrade|throttle|fallback)$")
    is_active: bool | None = None


class ModelBudgetResponse(BaseModel):
    id: str
    api_key_id: str
    model_pattern: str
    max_spend_usd: Decimal | None
    period_type: str
    rpm_limit: int | None
    tpm_limit: int | None
    action: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelBudgetList(BaseModel):
    items: list[ModelBudgetResponse]
