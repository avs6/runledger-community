"""Tests for admin auth endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from runledger_api.core.config import settings

ADMIN_HEADERS = {"X-Admin-Secret": settings.effective_admin_secret}


def _scalar_result(value: object) -> MagicMock:
    """Build the mock chain returned by db.execute(): .scalar_one_or_none() → value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list) -> MagicMock:
    """Build the mock chain returned by db.execute(): .scalars().all() → values."""
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _refresh_side_effect(*_fields: str):
    """Return an async side_effect that sets id + created_at (and extra fields) on the object."""

    async def _refresh(obj: object) -> None:
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()  # type: ignore[union-attr]
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(UTC)  # type: ignore[union-attr]
        for field in _fields:
            if not getattr(obj, field, None):
                obj.__dict__[field] = []  # type: ignore[union-attr]

    return _refresh


# ── Admin secret enforcement ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_tenant_no_header(client: AsyncClient) -> None:
    response = await client.post("/admin/tenants", json={"slug": "acme", "name": "Acme Corp"})
    # Missing required X-Admin-Secret header → FastAPI 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_tenant_wrong_secret(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/tenants",
        json={"slug": "acme", "name": "Acme Corp"},
        headers={"X-Admin-Secret": "wrong-secret"},
    )
    assert response.status_code == 403


# ── Tenant creation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_tenant_success(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(None))
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_side_effect())

    response = await client.post(
        "/admin/tenants",
        json={"slug": "acme", "name": "Acme Corp"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "acme"
    assert data["name"] == "Acme Corp"
    assert data["plan"] == "free"
    assert data["id"] is not None
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug(
    client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    # Return a truthy object to simulate an existing tenant
    mock_db_session.execute = AsyncMock(return_value=_scalar_result(SimpleNamespace(slug="acme")))

    response = await client.post(
        "/admin/tenants",
        json={"slug": "acme", "name": "Another Acme"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_tenants(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_result([]))

    response = await client.get("/admin/tenants", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json() == []


# ── Workspace creation ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_workspace_tenant_not_found(
    client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.get = AsyncMock(return_value=None)

    response = await client.post(
        "/admin/workspaces",
        json={"tenant_id": str(uuid.uuid4()), "name": "prod"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_workspace_success(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    tenant_id = uuid.uuid4()
    mock_db_session.get = AsyncMock(return_value=SimpleNamespace(id=tenant_id))
    mock_db_session.refresh = AsyncMock(side_effect=_refresh_side_effect())

    response = await client.post(
        "/admin/workspaces",
        json={"tenant_id": str(tenant_id), "name": "prod"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "prod"
    assert data["tenant_id"] == str(tenant_id)
    assert data["id"] is not None


# ── API key creation ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_api_key_workspace_not_found(
    client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.get = AsyncMock(return_value=None)

    response = await client.post(
        f"/admin/workspaces/{uuid.uuid4()}/api-keys",
        json={"name": "key"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_api_key_success(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    workspace_id = uuid.uuid4()
    mock_db_session.get = AsyncMock(return_value=SimpleNamespace(id=workspace_id))

    async def mock_refresh(obj: object) -> None:
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()  # type: ignore[union-attr]
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(UTC)  # type: ignore[union-attr]
        if not getattr(obj, "scopes", None):
            obj.scopes = []  # type: ignore[union-attr]
        if not hasattr(obj, "created_by"):
            obj.created_by = None  # type: ignore[union-attr]

    mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

    response = await client.post(
        f"/admin/workspaces/{workspace_id}/api-keys",
        json={"name": "my-key"},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    data = response.json()
    assert "key" in data
    assert data["key"].startswith("rl_test_")
    assert data["key_prefix"] == data["key"][:24]
    assert data["workspace_id"] == str(workspace_id)


# ── API key revocation ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_api_key_not_found(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    mock_db_session.get = AsyncMock(return_value=None)

    response = await client.delete(
        f"/admin/api-keys/{uuid.uuid4()}",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_revoke_api_key_success(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    key_id = uuid.uuid4()
    api_key = SimpleNamespace(id=key_id, revoked_at=None)
    mock_db_session.get = AsyncMock(return_value=api_key)

    response = await client.delete(
        f"/admin/api-keys/{key_id}",
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 204
    assert api_key.revoked_at is not None
