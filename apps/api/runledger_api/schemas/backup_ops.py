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
