"""
Pydantic schemas for budget tier CRUD.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BudgetTierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    max_spend_usd: Decimal | None = Field(None, gt=0)
    period_type: str = Field("monthly", pattern="^(daily|monthly|total)$")
    rpm_limit: int | None = Field(None, gt=0)
    tpm_limit: int | None = Field(None, gt=0)
    allowed_models: list[str] | None = None
    is_default: bool = False


class BudgetTierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    max_spend_usd: Decimal | None = Field(None, gt=0)
    period_type: str | None = Field(None, pattern="^(daily|monthly|total)$")
    rpm_limit: int | None = Field(None, gt=0)
    tpm_limit: int | None = Field(None, gt=0)
    allowed_models: list[str] | None = None
    is_default: bool | None = None


class BudgetTierResponse(BaseModel):
    id: str
    name: str
    max_spend_usd: Decimal | None
    period_type: str
    rpm_limit: int | None
    tpm_limit: int | None
    allowed_models: list[str] | None
    is_default: bool
    is_active: bool
    created_at: datetime
    key_count: int = 0

    model_config = {"from_attributes": True}


class BudgetTierList(BaseModel):
    items: list[BudgetTierResponse]
