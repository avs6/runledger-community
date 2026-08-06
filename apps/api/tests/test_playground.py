"""Tests for Phase 16 — API Playground.

Covers:
  Session CRUD — create, list, get, update, delete
  Send request
  Request history — list, get detail
  Compare models
  Not-found cases

13 tests total.
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


def _make_session(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="My Session",
        system_prompt="You are helpful.",
        mode="single",
        is_favorite=False,
        config={},
        created_by=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_request(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        session_id=None,
        model="gpt-4o",
        provider=None,
        system_prompt=None,
        user_prompt="Hello world",
        parameters={},
        response_text="Hi there!",
        input_tokens=10,
        output_tokens=5,
        cost_usd=None,
        latency_ms=120,
        status="completed",
        route_decision=None,
        error=None,
        gateway_request_id=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _refresh_defaults(obj):
    now = datetime.now(UTC)
    for attr, val in {
        "is_favorite": False,
        "mode": "single",
        "status": "completed",
        "input_tokens": 0,
        "output_tokens": 0,
        "created_at": now,
        "updated_at": now,
    }.items():
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, val)


# ── Session CRUD ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/playground/sessions",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "Test Session", "mode": "single"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Session"
    assert data["mode"] == "single"


@pytest.mark.asyncio
async def test_list_sessions_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/playground/sessions",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_session_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    sess = _make_session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sess
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/playground/sessions/{sess.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Session"


@pytest.mark.asyncio
async def test_get_session_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/playground/sessions/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_session(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    sess = _make_session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sess
    mock_db_session.execute = AsyncMock(return_value=result)
    mock_db_session.refresh = AsyncMock()

    resp = await authed_client.put(
        f"/playground/sessions/{sess.id}",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "Renamed", "is_favorite": True},
    )
    assert resp.status_code == 200
    assert sess.name == "Renamed"
    assert sess.is_favorite is True


@pytest.mark.asyncio
async def test_delete_session(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    sess = _make_session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sess
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/playground/sessions/{sess.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_session_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/playground/sessions/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Send Request ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_request(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/playground/send",
        headers={"Authorization": "Bearer test-key"},
        json={"model": "gpt-4o", "user_prompt": "Hello"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["model"] == "gpt-4o"
    assert data["user_prompt"] == "Hello"
    assert data["status"] == "completed"


# ── History ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_history(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    req = _make_request()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [req]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/playground/history",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["requests"][0]["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_get_request_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    req = _make_request()
    result = MagicMock()
    result.scalar_one_or_none.return_value = req
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/playground/history/{req.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_prompt"] == "Hello world"


@pytest.mark.asyncio
async def test_get_request_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/playground/history/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Compare ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_models(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/playground/compare",
        headers={"Authorization": "Bearer test-key"},
        json={
            "models": ["gpt-4o", "claude-sonnet-4-20250514"],
            "user_prompt": "What is 2+2?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    models = {r["model"] for r in data["results"]}
    assert models == {"gpt-4o", "claude-sonnet-4-20250514"}


@pytest.mark.asyncio
async def test_compare_requires_two_models(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    resp = await authed_client.post(
        "/playground/compare",
        headers={"Authorization": "Bearer test-key"},
        json={"models": ["gpt-4o"], "user_prompt": "Hello"},
    )
    assert resp.status_code == 422
