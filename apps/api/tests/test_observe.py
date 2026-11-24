"""Observe stream (W1-E): shared service rules and the new runs endpoints.

Covers status vocabulary (O-01/O-10), the composite cursor (O-10), payload access
(O-05), the access-group status mapping (O-14), saved views and compare (ENH).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from runledger_api.routers.runs import strip_payloads
from runledger_api.services import observe
from runledger_api.services.observe import (
    AccessGroupFilters,
    call_statuses_for,
    can_view_payloads,
    decode_cursor,
    encode_cursor,
    normalize_run_status,
)

# ── Status vocabulary ─────────────────────────────────────────────────────────


def test_run_status_accepts_both_vocabularies() -> None:
    assert normalize_run_status("succeeded") == "succeeded"
    assert normalize_run_status("success") == "succeeded"
    assert normalize_run_status("error") == "failed"
    assert normalize_run_status(None) is None
    assert normalize_run_status("  ") is None


def test_run_status_rejects_unknown_value() -> None:
    with pytest.raises(HTTPException) as exc:
        normalize_run_status("exploded")
    assert exc.value.status_code == 422


def test_explorer_status_maps_run_words_to_call_statuses() -> None:
    # The Explorer UI sends run statuses; provider calls store success/error (O-01).
    assert call_statuses_for("succeeded") == ["success"]
    assert "error" in (call_statuses_for("failed") or [])
    assert call_statuses_for("success") == ["success"]
    assert call_statuses_for("") is None
    with pytest.raises(HTTPException):
        call_statuses_for("bogus")


def test_access_group_statuses_map_to_both_tables() -> None:
    filters = AccessGroupFilters(statuses=["succeeded"])
    call_sql = " ".join(str(c) for c in observe.call_access_clauses(filters))
    run_sql = " ".join(str(c) for c in observe.run_access_clauses(filters, [uuid.uuid4()]))
    assert "provider_calls.status IN" in call_sql
    assert "agent_runs.status IN" in run_sql
    # Statuses can't be expressed on the rollup, so charts fall back to raw calls.
    assert observe.rollup_access_clauses(filters) is None
    assert observe.rollup_access_clauses(AccessGroupFilters(models=["gpt-4o"])) is not None


# ── Composite cursor ──────────────────────────────────────────────────────────


def test_cursor_round_trip_keeps_the_tie_breaker() -> None:
    ts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    rid = uuid.uuid4()
    assert decode_cursor(encode_cursor(ts, rid)) == (ts, rid)


def test_cursor_accepts_legacy_iso_timestamp() -> None:
    ts = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    assert decode_cursor(ts.isoformat()) == (ts, None)


def test_cursor_rejects_garbage() -> None:
    with pytest.raises(HTTPException) as exc:
        decode_cursor("not-a-cursor!!")
    assert exc.value.status_code == 422


# ── Payload access (O-05) ─────────────────────────────────────────────────────


def _request(api_key: object, user: object = None) -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(api_key=api_key, session_user=user))


@pytest.mark.asyncio
async def test_read_only_workload_key_gets_no_payloads() -> None:
    ws = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
    key = SimpleNamespace(is_session=False, scopes=["read"])
    assert await can_view_payloads(_request(key), ws, AsyncMock()) is False  # type: ignore[arg-type]
    full = SimpleNamespace(is_session=False, scopes=[])
    assert await can_view_payloads(_request(full), ws, AsyncMock()) is True  # type: ignore[arg-type]
    writer = SimpleNamespace(is_session=False, scopes=["write"])
    assert await can_view_payloads(_request(writer), ws, AsyncMock()) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_platform_admin_session_sees_payloads() -> None:
    ws = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
    key = SimpleNamespace(is_session=True, scopes=[])
    admin = SimpleNamespace(id=uuid.uuid4(), is_platform_admin=True)
    assert await can_view_payloads(_request(key, admin), ws, AsyncMock()) is True  # type: ignore[arg-type]


def test_span_metadata_never_repeats_payloads() -> None:
    meta = {"messages": [{"role": "user"}], "response": "hi", "model": "gpt-4o"}
    assert strip_payloads(meta) == {"model": "gpt-4o"}
    assert strip_payloads(None) is None


# ── Runs endpoints ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_runs_rejects_unknown_status(authed_client: AsyncClient) -> None:
    resp = await authed_client.get("/runs", params={"status": "exploded"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_runs_rejects_bad_cursor(authed_client: AsyncClient) -> None:
    resp = await authed_client.get("/runs", params={"cursor": "%%%", "include_total": "false"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_runs_without_total_skips_count(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=rows)
    resp = await authed_client.get("/runs", params={"include_total": "false"})
    assert resp.status_code == 200
    assert resp.json()["total"] is None
    assert "x-total-count" not in resp.headers
    assert mock_db_session.execute.await_count == 1  # no COUNT(*) (O-07)


@pytest.mark.asyncio
async def test_run_stats_reports_server_aggregates(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    row = SimpleNamespace(
        total=10,
        succeeded=6,
        failed=2,
        running=1,
        cancelled=1,
        cost=Decimal("1.50"),
        inp=100,
        out=50,
        avg_ms=1200.0,
        p95_ms=3000.0,
    )
    result = MagicMock()
    result.one.return_value = row
    mock_db_session.execute = AsyncMock(return_value=result)
    resp = await authed_client.get("/runs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert data["success_rate"] == "0.7500"  # 6 / (6 + 2)
    assert data["avg_cost_usd"] == "0.15"
    assert data["p95_duration_ms"] == 3000


@pytest.mark.asyncio
async def test_saved_view_rejects_unknown_page(authed_client: AsyncClient) -> None:
    resp = await authed_client.post(
        "/runs/saved-views", json={"page": "billing", "name": "x", "query": "status=failed"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_saved_view_delete_of_other_users_view_is_404(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.get = AsyncMock(
        return_value=SimpleNamespace(workspace_id=uuid.uuid4(), user_id=uuid.uuid4())
    )
    resp = await authed_client.delete(f"/runs/saved-views/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compare_unknown_run_is_404(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    resp = await authed_client.get(
        "/runs/compare", params={"a": str(uuid.uuid4()), "b": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_facets_lists_statuses(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["gpt-4o"]
    mock_db_session.execute = AsyncMock(return_value=result)
    resp = await authed_client.get("/runs/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["models"] == ["gpt-4o"]
    assert "succeeded" in data["statuses"]


# ── Monitoring feeds (O-18) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_monitoring_security_events_pages_on_the_server(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    count = MagicMock()
    count.scalar_one.return_value = 42
    page = MagicMock()
    page.scalars.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[count, page])
    resp = await authed_client.get(
        "/analytics/monitoring/security-events",
        params={"from": "2026-10-01T00:00:00+00:00", "limit": 25, "offset": 25},
    )
    assert resp.status_code == 200
    assert resp.headers["x-total-count"] == "42"
    sql = str(mock_db_session.execute.await_args_list[1].args[0])
    assert "LIMIT" in sql and "OFFSET" in sql and "detected_at >=" in sql


@pytest.mark.asyncio
async def test_monitoring_alerts_rejects_unknown_state(authed_client: AsyncClient) -> None:
    resp = await authed_client.get("/analytics/monitoring/alerts", params={"state": "maybe"})
    assert resp.status_code == 422
