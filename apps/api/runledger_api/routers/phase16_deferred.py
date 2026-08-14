"""Deferred Phase 16 management routers."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.access_groups import AccessGroup, AccessGroupMember
from runledger_api.models.cache_config import ResponseCacheConfig
from runledger_api.models.events import ToolCall
from runledger_api.models.gateway import PromptCache
from runledger_api.models.search_tools import SearchTool
from runledger_api.models.tags import AutoTaggingRule, Tag
from runledger_api.models.tenant import Workspace
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.schemas.phase16_deferred import (
    AccessGroupCreate,
    AccessGroupDashboardItem,
    AccessGroupDashboardResponse,
    AccessGroupListResponse,
    AccessGroupMemberCreate,
    AccessGroupMemberListResponse,
    AccessGroupMemberResponse,
    AccessGroupResponse,
    AccessGroupUpdate,
    AutoTaggingRuleCreate,
    AutoTaggingRuleListResponse,
    AutoTaggingRuleResponse,
    AutoTaggingRuleUpdate,
    AutoTaggingSimulationMatch,
    AutoTaggingSimulationRequest,
    AutoTaggingSimulationResponse,
    ResponseCacheConfigCreate,
    ResponseCacheConfigListResponse,
    ResponseCacheConfigResponse,
    ResponseCacheConfigUpdate,
    ResponseCacheStatsResponse,
    SearchToolCreate,
    SearchToolListResponse,
    SearchToolPolicySummary,
    SearchToolResponse,
    SearchToolUpdate,
    TagCreate,
    TagListResponse,
    TagResponse,
    TagTreeNode,
    TagTreeResponse,
    TagUpdate,
    ToolPolicyCreate,
    ToolPolicyListResponse,
    ToolPolicyResponse,
    ToolPolicySimulationRequest,
    ToolPolicySimulationResponse,
    ToolPolicyUpdate,
    ToolUsageAnalyticsItem,
    ToolUsageAnalyticsResponse,
)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]

tags_router = APIRouter(prefix="/tags", tags=["tags"])
search_tools_router = APIRouter(prefix="/search-tools", tags=["search-tools"])
tool_policies_router = APIRouter(prefix="/tool-policies", tags=["tool-policies"])
access_groups_router = APIRouter(prefix="/access-groups", tags=["access-groups"])
response_cache_router = APIRouter(prefix="/response-cache", tags=["response-cache"])


def _tag_to_response(tag: Tag) -> TagResponse:
    return TagResponse(
        id=tag.id,
        workspace_id=tag.workspace_id,
        category=tag.category,
        key=tag.key,
        value=tag.value,
        description=tag.description,
        parent_tag_id=tag.parent_tag_id,
        is_active=tag.is_active,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


def _rule_to_response(rule: AutoTaggingRule) -> AutoTaggingRuleResponse:
    return AutoTaggingRuleResponse(
        id=rule.id,
        workspace_id=rule.workspace_id,
        name=rule.name,
        description=rule.description,
        match_type=rule.match_type,
        match_field=rule.match_field,
        match_pattern=rule.match_pattern,
        tag_key=rule.tag_key,
        tag_value=rule.tag_value,
        priority=rule.priority,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _policy_to_response(policy: ToolPolicy) -> ToolPolicyResponse:
    return ToolPolicyResponse(
        id=policy.id,
        workspace_id=policy.workspace_id,
        name=policy.name,
        description=policy.description,
        tool_name=policy.tool_name,
        action=policy.action,
        condition_type=policy.condition_type,
        condition_config=policy.condition_config or {},
        scope_type=policy.scope_type,
        scope_id=policy.scope_id,
        priority=policy.priority,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


def _search_tool_to_response(tool: SearchTool, policy_count: int = 0) -> SearchToolResponse:
    return SearchToolResponse(
        id=tool.id,
        workspace_id=tool.workspace_id,
        name=tool.name,
        description=tool.description,
        tool_type=tool.tool_type,
        endpoint_url=tool.endpoint_url,
        auth_type=tool.auth_type,
        auth_config=tool.auth_config or {},
        rate_limit_rpm=tool.rate_limit_rpm,
        cost_per_query=tool.cost_per_query,
        is_active=tool.is_active,
        total_queries=tool.total_queries,
        total_cost_usd=tool.total_cost_usd,
        avg_quality_score=tool.avg_quality_score,
        config=tool.config or {},
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        policy_count=policy_count,
    )


def _group_to_response(group: AccessGroup) -> AccessGroupResponse:
    return AccessGroupResponse(
        id=group.id,
        workspace_id=group.workspace_id,
        name=group.name,
        description=group.description,
        permissions=group.permissions or {},
        budget_usd=group.budget_usd,
        budget_period=group.budget_period,
        guardrail_profile=group.guardrail_profile,
        is_active=group.is_active,
        member_count=group.member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _member_to_response(member: AccessGroupMember) -> AccessGroupMemberResponse:
    return AccessGroupMemberResponse(
        id=member.id,
        group_id=member.group_id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at,
    )


def _cache_to_response(config: ResponseCacheConfig) -> ResponseCacheConfigResponse:
    return ResponseCacheConfigResponse(
        id=config.id,
        workspace_id=config.workspace_id,
        name=config.name,
        is_enabled=config.is_enabled,
        ttl_seconds=config.ttl_seconds,
        max_entries=config.max_entries,
        eviction_policy=config.eviction_policy,
        similarity_threshold=config.similarity_threshold,
        embedding_model=config.embedding_model,
        scope_models=config.scope_models or [],
        total_hits=config.total_hits,
        total_misses=config.total_misses,
        total_savings_usd=config.total_savings_usd,
        config=config.config or {},
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _match_rule(match_type: str, pattern: str, value: str | None) -> bool:
    candidate = value or ""
    if match_type == "equals":
        return candidate == pattern
    if match_type == "contains":
        return pattern.lower() in candidate.lower()
    if match_type == "prefix":
        return candidate.lower().startswith(pattern.lower())
    if match_type == "suffix":
        return candidate.lower().endswith(pattern.lower())
    if match_type == "regex":
        return bool(re.search(pattern, candidate))
    return False


def _policy_matches(policy: ToolPolicy, request: ToolPolicySimulationRequest) -> tuple[bool, str]:
    if policy.tool_name not in {"*", request.tool_name}:
        return False, "tool mismatch"

    condition = policy.condition_type or "all"
    config = policy.condition_config or {}
    if condition == "all":
        return True, "global policy"
    if condition == "risk_score_gte":
        threshold = int(config.get("threshold", 0))
        return (request.risk_score or 0) >= threshold, f"risk_score>={threshold}"
    if condition == "tool_type":
        expected = str(config.get("tool_type", ""))
        return request.tool_type == expected, f"tool_type={expected}"
    if condition == "end_user":
        expected = str(config.get("end_user_id", ""))
        return request.end_user_id == expected, f"end_user_id={expected}"
    if condition == "feature_tag":
        expected = str(config.get("feature_tag", ""))
        return request.feature_tag == expected, f"feature_tag={expected}"
    if condition == "context_equals":
        key = str(config.get("key", ""))
        expected = config.get("value")
        return request.context.get(key) == expected, f"context.{key}={expected}"
    return False, f"unsupported condition:{condition}"


async def _get_policy_count(db: AsyncSession, workspace_id: uuid.UUID, tool_name: str) -> int:
    result = await db.execute(
        select(func.count(ToolPolicy.id)).where(
            ToolPolicy.workspace_id == workspace_id,
            ToolPolicy.tool_name.in_([tool_name, "*"]),
            ToolPolicy.is_active.is_(True),
        )
    )
    return result.scalar() or 0


async def _get_group_or_404(db: AsyncSession, workspace_id: uuid.UUID, group_id: uuid.UUID) -> AccessGroup:
    group = (
        await db.execute(
            select(AccessGroup).where(
                AccessGroup.id == group_id,
                AccessGroup.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Access group not found")
    return group


@tags_router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_tag(body: TagCreate, ws: WorkspaceDep, db: DbDep) -> TagResponse:
    tag = Tag(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        category=body.category,
        key=body.key,
        value=body.value,
        description=body.description,
        parent_tag_id=body.parent_tag_id,
        is_active=body.is_active,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return _tag_to_response(tag)


@tags_router.get("", response_model=TagListResponse, dependencies=[Depends(analytics_rate_limit)])
async def list_tags(
    ws: WorkspaceDep,
    db: DbDep,
    category: str | None = None,
    include_inactive: bool = False,
) -> TagListResponse:
    q = select(Tag).where(Tag.workspace_id == ws.id)
    if category:
        q = q.where(Tag.category == category)
    if not include_inactive:
        q = q.where(Tag.is_active.is_(True))
    rows = (await db.execute(q.order_by(Tag.category, Tag.key, Tag.value))).scalars().all()
    return TagListResponse(items=[_tag_to_response(tag) for tag in rows], total=len(rows))


@tags_router.get("/tree", response_model=TagTreeResponse, dependencies=[Depends(analytics_rate_limit)])
async def get_tag_tree(
    ws: WorkspaceDep,
    db: DbDep,
    category: str | None = None,
) -> TagTreeResponse:
    q = select(Tag).where(Tag.workspace_id == ws.id, Tag.is_active.is_(True))
    if category:
        q = q.where(Tag.category == category)
    rows = (await db.execute(q.order_by(Tag.category, Tag.key, Tag.value))).scalars().all()
    by_parent: dict[uuid.UUID | None, list[Tag]] = defaultdict(list)
    for row in rows:
        by_parent[row.parent_tag_id].append(row)

    def build(parent_id: uuid.UUID | None) -> list[TagTreeNode]:
        return [
            TagTreeNode(**_tag_to_response(item).model_dump(), children=build(item.id))
            for item in by_parent.get(parent_id, [])
        ]

    return TagTreeResponse(items=build(None), total=len(rows))


@tags_router.put(
    "/{tag_id}",
    response_model=TagResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_tag(tag_id: uuid.UUID, body: TagUpdate, ws: WorkspaceDep, db: DbDep) -> TagResponse:
    tag = (
        await db.execute(
            select(Tag).where(Tag.id == tag_id, Tag.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    tag.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(tag)
    return _tag_to_response(tag)


@tags_router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def delete_tag(tag_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> Response:
    tag = (
        await db.execute(
            select(Tag).where(Tag.id == tag_id, Tag.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tag not found")
    tag.is_active = False
    tag.updated_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@tags_router.post(
    "/auto-rules",
    response_model=AutoTaggingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_auto_tag_rule(
    body: AutoTaggingRuleCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AutoTaggingRuleResponse:
    rule = AutoTaggingRule(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        match_type=body.match_type,
        match_field=body.match_field,
        match_pattern=body.match_pattern,
        tag_key=body.tag_key,
        tag_value=body.tag_value,
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_response(rule)


@tags_router.get(
    "/auto-rules",
    response_model=AutoTaggingRuleListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_auto_tag_rules(ws: WorkspaceDep, db: DbDep) -> AutoTaggingRuleListResponse:
    rows = (
        await db.execute(
            select(AutoTaggingRule)
            .where(AutoTaggingRule.workspace_id == ws.id)
            .order_by(AutoTaggingRule.priority.asc(), AutoTaggingRule.created_at.desc())
        )
    ).scalars().all()
    return AutoTaggingRuleListResponse(
        items=[_rule_to_response(rule) for rule in rows],
        total=len(rows),
    )


@tags_router.put(
    "/auto-rules/{rule_id}",
    response_model=AutoTaggingRuleResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_auto_tag_rule(
    rule_id: uuid.UUID,
    body: AutoTaggingRuleUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AutoTaggingRuleResponse:
    rule = (
        await db.execute(
            select(AutoTaggingRule).where(
                AutoTaggingRule.id == rule_id,
                AutoTaggingRule.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auto-tagging rule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_response(rule)


@tags_router.post(
    "/auto-rules/simulate",
    response_model=AutoTaggingSimulationResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def simulate_auto_tagging(
    body: AutoTaggingSimulationRequest,
    ws: WorkspaceDep,
    db: DbDep,
) -> AutoTaggingSimulationResponse:
    rows = (
        await db.execute(
            select(AutoTaggingRule)
            .where(
                AutoTaggingRule.workspace_id == ws.id,
                AutoTaggingRule.is_active.is_(True),
            )
            .order_by(AutoTaggingRule.priority.asc(), AutoTaggingRule.created_at.asc())
        )
    ).scalars().all()
    matched: list[AutoTaggingSimulationMatch] = []
    applied_tags: dict[str, str] = {}
    for rule in rows:
        if _match_rule(rule.match_type, rule.match_pattern, body.fields.get(rule.match_field)):
            matched.append(
                AutoTaggingSimulationMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    tag_key=rule.tag_key,
                    tag_value=rule.tag_value,
                    priority=rule.priority,
                )
            )
            applied_tags[rule.tag_key] = rule.tag_value
    return AutoTaggingSimulationResponse(matched=matched, applied_tags=applied_tags)


@search_tools_router.post(
    "",
    response_model=SearchToolResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_search_tool(body: SearchToolCreate, ws: WorkspaceDep, db: DbDep) -> SearchToolResponse:
    tool = SearchTool(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        tool_type=body.tool_type,
        endpoint_url=body.endpoint_url,
        auth_type=body.auth_type,
        auth_config=body.auth_config,
        rate_limit_rpm=body.rate_limit_rpm,
        cost_per_query=body.cost_per_query,
        is_active=body.is_active,
        avg_quality_score=body.avg_quality_score,
        config=body.config,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return _search_tool_to_response(tool)


@search_tools_router.get(
    "",
    response_model=SearchToolListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_search_tools(
    ws: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = False,
) -> SearchToolListResponse:
    q = select(SearchTool).where(SearchTool.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(SearchTool.is_active.is_(True))
    rows = (await db.execute(q.order_by(SearchTool.name))).scalars().all()
    items = []
    for row in rows:
        items.append(_search_tool_to_response(row, await _get_policy_count(db, ws.id, row.name)))
    return SearchToolListResponse(items=items, total=len(items))


@search_tools_router.get(
    "/{tool_id}",
    response_model=SearchToolResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_search_tool(tool_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> SearchToolResponse:
    tool = (
        await db.execute(
            select(SearchTool).where(SearchTool.id == tool_id, SearchTool.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Search tool not found")
    return _search_tool_to_response(tool, await _get_policy_count(db, ws.id, tool.name))


@search_tools_router.put(
    "/{tool_id}",
    response_model=SearchToolResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_search_tool(
    tool_id: uuid.UUID,
    body: SearchToolUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> SearchToolResponse:
    tool = (
        await db.execute(
            select(SearchTool).where(SearchTool.id == tool_id, SearchTool.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Search tool not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tool, field, value)
    tool.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(tool)
    return _search_tool_to_response(tool, await _get_policy_count(db, ws.id, tool.name))


@search_tools_router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def delete_search_tool(tool_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> Response:
    tool = (
        await db.execute(
            select(SearchTool).where(SearchTool.id == tool_id, SearchTool.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Search tool not found")
    tool.is_active = False
    tool.updated_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@search_tools_router.get(
    "/{tool_id}/policies",
    response_model=SearchToolPolicySummary,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_search_tool_policies(
    tool_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> SearchToolPolicySummary:
    tool = (
        await db.execute(
            select(SearchTool).where(SearchTool.id == tool_id, SearchTool.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Search tool not found")
    policies = (
        await db.execute(
            select(ToolPolicy)
            .where(
                ToolPolicy.workspace_id == ws.id,
                ToolPolicy.tool_name.in_([tool.name, "*"]),
                ToolPolicy.is_active.is_(True),
            )
            .order_by(ToolPolicy.priority.asc(), ToolPolicy.created_at.asc())
        )
    ).scalars().all()
    return SearchToolPolicySummary(
        tool_id=tool.id,
        tool_name=tool.name,
        policies=[_policy_to_response(policy) for policy in policies],
    )


@tool_policies_router.post(
    "",
    response_model=ToolPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_tool_policy(
    body: ToolPolicyCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> ToolPolicyResponse:
    policy = ToolPolicy(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        tool_name=body.tool_name,
        action=body.action,
        condition_type=body.condition_type,
        condition_config=body.condition_config,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return _policy_to_response(policy)


@tool_policies_router.get(
    "",
    response_model=ToolPolicyListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_tool_policies(
    ws: WorkspaceDep,
    db: DbDep,
    tool_name: str | None = None,
    include_inactive: bool = False,
) -> ToolPolicyListResponse:
    q = select(ToolPolicy).where(ToolPolicy.workspace_id == ws.id)
    if tool_name:
        q = q.where(ToolPolicy.tool_name == tool_name)
    if not include_inactive:
        q = q.where(ToolPolicy.is_active.is_(True))
    rows = (
        await db.execute(q.order_by(ToolPolicy.priority.asc(), ToolPolicy.created_at.asc()))
    ).scalars().all()

    if not rows and not tool_name:
        for pol_def in DEFAULT_POPULAR_TOOL_POLICIES:
            pol = ToolPolicy(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                name=pol_def["name"],
                description=pol_def["description"],
                tool_name=pol_def["tool_name"],
                action=pol_def["action"],
                priority=pol_def["priority"],
                is_active=True,
            )
            db.add(pol)
        await db.commit()
        rows = (
            await db.execute(q.order_by(ToolPolicy.priority.asc(), ToolPolicy.created_at.asc()))
        ).scalars().all()
    return ToolPolicyListResponse(
        items=[_policy_to_response(policy) for policy in rows],
        total=len(rows),
    )


@tool_policies_router.put(
    "/{policy_id}",
    response_model=ToolPolicyResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_tool_policy(
    policy_id: uuid.UUID,
    body: ToolPolicyUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> ToolPolicyResponse:
    policy = (
        await db.execute(
            select(ToolPolicy).where(ToolPolicy.id == policy_id, ToolPolicy.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool policy not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    policy.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(policy)
    return _policy_to_response(policy)


@tool_policies_router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def delete_tool_policy(policy_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> Response:
    policy = (
        await db.execute(
            select(ToolPolicy).where(ToolPolicy.id == policy_id, ToolPolicy.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool policy not found")
    policy.is_active = False
    policy.updated_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@tool_policies_router.post(
    "/simulate",
    response_model=ToolPolicySimulationResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def simulate_tool_policy(
    body: ToolPolicySimulationRequest,
    ws: WorkspaceDep,
    db: DbDep,
) -> ToolPolicySimulationResponse:
    policies = (
        await db.execute(
            select(ToolPolicy)
            .where(
                ToolPolicy.workspace_id == ws.id,
                ToolPolicy.is_active.is_(True),
                ToolPolicy.tool_name.in_([body.tool_name, "*"]),
            )
            .order_by(ToolPolicy.priority.asc(), ToolPolicy.created_at.asc())
        )
    ).scalars().all()
    matched_ids: list[uuid.UUID] = []
    matched_names: list[str] = []
    reasons: list[str] = []
    final_action = "allow"
    for policy in policies:
        matched, reason = _policy_matches(policy, body)
        if not matched:
            continue
        matched_ids.append(policy.id)
        matched_names.append(policy.name)
        reasons.append(reason)
        if policy.action == "deny":
            final_action = "deny"
            break
        if policy.action == "audit" and final_action == "allow":
            final_action = "audit"
    return ToolPolicySimulationResponse(
        tool_name=body.tool_name,
        final_action=final_action,
        matched_policy_ids=matched_ids,
        matched_policy_names=matched_names,
        reasons=reasons,
    )


@tool_policies_router.get(
    "/analytics",
    response_model=ToolUsageAnalyticsResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_tool_policy_analytics(
    ws: WorkspaceDep,
    db: DbDep,
    limit: int = Query(500, ge=1, le=2000),
) -> ToolUsageAnalyticsResponse:
    rows = (
        await db.execute(
            select(ToolCall)
            .where(ToolCall.workspace_id == ws.id)
            .order_by(ToolCall.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    summaries: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = summaries.setdefault(
            row.tool_name,
            {
                "tool_name": row.tool_name,
                "total_calls": 0,
                "allowed_calls": 0,
                "denied_calls": 0,
                "audited_calls": 0,
                "success_count": 0,
                "failure_count": 0,
                "duration_sum": 0,
                "duration_count": 0,
                "risk_sum": 0,
                "risk_count": 0,
            },
        )
        item["total_calls"] += 1
        if row.status == "blocked":
            item["denied_calls"] += 1
        elif row.status == "audited":
            item["audited_calls"] += 1
        else:
            item["allowed_calls"] += 1
        if row.status in {"failed", "error", "blocked"}:
            item["failure_count"] += 1
        else:
            item["success_count"] += 1
        if row.duration_ms is not None:
            item["duration_sum"] += row.duration_ms
            item["duration_count"] += 1
        if row.risk_score is not None:
            item["risk_sum"] += row.risk_score
            item["risk_count"] += 1
    items = [
        ToolUsageAnalyticsItem(
            tool_name=data["tool_name"],
            total_calls=data["total_calls"],
            allowed_calls=data["allowed_calls"],
            denied_calls=data["denied_calls"],
            audited_calls=data["audited_calls"],
            success_count=data["success_count"],
            failure_count=data["failure_count"],
            avg_duration_ms=(
                data["duration_sum"] / data["duration_count"] if data["duration_count"] else None
            ),
            avg_risk_score=(
                data["risk_sum"] / data["risk_count"] if data["risk_count"] else None
            ),
        )
        for data in summaries.values()
    ]
    items.sort(key=lambda item: item.total_calls, reverse=True)
    return ToolUsageAnalyticsResponse(
        items=items,
        total_calls=len(rows),
        unique_tools=len(items),
    )


@access_groups_router.post(
    "",
    response_model=AccessGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_access_group(
    body: AccessGroupCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AccessGroupResponse:
    group = AccessGroup(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        permissions=body.permissions,
        budget_usd=body.budget_usd,
        budget_period=body.budget_period,
        guardrail_profile=body.guardrail_profile,
        is_active=body.is_active,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return _group_to_response(group)


@access_groups_router.get(
    "",
    response_model=AccessGroupListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_access_groups(
    ws: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = False,
) -> AccessGroupListResponse:
    q = select(AccessGroup).where(AccessGroup.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(AccessGroup.is_active.is_(True))
    rows = (await db.execute(q.order_by(AccessGroup.name))).scalars().all()
    return AccessGroupListResponse(
        items=[_group_to_response(group) for group in rows],
        total=len(rows),
    )


@access_groups_router.put(
    "/{group_id}",
    response_model=AccessGroupResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_access_group(
    group_id: uuid.UUID,
    body: AccessGroupUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AccessGroupResponse:
    group = await _get_group_or_404(db, ws.id, group_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    group.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(group)
    return _group_to_response(group)


@access_groups_router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def delete_access_group(group_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> Response:
    group = await _get_group_or_404(db, ws.id, group_id)
    group.is_active = False
    group.updated_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@access_groups_router.post(
    "/{group_id}/members",
    response_model=AccessGroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def add_access_group_member(
    group_id: uuid.UUID,
    body: AccessGroupMemberCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> AccessGroupMemberResponse:
    group = await _get_group_or_404(db, ws.id, group_id)
    member = AccessGroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(member)
    group.member_count = (group.member_count or 0) + 1
    group.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(member)
    return _member_to_response(member)


@access_groups_router.get(
    "/{group_id}/members",
    response_model=AccessGroupMemberListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_access_group_members(
    group_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> AccessGroupMemberListResponse:
    await _get_group_or_404(db, ws.id, group_id)
    rows = (
        await db.execute(
            select(AccessGroupMember)
            .where(AccessGroupMember.group_id == group_id)
            .order_by(AccessGroupMember.created_at.desc())
        )
    ).scalars().all()
    return AccessGroupMemberListResponse(
        items=[_member_to_response(member) for member in rows],
        total=len(rows),
    )


@access_groups_router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def remove_access_group_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> Response:
    group = await _get_group_or_404(db, ws.id, group_id)
    member = (
        await db.execute(
            select(AccessGroupMember).where(
                AccessGroupMember.group_id == group_id,
                AccessGroupMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group member not found")
    await db.delete(member)
    group.member_count = max((group.member_count or 0) - 1, 0)
    group.updated_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@access_groups_router.get(
    "/dashboard",
    response_model=AccessGroupDashboardResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_access_group_dashboard(
    ws: WorkspaceDep,
    db: DbDep,
    group_id: uuid.UUID | None = None,
) -> AccessGroupDashboardResponse:
    q = select(AccessGroup).where(AccessGroup.workspace_id == ws.id)
    if group_id:
        q = q.where(AccessGroup.id == group_id)
    rows = (await db.execute(q.order_by(AccessGroup.name))).scalars().all()
    return AccessGroupDashboardResponse(
        groups=[
            AccessGroupDashboardItem(
                id=row.id,
                name=row.name,
                member_count=row.member_count,
                budget_usd=row.budget_usd,
                budget_period=row.budget_period,
                guardrail_profile=row.guardrail_profile,
                dashboard_filters=(row.permissions or {}).get("dashboard_filters", {}),
                is_active=row.is_active,
            )
            for row in rows
        ],
        selected_group_id=group_id,
    )


@response_cache_router.post(
    "",
    response_model=ResponseCacheConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_response_cache_config(
    body: ResponseCacheConfigCreate,
    ws: WorkspaceDep,
    db: DbDep,
) -> ResponseCacheConfigResponse:
    config = ResponseCacheConfig(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        is_enabled=body.is_enabled,
        ttl_seconds=body.ttl_seconds,
        max_entries=body.max_entries,
        eviction_policy=body.eviction_policy,
        similarity_threshold=body.similarity_threshold,
        embedding_model=body.embedding_model,
        scope_models=body.scope_models,
        config=body.config,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return _cache_to_response(config)


@response_cache_router.get(
    "",
    response_model=ResponseCacheConfigListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_response_cache_configs(
    ws: WorkspaceDep,
    db: DbDep,
) -> ResponseCacheConfigListResponse:
    rows = (
        await db.execute(
            select(ResponseCacheConfig)
            .where(ResponseCacheConfig.workspace_id == ws.id)
            .order_by(ResponseCacheConfig.created_at.desc())
        )
    ).scalars().all()
    return ResponseCacheConfigListResponse(
        items=[_cache_to_response(row) for row in rows],
        total=len(rows),
    )


@response_cache_router.put(
    "/{config_id}",
    response_model=ResponseCacheConfigResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_response_cache_config(
    config_id: uuid.UUID,
    body: ResponseCacheConfigUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> ResponseCacheConfigResponse:
    config = (
        await db.execute(
            select(ResponseCacheConfig).where(
                ResponseCacheConfig.id == config_id,
                ResponseCacheConfig.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response cache config not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    config.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(config)
    return _cache_to_response(config)


@response_cache_router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def delete_response_cache_config(
    config_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> Response:
    config = (
        await db.execute(
            select(ResponseCacheConfig).where(
                ResponseCacheConfig.id == config_id,
                ResponseCacheConfig.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response cache config not found")
    await db.delete(config)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@response_cache_router.get(
    "/stats",
    response_model=ResponseCacheStatsResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_response_cache_stats(ws: WorkspaceDep, db: DbDep) -> ResponseCacheStatsResponse:
    configs = (
        await db.execute(
            select(ResponseCacheConfig).where(ResponseCacheConfig.workspace_id == ws.id)
        )
    ).scalars().all()
    cache_entries = (
        await db.execute(
            select(PromptCache.model, PromptCache.hit_count)
            .where(PromptCache.workspace_id == ws.id)
            .order_by(PromptCache.hit_count.desc())
            .limit(5)
        )
    ).all()
    total_hits = sum(int(config.total_hits or 0) for config in configs)
    total_misses = sum(int(config.total_misses or 0) for config in configs)
    total_requests = total_hits + total_misses
    return ResponseCacheStatsResponse(
        config_count=len(configs),
        enabled_config_count=sum(1 for config in configs if config.is_enabled),
        total_hits=total_hits,
        total_misses=total_misses,
        hit_rate=(total_hits / total_requests) if total_requests else None,
        total_savings_usd=sum((config.total_savings_usd or Decimal("0")) for config in configs),
        live_entry_count=sum(int(config.max_entries or 0) for config in configs if config.is_enabled),
        top_models=[
            {"model": row[0], "hit_count": row[1]}
            for row in cache_entries
        ],
    )


@response_cache_router.get(
    "/{config_id}",
    response_model=ResponseCacheConfigResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_response_cache_config(
    config_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
) -> ResponseCacheConfigResponse:
    config = (
        await db.execute(
            select(ResponseCacheConfig).where(
                ResponseCacheConfig.id == config_id,
                ResponseCacheConfig.workspace_id == ws.id,
            )
        )
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Response cache config not found")
    return _cache_to_response(config)
