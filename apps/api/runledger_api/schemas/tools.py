"""Pydantic schemas for tool registry and security events (Phase 11)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ToolRegistryCreate(BaseModel):
    tool_name: str
    policy: str = "audit"
    description: str | None = None


class ToolRegistryUpdate(BaseModel):
    policy: str | None = None
    description: str | None = None


class ToolRegistryResponse(BaseModel):
    id: str
    workspace_id: str
    tool_name: str
    policy: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolRegistryList(BaseModel):
    items: list[ToolRegistryResponse]


class SecurityEventResponse(BaseModel):
    id: str
    workspace_id: str
    event_type: str
    tool_name: str | None
    end_user_id: str | None
    run_id: str | None
    details: dict
    detected_at: datetime

    model_config = {"from_attributes": True}


class SecurityEventList(BaseModel):
    items: list[SecurityEventResponse]
