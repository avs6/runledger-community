"""
Tests for Phase 22 — SaaS Foundation.

Covers: signup, subscription retrieval, checkout/portal (Stripe disabled),
quota enforcement, quota increment, stripe webhook dispatch.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sub(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        stripe_customer_id=None,
        stripe_subscription_id=None,
        plan="free",
        status="active",
        current_period_start=datetime.now(UTC),
        current_period_end=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_quota(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        events_limit=10_000,
        events_used=0,
        period_start=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── Signup ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signup_creates_account(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    """POST /auth/signup returns 201 with api_key when email is new."""
    # No existing user found
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    # Capture added objects and assign UUIDs on flush so the response validates
    added: list[object] = []
    mock_db_session.add = MagicMock(side_effect=added.append)
    mock_db_session.commit = AsyncMock()

    async def fake_flush() -> None:
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    mock_db_session.flush = fake_flush

    with patch("runledger_api.routers.saas.generate_api_key", return_value=("rl_test_abc", "hash", "rl_test_")):
        resp = await client.post("/auth/signup", json={
            "email": "alice@example.com",
            "password": "password123",
            "full_name": "Alice Smith",
            "org_name": "Acme Corp",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["api_key"] == "rl_test_abc"
    assert "workspace_id" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409(client: AsyncClient, mock_db_session: AsyncMock) -> None:
    """POST /auth/signup returns 409 when email already exists."""
    existing_user = SimpleNamespace(id=uuid.uuid4(), email="alice@example.com")
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
    )

    resp = await client.post("/auth/signup", json={
        "email": "alice@example.com",
        "password": "password123",
        "full_name": "Alice Smith",
        "org_name": "Acme",
    })

    assert resp.status_code == 409


# ── Subscription ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_subscription_returns_plan(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    """GET /billing/subscription returns plan + usage data."""
    tenant_id = mock_workspace.tenant_id
    sub = _make_sub(tenant_id=tenant_id, plan="starter", events_used=0)
    quota = _make_quota(tenant_id=tenant_id, events_limit=500_000, events_used=12_345)

    mock_db_session.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=sub)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=quota)),
    ])

    resp = await authed_client.get("/billing/subscription")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "starter"
    assert data["events_used"] == 12_345
    assert data["events_limit"] == 500_000
    assert data["usage_pct"] == pytest.approx(2.469, abs=0.01)


@pytest.mark.asyncio
async def test_get_subscription_no_rows_returns_free_defaults(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    """GET /billing/subscription returns free defaults when no DB rows exist."""
    mock_db_session.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ])

    resp = await authed_client.get("/billing/subscription")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["events_limit"] == 10_000
    assert data["events_used"] == 0


# ── Stripe disabled ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkout_without_stripe_returns_503(authed_client: AsyncClient) -> None:
    """POST /billing/checkout returns 503 when STRIPE_SECRET_KEY not set."""
    resp = await authed_client.post("/billing/checkout", json={
        "plan": "starter",
        "success_url": "http://localhost:3000/billing/subscription?upgraded=1",
        "cancel_url": "http://localhost:3000/billing/subscription",
    })
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_portal_without_stripe_returns_503(authed_client: AsyncClient) -> None:
    """POST /billing/portal returns 503 when STRIPE_SECRET_KEY not set."""
    resp = await authed_client.post("/billing/portal", json={
        "return_url": "http://localhost:3000/billing/subscription",
    })
    assert resp.status_code == 503


# ── Quota enforcement ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quota_check_blocks_at_limit(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    """POST /ingest/v1/events returns 402 when quota exhausted."""
    quota = _make_quota(
        tenant_id=mock_workspace.tenant_id,
        events_limit=100,
        events_used=100,
    )
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=quota))
    )

    resp = await authed_client.post("/ingest/v1/events", json={"event_type": "run_start", "run_id": str(uuid.uuid4()), "started_at": datetime.now(UTC).isoformat()})
    assert resp.status_code == 402
    assert resp.json()["detail"]["error"] == "quota_exceeded"


@pytest.mark.asyncio
async def test_quota_check_allows_when_under_limit(authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace) -> None:
    """POST /ingest/v1/events returns 202 when quota not exceeded."""
    quota = _make_quota(
        tenant_id=mock_workspace.tenant_id,
        events_limit=10_000,
        events_used=42,
    )
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=quota))
    )
    mock_db_session.commit = AsyncMock()

    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post("/ingest/v1/events", json={"event_type": "run_start", "run_id": str(uuid.uuid4()), "started_at": datetime.now(UTC).isoformat()})

    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_quota_check_allows_when_no_row(authed_client: AsyncClient, mock_db_session: AsyncMock) -> None:
    """POST /ingest/v1/events allows request when no quota row (OSS self-hosted path)."""
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db_session.commit = AsyncMock()

    with patch("runledger_api.routers.ingest.process_events_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await authed_client.post("/ingest/v1/events", json={"event_type": "run_start", "run_id": str(uuid.uuid4()), "started_at": datetime.now(UTC).isoformat()})

    assert resp.status_code == 202


# ── Stripe webhook ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stripe_webhook_without_stripe_returns_503(client: AsyncClient) -> None:
    """POST /webhooks/stripe returns 503 when STRIPE_SECRET_KEY not configured."""
    resp = await client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=abc"})
    assert resp.status_code == 503
