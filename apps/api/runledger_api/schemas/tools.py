"""Pydantic schemas for tool registry and security events (Phase 11 + runtime enforcement)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ToolRegistryCreate(BaseModel):
    tool_name: str
    policy: str = "audit"
    description: str | None = None
    runtime_enforcement: bool = False


class ToolRegistryUpdate(BaseModel):
    policy: str | None = None
    description: str | None = None
    runtime_enforcement: bool | None = None


class ToolRegistryResponse(BaseModel):
    id: str
    workspace_id: str
    tool_name: str
    policy: str
    runtime_enforcement: bool
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolRegistryList(BaseModel):
    items: list[ToolRegistryResponse]


class ToolCheckResponse(BaseModel):
    """Response from GET /tools/check/{tool_name} — used by SDK runtime enforcement."""

    tool_name: str
    policy: str  # allow | audit | block
    runtime_enforcement: bool
    allowed: bool  # False when policy=block and runtime_enforcement=True


class SecurityEventResponse(BaseModel):
    id: str
    workspace_id: str
    event_type: str
    tool_name: str | None
    end_user_id: str | None
    run_id: str | None
    details: dict[str, Any]
    detected_at: datetime

    model_config = {"from_attributes": True}


class SecurityEventList(BaseModel):
    items: list[SecurityEventResponse]
