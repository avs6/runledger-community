"""Pydantic schemas for prompt management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

_ENV = "^(production|staging|dev)$"


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    default_environment: str = Field("dev", pattern=_ENV)
    # Score gate for promotion to production (ENH): the source version must have an
    # average score >= this value (from an experiment or scored runs).
    promotion_min_score: float | None = Field(None, ge=0, le=1)
    promotion_score_name: str | None = Field(None, max_length=255)


class PromptUpdate(BaseModel):
    description: str | None = None
    default_environment: str | None = Field(None, pattern=_ENV)
    promotion_min_score: float | None = Field(None, ge=0, le=1)
    promotion_score_name: str | None = Field(None, max_length=255)
    clear_promotion_gate: bool = False


class PromptResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    default_environment: str
    promotion_min_score: float | None = None
    promotion_score_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptList(BaseModel):
    items: list[PromptResponse]


class VersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    commit_message: str | None = None
    # New versions land in dev. Writing straight to production needs an approved
    # ``prompt_promote`` approval for this prompt (review B-02).
    environment: str = Field("dev", pattern=_ENV)
    model_hint: str | None = None
    approval_id: uuid.UUID | None = None


class VersionResponse(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    version: int
    content: str
    variables: Any
    commit_message: str | None
    environment: str
    model_hint: str | None
    approval_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionList(BaseModel):
    items: list[VersionResponse]


class PromptRender(BaseModel):
    """Rendered prompt with variable substitution applied."""

    content: str
    version: int
    environment: str
    model_hint: str | None
    variables: Any


class PromoteRequest(BaseModel):
    source_environment: str = Field("staging", pattern=_ENV)
    target_environment: str = Field("production", pattern=_ENV)
    commit_message: str | None = None
    approval_id: uuid.UUID | None = None


class PromotionRequestCreate(BaseModel):
    """Ask for approval to promote a version to production (review B-03)."""

    source_environment: str = Field("staging", pattern=_ENV)
    version: int | None = Field(None, ge=1)
    reason: str | None = Field(None, max_length=2000)


class PromotionApproval(BaseModel):
    id: uuid.UUID
    status: str
    source_environment: str | None = None
    version: int | None = None
    requested_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None
    used_by_version: int | None = None
    created_at: datetime


class PromotionApprovalList(BaseModel):
    items: list[PromotionApproval]


class VersionScore(BaseModel):
    version: int
    score: float | None
    source: str | None  # "experiment" | "runs" | None
    sample_size: int
    min_score: float | None
    passes_gate: bool | None


class DiffLine(BaseModel):
    kind: str  # "context" | "add" | "remove" | "hunk"
    text: str
    old_line: int | None = None
    new_line: int | None = None


class PromptDiff(BaseModel):
    name: str
    from_version: int
    to_version: int
    from_environment: str
    to_environment: str
    added: int
    removed: int
    lines: list[DiffLine]
    model_hint_changed: bool
    variables_changed: bool


class VersionMetrics(BaseModel):
    version: int
    environment: str
    run_count: int
    avg_cost_usd: float | None
    avg_score: float | None
    commit_message: str | None
    created_at: datetime


class PromptMetrics(BaseModel):
    items: list[VersionMetrics]
