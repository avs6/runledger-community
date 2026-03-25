"""Pydantic schemas for eval experiments and datasets."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Dataset ───────────────────────────────────────────────────────────────────

class DatasetItem(BaseModel):
    input: str
    expected_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source: str = "manual"
    items: list[DatasetItem] = Field(default_factory=list)


class EvalDatasetUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    items: list[DatasetItem] | None = None


class EvalDatasetResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    source: str
    item_count: int
    items: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvalDatasetList(BaseModel):
    items: list[EvalDatasetResponse]


# ── Experiment ────────────────────────────────────────────────────────────────

class ExperimentModelConfig(BaseModel):
    model: str
    provider: str = "openai"
    label: str | None = None


class EvalExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    dataset_id: uuid.UUID | None = None
    prompt_name: str | None = None
    prompt_version: int | None = None
    evaluator_ids: list[uuid.UUID] = Field(default_factory=list)
    models: list[ExperimentModelConfig] = Field(default_factory=list)


class EvalExperimentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    dataset_id: uuid.UUID | None = None
    prompt_name: str | None = None
    prompt_version: int | None = None
    evaluator_ids: list[uuid.UUID] | None = None
    models: list[ExperimentModelConfig] | None = None


class ModelResult(BaseModel):
    model: str
    provider: str
    label: str | None
    items_run: int
    avg_score: float | None
    score_breakdown: dict[str, float]


class EvalExperimentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None
    name: str
    description: str | None
    prompt_name: str | None
    prompt_version: int | None
    evaluator_ids: list[Any]
    models: list[Any]
    status: str
    results: dict[str, Any] | None
    run_count: int
    scores_created: int
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalExperimentList(BaseModel):
    items: list[EvalExperimentResponse]


# ── GitHub sync ───────────────────────────────────────────────────────────────

class GithubConfigCreate(BaseModel):
    repo: str = Field(..., description="owner/repo")
    branch: str = "main"
    path_prefix: str = "prompts/"
    token: str | None = Field(None, description="GitHub PAT — stored encrypted")
    auto_sync: bool = False


class GithubConfigUpdate(BaseModel):
    repo: str | None = None
    branch: str | None = None
    path_prefix: str | None = None
    token: str | None = None
    auto_sync: bool | None = None


class GithubConfigResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    repo: str
    branch: str
    path_prefix: str
    auto_sync: bool
    last_sync_at: datetime | None
    last_sync_status: str | None
    last_sync_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GithubSyncResult(BaseModel):
    pushed: int
    pulled: int
    skipped: int
    errors: list[str]
    synced_at: datetime
