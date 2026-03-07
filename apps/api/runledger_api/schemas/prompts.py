"""Pydantic schemas for prompt management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    default_environment: str = Field("production", pattern="^(production|staging|dev)$")


class PromptResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    default_environment: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptList(BaseModel):
    items: list[PromptResponse]


class VersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    commit_message: str | None = None
    environment: str = Field("production", pattern="^(production|staging|dev)$")
    model_hint: str | None = None


class VersionResponse(BaseModel):
    id: uuid.UUID
    prompt_id: uuid.UUID
    version: int
    content: str
    variables: Any
    commit_message: str | None
    environment: str
    model_hint: str | None
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
    source_environment: str = Field("staging", pattern="^(production|staging|dev)$")
    target_environment: str = Field("production", pattern="^(production|staging|dev)$")
    commit_message: str | None = None


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
