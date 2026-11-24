"""Pydantic schemas for tool registry and security events (Phase 11 + runtime enforcement)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ToolAction = Literal["allow", "audit", "require_approval", "block"]


class ToolRegistryCreate(BaseModel):
    """A catalog entry. ``policy`` is stored as the managed ``registry:<tool>``
    ToolPolicy (priority 50), so the registry and /tool-policies are one system."""

    tool_name: str = Field(..., min_length=1, max_length=200)
    policy: ToolAction = "audit"
    description: str | None = Field(None, max_length=2000)
    # Deprecated: enforcement is always on. Kept so older clients still validate.
    runtime_enforcement: bool | None = None


class ToolRegistryUpdate(BaseModel):
    policy: ToolAction | None = None
    description: str | None = Field(None, max_length=2000)
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
    # The decision the shared evaluator returns for a workspace-wide caller (may come
    # from a /tool-policies rule rather than the registry's own policy).
    effective_action: str | None = None
    effective_policy_name: str | None = None
    policy_id: str | None = None

    model_config = {"from_attributes": True}


class ToolRegistryList(BaseModel):
    items: list[ToolRegistryResponse]


class ToolCheckResponse(BaseModel):
    """Response from GET /tools/check/{tool_name} — used by SDK runtime enforcement."""

    tool_name: str
    policy: str  # allow | audit | require_approval | block (the decision)
    runtime_enforcement: bool  # always True; enforcement is not optional any more
    allowed: bool
    policy_name: str | None = None
    reason: str | None = None


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
