"""Tests for agent registry and workflow runs.

Covers:
  Agent CRUD — create, list, get, update, retire
  Agent stats and runs listing
  Workflow definition CRUD — create, list, get, update, archive
  Cost attribution

Workflow runs are a view over agent_runs now; see test_workflows_spine.py.
"""

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


def _make_agent(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="test-agent",
        description="A test agent",
        agent_type="autonomous",
        owner="alice",
        default_model="gpt-4o",
        default_tools=["web_search"],
        budget_envelope=Decimal("10.0000"),
        allowed_aliases=[],
        status="active",
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_workflow(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="test-workflow",
        description="A test workflow",
        steps_schema=[{"name": "classify", "type": "model"}],
        feature_tag=None,
        gateway_alias=None,
        owner=None,
        status="active",
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── Agent CRUD ────────────────────────────────────────────────────────────────


def _refresh_defaults(obj):
    """Simulate DB refresh by filling server-default fields on ORM-like objects."""
    now = datetime.now(UTC)
    defaults = {
        "status": "active" if hasattr(obj, "agent_type") else "pending",
        "cost": Decimal("0"),
        "tokens": 0,
        "total_cost": Decimal("0"),
        "total_tokens": 0,
        "created_at": now,
        "updated_at": now,
    }
    for attr, val in defaults.items():
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, val)


@pytest.mark.asyncio
async def test_create_agent(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/agents",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "my-agent", "agent_type": "autonomous", "default_model": "gpt-4o"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my-agent"
    assert data["agent_type"] == "autonomous"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_agents_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result_mock = MagicMock()
    result_mock.scalar.return_value = 0
    scalars_mock = MagicMock()
    scalars_mock.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[result_mock, scalars_mock])

    resp = await authed_client.get(
        "/agents",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["agents"] == []


@pytest.mark.asyncio
async def test_list_agents_with_results(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [agent]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/agents",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["agents"]) == 1
    assert data["agents"][0]["name"] == "test-agent"


@pytest.mark.asyncio
async def test_get_agent_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    result = MagicMock()
    result.scalar_one_or_none.return_value = agent
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/agents/{agent.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-agent"


@pytest.mark.asyncio
async def test_get_agent_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/agents/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_agent(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    result = MagicMock()
    result.scalar_one_or_none.return_value = agent
    mock_db_session.execute = AsyncMock(return_value=result)
    mock_db_session.refresh = AsyncMock()

    resp = await authed_client.put(
        f"/agents/{agent.id}",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "renamed-agent"},
    )
    assert resp.status_code == 200
    assert agent.name == "renamed-agent"


@pytest.mark.asyncio
async def test_retire_agent(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent = _make_agent()
    result = MagicMock()
    result.scalar_one_or_none.return_value = agent
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/agents/{agent.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 204
    assert agent.status == "retired"


@pytest.mark.asyncio
async def test_retire_agent_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/agents/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Agent Runs ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_agent_runs_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agent_result = MagicMock()
    agent_result.scalar_one_or_none.return_value = _make_agent()
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[agent_result, count_result, list_result])

    resp = await authed_client.get(
        f"/agents/{uuid.uuid4()}/runs",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Agent Stats ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_stats_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/agents/{uuid.uuid4()}/stats",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Workflow Definition CRUD ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_workflow(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/workflows",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "support-flow", "description": "Customer support"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "support-flow"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_workflows_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/workflows",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_workflow_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    wf = _make_workflow()
    result = MagicMock()
    result.scalar_one_or_none.return_value = wf
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/workflows/{wf.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-workflow"


@pytest.mark.asyncio
async def test_get_workflow_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/workflows/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_workflow(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    wf = _make_workflow()
    result = MagicMock()
    result.scalar_one_or_none.return_value = wf
    mock_db_session.execute = AsyncMock(return_value=result)
    mock_db_session.refresh = AsyncMock()

    resp = await authed_client.put(
        f"/workflows/{wf.id}",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "renamed-workflow"},
    )
    assert resp.status_code == 200
    assert wf.name == "renamed-workflow"


@pytest.mark.asyncio
async def test_archive_workflow(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    wf = _make_workflow()
    result = MagicMock()
    result.scalar_one_or_none.return_value = wf
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/workflows/{wf.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 204
    assert wf.status == "archived"


# ── Workflow Runs ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_workflow_cost_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/workflows/{uuid.uuid4()}/cost",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404
