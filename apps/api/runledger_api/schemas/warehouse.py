"""Pydantic schemas for Phase 28 — Warehouse Export."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

VALID_RESOURCES = {"runs", "spans", "provider_calls"}
VALID_FORMATS = {"jsonl", "parquet"}
VALID_PROVIDERS = {"s3", "gcs", "r2"}


class WarehouseDestinationCreate(BaseModel):
    name: str
    provider: Literal["s3", "gcs", "r2"]
    bucket: str
    prefix: str = ""
    region: str | None = None
    endpoint_url: str | None = None
    access_key_id: str
    secret_access_key: str
    format: Literal["jsonl", "parquet"] = "jsonl"
    resources: list[str] = ["runs", "spans", "provider_calls"]
    is_active: bool = True

    @field_validator("resources")
    @classmethod
    def validate_resources(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_RESOURCES
        if invalid:
            raise ValueError(f"Invalid resources: {invalid}. Must be from {VALID_RESOURCES}")
        if not v:
            raise ValueError("At least one resource must be specified")
        return v


class WarehouseDestinationUpdate(BaseModel):
    name: str | None = None
    prefix: str | None = None
    region: str | None = None
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    format: Literal["jsonl", "parquet"] | None = None
    resources: list[str] | None = None
    is_active: bool | None = None

    @field_validator("resources")
    @classmethod
    def validate_resources(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        invalid = set(v) - VALID_RESOURCES
        if invalid:
            raise ValueError(f"Invalid resources: {invalid}")
        if not v:
            raise ValueError("At least one resource must be specified")
        return v


class WarehouseDestinationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    provider: str
    bucket: str
    prefix: str
    region: str | None
    endpoint_url: str | None
    access_key_id: str
    # secret_access_key is intentionally excluded (write-only)
    format: str
    resources: list[str]
    is_active: bool
    created_at: datetime
    last_export_at: datetime | None


class WarehouseDestinationList(BaseModel):
    items: list[WarehouseDestinationResponse]
    total: int


class ConnectionTestResult(BaseModel):
    ok: bool
    error: str | None = None


class ExportJobTrigger(BaseModel):
    destination_id: uuid.UUID
    export_date: date | None = None  # defaults to yesterday
    resources: list[str] | None = None  # defaults to destination.resources


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    destination_id: uuid.UUID
    export_date: date
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    resources: list[str]
    file_keys: dict[str, str] | None
    row_counts: dict[str, int] | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ExportJobList(BaseModel):
    items: list[ExportJobResponse]
    total: int
