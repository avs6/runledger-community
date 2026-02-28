"""
Pydantic request/response schemas for the Replay harness API.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ExperimentConfig(BaseModel):
    model: str
    label: str | None = None


class DatasetCreate(BaseModel):
    name: str
    run_ids: list[str]
    source: str = "live_runs"


class DatasetResponse(BaseModel):
    id: str
    name: str
    source: str
    run_ids: list[str]
    run_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class DatasetList(BaseModel):
    items: list[DatasetResponse]


class ExperimentCreate(BaseModel):
    dataset_id: str
    name: str
    configs: list[ExperimentConfig]


class ExperimentResponse(BaseModel):
    id: str
    dataset_id: str
    name: str
    configs: list[ExperimentConfig]
    status: str
    estimated_cost_usd: Decimal | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ExperimentList(BaseModel):
    items: list[ExperimentResponse]


class ConfigResult(BaseModel):
    model: str
    label: str | None
    run_count: int
    total_input_tokens: int
    total_output_tokens: int
    projected_cost_usd: Decimal
    avg_cost_per_run: Decimal
    pricing_found: bool


class ConfigDelta(BaseModel):
    config_a: str
    config_b: str
    cost_delta_pct: Decimal | None


class ExperimentResults(BaseModel):
    experiment_id: str
    experiment_name: str
    status: str
    dataset_run_count: int
    configs: list[ConfigResult]
    deltas: list[ConfigDelta]
    completed_at: datetime | None
