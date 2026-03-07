"""
Tests for Phase 18 Prompt Management endpoints.

Covers:
  POST   /prompts                     — create prompt (success, auth, duplicate)
  GET    /prompts                     — list prompts (empty, items)
  GET    /prompts/{name}              — get prompt (success, not found)
  POST   /prompts/{name}/versions     — commit version
  GET    /prompts/{name}/latest       — SDK pull endpoint
  GET    /prompts/{name}/versions/{v} — get specific version
  POST   /prompts/{name}/promote      — promote staging → production
  GET    /prompts/{name}/metrics      — per-version metrics

Uses authed_client / client / mock_db_session / mock_workspace fixtures from conftest.
No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Mock result helpers ────────────────────────────────────────────────────────


def _scalar_one_or_none_result(val: object) -> MagicMock:
    """Result where .scalar_one_or_none() returns val."""
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=val)
    return m


def _scalar_result(val: object) -> MagicMock:
    """Result where .scalar() returns val."""
    m = MagicMock()
    m.scalar = MagicMock(return_value=val)
    return m


def _scalars_all_result(items: list[object]) -> MagicMock:
    """Result where .scalars().all() returns items."""
    scalars_m = MagicMock()
    scalars_m.all = MagicMock(return_value=items)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_m)
    return m


def _one_result(row: object) -> MagicMock:
    """Result where .one() returns row."""
    m = MagicMock()
    m.one = MagicMock(return_value=row)
    return m


def _make_prompt(**kwargs: object) -> SimpleNamespace:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="support-agent",
        description=None,
        default_environment="production",
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_version(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        version=1,
        content="Hello {{user_name}}, how can I help?",
        variables=[{"name": "user_name", "type": "string", "description": "User name"}],
        commit_message="Initial version",
        environment="production",
        model_hint=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /prompts ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_prompt_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /prompts → 201 with id/name/default_environment."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)

    async def set_attrs(obj: object) -> None:
        obj.id = prompt.id  # type: ignore[attr-defined]
        obj.created_at = prompt.created_at  # type: ignore[attr-defined]
        obj.updated_at = prompt.updated_at  # type: ignore[attr-defined]

    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar_one_or_none_result(None)]  # uniqueness check → no conflict
    )
    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/prompts",
        json={"name": "support-agent", "default_environment": "production"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "support-agent"
    assert data["default_environment"] == "production"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_prompt_requires_auth(
    client: AsyncClient,
) -> None:
    """POST /prompts without auth → 401."""
    resp = await client.post(
        "/prompts",
        json={"name": "test-prompt"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_prompt_duplicate(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /prompts with existing name → 409 Conflict."""
    existing = _make_prompt(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar_one_or_none_result(existing)]  # found conflict
    )

    resp = await authed_client.post(
        "/prompts",
        json={"name": "support-agent"},
    )
    assert resp.status_code == 409


# ── GET /prompts ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_prompts_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /prompts with no prompts → {"items": []}."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result([]))

    resp = await authed_client.get("/prompts")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_list_prompts_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /prompts → returns 2 prompts."""
    p1 = _make_prompt(workspace_id=mock_workspace.id, name="chat-agent")
    p2 = _make_prompt(workspace_id=mock_workspace.id, name="search-agent")
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result([p1, p2]))

    resp = await authed_client.get("/prompts")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["name"] == "chat-agent"


# ── GET /prompts/{name} ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_prompt_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /prompts/{name} → 200 with prompt metadata."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(
        return_value=_scalar_one_or_none_result(prompt)
    )

    resp = await authed_client.get("/prompts/support-agent")
    assert resp.status_code == 200
    assert resp.json()["name"] == "support-agent"


@pytest.mark.asyncio
async def test_get_prompt_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /prompts/{name} when prompt doesn't exist → 404."""
    mock_db_session.execute = AsyncMock(
        return_value=_scalar_one_or_none_result(None)
    )

    resp = await authed_client.get("/prompts/nonexistent")
    assert resp.status_code == 404


# ── POST /prompts/{name}/versions ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_version_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /prompts/{name}/versions → 201 with version=1."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    version = _make_version(prompt_id=prompt.id)

    async def set_version_attrs(obj: object) -> None:
        obj.id = version.id  # type: ignore[attr-defined]
        obj.created_at = version.created_at  # type: ignore[attr-defined]

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(prompt),  # get prompt
            _scalar_result(0),                   # max version = 0 → new = 1
        ]
    )
    mock_db_session.refresh.side_effect = set_version_attrs

    resp = await authed_client.post(
        "/prompts/support-agent/versions",
        json={
            "content": "Hello {{user_name}}, how can I help?",
            "variables": [{"name": "user_name", "type": "string"}],
            "commit_message": "Initial version",
            "environment": "production",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == 1
    assert "{{user_name}}" in data["content"]


# ── GET /prompts/{name}/latest ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_latest_version(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /prompts/{name}/latest → 200 with latest version for environment."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    version = _make_version(prompt_id=prompt.id, version=3, environment="production")

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(prompt),    # get prompt
            _scalar_one_or_none_result(version),   # get latest
        ]
    )

    resp = await authed_client.get("/prompts/support-agent/latest?environment=production")
    assert resp.status_code == 200
    assert resp.json()["version"] == 3
    assert resp.json()["environment"] == "production"


# ── GET /prompts/{name}/versions/{v} ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_specific_version(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /prompts/{name}/versions/{v} → 200 for existing version."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    version = _make_version(prompt_id=prompt.id, version=2)

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(prompt),   # get prompt
            _scalar_one_or_none_result(version),  # get specific version
        ]
    )

    resp = await authed_client.get("/prompts/support-agent/versions/2")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


# ── POST /prompts/{name}/promote ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_promote_version(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /prompts/{name}/promote → 201, staging version copied to production."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    staging_v = _make_version(
        prompt_id=prompt.id, version=1, environment="staging",
        commit_message="Staging draft",
    )
    promoted = _make_version(
        prompt_id=prompt.id, version=2, environment="production",
        commit_message="Promoted from staging v1",
    )

    async def set_promoted_attrs(obj: object) -> None:
        obj.id = promoted.id  # type: ignore[attr-defined]
        obj.created_at = promoted.created_at  # type: ignore[attr-defined]

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(prompt),      # get prompt
            _scalar_one_or_none_result(staging_v),   # find latest in staging
            _scalar_result(1),                       # max version = 1 → new = 2
        ]
    )
    mock_db_session.refresh.side_effect = set_promoted_attrs

    resp = await authed_client.post(
        "/prompts/support-agent/promote",
        json={"source_environment": "staging", "target_environment": "production"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["environment"] == "production"
    assert data["version"] == 2


# ── GET /prompts/{name}/metrics ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prompt_metrics(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /prompts/{name}/metrics → per-version run count, avg cost, avg score."""
    prompt = _make_prompt(workspace_id=mock_workspace.id)
    version = _make_version(prompt_id=prompt.id, version=1)
    run_row = SimpleNamespace(run_count=5, avg_cost=0.0042)

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_one_or_none_result(prompt),     # get prompt
            _scalars_all_result([version]),          # get all versions
            _one_result(run_row),                   # run stats for v1
            _scalar_result(0.87),                   # avg score for v1
        ]
    )

    resp = await authed_client.get("/prompts/support-agent/metrics")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["version"] == 1
    assert items[0]["run_count"] == 5
    assert items[0]["avg_cost_usd"] == pytest.approx(0.0042, rel=1e-3)
    assert items[0]["avg_score"] == pytest.approx(0.87, rel=1e-3)
