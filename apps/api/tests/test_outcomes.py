"""
Tests for Phase 24 — Outcome & ROI Ledger.

Covers:
  POST /outcomes                         — create outcome
  GET  /outcomes                         — list outcomes with filters
  GET  /outcomes/summary                 — cost-per-outcome + ROI aggregation
  GET  /outcomes/trend                   — daily rollup trend
  GET  /outcomes/workflows               — workflow ROI by feature_tag
  GET  /outcomes/quality-correlation     — quality score ↔ success rate

Also covers the SDK rl.outcome() method (unit test, local=True).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scalars_list(rows: list) -> MagicMock:
    m = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m.scalars = MagicMock(return_value=scalars)
    return m


def _scalar(val) -> MagicMock:
    m = MagicMock()
    m.scalar = MagicMock(return_value=val)
    return m


def _rows(rows: list) -> MagicMock:
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _make_outcome(**kwargs) -> SimpleNamespace:
    ws_id = uuid.uuid4()
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        run_id=uuid.uuid4(),
        session_id="sess_abc",
        end_user_id="user_1",
        outcome_type="checkout_completed",
        success=True,
        value_usd=Decimal("5.00"),
        labels={},
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_rollup(**kwargs) -> SimpleNamespace:
    defaults = dict(
        workspace_id=uuid.uuid4(),
        day=date(2026, 3, 21),
        outcome_type="checkout_completed",
        success_rate=Decimal("0.8500"),
        count=20,
        total_cost_usd=Decimal("0.004000"),
        cost_per_success_usd=Decimal("0.000470"),
        total_value_usd=Decimal("85.00"),
        roi=Decimal("2025.0000"),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_agg_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        outcome_type="checkout_completed",
        count=10,
        success_count_raw=8,
        total_value=Decimal("40.00"),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_workflow_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        feature_tag="checkout-flow",
        outcome_type="checkout_completed",
        run_count=5,
        total_value=Decimal("25.00"),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_corr_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        outcome_type="checkout_completed",
        total=10,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_corr_sc_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        outcome_type="checkout_completed",
        sc=8,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_corr_score_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        outcome_type="checkout_completed",
        avg_score=Decimal("82.5"),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /outcomes ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_outcome_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    outcome = _make_outcome(workspace_id=mock_workspace.id)

    async def mock_refresh(obj: object) -> None:
        obj.id = outcome.id  # type: ignore[attr-defined]
        obj.created_at = outcome.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.post(
        "/outcomes",
        json={
            "outcome_type": "checkout_completed",
            "success": True,
            "value_usd": "5.00",
            "labels": {},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["outcome_type"] == "checkout_completed"
    assert data["success"] is True


@pytest.mark.asyncio
async def test_create_outcome_with_run_id(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    run_id = str(uuid.uuid4())
    outcome = _make_outcome(workspace_id=mock_workspace.id, run_id=uuid.UUID(run_id))

    async def mock_refresh(obj: object) -> None:
        obj.id = outcome.id  # type: ignore[attr-defined]
        obj.created_at = outcome.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    resp = await authed_client.post(
        "/outcomes",
        json={
            "outcome_type": "lead_qualified",
            "success": False,
            "run_id": run_id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["outcome_type"] == "lead_qualified"
    assert data["success"] is False


@pytest.mark.asyncio
async def test_create_outcome_unauthenticated(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/outcomes",
        json={"outcome_type": "checkout_completed", "success": True},
    )
    assert resp.status_code == 401


# ── GET /outcomes ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_outcomes_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(0), _scalars_list([])]
    )
    resp = await authed_client.get("/outcomes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_outcomes_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    outcome = _make_outcome(workspace_id=mock_workspace.id)
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(1), _scalars_list([outcome])]
    )
    resp = await authed_client.get("/outcomes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["outcome_type"] == "checkout_completed"


@pytest.mark.asyncio
async def test_list_outcomes_filter_by_type(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(0), _scalars_list([])]
    )
    resp = await authed_client.get("/outcomes?outcome_type=lead_qualified")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_outcomes_filter_by_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_scalar(0), _scalars_list([])]
    )
    resp = await authed_client.get("/outcomes?success=true")
    assert resp.status_code == 200


# ── GET /outcomes/summary ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outcome_summary_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_rows([]))
    resp = await authed_client.get("/outcomes/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["window_days"] == 30


@pytest.mark.asyncio
async def test_outcome_summary_with_data(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agg = _make_agg_row()
    success_row = SimpleNamespace(outcome_type="checkout_completed", success_count=8)
    cost_row = SimpleNamespace(outcome_type="checkout_completed", total_cost=Decimal("0.004"))

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _rows([agg]),
            _rows([success_row]),
            _rows([cost_row]),
        ]
    )
    resp = await authed_client.get("/outcomes/summary?window_days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["outcome_type"] == "checkout_completed"
    assert item["count"] == 10
    assert item["success_count"] == 8
    assert float(item["success_rate"]) == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_outcome_summary_roi_computed(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    agg = _make_agg_row(total_value=Decimal("40.00"))
    success_row = SimpleNamespace(outcome_type="checkout_completed", success_count=8)
    cost_row = SimpleNamespace(outcome_type="checkout_completed", total_cost=Decimal("1.00"))

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _rows([agg]),
            _rows([success_row]),
            _rows([cost_row]),
        ]
    )
    resp = await authed_client.get("/outcomes/summary")
    assert resp.status_code == 200
    data = resp.json()
    item = data["items"][0]
    # ROI = (40 - 1) / 1 * 100 = 3900%
    assert float(item["roi"]) == pytest.approx(3900.0)


# ── GET /outcomes/trend ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outcome_trend_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/outcomes/trend")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_outcome_trend_returns_rollups(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    rollup = _make_rollup()
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([rollup]))
    resp = await authed_client.get("/outcomes/trend?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["outcome_type"] == "checkout_completed"
    assert item["count"] == 20
    assert float(item["success_rate"]) == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_outcome_trend_filter_by_type(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_scalars_list([]))
    resp = await authed_client.get("/outcomes/trend?outcome_type=lead_qualified")
    assert resp.status_code == 200


# ── GET /outcomes/workflows ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_workflow_roi_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(return_value=_rows([]))
    resp = await authed_client.get("/outcomes/workflows")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_workflow_roi_with_data(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    wf_row = _make_workflow_row()
    success_row = SimpleNamespace(
        feature_tag="checkout-flow",
        outcome_type="checkout_completed",
        success_count=4,
    )
    cost_row = SimpleNamespace(
        feature_tag="checkout-flow",
        outcome_type="checkout_completed",
        total_cost=Decimal("0.50"),
    )
    mock_db_session.execute = AsyncMock(
        side_effect=[_rows([wf_row]), _rows([success_row]), _rows([cost_row])]
    )
    resp = await authed_client.get("/outcomes/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["feature_tag"] == "checkout-flow"
    assert item["run_count"] == 5
    assert item["success_count"] == 4
    # ROI = (25 - 0.5) / 0.5 * 100 = 4900%
    assert float(item["roi"]) == pytest.approx(4900.0)


# ── GET /outcomes/quality-correlation ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_quality_correlation_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    mock_db_session.execute = AsyncMock(
        side_effect=[_rows([]), _rows([]), _rows([])]
    )
    resp = await authed_client.get("/outcomes/quality-correlation")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_quality_correlation_with_data(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    total_row = _make_corr_row()
    success_row = _make_corr_sc_row()
    score_row = _make_corr_score_row()

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _rows([total_row]),
            _rows([success_row]),
            _rows([score_row]),
        ]
    )
    resp = await authed_client.get("/outcomes/quality-correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert item["outcome_type"] == "checkout_completed"
    assert float(item["success_rate"]) == pytest.approx(0.8)
    assert float(item["avg_score"]) == pytest.approx(82.5)
    assert item["sample_count"] == 10


# ── SDK rl.outcome() unit test ─────────────────────────────────────────────────

def test_sdk_outcome_local_mode() -> None:
    """rl.outcome() in local=True mode should log and not call the network."""
    from runledger_sdk.client import RunLedger

    rl = RunLedger(local=True)
    # Should not raise — just logs
    rl.outcome("checkout_completed", success=True, value_usd=5.0)


def test_sdk_outcome_posts_to_api() -> None:
    """rl.outcome() should POST to /outcomes with correct payload."""
    import httpx
    from runledger_sdk.client import RunLedger

    rl = RunLedger(api_key="rl_test_key")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        rl.outcome(
            "checkout_completed",
            success=True,
            value_usd=5.0,
            labels={"channel": "web"},
        )

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "/outcomes" in call_kwargs[0][0]
    payload = call_kwargs[1]["json"]
    assert payload["outcome_type"] == "checkout_completed"
    assert payload["success"] is True
    assert payload["value_usd"] == 5.0
    assert payload["labels"] == {"channel": "web"}


def test_sdk_outcome_fails_gracefully() -> None:
    """rl.outcome() should swallow exceptions and not propagate."""
    from runledger_sdk.client import RunLedger

    rl = RunLedger(api_key="rl_test_key")

    with patch("httpx.post", side_effect=Exception("network error")):
        # Must not raise
        rl.outcome("checkout_completed", success=True)
