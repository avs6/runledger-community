"""
Tests for Phase 12 settings endpoints.

Covers:
  GET    /settings/api-keys          — list active keys
  POST   /settings/api-keys          — create key (raw key returned once)
  DELETE /settings/api-keys/{id}     — revoke key
  Auth enforcement
  GET    /providers/pricing           — includes global rows
  POST + DELETE /providers/pricing    — workspace-scoped flow

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _scalars_list(rows: list[object]) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


# ── API Key tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_api_keys_empty(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute.return_value = _scalars_list([])

    resp = await authed_client.get("/settings/api-keys")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_api_key(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    now = datetime.now(UTC)

    key_id = uuid.uuid4()

    async def set_attrs(obj: object) -> None:
        obj.id = key_id  # type: ignore[attr-defined]
        obj.created_at = now  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/settings/api-keys",
        json={"name": "Test Key", "environment": "dev", "scopes": []},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "key" in data
    assert data["key"].startswith("rl_test_")
    assert data["name"] == "Test Key"
    assert data["workspace_id"] == str(mock_workspace.id)


@pytest.mark.asyncio
async def test_create_api_key_raw_key_not_stored(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    now = datetime.now(UTC)
    captured: list[object] = []

    async def set_attrs(obj: object) -> None:
        obj.id = uuid.uuid4()  # type: ignore[attr-defined]
        obj.created_at = now  # type: ignore[attr-defined]
        captured.append(obj)

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/settings/api-keys",
        json={"name": "Key", "environment": "dev"},
    )

    assert resp.status_code == 201
    raw_key: str = resp.json()["key"]
    assert len(captured) == 1
    stored = captured[0]
    # DB stores hash, not raw key
    assert stored.key_hash != raw_key  # type: ignore[attr-defined]
    assert stored.key_hash == hashlib.sha256(raw_key.encode()).hexdigest()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_revoke_api_key(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    key_id = uuid.uuid4()
    mock_api_key = SimpleNamespace(
        id=key_id,
        workspace_id=mock_workspace.id,
        revoked_at=None,
    )
    mock_db_session.get.return_value = mock_api_key

    resp = await authed_client.delete(f"/settings/api-keys/{key_id}")

    assert resp.status_code == 204
    assert mock_api_key.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_wrong_workspace(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    key_id = uuid.uuid4()
    mock_api_key = SimpleNamespace(
        id=key_id,
        workspace_id=uuid.uuid4(),  # different workspace
        revoked_at=None,
    )
    mock_db_session.get.return_value = mock_api_key

    resp = await authed_client.delete(f"/settings/api-keys/{key_id}")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_settings_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/settings/api-keys")

    assert resp.status_code == 401


# ── Provider pricing integration tests (via settings test suite) ──────────────


@pytest.mark.asyncio
async def test_list_pricing_includes_global(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    now = datetime.now(UTC)
    global_row = SimpleNamespace(
        id=uuid.uuid4(),
        provider="openai",
        model="gpt-4o",
        input_cost_per_1m=Decimal("2.50"),
        output_cost_per_1m=Decimal("10.00"),
        cached_input_cost_per_1m=None,
        effective_from=now,
        effective_to=None,
        workspace_id=None,  # global row
        created_at=now,
    )
    mock_db_session.execute.return_value = _scalars_list([global_row])

    resp = await authed_client.get("/providers/pricing")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["workspace_id"] is None
    assert data["items"][0]["provider"] == "openai"


@pytest.mark.asyncio
async def test_create_and_delete_pricing(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    now = datetime.now(UTC)

    async def set_attrs(obj: object) -> None:
        obj.id = uuid.uuid4()  # type: ignore[attr-defined]
        obj.created_at = now  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    # Create workspace-scoped pricing
    resp = await authed_client.post(
        "/providers/pricing",
        json={
            "provider": "openai",
            "model": "gpt-4o-custom",
            "input_cost_per_1m": "5.00",
            "output_cost_per_1m": "15.00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["workspace_id"] == str(mock_workspace.id)
    pricing_id = data["id"]

    # Delete the workspace-scoped pricing
    mock_pricing = SimpleNamespace(
        id=uuid.UUID(pricing_id),
        workspace_id=mock_workspace.id,
    )
    mock_db_session.get.return_value = mock_pricing

    resp2 = await authed_client.delete(f"/providers/pricing/{pricing_id}")
    assert resp2.status_code == 204
