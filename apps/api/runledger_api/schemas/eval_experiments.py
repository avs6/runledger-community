"""Pydantic schemas for eval experiments and datasets."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# ── Dataset ───────────────────────────────────────────────────────────────────


class DatasetItem(BaseModel):
    """One test case. Eval items have ``input``; replay items carry the captured
    ``messages`` of a recorded run (``run_id``)."""

    input: str | None = None
    messages: list[dict[str, Any]] | None = None
    run_id: str | None = None
    expected_output: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _has_content(self) -> DatasetItem:
        if not self.input and not self.messages:
            raise ValueError("a dataset item needs 'input' or 'messages'")
        return self


class DatasetFromRuns(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    run_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)
    # Use each run's recorded response as the expected output (regression replay).
    use_output_as_expected: bool = False


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


ExperimentMode = Literal["eval", "replay"]


class ExperimentModelConfig(BaseModel):
    """A gateway route alias to run, with an optional label and sampling params."""

    model: str = Field(..., min_length=1, max_length=255)
    provider: str | None = None
    label: str | None = None
    params: dict[str, Any] | None = None


class EvalExperimentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    mode: ExperimentMode = "eval"
    dataset_id: uuid.UUID | None = None
    prompt_name: str | None = None
    prompt_version: int | None = None
    evaluator_ids: list[uuid.UUID] = Field(default_factory=list)
    models: list[ExperimentModelConfig] = Field(default_factory=list, max_length=6)


class EvalExperimentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    mode: ExperimentMode | None = None
    dataset_id: uuid.UUID | None = None
    prompt_name: str | None = None
    prompt_version: int | None = None
    evaluator_ids: list[uuid.UUID] | None = None
    models: list[ExperimentModelConfig] | None = Field(None, max_length=6)


class EvalExperimentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    dataset_id: uuid.UUID | None
    name: str
    description: str | None
    mode: str = "eval"
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


class RouteRecommendationRequest(BaseModel):
    # How much score the candidate may lose against the baseline and still win on cost.
    max_score_drop: float = Field(0.02, ge=0, le=1)


class RouteRecommendationResponse(BaseModel):
    recommendation_id: uuid.UUID
    alias: str
    current_model: str
    proposed_model: str
    current_quality: float | None
    proposed_quality: float | None
    est_cost_delta_pct: float | None
    rationale: str


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
