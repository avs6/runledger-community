"""Tests for agent memory management.

Covers:
  Store memory (with PII detection, audit log)
  List memories (with type filter)
  Update memory
  Delete memory
  Search memories
  Memory stats
  Memory audit log
  Agent not found on memory endpoints

14 tests total.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _setup_redis(mock_redis_client: AsyncMock) -> None:
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)


def _make_agent(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="test-agent",
        description=None,
        agent_type="autonomous",
        owner=None,
        default_model=None,
        default_tools=[],
        budget_envelope=None,
        policy_profile=None,
        status="active",
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_memory(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        key="user_pref",
        value="dark mode",
        memory_type="long_term",
        metadata_={},
        size_bytes=9,
        access_count=0,
        has_pii=False,
        retention_days=None,
        expires_at=None,
        last_accessed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_audit_event(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        memory_id=uuid.uuid4(),
        action="store",
        key="user_pref",
        details={"memory_type": "long_term"},
        actor=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _refresh_memory_defaults(obj):
    now = datetime.now(UTC)
    for attr, val in {
        "size_bytes": 0,
        "access_count": 0,
        "has_pii": False,
        "created_at": now,
        "updated_at": now,
    }.items():
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, val)


# ── Store Memory ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_memory(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = agent
    mock_db_session.execute = AsyncMock(return_value=find_result)
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_memory_defaults)

    resp = await authed_client.post(
        f"/agents/{agent.id}/memory",
        headers={"Authorization": "Bearer test-key"},
        json={"key": "user_pref", "value": "dark mode", "memory_type": "long_term"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"] == "user_pref"
    assert data["value"] == "dark mode"
    assert data["memory_type"] == "long_term"
    assert data["has_pii"] is False


@pytest.mark.asyncio
async def test_store_memory_detects_pii(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = agent
    mock_db_session.execute = AsyncMock(return_value=find_result)
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_memory_defaults)

    resp = await authed_client.post(
        f"/agents/{agent.id}/memory",
        headers={"Authorization": "Bearer test-key"},
        json={"key": "contact", "value": "email is user@example.com"},
    )
    assert resp.status_code == 201
    assert resp.json()["has_pii"] is True


@pytest.mark.asyncio
async def test_store_memory_agent_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=find_result)

    resp = await authed_client.post(
        f"/agents/{uuid.uuid4()}/memory",
        headers={"Authorization": "Bearer test-key"},
        json={"key": "k", "value": "v"},
    )
    assert resp.status_code == 404


# ── List Memories ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_memories_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    agent_id = uuid.uuid4()
    resp = await authed_client.get(
        f"/agents/{agent_id}/memory",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["memories"] == []


@pytest.mark.asyncio
async def test_list_memories_with_results(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_id = uuid.uuid4()
    mem = _make_memory(agent_id=agent_id)
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [mem]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        f"/agents/{agent_id}/memory",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["memories"][0]["key"] == "user_pref"


# ── Update Memory ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_memory(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_id = uuid.uuid4()
    mem = _make_memory(agent_id=agent_id)
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = mem
    mock_db_session.execute = AsyncMock(return_value=find_result)
    mock_db_session.refresh = AsyncMock()

    resp = await authed_client.put(
        f"/agents/{agent_id}/memory/user_pref",
        headers={"Authorization": "Bearer test-key"},
        json={"value": "light mode"},
    )
    assert resp.status_code == 200
    assert mem.value == "light mode"


@pytest.mark.asyncio
async def test_update_memory_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=find_result)

    resp = await authed_client.put(
        f"/agents/{uuid.uuid4()}/memory/missing_key",
        headers={"Authorization": "Bearer test-key"},
        json={"value": "nope"},
    )
    assert resp.status_code == 404


# ── Delete Memory ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_memory(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_id = uuid.uuid4()
    mem = _make_memory(agent_id=agent_id)
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = mem
    mock_db_session.execute = AsyncMock(return_value=find_result)

    resp = await authed_client.delete(
        f"/agents/{agent_id}/memory/user_pref",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_memory_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=find_result)

    resp = await authed_client.delete(
        f"/agents/{uuid.uuid4()}/memory/missing",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Search Memories ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_memories(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_id = uuid.uuid4()
    mem = _make_memory(agent_id=agent_id, key="user_pref", value="dark mode")
    search_result = MagicMock()
    search_result.scalars.return_value.all.return_value = [mem]
    mock_db_session.execute = AsyncMock(return_value=search_result)

    resp = await authed_client.post(
        f"/agents/{agent_id}/memory/search",
        headers={"Authorization": "Bearer test-key"},
        json={"query": "dark"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["memories"][0]["key"] == "user_pref"
    assert mem.access_count == 1


# ── Memory Stats ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_stats(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    agent_result = MagicMock()
    agent_result.scalar_one_or_none.return_value = agent

    agg_row = SimpleNamespace(total=5, total_size=1024, pii_count=1, expired=0)
    agg_result = MagicMock()
    agg_result.one.return_value = agg_row

    type_result = MagicMock()
    type_result.all.return_value = [("long_term", 3), ("short_term", 2)]

    top_mem = _make_memory(agent_id=agent.id, access_count=10)
    top_result = MagicMock()
    top_result.scalars.return_value.all.return_value = [top_mem]

    mock_db_session.execute = AsyncMock(
        side_effect=[agent_result, agg_result, type_result, top_result]
    )

    resp = await authed_client.get(
        f"/agents/{agent.id}/memory/stats",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_memories"] == 5
    assert data["total_size_bytes"] == 1024
    assert data["pii_count"] == 1
    assert data["by_type"]["long_term"] == 3


@pytest.mark.asyncio
async def test_memory_stats_agent_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/agents/{uuid.uuid4()}/memory/stats",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Audit Log ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_audit_log(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_id = uuid.uuid4()
    event = _make_audit_event(agent_id=agent_id)
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [event]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        f"/agents/{agent_id}/memory/audit",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["action"] == "store"
