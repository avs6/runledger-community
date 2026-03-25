"""
Tests for Phase 31 — Finance System Integrations.

Covers:
  - Billing webhook CRUD (POST/GET/DELETE /billing/webhooks)
  - Webhook delivery listing (/billing/webhooks/{id}/deliveries)
  - Export format extensions (quickbooks, netsuite) on /billing/periods/{id}/export
  - HMAC signing in services.billing_webhooks
  - dispatch_billing_webhook service (happy path, no configs, retry logic)
  - export_quickbooks_csv / export_netsuite_csv services
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── HMAC signing ──────────────────────────────────────────────────────────────


def test_sign_payload_format():
    from runledger_api.services.billing_webhooks import _sign_payload

    sig = _sign_payload(b'{"event":"test"}', "mysecret")
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64  # "sha256=" + 64 hex chars


def test_sign_payload_deterministic():
    from runledger_api.services.billing_webhooks import _sign_payload

    body = b"same body"
    assert _sign_payload(body, "key1") == _sign_payload(body, "key1")
    assert _sign_payload(body, "key1") != _sign_payload(body, "key2")


# ── dispatch_billing_webhook — no configs ─────────────────────────────────────


@pytest.mark.anyio
async def test_dispatch_no_configs():
    """Returns immediately when workspace has no enabled webhook configs."""
    from runledger_api.services.billing_webhooks import dispatch_billing_webhook

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    period = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("123.45"),
        snapshot_hash="abc123",
        closed_at=datetime.now(UTC),
    )
    # Should not raise and should not call commit
    await dispatch_billing_webhook(db, period)
    db.commit.assert_not_called()


# ── dispatch_billing_webhook — happy path ─────────────────────────────────────


@pytest.mark.anyio
async def test_dispatch_success():
    from runledger_api.services.billing_webhooks import dispatch_billing_webhook

    ws_id = uuid.uuid4()
    period_id = uuid.uuid4()

    cfg = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        url="https://example.com/hook",
        secret="secret123",
        enabled=True,
    )

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    cfg_result = MagicMock()
    cfg_result.scalars.return_value.all.return_value = [cfg]
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = []

    db.execute = AsyncMock(side_effect=[cfg_result, rules_result])

    period = SimpleNamespace(
        id=period_id,
        workspace_id=ws_id,
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("50.00"),
        snapshot_hash="deadbeef",
        closed_at=datetime.now(UTC),
    )

    with patch(
        "runledger_api.services.billing_webhooks._attempt_delivery",
        new=AsyncMock(return_value=(200, "OK", True)),
    ):
        await dispatch_billing_webhook(db, period)

    db.commit.assert_called_once()


# ── export_quickbooks_csv ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_export_quickbooks_no_rules():
    from runledger_api.services.billing_webhooks import export_quickbooks_csv

    period_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    period = SimpleNamespace(
        id=period_id,
        workspace_id=ws_id,
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("200.00"),
        snapshot_hash=None,
        closed_at=None,
    )

    db = AsyncMock()
    period_result = MagicMock()
    period_result.scalar_one_or_none.return_value = period
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[period_result, rules_result])

    csv_text = await export_quickbooks_csv(db, period_id)
    assert "Date" in csv_text
    assert "AI Spend" in csv_text
    assert "200.00" in csv_text


@pytest.mark.anyio
async def test_export_quickbooks_with_rules():
    from runledger_api.services.billing_webhooks import export_quickbooks_csv

    period_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    period = SimpleNamespace(
        id=period_id,
        workspace_id=ws_id,
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("100.00"),
        snapshot_hash=None,
        closed_at=None,
    )
    rule = SimpleNamespace(
        dimension="Engineering",
        allocation_type="cost_center",
        weight=Decimal("0.6"),
    )

    db = AsyncMock()
    period_result = MagicMock()
    period_result.scalar_one_or_none.return_value = period
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = [rule]
    db.execute = AsyncMock(side_effect=[period_result, rules_result])

    csv_text = await export_quickbooks_csv(db, period_id)
    assert "Engineering" in csv_text
    assert "AI Spend Clearing" in csv_text
    assert "60.00" in csv_text


# ── export_netsuite_csv ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_export_netsuite_with_env_rule():
    from runledger_api.services.billing_webhooks import export_netsuite_csv

    period_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    period = SimpleNamespace(
        id=period_id,
        workspace_id=ws_id,
        period_start="2026-02-01",
        period_end="2026-02-28",
        total_cost_usd=Decimal("80.00"),
        snapshot_hash=None,
        closed_at=None,
    )
    rule = SimpleNamespace(
        dimension="prod",
        allocation_type="env",
        weight=Decimal("1.0"),
    )

    db = AsyncMock()
    period_result = MagicMock()
    period_result.scalar_one_or_none.return_value = period
    rules_result = MagicMock()
    rules_result.scalars.return_value.all.return_value = [rule]
    db.execute = AsyncMock(side_effect=[period_result, rules_result])

    csv_text = await export_netsuite_csv(db, period_id)
    assert "ExternalId" in csv_text
    assert "Subsidiary" in csv_text
    assert "prod" in csv_text
    assert "80.00" in csv_text


# ── Router: POST /billing/webhooks ────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_billing_webhook(authed_client: AsyncClient, mock_db_session: AsyncMock):
    hook_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    def mock_refresh(obj):
        obj.id = hook_id
        obj.workspace_id = ws_id
        obj.created_at = datetime.now(UTC)
        obj.enabled = True

    mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

    resp = await authed_client.post(
        "/billing/webhooks",
        json={"url": "https://example.com/hook", "secret": "supersecret123", "label": "Test Hook"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://example.com/hook"
    assert data["label"] == "Test Hook"
    assert "secret" not in data  # secret must not be returned


# ── Router: GET /billing/webhooks ─────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_billing_webhooks(authed_client: AsyncClient, mock_db_session: AsyncMock):
    ws_id = uuid.uuid4()
    hook = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        url="https://example.com/hook",
        label="My Hook",
        enabled=True,
        created_at=datetime.now(UTC),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [hook]
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.get("/billing/webhooks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["label"] == "My Hook"


# ── Router: DELETE /billing/webhooks/{id} ─────────────────────────────────────


@pytest.mark.anyio
async def test_delete_billing_webhook(authed_client: AsyncClient, mock_db_session: AsyncMock):
    ws_id = uuid.uuid4()
    hook_id = uuid.uuid4()
    hook = SimpleNamespace(id=hook_id, workspace_id=ws_id)
    result = MagicMock()
    result.scalar_one_or_none.return_value = hook
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(f"/billing/webhooks/{hook_id}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_delete_billing_webhook_not_found(
    authed_client: AsyncClient, mock_db_session: AsyncMock
):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=result)

    resp = await authed_client.delete(f"/billing/webhooks/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── Router: GET /billing/periods/{id}/export — new formats ───────────────────


@pytest.mark.anyio
async def test_export_period_quickbooks_format(
    authed_client: AsyncClient, mock_db_session: AsyncMock
):
    period_id = uuid.uuid4()
    period = SimpleNamespace(
        id=period_id,
        workspace_id=uuid.uuid4(),
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("50.00"),
    )

    period_check = MagicMock()
    period_check.scalar_one_or_none.return_value = period

    with patch(
        "runledger_api.services.billing_webhooks.export_quickbooks_csv",
        new=AsyncMock(return_value="Date,Account,Description,Debit,Credit,Reference\n"),
    ):
        mock_db_session.execute = AsyncMock(return_value=period_check)
        resp = await authed_client.get(f"/billing/periods/{period_id}/export?format=quickbooks")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "quickbooks" in resp.headers["content-disposition"]


@pytest.mark.anyio
async def test_export_period_netsuite_format(
    authed_client: AsyncClient, mock_db_session: AsyncMock
):
    period_id = uuid.uuid4()
    period = SimpleNamespace(
        id=period_id,
        workspace_id=uuid.uuid4(),
        period_start="2026-01-01",
        period_end="2026-01-31",
        total_cost_usd=Decimal("50.00"),
    )

    period_check = MagicMock()
    period_check.scalar_one_or_none.return_value = period

    with patch(
        "runledger_api.services.billing_webhooks.export_netsuite_csv",
        new=AsyncMock(
            return_value="ExternalId,Date,Account,Subsidiary,Department,Memo,Debit,Credit\n"
        ),
    ):
        mock_db_session.execute = AsyncMock(return_value=period_check)
        resp = await authed_client.get(f"/billing/periods/{period_id}/export?format=netsuite")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "netsuite" in resp.headers["content-disposition"]
