"""
Tests for Phase 12 providers router.

Covers:
  GET    /providers/pricing           — list global + workspace rows
  POST   /providers/pricing           — create workspace-scoped override
  DELETE /providers/pricing/{id}      — delete workspace row
  DELETE global row → 403 Forbidden
  Auth enforcement

Uses authed_client / client / mock_db_session fixtures from conftest.
"""

from __future__ import annotations

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


def _make_pricing(**kwargs: object) -> SimpleNamespace:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        provider="openai",
        model="gpt-4o",
        input_cost_per_1m=Decimal("2.50"),
        output_cost_per_1m=Decimal("10.00"),
        cached_input_cost_per_1m=None,
        effective_from=now,
        effective_to=None,
        workspace_id=None,
        created_at=now,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_provider_pricing(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute.return_value = _scalars_list([])

    resp = await authed_client.get("/providers/pricing")

    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_create_provider_pricing(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    now = datetime.now(UTC)

    async def set_attrs(obj: object) -> None:
        obj.id = uuid.uuid4()  # type: ignore[attr-defined]
        obj.created_at = now  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/providers/pricing",
        json={
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "input_cost_per_1m": "3.00",
            "output_cost_per_1m": "15.00",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-3-5-sonnet"
    assert data["workspace_id"] == str(mock_workspace.id)


@pytest.mark.asyncio
async def test_delete_provider_pricing(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    pricing_id = uuid.uuid4()
    mock_pricing = SimpleNamespace(
        id=pricing_id,
        workspace_id=mock_workspace.id,
    )
    mock_db_session.get.return_value = mock_pricing

    resp = await authed_client.delete(f"/providers/pricing/{pricing_id}")

    assert resp.status_code == 204
    mock_db_session.delete.assert_called_once_with(mock_pricing)


@pytest.mark.asyncio
async def test_delete_global_pricing_forbidden(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    pricing_id = uuid.uuid4()
    mock_pricing = SimpleNamespace(
        id=pricing_id,
        workspace_id=None,  # global row — cannot delete
    )
    mock_db_session.get.return_value = mock_pricing

    resp = await authed_client.delete(f"/providers/pricing/{pricing_id}")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_providers_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/providers/pricing")

    assert resp.status_code == 401
