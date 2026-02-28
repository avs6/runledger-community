from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProviderPricingCreate(BaseModel):
    provider: str
    model: str
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    cached_input_cost_per_1m: Decimal | None = None
    effective_from: datetime | None = None  # defaults to NOW() if omitted


class ProviderPricingUpdate(BaseModel):
    input_cost_per_1m: Decimal | None = None
    output_cost_per_1m: Decimal | None = None
    cached_input_cost_per_1m: Decimal | None = None


class ProviderPricingResponse(BaseModel):
    id: uuid.UUID
    provider: str
    model: str
    input_cost_per_1m: Decimal
    output_cost_per_1m: Decimal
    cached_input_cost_per_1m: Decimal | None
    effective_from: datetime
    effective_to: datetime | None
    workspace_id: uuid.UUID | None  # None means global
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderPricingList(BaseModel):
    items: list[ProviderPricingResponse]
