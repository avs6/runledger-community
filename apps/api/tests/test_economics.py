"""
Tests for Phase 9 unit-economics and change-impact endpoints.

Covers:
  GET  /analytics/economics/{run_id}  — per-run cost by span type + model
  GET  /analytics/workflows/top       — top workflow groups
  GET  /analytics/compare             — version-to-version cost/token/latency delta
  GET  /analytics/regressions         — cost regression detection
  POST /analytics/annotations         — create annotation
  GET  /analytics/annotations         — list annotations

Uses authed_client / mock_db_session fixtures from conftest. No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


# ── Mock result helpers ────────────────────────────────────────────────────────


def _scalar_orm_result(value: object) -> MagicMock:
    """Result where .scalar_one_or_none() returns value (ORM model lookup)."""
    m = MagicMock()
    m.scalar_one_or_none = MagicMock(return_value=value)
    return m


def _scalar_value_result(value: object) -> MagicMock:
    """Result where .scalar() returns value (aggregate query)."""
    m = MagicMock()
    m.scalar = MagicMock(return_value=value)
    return m


def _row_result(rows: list[object]) -> MagicMock:
    """Result where .all() returns a list of rows."""
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _one_result(row: object) -> MagicMock:
    """Result where .one() returns a single row."""
    m = MagicMock()
    m.one = MagicMock(return_value=row)
    return m


def _scalars_list_result(rows: list[object]) -> MagicMock:
    """Result where .scalars().all() returns rows (ORM list query)."""
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


# ── Fixtures / factories ───────────────────────────────────────────────────────


def _make_run(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        feature_tag="chat",
        application_id=None,
        deployment_version="v1",
        total_cost_usd=Decimal("0.05"),
        total_input_tokens=1000,
        total_output_tokens=500,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        status="succeeded",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_annotation(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        note="switched to gpt-4o-mini",
        annotation_date=date(2026, 2, 27),
        version="v2",
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── GET /analytics/economics/{run_id} — span types ────────────────────────────


@pytest.mark.asyncio
async def test_run_economics_by_span_type(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /economics/{run_id} → cost_by_span_type is populated."""
    run = _make_run()
    span_rows = [
        SimpleNamespace(span_type="llm", cost_usd=Decimal("0.04")),
        SimpleNamespace(span_type="tool", cost_usd=Decimal("0.01")),
    ]
    model_rows = [
        SimpleNamespace(
            model="gpt-4o", provider="openai", cost_usd=Decimal("0.05"), call_count=2
        )
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_orm_result(run),   # run lookup
            _row_result(span_rows),    # span-type costs
            _row_result(model_rows),   # model costs
            _scalar_value_result(Decimal("0")),  # retry cost
        ]
    )

    response = await authed_client.get(f"/analytics/economics/{run.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == str(run.id)
    types = [s["span_type"] for s in data["cost_by_span_type"]]
    assert "llm" in types
    assert "tool" in types
    assert float(data["total_cost_usd"]) == pytest.approx(0.05)


# ── GET /analytics/economics/{run_id} — models ────────────────────────────────


@pytest.mark.asyncio
async def test_run_economics_by_model(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /economics/{run_id} → cost_by_model is populated."""
    run = _make_run()
    span_rows: list[object] = []
    model_rows = [
        SimpleNamespace(
            model="gpt-4o-mini", provider="openai", cost_usd=Decimal("0.02"), call_count=3
        )
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalar_orm_result(run),
            _row_result(span_rows),
            _row_result(model_rows),
            _scalar_value_result(Decimal("0")),
        ]
    )

    response = await authed_client.get(f"/analytics/economics/{run.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["cost_by_model"]) == 1
    assert data["cost_by_model"][0]["model"] == "gpt-4o-mini"
    assert data["cost_by_model"][0]["call_count"] == 3


# ── GET /analytics/economics/{run_id} — 404 ───────────────────────────────────


@pytest.mark.asyncio
async def test_run_economics_404(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Unknown run_id in wrong workspace → 404."""
    mock_db_session.execute = AsyncMock(return_value=_scalar_orm_result(None))

    response = await authed_client.get(f"/analytics/economics/{uuid.uuid4()}")

    assert response.status_code == 404


# ── GET /analytics/workflows/top — items ──────────────────────────────────────


@pytest.mark.asyncio
async def test_top_workflows_returns_list(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /workflows/top → items list with expected fields."""
    run_rows = [
        SimpleNamespace(
            feature_tag="chat",
            application_id=None,
            run_count=10,
            avg_cost_usd=Decimal("0.05"),
            p95_cost_usd=Decimal("0.12"),
            total_cost_usd=Decimal("0.50"),
        )
    ]
    call_rows = [
        SimpleNamespace(feature_tag="chat", application_id=None, call_count=30)
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[_row_result(run_rows), _row_result(call_rows)]
    )

    response = await authed_client.get("/analytics/workflows/top")

    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "cost"
    assert len(data["items"]) == 1
    assert data["items"][0]["feature_tag"] == "chat"
    assert data["items"][0]["run_count"] == 10
    assert data["items"][0]["call_count"] == 30


# ── GET /analytics/workflows/top — limit ──────────────────────────────────────


@pytest.mark.asyncio
async def test_top_workflows_limit(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """?limit=5 is honoured (SQL LIMIT applied; mock returns empty list)."""
    mock_db_session.execute = AsyncMock(
        side_effect=[_row_result([]), _row_result([])]
    )

    response = await authed_client.get("/analytics/workflows/top?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


# ── GET /analytics/compare — delta computed ────────────────────────────────────


@pytest.mark.asyncio
async def test_version_compare_delta_pct(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """cost_delta_pct computed correctly from mocked version data."""
    base_row = SimpleNamespace(
        run_count=20,
        avg_cost_usd=Decimal("0.10"),
        avg_input_tokens=Decimal("500"),
        avg_output_tokens=Decimal("200"),
        avg_latency_ms=Decimal("1200"),
    )
    cmp_row = SimpleNamespace(
        run_count=25,
        avg_cost_usd=Decimal("0.15"),
        avg_input_tokens=Decimal("600"),
        avg_output_tokens=Decimal("240"),
        avg_latency_ms=Decimal("1100"),
    )
    span_rows: list[object] = []

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _one_result(base_row),   # baseline run stats
            _one_result(cmp_row),    # comparison run stats
            _row_result(span_rows),  # baseline span costs
            _row_result(span_rows),  # comparison span costs
        ]
    )

    response = await authed_client.get(
        "/analytics/compare?baseline_version=v1&comparison_version=v2"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["baseline"]["version"] == "v1"
    assert data["comparison"]["version"] == "v2"
    # (0.15 - 0.10) / 0.10 * 100 = 50.0
    assert float(data["cost_delta_pct"]) == pytest.approx(50.0)


# ── GET /analytics/compare — zero baseline ────────────────────────────────────


@pytest.mark.asyncio
async def test_version_compare_missing_baseline(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Baseline has 0 avg cost → cost_delta_pct is None."""
    base_row = SimpleNamespace(
        run_count=0,
        avg_cost_usd=Decimal("0"),
        avg_input_tokens=Decimal("0"),
        avg_output_tokens=Decimal("0"),
        avg_latency_ms=None,
    )
    cmp_row = SimpleNamespace(
        run_count=10,
        avg_cost_usd=Decimal("0.10"),
        avg_input_tokens=Decimal("300"),
        avg_output_tokens=Decimal("150"),
        avg_latency_ms=Decimal("900"),
    )
    span_rows: list[object] = []

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _one_result(base_row),
            _one_result(cmp_row),
            _row_result(span_rows),
            _row_result(span_rows),
        ]
    )

    response = await authed_client.get(
        "/analytics/compare?baseline_version=v0&comparison_version=v1"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cost_delta_pct"] is None


# ── GET /analytics/regressions — flagged ──────────────────────────────────────


@pytest.mark.asyncio
async def test_regressions_detected(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """>20% cost increase with run_count>=3 is flagged in items."""
    curr_rows = [
        SimpleNamespace(feature_tag="chat", avg_cost=Decimal("0.30"), run_count=5)
    ]
    prior_rows = [
        SimpleNamespace(feature_tag="chat", avg_cost=Decimal("0.20"), run_count=6)
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[_row_result(curr_rows), _row_result(prior_rows)]
    )

    response = await authed_client.get("/analytics/regressions")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["feature_tag"] == "chat"
    # (0.30 - 0.20) / 0.20 * 100 = 50.0
    assert float(data["items"][0]["change_pct"]) == pytest.approx(50.0)


# ── GET /analytics/regressions — not flagged ──────────────────────────────────


@pytest.mark.asyncio
async def test_regressions_below_threshold(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """<20% increase → items is empty."""
    curr_rows = [
        SimpleNamespace(feature_tag="search", avg_cost=Decimal("0.22"), run_count=5)
    ]
    prior_rows = [
        SimpleNamespace(feature_tag="search", avg_cost=Decimal("0.20"), run_count=5)
    ]

    mock_db_session.execute = AsyncMock(
        side_effect=[_row_result(curr_rows), _row_result(prior_rows)]
    )

    response = await authed_client.get("/analytics/regressions")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


# ── POST /analytics/annotations ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_annotation(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """POST /annotations → 201 with correct fields."""
    annot_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def mock_refresh(obj: object) -> None:
        obj.id = annot_id  # type: ignore[attr-defined]
        obj.created_at = created_at  # type: ignore[attr-defined]

    mock_db_session.refresh = mock_refresh

    response = await authed_client.post(
        "/analytics/annotations",
        json={
            "note": "switched to gpt-4o-mini",
            "annotation_date": "2026-02-27",
            "version": "v2",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(annot_id)
    assert data["note"] == "switched to gpt-4o-mini"
    assert data["annotation_date"] == "2026-02-27"
    assert data["version"] == "v2"


# ── GET /analytics/annotations ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_annotations(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /annotations → items list."""
    annot = _make_annotation()
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([annot]))

    response = await authed_client.get("/analytics/annotations")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["note"] == annot.note
    assert data["items"][0]["annotation_date"] == "2026-02-27"


# ── Auth enforcement ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_economics_requires_auth(client: AsyncClient) -> None:
    """GET /analytics/economics/{id} without auth → 401."""
    response = await client.get(f"/analytics/economics/{uuid.uuid4()}")
    assert response.status_code == 401
