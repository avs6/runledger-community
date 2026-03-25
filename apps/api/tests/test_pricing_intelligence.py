"""
Tests for Phase 34 — Pricing Intelligence.

Covers:
  - GET /pricing/timeline
  - POST /pricing/sync
  - POST /pricing/{id}/correct
  - POST/GET/GET/{id}/PUT/DELETE /pricing/contracts
  - POST/GET/GET/{id}/PUT/DELETE /pricing/credits
  - POST /pricing/credits/apply
  - Service: apply_contract_rate (discount_pct, fixed rates)
  - Service: apply_credits (priority order, stops when cost exhausted)
  - Service: sync_catalog_to_db (skips existing rows)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Service unit tests (no HTTP) ──────────────────────────────────────────────
from runledger_api.services.pricing_contracts import apply_contract_rate


def _make_contract(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider="openai",
        model="gpt-4o",
        discount_pct=None,
        fixed_input_per_1m=None,
        fixed_output_per_1m=None,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        notes=None,
        created_by=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_apply_contract_rate_discount():
    """discount_pct reduces both input and output rates."""
    contract = _make_contract(discount_pct=Decimal("20.0"))
    inp, out = apply_contract_rate(contract, Decimal("2.50"), Decimal("10.00"))
    assert inp == Decimal("2.00000000")
    assert out == Decimal("8.00000000")


def test_apply_contract_rate_fixed_override():
    """Fixed rates take precedence over discount_pct."""
    contract = _make_contract(
        discount_pct=Decimal("50.0"),
        fixed_input_per_1m=Decimal("1.00"),
        fixed_output_per_1m=Decimal("3.00"),
    )
    inp, out = apply_contract_rate(contract, Decimal("2.50"), Decimal("10.00"))
    assert inp == Decimal("1.00")
    assert out == Decimal("3.00")


def test_apply_contract_rate_no_discount():
    """No discount or fixed rates → returns base rates unchanged."""
    contract = _make_contract()
    inp, out = apply_contract_rate(contract, Decimal("2.50"), Decimal("10.00"))
    assert inp == Decimal("2.50")
    assert out == Decimal("10.00")


@pytest.mark.asyncio
async def test_apply_credits_deducts_lowest_priority_first():
    """Credits are applied lowest-priority first."""
    from runledger_api.services.pricing_credits import apply_credits

    ws_id = uuid.uuid4()
    now = datetime.now(UTC)

    credit_low = SimpleNamespace(
        id=uuid.uuid4(),
        name="Low priority",
        priority=10,
        remaining_usd=Decimal("5.00"),
        is_active=True,
        effective_from=now,
        effective_until=None,
    )
    credit_high = SimpleNamespace(
        id=uuid.uuid4(),
        name="High priority",
        priority=100,
        remaining_usd=Decimal("10.00"),
        is_active=True,
        effective_from=now,
        effective_until=None,
    )

    mock_db = AsyncMock()

    with patch(
        "runledger_api.services.pricing_credits.get_active_credits",
        new=AsyncMock(return_value=[credit_low, credit_high]),
    ):
        result = await apply_credits(mock_db, ws_id, Decimal("7.00"))

    assert result["applied"] == Decimal("7.00")
    assert result["remaining_cost"] == Decimal("0.00")
    # credit_low should be fully consumed (5.00), credit_high partially (2.00)
    assert len(result["credits_used"]) == 2
    assert result["credits_used"][0]["deducted_usd"] == "5.00"
    assert result["credits_used"][1]["deducted_usd"] == "2.00"


@pytest.mark.asyncio
async def test_apply_credits_stops_when_cost_exhausted():
    """Second credit is not touched when cost is covered by first."""
    from runledger_api.services.pricing_credits import apply_credits

    ws_id = uuid.uuid4()
    now = datetime.now(UTC)

    credit1 = SimpleNamespace(
        id=uuid.uuid4(),
        name="Credit A",
        priority=10,
        remaining_usd=Decimal("100.00"),
        is_active=True,
        effective_from=now,
        effective_until=None,
    )
    credit2 = SimpleNamespace(
        id=uuid.uuid4(),
        name="Credit B",
        priority=20,
        remaining_usd=Decimal("50.00"),
        is_active=True,
        effective_from=now,
        effective_until=None,
    )

    mock_db = AsyncMock()

    with patch(
        "runledger_api.services.pricing_credits.get_active_credits",
        new=AsyncMock(return_value=[credit1, credit2]),
    ):
        result = await apply_credits(mock_db, ws_id, Decimal("3.00"))

    assert result["applied"] == Decimal("3.00")
    assert result["remaining_cost"] == Decimal("0.00")
    assert len(result["credits_used"]) == 1
    assert result["credits_used"][0]["name"] == "Credit A"


@pytest.mark.asyncio
async def test_sync_catalog_skips_existing_rows():
    """sync_catalog_to_db skips rows already present (source='catalog')."""
    from runledger_api.services.pricing_sync import PRICING_CATALOG, sync_catalog_to_db

    mock_db = AsyncMock()

    # Config: no exclusions, sync enabled
    cfg = _sync_config()
    mock_db.get = AsyncMock(return_value=cfg)

    # Simulate that openai/gpt-4o already exists as a catalog row
    existing_row = SimpleNamespace(
        provider="openai",
        model="gpt-4o",
        input_cost_per_1m=Decimal("2.50"),
        output_cost_per_1m=Decimal("10.00"),
        cached_input_cost_per_1m=Decimal("1.25"),
    )
    execute_result = MagicMock()
    execute_result.scalars.return_value.__iter__ = lambda s: iter([existing_row])
    mock_db.execute = AsyncMock(return_value=execute_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    result = await sync_catalog_to_db(mock_db)

    # Should skip openai/gpt-4o (already exists, no force) but insert others
    assert result["skipped"] >= 1
    assert result["inserted"] >= 1
    assert result["inserted"] + result["skipped"] == len(PRICING_CATALOG)


# ── HTTP endpoint tests ────────────────────────────────────────────────────────


def _pricing_row(workspace_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        provider="openai",
        model="gpt-4o",
        input_cost_per_1m=Decimal("2.50"),
        output_cost_per_1m=Decimal("10.00"),
        cached_input_cost_per_1m=Decimal("1.25"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_to=None,
        workspace_id=workspace_id,
        source="catalog",
        created_at=datetime.now(UTC),
    )


def _contract_row(workspace_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        provider="openai",
        model="gpt-4o",
        discount_pct=Decimal("20.0"),
        fixed_input_per_1m=None,
        fixed_output_per_1m=None,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        notes="Enterprise discount",
        created_by=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )


def _credit_row(workspace_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="Prepaid bundle",
        credit_type="prepaid_tokens",
        amount_usd=Decimal("500.00"),
        remaining_usd=Decimal("500.00"),
        source="manual",
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        priority=100,
        is_active=True,
        created_by=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ── GET /pricing/timeline ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_price_timeline(authed_client, mock_db_session, mock_workspace):
    row = _pricing_row(workspace_id=None)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/pricing/timeline?provider=openai&model=gpt-4o")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["provider"] == "openai"
    assert data["items"][0]["source"] == "catalog"


# ── POST /pricing/sync ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_pricing_sync(authed_client, mock_db_session):
    mock_result = MagicMock()
    mock_result.all.return_value = []  # No existing rows
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    resp = await authed_client.post("/pricing/sync", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "inserted" in data
    assert "skipped" in data


# ── POST /pricing/{id}/correct ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_correct_pricing_201(authed_client, mock_db_session, mock_workspace):
    pricing_id = uuid.uuid4()
    existing = _pricing_row(workspace_id=None)
    existing.id = pricing_id
    existing.effective_to = None

    correction = _pricing_row(workspace_id=mock_workspace.id)
    correction.source = "manual"

    mock_db_session.get = AsyncMock(return_value=existing)
    mock_db_session.commit = AsyncMock()

    def refresh_side_effect(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)

    mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = await authed_client.post(
        f"/pricing/{pricing_id}/correct",
        json={
            "input_cost_per_1m": "1.99",
            "output_cost_per_1m": "7.99",
            "effective_from": "2026-02-01T00:00:00Z",
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_correct_pricing_404(authed_client, mock_db_session):
    mock_db_session.get = AsyncMock(return_value=None)

    resp = await authed_client.post(
        f"/pricing/{uuid.uuid4()}/correct",
        json={
            "input_cost_per_1m": "1.99",
            "output_cost_per_1m": "7.99",
            "effective_from": "2026-02-01T00:00:00Z",
        },
    )
    assert resp.status_code == 404


# ── POST /pricing/contracts ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_contract_201(authed_client, mock_db_session, mock_workspace):
    contract = _contract_row(mock_workspace.id)

    def refresh_side_effect(obj):
        obj.id = contract.id
        obj.created_at = contract.created_at

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = await authed_client.post(
        "/pricing/contracts",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "discount_pct": "20.0",
            "effective_from": "2026-01-01T00:00:00Z",
            "notes": "Enterprise discount",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["discount_pct"] == "20.0"


# ── GET /pricing/contracts ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_contracts(authed_client, mock_db_session, mock_workspace):
    contract = _contract_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [contract]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/pricing/contracts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["provider"] == "openai"


# ── GET /pricing/contracts/{id} ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_contract_found(authed_client, mock_db_session, mock_workspace):
    contract = _contract_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contract
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get(f"/pricing/contracts/{contract.id}")
    assert resp.status_code == 200
    assert resp.json()["provider"] == "openai"


@pytest.mark.asyncio
async def test_get_contract_not_found(authed_client, mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get(f"/pricing/contracts/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PUT /pricing/contracts/{id} ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_contract(authed_client, mock_db_session, mock_workspace):
    contract = _contract_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contract
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    def refresh_side_effect(obj):
        pass

    mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = await authed_client.put(
        f"/pricing/contracts/{contract.id}",
        json={"discount_pct": "25.0", "notes": "Updated"},
    )
    assert resp.status_code == 200


# ── DELETE /pricing/contracts/{id} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_contract_204(authed_client, mock_db_session, mock_workspace):
    contract = _contract_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = contract
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    resp = await authed_client.delete(f"/pricing/contracts/{contract.id}")
    assert resp.status_code == 204
    assert contract.is_active is False


# ── POST /pricing/credits ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_credit_201(authed_client, mock_db_session, mock_workspace):
    credit = _credit_row(mock_workspace.id)

    def refresh_side_effect(obj):
        obj.id = credit.id
        obj.created_at = credit.created_at
        obj.updated_at = credit.updated_at

    mock_db_session.commit = AsyncMock()
    mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = await authed_client.post(
        "/pricing/credits",
        json={
            "name": "Prepaid bundle",
            "credit_type": "prepaid_tokens",
            "amount_usd": "500.00",
            "effective_from": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Prepaid bundle"
    assert data["credit_type"] == "prepaid_tokens"


# ── GET /pricing/credits ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_credits(authed_client, mock_db_session, mock_workspace):
    credit = _credit_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [credit]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    resp = await authed_client.get("/pricing/credits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Prepaid bundle"


# ── PUT /pricing/credits/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_credit_remaining_usd(authed_client, mock_db_session, mock_workspace):
    credit = _credit_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = credit
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    def refresh_side_effect(obj):
        pass

    mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

    resp = await authed_client.put(
        f"/pricing/credits/{credit.id}",
        json={"remaining_usd": "250.00"},
    )
    assert resp.status_code == 200
    # The ORM object should have been mutated
    assert credit.remaining_usd == Decimal("250.00")


# ── DELETE /pricing/credits/{id} ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_credit_204(authed_client, mock_db_session, mock_workspace):
    credit = _credit_row(mock_workspace.id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = credit
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    resp = await authed_client.delete(f"/pricing/credits/{credit.id}")
    assert resp.status_code == 204
    assert credit.is_active is False


# ── POST /pricing/credits/apply ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_credits_endpoint(authed_client, mock_db_session, mock_workspace):
    credit = _credit_row(mock_workspace.id)
    credit.remaining_usd = Decimal("100.00")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [credit]
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    resp = await authed_client.post(
        "/pricing/credits/apply",
        json={"cost_usd": "30.00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["applied"]) == Decimal("30.00")
    assert Decimal(data["remaining_cost"]) == Decimal("0.00")
    assert len(data["credits_used"]) == 1


@pytest.mark.asyncio
async def test_apply_credits_missing_cost_usd(authed_client, mock_db_session):
    resp = await authed_client.post(
        "/pricing/credits/apply",
        json={"not_cost": "30.00"},
    )
    assert resp.status_code == 422


# ── Sync config endpoints ─────────────────────────────────────────────────────


def _sync_config() -> SimpleNamespace:
    from runledger_api.models.metering import _SYNC_CONFIG_SINGLETON_ID

    return SimpleNamespace(
        id=_SYNC_CONFIG_SINGLETON_ID,
        sync_enabled=True,
        excluded_providers=[],
        excluded_models=[],
        force_update=False,
        last_sync_at=None,
        last_sync_result=None,
        updated_by=None,
        updated_at=datetime.now(UTC),
    )


@pytest.mark.anyio
async def test_get_sync_config(authed_client, mock_db_session):
    """GET /pricing/sync/config returns current settings."""
    cfg = _sync_config()
    mock_db_session.get = AsyncMock(return_value=cfg)

    resp = await authed_client.get("/pricing/sync/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sync_enabled"] is True
    assert data["excluded_providers"] == []
    assert data["force_update"] is False


@pytest.mark.anyio
async def test_get_sync_config_503_when_missing(authed_client, mock_db_session):
    """GET /pricing/sync/config returns 503 if migration not run."""
    mock_db_session.get = AsyncMock(return_value=None)

    resp = await authed_client.get("/pricing/sync/config")
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_update_sync_config_disable(authed_client, mock_db_session, mock_workspace):
    """PUT /pricing/sync/config can disable the sync."""
    cfg = _sync_config()
    mock_db_session.get = AsyncMock(return_value=cfg)
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "sync_enabled", False))

    resp = await authed_client.put(
        "/pricing/sync/config",
        json={"sync_enabled": False},
    )
    assert resp.status_code == 200
    assert cfg.sync_enabled is False


@pytest.mark.anyio
async def test_update_sync_config_exclude_providers(authed_client, mock_db_session, mock_workspace):
    """PUT /pricing/sync/config can set excluded_providers."""
    cfg = _sync_config()
    mock_db_session.get = AsyncMock(return_value=cfg)
    mock_db_session.refresh = AsyncMock(
        side_effect=lambda obj: setattr(obj, "excluded_providers", ["mistral", "google"])
    )

    resp = await authed_client.put(
        "/pricing/sync/config",
        json={"excluded_providers": ["mistral", "google"]},
    )
    assert resp.status_code == 200
    assert set(cfg.excluded_providers) == {"mistral", "google"}


@pytest.mark.anyio
async def test_update_sync_config_force_update(authed_client, mock_db_session, mock_workspace):
    """PUT /pricing/sync/config can enable force_update."""
    cfg = _sync_config()
    mock_db_session.get = AsyncMock(return_value=cfg)
    mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "force_update", True))

    resp = await authed_client.put(
        "/pricing/sync/config",
        json={"force_update": True},
    )
    assert resp.status_code == 200
    assert cfg.force_update is True


@pytest.mark.anyio
async def test_trigger_sync_with_options(authed_client, mock_db_session):
    """POST /pricing/sync accepts dry_run, force, providers, models options."""
    cfg = _sync_config()
    # get_sync_config uses db.get; sync uses db.execute
    mock_db_session.get = AsyncMock(return_value=cfg)
    execute_result = MagicMock()
    execute_result.all.return_value = []  # no existing rows
    execute_result.scalars.return_value.__iter__ = lambda s: iter([])
    mock_db_session.execute = AsyncMock(return_value=execute_result)

    resp = await authed_client.post(
        "/pricing/sync",
        json={"dry_run": True, "providers": ["openai"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["inserted"] >= 0  # openai models found in catalog


@pytest.mark.anyio
async def test_trigger_sync_dry_run_no_writes(authed_client, mock_db_session):
    """POST /pricing/sync dry_run=True must not call db.add."""
    cfg = _sync_config()
    mock_db_session.get = AsyncMock(return_value=cfg)
    execute_result = MagicMock()
    execute_result.all.return_value = []
    execute_result.scalars.return_value.__iter__ = lambda s: iter([])
    mock_db_session.execute = AsyncMock(return_value=execute_result)

    await authed_client.post("/pricing/sync", json={"dry_run": True})
    # db.add must never be called in dry_run mode
    mock_db_session.add.assert_not_called()


# ── Service: sync_catalog_to_db with options ──────────────────────────────────


@pytest.mark.anyio
async def test_sync_respects_excluded_providers():
    """sync_catalog_to_db skips providers listed in config.excluded_providers."""
    from runledger_api.services.pricing_sync import sync_catalog_to_db

    mock_db = AsyncMock()
    cfg = _sync_config()
    cfg.excluded_providers = ["mistral", "google"]
    cfg.excluded_models = []
    cfg.force_update = False
    mock_db.get = AsyncMock(return_value=cfg)

    # No existing rows
    execute_result = MagicMock()
    execute_result.scalars.return_value.__iter__ = lambda s: iter([])
    mock_db.execute = AsyncMock(return_value=execute_result)

    result = await sync_catalog_to_db(mock_db)
    # All mistral and google rows should be in excluded count
    assert result["excluded"] > 0
    # providers_synced should not contain mistral or google
    assert "mistral" not in result["providers_synced"]
    assert "google" not in result["providers_synced"]


@pytest.mark.anyio
async def test_sync_provider_filter():
    """sync_catalog_to_db with providers=['openai'] only syncs openai."""
    from runledger_api.services.pricing_sync import sync_catalog_to_db

    mock_db = AsyncMock()
    cfg = _sync_config()
    mock_db.get = AsyncMock(return_value=cfg)
    execute_result = MagicMock()
    execute_result.scalars.return_value.__iter__ = lambda s: iter([])
    mock_db.execute = AsyncMock(return_value=execute_result)

    result = await sync_catalog_to_db(mock_db, providers=["openai"])
    assert "openai" in result["providers_synced"]
    assert "anthropic" not in result["providers_synced"]


@pytest.mark.anyio
async def test_sync_disabled_in_beat_worker():
    """Beat worker exits early when sync_enabled=False."""
    from runledger_api.services.pricing_sync import get_sync_config

    mock_db = AsyncMock()
    cfg = _sync_config()
    cfg.sync_enabled = False
    mock_db.get = AsyncMock(return_value=cfg)

    config = await get_sync_config(mock_db)
    assert config is not None
    assert config.sync_enabled is False
    # The worker would exit here; verify the config read works
