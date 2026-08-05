"""
Pydantic schemas for budget overrides (temporary increases).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BudgetOverrideCreate(BaseModel):
    override_limit_usd: Decimal = Field(..., gt=0)
    starts_at: datetime
    expires_at: datetime
    reason: str | None = None


class BudgetOverrideResponse(BaseModel):
    id: str
    budget_id: str
    original_limit_usd: Decimal
    override_limit_usd: Decimal
    starts_at: datetime
    expires_at: datetime
    reason: str | None
    approved_by: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetOverrideList(BaseModel):
    items: list[BudgetOverrideResponse]
