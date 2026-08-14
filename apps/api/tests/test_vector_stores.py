"""Tests for vector store management.

Covers:
  Collection CRUD — create, list, get, update, delete (soft)
  Collection stats
  Query listing
  Search test

12 tests total.
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


def _make_collection(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="knowledge-base",
        description="Main KB",
        qdrant_collection="kb_v1",
        embedding_model="bge-small-en-v1.5",
        dimensions=384,
        distance_metric="cosine",
        document_count=1000,
        size_bytes=5242880,
        total_queries=50,
        total_query_cost=Decimal("0.005"),
        total_embed_cost=Decimal("0.010"),
        status="active",
        config={},
        last_queried_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_query(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        query_text="what is RAG?",
        top_k=5,
        threshold=None,
        result_count=3,
        best_score=Decimal("0.9512"),
        latency_ms=45,
        embed_cost=Decimal("0.0001"),
        query_cost=Decimal("0.0002"),
        results=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _refresh_defaults(obj):
    now = datetime.now(UTC)
    for attr, val in {
        "document_count": 0,
        "size_bytes": 0,
        "total_queries": 0,
        "total_query_cost": Decimal("0"),
        "total_embed_cost": Decimal("0"),
        "status": "active",
        "result_count": 0,
        "created_at": now,
        "updated_at": now,
    }.items():
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, val)


# ── Collection CRUD ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_collection(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        "/vector-stores",
        headers={"Authorization": "Bearer test-key"},
        json={
            "name": "my-kb",
            "qdrant_collection": "kb_v1",
            "embedding_model": "bge-small-en-v1.5",
            "dimensions": 384,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my-kb"
    assert data["qdrant_collection"] == "kb_v1"
    assert data["distance_metric"] == "cosine"


@pytest.mark.asyncio
async def test_list_collections_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/vector-stores",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["collections"] == []


@pytest.mark.asyncio
async def test_list_collections_with_results(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [coll]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        "/vector-stores",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["collections"][0]["name"] == "knowledge-base"


@pytest.mark.asyncio
async def test_get_collection_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    result = MagicMock()
    result.scalar_one_or_none.return_value = coll
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/vector-stores/{coll.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "knowledge-base"


@pytest.mark.asyncio
async def test_get_collection_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/vector-stores/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_collection(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    result = MagicMock()
    result.scalar_one_or_none.return_value = coll
    mock_db_session.execute = AsyncMock(return_value=result)
    mock_db_session.refresh = AsyncMock()

    resp = await authed_client.put(
        f"/vector-stores/{coll.id}",
        headers={"Authorization": "Bearer test-key"},
        json={"name": "renamed-kb"},
    )
    assert resp.status_code == 200
    assert coll.name == "renamed-kb"


@pytest.mark.asyncio
async def test_delete_collection(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    result = MagicMock()
    result.scalar_one_or_none.return_value = coll
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/vector-stores/{coll.id}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 204
    assert coll.status == "deleted"


@pytest.mark.asyncio
async def test_delete_collection_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(
        f"/vector-stores/{uuid.uuid4()}",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Stats ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_collection_stats(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    coll_result = MagicMock()
    coll_result.scalar_one_or_none.return_value = coll

    agg_row = SimpleNamespace(avg_latency=42.5, avg_results=3.2)
    agg_result = MagicMock()
    agg_result.one.return_value = agg_row

    mock_db_session.execute = AsyncMock(side_effect=[coll_result, agg_result])

    resp = await authed_client.get(
        f"/vector-stores/{coll.id}/stats",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_count"] == 1000
    assert data["total_queries"] == 50


@pytest.mark.asyncio
async def test_collection_stats_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get(
        f"/vector-stores/{uuid.uuid4()}/stats",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 404


# ── Queries ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_queries(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    q = _make_query()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [q]
    mock_db_session.execute = AsyncMock(side_effect=[count_result, list_result])

    resp = await authed_client.get(
        f"/vector-stores/{q.collection_id}/queries",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["queries"][0]["query_text"] == "what is RAG?"


# ── Search Test ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_test(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    coll = _make_collection()
    result = MagicMock()
    result.scalar_one_or_none.return_value = coll
    mock_db_session.execute = AsyncMock(return_value=result)
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_defaults)

    resp = await authed_client.post(
        f"/vector-stores/{coll.id}/search-test",
        headers={"Authorization": "Bearer test-key"},
        json={"query": "what is RAG?", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "what is RAG?"
    assert data["result_count"] == 0
