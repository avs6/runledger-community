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


class CapturePolicyScopeUpsert(BaseModel):
    scope_type: str
    scope_id: str
    privacy_mode: str
    sampled_rate: Decimal | None = None


class CapturePolicyScopeResponse(BaseModel):
    scope_type: str
    scope_id: str
    privacy_mode: str
    sampled_rate: Decimal | None

    model_config = {"from_attributes": True}


class CapturePolicyScopeList(BaseModel):
    items: list[CapturePolicyScopeResponse]


class RetentionPreviewResponse(BaseModel):
    privacy_mode: str
    estimated_storage_mb_per_month: str
    fields_captured: list[str]
    fields_redacted: list[str]
    compliance_notes: list[str]


class PiiDetectionResponse(BaseModel):
    type: str
    value: str
    start: int
    end: int
    confidence: str


class PiiTestRequest(BaseModel):
    text: str


class PiiTestResultResponse(BaseModel):
    input_text: str
    detected_pii: list[PiiDetectionResponse]
    redacted_text: str
