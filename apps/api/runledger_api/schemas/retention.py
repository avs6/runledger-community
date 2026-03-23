"""Retention policy schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ResourceType = Literal["runs", "spans", "payloads", "provider_calls"]
ActionType = Literal["delete", "scrub"]
ScopeType = Literal["workspace", "end_user"]


class RetentionPolicyCreate(BaseModel):
    resource_type: ResourceType
    action: ActionType
    scope: ScopeType = "workspace"
    scope_value: str | None = Field(None, max_length=255)
    max_age_days: int | None = Field(None, ge=1, le=3650)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self) -> RetentionPolicyCreate:
        if self.scope == "end_user" and not self.scope_value:
            raise ValueError("scope_value (end_user_id) is required when scope=end_user")
        if self.scope == "workspace" and self.max_age_days is None:
            raise ValueError("max_age_days is required for workspace-scope policies")
        if self.action == "scrub" and self.resource_type not in ("spans", "payloads"):
            raise ValueError("action=scrub is only valid for resource_type=spans or payloads")
        if self.scope == "end_user" and self.scope_value and len(self.scope_value) == 0:
            raise ValueError("scope_value must not be empty")
        return self


class RetentionPolicyUpdate(BaseModel):
    max_age_days: int | None = Field(None, ge=1, le=3650)
    is_active: bool | None = None
    scope_value: str | None = Field(None, max_length=255)


class RetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    resource_type: str
    action: str
    scope: str
    scope_value: str | None
    max_age_days: int | None
    is_active: bool
    created_at: datetime
    last_run_at: datetime | None
    last_purged_count: int | None

    model_config = {"from_attributes": True}


class RetentionPolicyList(BaseModel):
    items: list[RetentionPolicyResponse]
    total: int


class PurgeRequest(BaseModel):
    """Immediate ad-hoc purge. Provide either policy_id OR explicit fields."""

    policy_id: uuid.UUID | None = None
    resource_type: ResourceType | None = None
    action: ActionType | None = None
    scope: ScopeType = "workspace"
    scope_value: str | None = None
    max_age_days: int | None = Field(None, ge=1, le=3650)
    dry_run: bool = False


class PurgeResult(BaseModel):
    resource_type: str
    action: str
    scope: str
    scope_value: str | None
    affected_rows: int
    dry_run: bool
    cutoff: datetime | None
