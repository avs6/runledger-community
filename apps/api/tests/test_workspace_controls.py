"""Tests for workspace control surfaces."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _setup_redis(mock_redis_client: AsyncMock) -> None:
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)


def _make_tag(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        category="team",
        key="department",
        value="support",
        description="Support org",
        parent_tag_id=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_rule(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Support search traffic",
        description=None,
        match_type="contains",
        match_field="prompt",
        match_pattern="search",
        tag_key="feature",
        tag_value="search",
        priority=10,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_search_tool(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="web-search",
        description="Search the public web",
        tool_type="web",
        endpoint_url="https://search.example.com",
        auth_type="api_key",
        auth_config={},
        rate_limit_rpm=60,
        cost_per_query=Decimal("0.002"),
        is_active=True,
        total_queries=24,
        total_cost_usd=Decimal("0.048"),
        avg_quality_score=Decimal("0.912"),
        config={},
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_policy(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Deny risky writes",
        description=None,
        tool_name="web-search",
        action="deny",
        condition_type="risk_score_gte",
        condition_config={"threshold": 50},
        scope_type="workspace",
        scope_id=None,
        priority=1,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_group(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Support",
        description="Support operators",
        permissions={"dashboard_filters": {"team": ["support"]}},
        budget_usd=Decimal("250.00"),
        budget_period="monthly",
        guardrail_profile="standard",
        is_active=True,
        member_count=2,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_group_member(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role="member",
        created_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_cache_config(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="semantic-default",
        is_enabled=True,
        ttl_seconds=3600,
        max_entries=5000,
        eviction_policy="lru",
        similarity_threshold=Decimal("0.95"),
        embedding_model="text-embedding-3-small",
        scope_models=["gpt-4o-mini"],
        total_hits=120,
        total_misses=30,
        total_savings_usd=Decimal("12.50"),
        config={},
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_tool_call(**overrides):
    now = datetime.now(UTC)
    data = dict(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        tool_name="web-search",
        tool_type="read",
        risk_score=20,
        duration_ms=120,
        status="success",
        created_at=now,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _refresh_defaults(obj) -> None:
    now = datetime.now(UTC)
    for key, value in {
        "created_at": now,
        "updated_at": now,
        "auth_config": {},
        "config": {},
        "permissions": {},
        "scope_models": [],
        "member_count": 0,
        "total_queries": 0,
        "total_cost_usd": Decimal("0"),
        "total_hits": 0,
        "total_misses": 0,
        "total_savings_usd": Decimal("0"),
    }.items():
        if hasattr(obj, key) and getattr(obj, key) is None:
            setattr(obj, key, value)


@pytest.mark.asyncio
async def test_tag_tree_and_rules(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    parent = _make_tag(key="team", value="ops")
    child = _make_tag(parent_tag_id=parent.id, key="squad", value="support")
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [parent, child]
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = [_make_rule()]
    mock_db_session.execute = AsyncMock(side_effect=[list_result, rules_result])

    tree_resp = await authed_client.get("/tags/tree", headers={"Authorization": "Bearer test-key"})
    assert tree_resp.status_code == 200
    assert tree_resp.json()["items"][0]["children"][0]["value"] == "support"

    rule_resp = await authed_client.get("/tags/auto-rules", headers={"Authorization": "Bearer test-key"})
    assert rule_resp.status_code == 200
    assert rule_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_auto_tagging_simulation(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = [_make_rule()]
    mock_db_session.execute = AsyncMock(return_value=rules_result)

    resp = await authed_client.post(
        "/tags/auto-rules/simulate",
        headers={"Authorization": "Bearer test-key"},
        json={"fields": {"prompt": "please search billing docs"}},
    )
    assert resp.status_code == 200
    assert resp.json()["applied_tags"]["feature"] == "search"


@pytest.mark.asyncio
async def test_create_and_list_search_tools(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    create_resp = await authed_client.post(
        "/search-tools",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "docs-search", "tool_type": "internal"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "docs-search"

    tool = _make_search_tool()
    tool_result = MagicMock()
    tool_result.scalars.return_value.all.return_value = [tool]
    count_result = MagicMock()
    count_result.scalar.return_value = 2
    mock_db_session.execute = AsyncMock(side_effect=[tool_result, count_result])

    list_resp = await authed_client.get("/search-tools", headers={"Authorization": "Bearer test-key"})
    assert list_resp.status_code == 200
    assert list_resp.json()["items"][0]["policy_count"] == 2


@pytest.mark.asyncio
async def test_search_tool_policy_summary(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    tool = _make_search_tool()
    tool_result = MagicMock()
    tool_result.scalar_one_or_none.return_value = tool
    policies_result = MagicMock()
    policies_result.scalars.return_value.all.return_value = [_make_policy()]
    mock_db_session.execute = AsyncMock(side_effect=[tool_result, policies_result])

    resp = await authed_client.get(
        f"/search-tools/{tool.id}/policies",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["policies"][0]["action"] == "deny"


@pytest.mark.asyncio
async def test_tool_policy_simulation_deny(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    policies_result = MagicMock()
    policies_result.scalars.return_value.all.return_value = [_make_policy()]
    mock_db_session.execute = AsyncMock(return_value=policies_result)

    resp = await authed_client.post(
        "/tool-policies/simulate",
        headers={"Authorization": "Bearer test-key"},
        json={"tool_name": "web-search", "risk_score": 90},
    )
    assert resp.status_code == 200
    assert resp.json()["final_action"] == "block"


@pytest.mark.asyncio
async def test_tool_policy_analytics(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [
        _make_tool_call(status="success", duration_ms=100, risk_score=10),
        _make_tool_call(status="blocked", duration_ms=200, risk_score=90),
    ]
    mock_db_session.execute = AsyncMock(return_value=rows_result)

    resp = await authed_client.get("/tool-policies/analytics", headers={"Authorization": "Bearer test-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 2
    assert data["items"][0]["denied_calls"] == 1


@pytest.mark.asyncio
async def test_access_groups_dashboard_and_members(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    group = _make_group()
    dashboard_result = MagicMock()
    dashboard_result.scalars.return_value.all.return_value = [group]
    group_lookup = MagicMock()
    group_lookup.scalar_one_or_none.return_value = group
    members_result = MagicMock()
    members_result.scalars.return_value.all.return_value = [_make_group_member(group_id=group.id)]
    mock_db_session.execute = AsyncMock(side_effect=[dashboard_result, group_lookup, members_result])

    dash_resp = await authed_client.get("/access-groups/dashboard", headers={"Authorization": "Bearer test-key"})
    assert dash_resp.status_code == 200
    assert dash_resp.json()["groups"][0]["dashboard_filters"]["team"] == ["support"]

    members_resp = await authed_client.get(
        f"/access-groups/{group.id}/members",
        headers={"Authorization": "Bearer test-key"},
    )
    assert members_resp.status_code == 200
    assert members_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_access_group_member(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    group = _make_group(member_count=0)
    group_result = MagicMock()
    group_result.scalar_one_or_none.return_value = group
    mock_db_session.execute = AsyncMock(return_value=group_result)
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    user_id = str(uuid.uuid4())
    resp = await authed_client.post(
        f"/access-groups/{group.id}/members",
        headers={"Authorization": "Bearer test-key"},
        json={"user_id": user_id, "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"
    assert group.member_count == 1


@pytest.mark.asyncio
async def test_response_cache_stats(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    configs_result = MagicMock()
    configs_result.scalars.return_value.all.return_value = [_make_cache_config()]
    cache_rows_result = MagicMock()
    cache_rows_result.all.return_value = [("gpt-4o-mini", 15)]
    mock_db_session.execute = AsyncMock(side_effect=[configs_result, cache_rows_result])

    resp = await authed_client.get("/response-cache/stats", headers={"Authorization": "Bearer test-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_hits"] == 120
    assert data["top_models"][0]["model"] == "gpt-4o-mini"
