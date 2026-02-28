"""Pydantic schemas for capture policies / privacy governance (Phase 11)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CapturePolicyUpsert(BaseModel):
    privacy_mode: str
    sampled_rate: Decimal | None = None


class CapturePolicyResponse(BaseModel):
    id: str
    workspace_id: str
    privacy_mode: str
    sampled_rate: Decimal | None
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
