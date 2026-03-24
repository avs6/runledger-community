"""
Tests for Phase 21B Model Gateway endpoints.

Covers:
  POST   /gateway/chat/completions  — cache hit, cache miss + forward
  POST   /gateway/routes            — create route
  GET    /gateway/routes            — list routes
  PUT    /gateway/routes/{id}       — update / toggle
  DELETE /gateway/routes/{id}       — delete
  GET    /gateway/stats             — stats aggregation

Uses authed_client / mock_db_session / mock_workspace from conftest.
No live DB or network required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

# ── Helper factories ──────────────────────────────────────────────────────────


def _scalars_all_result(rows: list) -> MagicMock:
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars)
    return m


def _all_result(rows: list) -> MagicMock:
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _scalar_one_or_none_result(value) -> MagicMock:
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


def _make_route(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        alias="gpt-4o",
        provider="openai",
        target_model="gpt-4o",
        base_url=None,
        api_key_env_var="OPENAI_API_KEY",
        priority=10,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /gateway/routes ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_gateway_route_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /gateway/routes → 201, response has alias/provider/target_model."""
    route = _make_route(workspace_id=mock_workspace.id)

    async def set_attrs(obj) -> None:
        obj.id = route.id
        obj.created_at = route.created_at
        obj.is_active = True
        obj.priority = 10
        obj.base_url = None
        obj.api_key_env_var = "OPENAI_API_KEY"

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/gateway/routes",
        json={
            "alias": "gpt-4o",
            "provider": "openai",
            "target_model": "gpt-4o",
            "api_key_env_var": "OPENAI_API_KEY",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["alias"] == "gpt-4o"
    assert data["provider"] == "openai"
    assert data["target_model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_create_gateway_route_requires_auth(
    client: AsyncClient,
) -> None:
    """Unauthenticated POST → 401."""
    resp = await client.post(
        "/gateway/routes",
        json={"alias": "x", "provider": "openai", "target_model": "gpt-4o"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_gateway_route_invalid_provider(
    authed_client: AsyncClient,
) -> None:
    """Completely unknown provider slug → 422."""
    resp = await authed_client.post(
        "/gateway/routes",
        json={"alias": "x", "provider": "unknown-provider-xyz", "target_model": "gpt-4"},
    )
    assert resp.status_code == 422


# ── GET /gateway/routes ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_gateway_routes_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /gateway/routes with no routes → empty items."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result([]))
    resp = await authed_client.get("/gateway/routes")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_gateway_routes_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /gateway/routes returns all active routes."""
    routes = [
        _make_route(workspace_id=mock_workspace.id, alias="gpt-4o"),
        _make_route(workspace_id=mock_workspace.id, alias="claude-3", provider="anthropic"),
    ]
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result(routes))
    resp = await authed_client.get("/gateway/routes")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


# ── PUT /gateway/routes/{id} ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_gateway_route_disable(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """PUT /gateway/routes/{id} with is_active=False → route disabled."""
    route = _make_route(workspace_id=mock_workspace.id, is_active=True)
    mock_db_session.get = AsyncMock(return_value=route)
    mock_db_session.refresh = AsyncMock(return_value=None)

    resp = await authed_client.put(
        f"/gateway/routes/{route.id}",
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert route.is_active is False


# ── DELETE /gateway/routes/{id} ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_gateway_route(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """DELETE /gateway/routes/{id} → 204, delete called."""
    route = _make_route(workspace_id=mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=route)

    resp = await authed_client.delete(f"/gateway/routes/{route.id}")
    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(route)


# ── GET /gateway/stats ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gateway_stats_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /gateway/stats with no requests → zeros."""
    mock_db_session.execute = AsyncMock(return_value=_all_result([]))
    resp = await authed_client.get("/gateway/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 0
    assert data["cache_hits"] == 0
    assert data["routes"] == []


@pytest.mark.asyncio
async def test_gateway_stats_uses_weighted_latency(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Overall avg latency is weighted by request counts, not route count."""
    route_a = uuid.uuid4()
    route_b = uuid.uuid4()

    stats_rows = [
        SimpleNamespace(
            route_id=route_a,
            total=100,
            cache_hits=10,
            avg_latency=300,
            errors=1,
        ),
        SimpleNamespace(
            route_id=route_b,
            total=10,
            cache_hits=1,
            avg_latency=100,
            errors=0,
        ),
    ]
    route_rows = [
        SimpleNamespace(id=route_a, alias="primary"),
        SimpleNamespace(id=route_b, alias="fallback"),
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[_all_result(stats_rows), _all_result(route_rows)]
    )

    resp = await authed_client.get("/gateway/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["avg_latency_ms"]) == pytest.approx(281.82)


# ── POST /gateway/chat/completions ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_completions_cache_hit(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """Cache hit path: returns cached response, no provider call."""
    cached_response = {
        "id": "chatcmpl-abc",
        "object": "chat.completion",
        "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
    }
    cache_entry = SimpleNamespace(
        id=uuid.uuid4(),
        response_json=cached_response,
        model="gpt-4o",
        prompt_tokens=10,
        completion_tokens=5,
        hit_count=0,
    )

    # check_cache returns cache_entry; then increment_hit_count + record both execute/add
    with (
        patch(
            "runledger_api.routers.gateway.check_cache",
            new=AsyncMock(return_value=cache_entry),
        ),
        patch(
            "runledger_api.routers.gateway.increment_hit_count",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "runledger_api.routers.gateway.record_gateway_request",
            new=AsyncMock(return_value=None),
        ),
    ):
        resp = await authed_client.post(
            "/gateway/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
                "cache": True,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "Hello!"


@pytest.mark.asyncio
async def test_completions_no_routes_returns_502(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """No configured routes → 502 Bad Gateway."""
    with (
        patch(
            "runledger_api.routers.gateway.check_cache",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "runledger_api.services.routing.select_route_with_policy",
            new=AsyncMock(
                side_effect=ValueError("No active gateway routes for alias 'unknown-model'")
            ),
        ),
        patch(
            "runledger_api.routers.gateway.record_gateway_request",
            new=AsyncMock(return_value=None),
        ),
    ):
        resp = await authed_client.post(
            "/gateway/chat/completions",
            json={
                "model": "unknown-model",
                "messages": [{"role": "user", "content": "Hi"}],
            },
        )

    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_make_cache_key_deterministic() -> None:
    """Same messages always produce the same cache key."""
    from runledger_api.services.gateway import make_cache_key

    messages = [{"role": "user", "content": "Hello"}]
    key1 = make_cache_key("gpt-4o", messages)
    key2 = make_cache_key("gpt-4o", messages)
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_make_cache_key_differs_by_model() -> None:
    """Different model → different cache key."""
    from runledger_api.services.gateway import make_cache_key

    messages = [{"role": "user", "content": "Hello"}]
    key1 = make_cache_key("gpt-4o", messages)
    key2 = make_cache_key("gpt-4-turbo", messages)
    assert key1 != key2


@pytest.mark.asyncio
async def test_route_and_forward_retries_once_on_transient_failure() -> None:
    """Each route is retried once on transient 429/5xx before fallback."""
    from runledger_api.services.gateway import route_and_forward

    route = _make_route()
    request = httpx.Request("POST", "https://example.com/chat/completions")
    response_503 = httpx.Response(503, request=request)
    transient_error = httpx.HTTPStatusError("unavailable", request=request, response=response_503)

    mock_db = AsyncMock()
    # _fetch_policy returns None (no policy → manual)
    mock_db.execute = AsyncMock(return_value=_scalar_one_or_none_result(None))

    with (
        patch(
            "runledger_api.services.routing._fetch_active_routes",
            new=AsyncMock(return_value=[route]),
        ),
        patch("runledger_api.services.gateway.select_routes", new=AsyncMock(return_value=[route])),
        patch(
            "runledger_api.services.gateway.forward_request",
            new=AsyncMock(side_effect=[transient_error, {"id": "ok"}]),
        ) as forward_mock,
    ):
        payload, winning_route, latency_ms, decision_reason = await route_and_forward(
            db=mock_db,
            workspace_id=uuid.uuid4(),
            model_alias="gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
            temperature=None,
            max_tokens=None,
        )

    assert payload["id"] == "ok"
    assert winning_route.id == route.id
    assert isinstance(latency_ms, int)
    assert forward_mock.await_count == 2
