"""Schemas for workspace control surfaces."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

TagMatchType = Literal["equals", "contains", "regex", "prefix", "suffix"]
ToolPolicyAction = Literal["allow", "audit", "block", "require_approval", "deny"]
ScopeType = Literal["workspace", "access_group", "group", "search_tool"]


class TagCreate(BaseModel):
    category: str = Field(..., max_length=50)
    key: str = Field(..., max_length=100)
    value: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=2000)
    parent_tag_id: uuid.UUID | None = None
    is_active: bool = True


class TagUpdate(BaseModel):
    category: str | None = Field(None, max_length=50)
    key: str | None = Field(None, max_length=100)
    value: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    parent_tag_id: uuid.UUID | None = None
    is_active: bool | None = None


class TagResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    category: str
    key: str
    value: str
    description: str | None = None
    parent_tag_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TagTreeNode(TagResponse):
    children: list["TagTreeNode"] = Field(default_factory=list)


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int


class TagTreeResponse(BaseModel):
    items: list[TagTreeNode]
    total: int


class AutoTaggingRuleCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    match_type: TagMatchType
    match_field: str = Field(..., max_length=100)
    match_pattern: str = Field(..., max_length=500)
    tag_key: str = Field(..., max_length=100)
    tag_value: str = Field(..., max_length=255)
    priority: int = Field(100, ge=0, le=10000)
    is_active: bool = True


class AutoTaggingRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    match_type: TagMatchType | None = None
    match_field: str | None = Field(None, max_length=100)
    match_pattern: str | None = Field(None, max_length=500)
    tag_key: str | None = Field(None, max_length=100)
    tag_value: str | None = Field(None, max_length=255)
    priority: int | None = Field(None, ge=0, le=10000)
    is_active: bool | None = None


class AutoTaggingRuleResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    match_type: str
    match_field: str
    match_pattern: str
    tag_key: str
    tag_value: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AutoTaggingRuleListResponse(BaseModel):
    items: list[AutoTaggingRuleResponse]
    total: int


class AutoTaggingSimulationRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


class AutoTaggingSimulationMatch(BaseModel):
    rule_id: uuid.UUID
    rule_name: str
    tag_key: str
    tag_value: str
    priority: int


class AutoTaggingSimulationResponse(BaseModel):
    matched: list[AutoTaggingSimulationMatch]
    applied_tags: dict[str, str]


class SearchToolCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    tool_type: str = Field(..., max_length=50)
    endpoint_url: str | None = Field(None, max_length=5000)
    auth_type: str | None = Field(None, max_length=50)
    auth_config: dict[str, Any] = Field(default_factory=dict)
    rate_limit_rpm: int | None = Field(None, ge=0)
    cost_per_query: Decimal = Decimal("0")
    is_active: bool = True
    avg_quality_score: Decimal | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class SearchToolUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    tool_type: str | None = Field(None, max_length=50)
    endpoint_url: str | None = Field(None, max_length=5000)
    auth_type: str | None = Field(None, max_length=50)
    auth_config: dict[str, Any] | None = None
    rate_limit_rpm: int | None = Field(None, ge=0)
    cost_per_query: Decimal | None = None
    is_active: bool | None = None
    avg_quality_score: Decimal | None = None
    config: dict[str, Any] | None = None


class SearchToolResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    tool_type: str
    endpoint_url: str | None = None
    auth_type: str | None = None
    auth_config: dict[str, Any]
    rate_limit_rpm: int | None = None
    cost_per_query: Decimal
    is_active: bool
    total_queries: int
    total_cost_usd: Decimal
    avg_quality_score: Decimal | None = None
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    policy_count: int = 0


class SearchToolListResponse(BaseModel):
    items: list[SearchToolResponse]
    total: int


class SearchToolPolicySummary(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    policies: list["ToolPolicyResponse"]


class ToolPolicyCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    tool_name: str = Field(..., max_length=200)
    action: ToolPolicyAction
    condition_type: str | None = Field(None, max_length=50)
    condition_config: dict[str, Any] = Field(default_factory=dict)
    scope_type: ScopeType = "workspace"
    scope_id: uuid.UUID | None = None
    priority: int = Field(100, ge=0, le=10000)
    is_active: bool = True


class ToolPolicyUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    tool_name: str | None = Field(None, max_length=200)
    action: ToolPolicyAction | None = None
    condition_type: str | None = Field(None, max_length=50)
    condition_config: dict[str, Any] | None = None
    scope_type: ScopeType | None = None
    scope_id: uuid.UUID | None = None
    priority: int | None = Field(None, ge=0, le=10000)
    is_active: bool | None = None


class ToolPolicyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    tool_name: str
    action: str
    condition_type: str | None = None
    condition_config: dict[str, Any]
    scope_type: str
    scope_id: uuid.UUID | None = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToolPolicyListResponse(BaseModel):
    items: list[ToolPolicyResponse]
    total: int


class ToolPolicySimulationRequest(BaseModel):
    tool_name: str = Field(..., max_length=200)
    tool_type: str | None = Field(None, max_length=50)
    risk_score: int | None = Field(None, ge=0, le=100)
    end_user_id: str | None = Field(None, max_length=255)
    feature_tag: str | None = Field(None, max_length=255)
    context: dict[str, Any] = Field(default_factory=dict)


class ToolPolicySimulationResponse(BaseModel):
    tool_name: str
    final_action: str
    matched_policy_ids: list[uuid.UUID]
    matched_policy_names: list[str]
    reasons: list[str]


class ToolUsageAnalyticsItem(BaseModel):
    tool_name: str
    total_calls: int
    allowed_calls: int
    denied_calls: int
    audited_calls: int
    success_count: int
    failure_count: int
    avg_duration_ms: float | None = None
    avg_risk_score: float | None = None


class ToolUsageAnalyticsResponse(BaseModel):
    items: list[ToolUsageAnalyticsItem]
    total_calls: int
    unique_tools: int


class AccessGroupCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = Field(None, max_length=2000)
    permissions: dict[str, Any] = Field(default_factory=dict)
    budget_usd: Decimal | None = None
    budget_period: str | None = Field(None, max_length=20)
    guardrail_profile: str | None = Field(None, max_length=100)
    is_active: bool = True


class AccessGroupUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    permissions: dict[str, Any] | None = None
    budget_usd: Decimal | None = None
    budget_period: str | None = Field(None, max_length=20)
    guardrail_profile: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class AccessGroupMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: str = Field("member", max_length=50)


class AccessGroupMemberResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime


class AccessGroupResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    permissions: dict[str, Any]
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    guardrail_profile: str | None = None
    is_active: bool
    member_count: int
    created_at: datetime
    updated_at: datetime


class AccessGroupListResponse(BaseModel):
    items: list[AccessGroupResponse]
    total: int


class AccessGroupMemberListResponse(BaseModel):
    items: list[AccessGroupMemberResponse]
    total: int


class AccessGroupDashboardItem(BaseModel):
    id: uuid.UUID
    name: str
    member_count: int
    budget_usd: Decimal | None = None
    budget_period: str | None = None
    guardrail_profile: str | None = None
    dashboard_filters: dict[str, Any]
    is_active: bool


class AccessGroupDashboardResponse(BaseModel):
    groups: list[AccessGroupDashboardItem]
    selected_group_id: uuid.UUID | None = None


class ResponseCacheConfigCreate(BaseModel):
    name: str = Field(..., max_length=200)
    is_enabled: bool = True
    ttl_seconds: int = Field(3600, ge=1)
    max_entries: int = Field(10000, ge=1)
    eviction_policy: str = Field("lru", max_length=20)
    similarity_threshold: Decimal = Field(Decimal("0.95"), ge=0, le=1)
    embedding_model: str | None = Field(None, max_length=100)
    scope_models: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ResponseCacheConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    is_enabled: bool | None = None
    ttl_seconds: int | None = Field(None, ge=1)
    max_entries: int | None = Field(None, ge=1)
    eviction_policy: str | None = Field(None, max_length=20)
    similarity_threshold: Decimal | None = Field(None, ge=0, le=1)
    embedding_model: str | None = Field(None, max_length=100)
    scope_models: list[str] | None = None
    config: dict[str, Any] | None = None


class ResponseCacheConfigResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    is_enabled: bool
    ttl_seconds: int
    max_entries: int
    eviction_policy: str
    similarity_threshold: Decimal
    embedding_model: str | None = None
    scope_models: list[str]
    total_hits: int
    total_misses: int
    total_savings_usd: Decimal
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ResponseCacheConfigListResponse(BaseModel):
    items: list[ResponseCacheConfigResponse]
    total: int


class ResponseCacheStatsResponse(BaseModel):
    config_count: int
    enabled_config_count: int
    total_hits: int
    total_misses: int
    hit_rate: float | None = None
    total_savings_usd: Decimal
    live_entry_count: int
    top_models: list[dict[str, Any]]
