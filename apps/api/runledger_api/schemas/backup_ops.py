from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class BackupRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    trigger_mode: Literal["manual", "scheduled"]
    status: Literal["queued", "running", "success", "failed"]
    backup_scope: str
    target: str | None
    command: str | None
    triggered_by: str | None
    size_bytes: int | None
    checksum: str | None
    output_excerpt: str | None
    error_detail: str | None
    details: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class BackupRunList(BaseModel):
    items: list[BackupRunResponse]
    total: int


class BackupActionResult(BaseModel):
    ok: bool
    message: str
    details: dict[str, Any] | None = None


class BackupTargetConfigBase(BaseModel):
    provider: Literal["s3"] = "s3"
    bucket: str
    prefix: str | None = None
    region: str | None = None
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    force_path_style: bool = True
    schedule_enabled: bool = False
    cadence: Literal["daily", "weekly", "monthly"] = "daily"
    run_hour_utc: int = 2
    retention_days: int = 30
    include_memory_db: bool = True
    include_qdrant: bool = False
    include_kuzu: bool = True
    include_skills: bool = True
    encryption_mode: Literal["none", "server_side"] = "server_side"


class BackupTargetConfigUpdate(BackupTargetConfigBase):
    pass


class BackupTargetConfigResponse(BackupTargetConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BackupSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    backup_run_id: uuid.UUID
    snapshot_type: str
    bucket: str
    prefix: str | None
    manifest_key: str | None
    checksum: str | None
    total_size_bytes: int | None
    artifact_count: int
    artifacts: dict[str, Any] | None
    integrity_status: str
    verified_at: datetime | None
    created_at: datetime


class BackupSnapshotList(BaseModel):
    items: list[BackupSnapshotResponse]
    total: int
