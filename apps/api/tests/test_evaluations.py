"""
Tests for Phase 17 Evaluations & Scores endpoints.

Covers:
  POST /evaluations/scores   — create quality score (validation, auth, success)
  GET  /evaluations/scores   — list scores
  GET  /analytics/scores/summary      — score summary with delta
  GET  /analytics/scores/regressions  — regression detection

Uses authed_client / mock_db_session / mock_workspace fixtures from conftest.
No live DB required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

# ── Mock result helpers ────────────────────────────────────────────────────────


def _scalars_list_result(rows: list[object]) -> MagicMock:
    """Result where .scalars().all() returns rows (ORM list query)."""
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


def _row_result(rows: list[object]) -> MagicMock:
    """Result where .all() returns rows (aggregate query)."""
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _make_score(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        run_id=None,
        span_id=None,
        session_id=None,
        end_user_id=None,
        name="relevance",
        value=Decimal("0.9"),
        label=None,
        source="human",
        confidence=None,
        evidence=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── POST /evaluations/scores ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_score_success(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """POST /evaluations/scores → 201, response has id/name/value/source."""
    score = _make_score(workspace_id=mock_workspace.id)

    async def set_attrs(obj: object) -> None:
        obj.id = score.id  # type: ignore[attr-defined]
        obj.created_at = score.created_at  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    response = await authed_client.post(
        "/evaluations/scores",
        json={"name": "relevance", "value": 0.9, "source": "human"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "relevance"
    assert float(data["value"]) == pytest.approx(0.9)
    assert data["source"] == "human"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_score_requires_auth(
    client: AsyncClient,
) -> None:
    """Unauthenticated POST → 401."""
    response = await client.post(
        "/evaluations/scores",
        json={"name": "relevance", "value": 0.9},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_score_with_run_id(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """run_id is stored and returned in response."""
    run_id = uuid.uuid4()
    score = _make_score(workspace_id=mock_workspace.id, run_id=run_id)

    async def set_attrs(obj: object) -> None:
        obj.id = score.id  # type: ignore[attr-defined]
        obj.created_at = score.created_at  # type: ignore[attr-defined]
        obj.run_id = run_id  # type: ignore[attr-defined]

    mock_db_session.refresh.side_effect = set_attrs

    response = await authed_client.post(
        "/evaluations/scores",
        json={"name": "accuracy", "value": 0.8, "run_id": str(run_id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_create_score_value_out_of_range(
    authed_client: AsyncClient,
) -> None:
    """value=150 → 422 Unprocessable Entity."""
    response = await authed_client.post(
        "/evaluations/scores",
        json={"name": "accuracy", "value": 150},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_score_invalid_source(
    authed_client: AsyncClient,
) -> None:
    """source='robot' → 422 (pattern validation)."""
    response = await authed_client.post(
        "/evaluations/scores",
        json={"name": "quality", "value": 0.5, "source": "robot"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_score_confidence_validation(
    authed_client: AsyncClient,
) -> None:
    """confidence=1.5 → 422 (must be 0–1)."""
    response = await authed_client.post(
        "/evaluations/scores",
        json={"name": "quality", "value": 0.5, "confidence": 1.5},
    )
    assert response.status_code == 422


# ── GET /evaluations/scores ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_scores_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /evaluations/scores with no rows → {"items": []}."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result([]))

    response = await authed_client.get("/evaluations/scores")

    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.asyncio
async def test_list_scores_returns_items(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /evaluations/scores with 2 rows → items len 2."""
    scores = [
        _make_score(workspace_id=mock_workspace.id, name="relevance"),
        _make_score(workspace_id=mock_workspace.id, name="accuracy"),
    ]
    mock_db_session.execute = AsyncMock(return_value=_scalars_list_result(scores))

    response = await authed_client.get("/evaluations/scores")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2


# ── GET /analytics/scores/summary ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_summary_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /analytics/scores/summary with no rows → {"items": []}."""
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _row_result([]),  # current window
            _row_result([]),  # prior window
        ]
    )

    response = await authed_client.get("/analytics/scores/summary")

    assert response.status_code == 200
    assert response.json() == {"items": []}


@pytest.mark.asyncio
async def test_score_summary_returns_aggregates(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Mocked rows → avg and count appear in response."""
    curr_rows = [
        SimpleNamespace(name="relevance", avg_value=Decimal("0.85"), sample_count=5),
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _row_result(curr_rows),  # current window
            _row_result([]),         # prior window (no data)
        ]
    )

    response = await authed_client.get("/analytics/scores/summary")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["name"] == "relevance"
    assert float(item["avg_value"]) == pytest.approx(0.85)
    assert item["sample_count"] == 5
    assert item["change_pct"] is None  # no prior data


@pytest.mark.asyncio
async def test_score_summary_delta_pct(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """Prior period has samples → change_pct is calculated."""
    curr_rows = [
        SimpleNamespace(name="relevance", avg_value=Decimal("0.90"), sample_count=5),
    ]
    prior_rows = [
        SimpleNamespace(name="relevance", avg_value=Decimal("0.80"), sample_count=4),
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _row_result(curr_rows),
            _row_result(prior_rows),
        ]
    )

    response = await authed_client.get("/analytics/scores/summary")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    # (0.90 - 0.80) / 0.80 * 100 = 12.5%
    assert float(item["change_pct"]) == pytest.approx(12.5)
    assert float(item["prev_avg_value"]) == pytest.approx(0.80)


# ── GET /analytics/scores/regressions ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_score_regressions_none(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """No drop > 20% → empty regression list."""
    curr_rows = [
        SimpleNamespace(name="relevance", avg_value=Decimal("0.85"), sample_count=5),
    ]
    prior_rows = [
        SimpleNamespace(name="relevance", avg_value=Decimal("0.80"), sample_count=5),
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _row_result(curr_rows),
            _row_result(prior_rows),
        ]
    )

    response = await authed_client.get("/analytics/scores/regressions")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_score_regressions_detected(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """current avg 0.5, prior 0.8 → -37.5% drop flagged."""
    curr_rows = [
        SimpleNamespace(name="accuracy", avg_value=Decimal("0.5"), sample_count=5),
    ]
    prior_rows = [
        SimpleNamespace(name="accuracy", avg_value=Decimal("0.8"), sample_count=5),
    ]
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _row_result(curr_rows),
            _row_result(prior_rows),
        ]
    )

    response = await authed_client.get("/analytics/scores/regressions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert item["name"] == "accuracy"
    assert float(item["change_pct"]) == pytest.approx(-37.5)
    assert item["sample_count"] == 5
