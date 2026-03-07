"""
Tests for Phase 19 Sessions UI + Payload Viewer endpoints.

Covers:
  GET /sessions               — list sessions grouped by session_id
  GET /sessions/{session_id}  — ordered runs for a session
  GET /sessions/{session_id}/cost-over-turns — per-turn cost breakdown
  GET /runs/{run_id}          — extended with input_payload / output_payload / span_payloads

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


def _all_result(rows: list[object]) -> MagicMock:
    """Result where .all() returns rows (aggregate query)."""
    m = MagicMock()
    m.all = MagicMock(return_value=rows)
    return m


def _scalars_all_result(rows: list[object]) -> MagicMock:
    """Result where .scalars().all() returns rows (ORM list query)."""
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars_mock)
    return m


def _scalar_one_result(value: object) -> MagicMock:
    """Result where .scalar_one() returns a single value."""
    m = MagicMock()
    m.scalar_one = MagicMock(return_value=value)
    return m


def _make_run(**kwargs: object) -> SimpleNamespace:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        session_id="sess-abc",
        end_user_id="alice",
        feature_tag=None,
        deployment_version=None,
        status="succeeded",
        total_cost_usd=Decimal("0.01"),
        total_input_tokens=100,
        total_output_tokens=50,
        started_at=now,
        ended_at=now,
        run_metadata=None,
        span_metadata=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_session_row(**kwargs: object) -> SimpleNamespace:
    """Simulates an aggregate GROUP BY row from the sessions query."""
    now = datetime.now(UTC)
    defaults = dict(
        session_id="sess-abc",
        end_user_id="alice",
        run_count=2,
        total_cost_usd=Decimal("0.02"),
        started_at=now,
        ended_at=now,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ── GET /sessions ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_empty(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /sessions with no data → empty items list, total=0."""
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _all_result([]),
            _scalar_one_result(0),
        ]
    )

    resp = await authed_client.get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_sessions_groups_by_session_id(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /sessions → 1 session row with correct run_count and total_cost_usd."""
    row = _make_session_row(run_count=3, total_cost_usd=Decimal("0.03"))

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _all_result([row]),
            _scalar_one_result(1),
        ]
    )

    resp = await authed_client.get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    item = data["items"][0]
    assert item["session_id"] == "sess-abc"
    assert item["run_count"] == 3
    assert float(item["total_cost_usd"]) == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_list_sessions_filter_by_end_user_id(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /sessions?end_user_id=bob returns list (query filter applied)."""
    row = _make_session_row(session_id="sess-bob", end_user_id="bob")

    mock_db_session.execute = AsyncMock(
        side_effect=[
            _all_result([row]),
            _scalar_one_result(1),
        ]
    )

    resp = await authed_client.get("/sessions?end_user_id=bob")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["end_user_id"] == "bob"


# ── GET /sessions/{session_id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_detail_chronological_order(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """GET /sessions/{session_id} → runs returned in turn order (turn_number 1, 2, 3)."""
    now = datetime.now(UTC)
    runs = [
        _make_run(
            workspace_id=mock_workspace.id,
            id=uuid.uuid4(),
            session_id="sess-abc",
            started_at=now,
            ended_at=now,
            total_cost_usd=Decimal("0.01"),
        )
        for _ in range(3)
    ]

    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result(runs))

    resp = await authed_client.get("/sessions/sess-abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-abc"
    assert data["run_count"] == 3
    turn_numbers = [r["turn_number"] for r in data["runs"]]
    assert turn_numbers == [1, 2, 3]


@pytest.mark.asyncio
async def test_session_detail_not_found(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
) -> None:
    """GET /sessions/{session_id} with no matching runs → 404."""
    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result([]))

    resp = await authed_client.get("/sessions/no-such-session")
    assert resp.status_code == 404


# ── GET /sessions/{session_id}/cost-over-turns ────────────────────────────────


@pytest.mark.asyncio
async def test_cost_over_turns(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """Cost-over-turns returns correct turn numbers and cumulative cost."""
    now = datetime.now(UTC)
    run_ids = [uuid.uuid4() for _ in range(3)]
    runs = [
        _make_run(
            workspace_id=mock_workspace.id,
            id=run_ids[i],
            session_id="sess-abc",
            started_at=now,
            ended_at=now,
            total_cost_usd=Decimal("0.01"),
        )
        for i in range(3)
    ]

    mock_db_session.execute = AsyncMock(return_value=_scalars_all_result(runs))

    resp = await authed_client.get("/sessions/sess-abc/cost-over-turns")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-abc"
    assert len(data["turns"]) == 3
    # cumulative cost should increase
    cumulative = [float(t["cumulative_cost_usd"]) for t in data["turns"]]
    assert cumulative == pytest.approx([0.01, 0.02, 0.03])
    # turn_numbers are 1-indexed
    assert [t["turn_number"] for t in data["turns"]] == [1, 2, 3]


# ── GET /runs/{run_id} — payload passthrough ──────────────────────────────────


@pytest.mark.asyncio
async def test_run_detail_includes_payloads(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """Run detail includes input/output payloads when span metadata is captured."""
    run_id = uuid.uuid4()
    span_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_run = _make_run(
        id=run_id,
        workspace_id=mock_workspace.id,
        session_id=None,
        started_at=now,
        ended_at=now,
    )
    mock_span = SimpleNamespace(
        id=span_id,
        run_id=run_id,
        parent_span_id=None,
        span_type="llm",
        name="chat",
        started_at=now,
        ended_at=now,
        status="succeeded",
        cost_usd=Decimal("0.01"),
        span_metadata={
            "messages": [{"role": "user", "content": "Hello"}],
            "response": "Hi there!",
        },
    )

    mock_db_session.get = AsyncMock(return_value=mock_run)
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalars_all_result([mock_span]),
            _scalars_all_result([]),
            _scalars_all_result([]),
        ]
    )

    resp = await authed_client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_payload"] == [{"role": "user", "content": "Hello"}]
    assert data["output_payload"] == "Hi there!"
    assert str(span_id) in data["span_payloads"]


@pytest.mark.asyncio
async def test_run_detail_no_payloads_without_metadata(
    authed_client: AsyncClient,
    mock_db_session: AsyncMock,
    mock_workspace: SimpleNamespace,
) -> None:
    """Run detail has null payload fields when span metadata is absent (METADATA_ONLY mode)."""
    run_id = uuid.uuid4()
    now = datetime.now(UTC)

    mock_run = _make_run(
        id=run_id,
        workspace_id=mock_workspace.id,
        session_id=None,
        started_at=now,
        ended_at=now,
    )
    mock_span = SimpleNamespace(
        id=uuid.uuid4(),
        run_id=run_id,
        parent_span_id=None,
        span_type="llm",
        name="chat",
        started_at=now,
        ended_at=now,
        status="succeeded",
        cost_usd=Decimal("0.01"),
        span_metadata=None,  # METADATA_ONLY — no payload stored
    )

    mock_db_session.get = AsyncMock(return_value=mock_run)
    mock_db_session.execute = AsyncMock(
        side_effect=[
            _scalars_all_result([mock_span]),
            _scalars_all_result([]),
            _scalars_all_result([]),
        ]
    )

    resp = await authed_client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["input_payload"] is None
    assert data["output_payload"] is None
    assert data["span_payloads"] is None
