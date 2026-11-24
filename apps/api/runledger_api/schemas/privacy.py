"""Pydantic schemas for capture policies / privacy governance (Phase 11)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# The capture modes the pipeline understands (review S-10: any string was accepted and
# silently behaved like METADATA_ONLY).
PrivacyMode = Literal["METADATA_ONLY", "ERRORS_ONLY", "SAMPLED", "FULL"]


def _check_sampled(mode: str, rate: Decimal | None) -> None:
    if mode == "SAMPLED" and rate is None:
        raise ValueError("sampled_rate is required when privacy_mode is SAMPLED")


class CapturePolicyUpsert(BaseModel):
    privacy_mode: PrivacyMode
    sampled_rate: Decimal | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _sampled(self) -> CapturePolicyUpsert:
        _check_sampled(self.privacy_mode, self.sampled_rate)
        return self


class CapturePolicyResponse(BaseModel):
    id: str
    workspace_id: str
    privacy_mode: str
    sampled_rate: Decimal | None
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class CapturePolicyScopeUpsert(BaseModel):
    # Only scopes the ingest pipeline can resolve from a run (review S-09):
    # api_key > user > feature_tag > intent > workspace.
    scope_type: Literal["api_key", "user", "feature_tag", "intent", "workspace"]
    scope_id: str = Field(..., min_length=1, max_length=255)
    privacy_mode: PrivacyMode
    sampled_rate: Decimal | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _sampled(self) -> CapturePolicyScopeUpsert:
        _check_sampled(self.privacy_mode, self.sampled_rate)
        return self


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
