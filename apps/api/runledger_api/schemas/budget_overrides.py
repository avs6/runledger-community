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
    require_approval: bool = False


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
    approval_id: str | None = None
    approval_status: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetOverrideList(BaseModel):
    items: list[BudgetOverrideResponse]
