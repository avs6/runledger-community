"""
Tests for Phase 14 — Integrations.

Covers:
  POST   /integrations/slack/test  — Slack webhook connectivity test
  GET    /analytics/export         — bulk daily spend export (JSON + CSV)
  Auth enforcement
  Unit:  build_budget_breach_blocks() structure

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


def _scalars_list(rows: list[object]) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


def _make_usage_daily_row(
    day: date | None = None,
    provider: str = "openai",
    model: str = "gpt-4o",
    cost_usd: Decimal = Decimal("1.23"),
    input_tokens: int = 1000,
    output_tokens: int = 500,
    call_count: int = 10,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        day=day or date(2026, 2, 1),
        provider=provider,
        model=model,
        cost_usd=cost_usd,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        call_count=call_count,
    )


# ── POST /integrations/slack/test ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slack_test_ok(authed_client: AsyncClient) -> None:
    """POST /integrations/slack/test with a mocked successful send returns ok=true."""
    with patch(
        "runledger_api.routers.integrations.send_slack_message",
        new=AsyncMock(return_value=None),
    ):
        resp = await authed_client.post(
            "/integrations/slack/test",
            json={"webhook_url": "https://hooks.slack.com/services/TEST/TEST/test"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["error"] is None


@pytest.mark.asyncio
async def test_slack_test_error(authed_client: AsyncClient) -> None:
    """POST /integrations/slack/test with a failing send returns ok=false with error."""
    with patch(
        "runledger_api.routers.integrations.send_slack_message",
        new=AsyncMock(side_effect=Exception("Connection refused")),
    ):
        resp = await authed_client.post(
            "/integrations/slack/test",
            json={"webhook_url": "https://hooks.slack.com/services/INVALID"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "Connection refused" in data["error"]


@pytest.mark.asyncio
async def test_integrations_requires_auth(client: AsyncClient) -> None:
    """POST /integrations/slack/test without Bearer token returns 401."""
    resp = await client.post(
        "/integrations/slack/test",
        json={"webhook_url": "https://hooks.slack.com/services/TEST"},
    )
    assert resp.status_code == 401


# ── GET /analytics/export ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_export_json(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/export?format=json returns items list."""
    row = _make_usage_daily_row()
    mock_db_session.execute.return_value = _scalars_list([row])

    resp = await authed_client.get("/analytics/export?format=json")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["date"] == "2026-02-01"
    assert item["provider"] == "openai"
    assert item["model"] == "gpt-4o"
    assert item["cost_usd"] == "1.23"
    assert item["input_tokens"] == 1000
    assert item["output_tokens"] == 500
    assert item["call_count"] == 10


@pytest.mark.asyncio
async def test_analytics_export_csv(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/export?format=csv returns text/csv content type."""
    row = _make_usage_daily_row()
    mock_db_session.execute.return_value = _scalars_list([row])

    resp = await authed_client.get("/analytics/export?format=csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    text = resp.text
    assert "date,provider,model,cost_usd,input_tokens,output_tokens,call_count" in text
    assert "openai" in text
    assert "gpt-4o" in text


@pytest.mark.asyncio
async def test_analytics_export_date_filter(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/export with from/to params passes date range to query."""
    row = _make_usage_daily_row(day=date(2026, 1, 15))
    mock_db_session.execute.return_value = _scalars_list([row])

    resp = await authed_client.get(
        "/analytics/export?format=json&from=2026-01-01T00:00:00&to=2026-01-31T23:59:59"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["date"] == "2026-01-15"


@pytest.mark.asyncio
async def test_analytics_export_requires_auth(client: AsyncClient) -> None:
    """GET /analytics/export without Bearer token returns 401."""
    resp = await client.get("/analytics/export")
    assert resp.status_code == 401


# ── Unit: build_budget_breach_blocks ──────────────────────────────────────────


def test_slack_blocks_budget_breach() -> None:
    """build_budget_breach_blocks returns a valid Block Kit structure."""
    from runledger_api.services.notifications import build_budget_breach_blocks

    blocks = build_budget_breach_blocks(
        budget_id="budget-123",
        scope_type="workspace",
        scope_id=None,
        spend_usd=Decimal("55.00"),
        limit_usd=Decimal("50.00"),
        action="block",
    )

    assert isinstance(blocks, list)
    assert len(blocks) >= 2
    # First block must be the header
    header = blocks[0]
    assert header["type"] == "header"
    assert "RunLedger" in header["text"]["text"]
    # Second block must be section with fields
    section = blocks[1]
    assert section["type"] == "section"
    assert "fields" in section
    field_texts = [f["text"] for f in section["fields"]]
    assert any("budget-123" in t for t in field_texts)
    assert any("55.00" in t for t in field_texts)
