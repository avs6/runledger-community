"""Audit event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_api_key_prefix: str | None
    action: str
    target_type: str | None
    target_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventList(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int
