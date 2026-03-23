"""Pydantic schemas for approval policy workflow."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ApprovalRequestType = Literal[
    "budget_increase",
    "prompt_promote",
    "tool_allow",
    "capture_policy_full",
    "shadow_routing",
]

ApprovalStatus = Literal["pending", "approved", "denied", "cancelled"]


class ApprovalCreate(BaseModel):
    request_type: ApprovalRequestType
    request: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Context for the approval request. Examples: "
            '{"budget_id": "...", "current_limit": 100, "new_limit": 500} for budget_increase; '
            '{"prompt_name": "...", "version": 3, "environment": "production"} for prompt_promote.'
        ),
    )
    reason: str | None = Field(
        None,
        max_length=1000,
        description="Human-readable explanation of why the change is needed.",
    )


class ApprovalDecision(BaseModel):
    note: str | None = Field(None, max_length=1000, description="Optional approver note.")


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    request_type: str
    request: dict[str, Any]
    status: str
    requested_by: str | None
    decided_by: str | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalList(BaseModel):
    items: list[ApprovalResponse]
    total: int


class ApprovalSummary(BaseModel):
    """Count of approvals by status for the dashboard."""

    pending: int
    approved: int
    denied: int
    cancelled: int
