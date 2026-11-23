"""Workflow spine (review top#4, B-11, B-14, B-15, B-17, B-18).

Unit tests run everywhere. The Postgres-backed tests at the bottom exercise the real
SQL (attribution at ingest, cross-workspace refusal, run view, step cost roll-up,
health card) and run only when ``RUNLEDGER_TEST_DATABASE_URL`` points at a database
migrated to head, e.g.::

    RUNLEDGER_TEST_DATABASE_URL=postgresql+asyncpg://u:p@127.0.0.1:55441/runledger \\
        uv run pytest tests/test_workflows_spine.py
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from runledger_api.routers.ingest import apply_workflow_header
from runledger_api.services import workflow_attribution as wa
from runledger_api.services.otlp_parse import _extract_run_context

# ── Unit: header + OTLP mapping + resolver plumbing ──────────────────────────


def test_workflow_header_stamps_only_unattributed_run_starts() -> None:
    events: list[dict[str, Any]] = [
        {"event_type": "run_start", "run_id": "a"},
        {"event_type": "run_start", "run_id": "b", "workflow": "explicit"},
        {"event_type": "run_start", "run_id": "c", "workflow_id": str(uuid.uuid4())},
        {"event_type": "provider_call", "run_id": "a"},
    ]
    apply_workflow_header(events, " support-triage ")
    assert events[0]["workflow"] == "support-triage"
    assert events[1]["workflow"] == "explicit"
    assert "workflow" not in events[2]
    assert "workflow" not in events[3]
    # No header: nothing changes.
    assert apply_workflow_header([{"event_type": "run_start"}], None) == [
        {"event_type": "run_start"}
    ]


def test_otlp_attributes_map_to_workflow_and_agent() -> None:
    ctx = _extract_run_context(
        {"service.name": "svc", "runledger.workflow": "support-triage"},
        {
            "runledger.workflow.id": "11111111-1111-1111-1111-111111111111",
            "gen_ai.agent.name": "triage-bot",
            "runledger.feature_tag": "support",
        },
    )
    assert ctx["workflow_id"] == "11111111-1111-1111-1111-111111111111"
    assert ctx["workflow"] == "support-triage"
    assert ctx["agent_name"] == "triage-bot"
    assert ctx["feature_tag"] == "support"
    # No workflow attributes: no keys (None must never reach the pipeline).
    assert "workflow" not in _extract_run_context({}, {"runledger.feature_tag": "x"})


@pytest.mark.asyncio
async def test_non_uuid_workflow_id_is_treated_as_a_reference() -> None:
    captured: dict[str, Any] = {}

    async def fake_resolve(session: Any, ws: uuid.UUID, **kw: Any) -> wa.RunAttribution:
        captured.update(kw)
        return wa.RunAttribution()

    with patch.object(wa, "resolve_run_attribution", fake_resolve):
        await wa.attribution_from_event(
            AsyncMock(), uuid.uuid4(), {"workflow_id": "support-triage", "feature_tag": "t"}
        )
    assert captured["workflow"] == "support-triage"
    assert captured["workflow_id"] is None
    assert captured["feature_tag"] == "t"


@pytest.mark.asyncio
async def test_attribution_reads_metadata_keys() -> None:
    captured: dict[str, Any] = {}

    async def fake_resolve(session: Any, ws: uuid.UUID, **kw: Any) -> wa.RunAttribution:
        captured.update(kw)
        return wa.RunAttribution()

    with patch.object(wa, "resolve_run_attribution", fake_resolve):
        await wa.attribution_from_event(
            AsyncMock(),
            uuid.uuid4(),
            {"metadata": {"runledger.workflow": "wf", "route_alias": "smart", "agent_name": "a"}},
        )
    assert captured["workflow"] == "wf"
    assert captured["route_alias"] == "smart"
    assert captured["agent_name"] == "a"


@pytest.mark.asyncio
async def test_ingest_batch_applies_workflow_header(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    payload = {
        "events": [
            {
                "event_type": "run_start",
                "run_id": str(uuid.uuid4()),
                "started_at": datetime.now(UTC).isoformat(),
            }
        ]
    }
    with patch("runledger_api.routers.ingest.process_events_task") as task:
        task.delay = MagicMock()
        resp = await authed_client.post(
            "/ingest/v1/batch", json=payload, headers={"X-RunLedger-Workflow": "support"}
        )
    assert resp.status_code == 202
    assert task.delay.call_args.kwargs["events"][0]["workflow"] == "support"


# ── Unit: router validation ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_workflow_rejects_tag_linked_elsewhere(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    clash = MagicMock()
    clash.first.return_value = (uuid.uuid4(), "Existing")
    mock_db_session.execute = AsyncMock(return_value=clash)
    resp = await authed_client.post("/workflows", json={"name": "New", "feature_tag": "support"})
    assert resp.status_code == 409
    assert "Existing" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_workflow_rejects_unknown_alias(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=missing)
    resp = await authed_client.post("/workflows", json={"name": "New", "gateway_alias": "nope"})
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("tag", ["has space", "-leading", "", "a" * 256])
async def test_create_workflow_validates_tag(authed_client: AsyncClient, tag: str) -> None:
    resp = await authed_client.post("/workflows", json={"name": "x", "feature_tag": tag})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_workflow_runs_rejects_unknown_status(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    found = MagicMock()
    found.scalar_one_or_none.return_value = SimpleNamespace(id=uuid.uuid4())
    mock_db_session.execute = AsyncMock(return_value=found)
    resp = await authed_client.get(f"/workflows/{uuid.uuid4()}/runs?status=bogus")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_removed_record_only_endpoints_are_gone(authed_client: AsyncClient) -> None:
    wf = uuid.uuid4()
    assert (await authed_client.post(f"/workflows/{wf}/runs", json={})).status_code == 405
    assert (
        await authed_client.post(f"/workflows/runs/{uuid.uuid4()}/steps", json={})
    ).status_code in (404, 405)


@pytest.mark.asyncio
async def test_envelope_blocks_when_spent() -> None:
    from runledger_api.routers.agents import envelope_status

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=Decimal("5"))))
    agent = SimpleNamespace(
        id=uuid.uuid4(), workspace_id=uuid.uuid4(), status="active", budget_envelope=Decimal("5")
    )
    st = await envelope_status(db, agent)  # type: ignore[arg-type]
    assert st.allowed is False and st.remaining_usd == Decimal("0")
    agent.budget_envelope = Decimal("10")
    st = await envelope_status(db, agent)  # type: ignore[arg-type]
    assert st.allowed is True and st.remaining_usd == Decimal("5")
    agent.status = "paused"
    assert (await envelope_status(db, agent)).allowed is False  # type: ignore[arg-type]


# ── Postgres-backed ──────────────────────────────────────────────────────────

DB_URL = os.environ.get("RUNLEDGER_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB_URL, reason="RUNLEDGER_TEST_DATABASE_URL not set")


@pytest.fixture
async def pg() -> AsyncGenerator[Any]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    assert DB_URL
    engine = create_async_engine(DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    tenant, ws1, ws2 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with factory() as s:
        await s.execute(
            text("INSERT INTO tenants(id, slug, name) VALUES (:id, :slug, 'T')"),
            {"id": tenant, "slug": f"t-{tenant.hex[:12]}"},
        )
        for w in (ws1, ws2):
            await s.execute(
                text("INSERT INTO workspaces(id, tenant_id, name) VALUES (:id, :t, 'W')"),
                {"id": w, "t": tenant},
            )
        await s.commit()
    try:
        yield SimpleNamespace(factory=factory, ws1=ws1, ws2=ws2)
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant})
            await s.execute(
                text("DELETE FROM workflow_definitions WHERE workspace_id IN (:a, :b)"),
                {"a": ws1, "b": ws2},
            )
            await s.execute(
                text("DELETE FROM agents WHERE workspace_id IN (:a, :b)"), {"a": ws1, "b": ws2}
            )
            await s.commit()
        await engine.dispose()


async def _run_start(pg: Any, ws: uuid.UUID, **fields: Any) -> uuid.UUID:
    from runledger_api.workers import pipeline

    run_id = uuid.uuid4()
    event = {
        "event_type": "run_start",
        "run_id": str(run_id),
        "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
        **fields,
    }
    with patch.object(pipeline.kafka_export, "publish_event", AsyncMock()):
        async with pg.factory() as s:
            await pipeline._handle_run_start(s, str(ws), event)
            await s.commit()
    return run_id


@pytest.fixture
async def pg_client(pg: Any) -> AsyncGenerator[AsyncClient]:
    from runledger_api.core.db import get_db
    from runledger_api.core.deps import (
        get_current_api_key,
        get_current_workspace,
        require_workspace_writer,
    )
    from runledger_api.core.redis import get_redis
    from runledger_api.main import app

    async def _db() -> AsyncGenerator[Any]:
        async with pg.factory() as s:
            yield s

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_workspace] = lambda: SimpleNamespace(id=pg.ws1, name="W")
    app.dependency_overrides[get_current_api_key] = lambda: SimpleNamespace(
        id=uuid.uuid4(), workspace_id=pg.ws1, is_session=True, scopes=None
    )
    app.dependency_overrides[require_workspace_writer] = lambda: None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@needs_db
@pytest.mark.asyncio
async def test_pg_attribution_end_to_end(pg: Any, pg_client: AsyncClient) -> None:
    from runledger_api.models.events import AgentRun, ProviderCall, Span, SpanTypeEnum
    from runledger_api.models.scores import ScoreEvent

    # Runs that exist before the workflow get linked when it is created.
    early = await _run_start(pg, pg.ws1, feature_tag="support")
    foreign = await _run_start(pg, pg.ws2, feature_tag="support")

    resp = await pg_client.post(
        "/workflows", json={"name": "Support triage", "feature_tag": "support"}
    )
    assert resp.status_code == 201, resp.text
    wf = resp.json()
    assert wf["linked_runs"] == 1
    wf_id = uuid.UUID(wf["id"])

    # Duplicate live tag → 409.
    dup = await pg_client.post("/workflows", json={"name": "Dup", "feature_tag": "support"})
    assert dup.status_code == 409

    # Explicit by name, by id, by tag; foreign id never attributes (B-17).
    by_name = await _run_start(pg, pg.ws1, workflow="support triage")
    by_id = await _run_start(pg, pg.ws1, workflow_id=str(wf_id))
    by_tag = await _run_start(pg, pg.ws1, feature_tag="support")
    other_ws = await _run_start(pg, pg.ws2, workflow_id=str(wf_id))

    async with pg.factory() as s:
        rows: dict[uuid.UUID, Any] = {}
        for i in (early, foreign, by_name, by_id, by_tag, other_ws):
            rows[i] = await s.get(AgentRun, i)
    assert rows[early].workflow_id == wf_id
    assert rows[by_name].workflow_id == wf_id
    assert rows[by_name].feature_tag == "support"  # inherited → budgets count it
    assert rows[by_id].workflow_id == wf_id
    assert rows[by_tag].workflow_id == wf_id
    assert rows[foreign].workflow_id is None
    assert rows[other_ws].workflow_id is None

    # Finish two runs with priced calls under named steps; score one.
    now = datetime.now(UTC)
    async with pg.factory() as s:
        for rid, step, cost, ok in (
            (by_id, "classify", "0.010", True),
            (by_tag, "respond", "0.030", False),
        ):
            run = await s.get(AgentRun, rid)
            assert run is not None
            run.status = "succeeded" if ok else "failed"  # type: ignore[assignment]
            run.ended_at = now
            run.total_cost_usd = Decimal(cost)
            span = Span(run_id=rid, span_type=SpanTypeEnum.llm, name=step, started_at=now)
            s.add(span)
            await s.flush()
            s.add(
                ProviderCall(
                    run_id=rid,
                    span_id=span.id,
                    workspace_id=pg.ws1,
                    provider="openai",
                    model="gpt-4o-mini",
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=Decimal(cost),
                    status="success",
                )
            )
        s.add(
            ScoreEvent(workspace_id=pg.ws1, run_id=by_id, name="helpfulness", value=Decimal("0.8"))
        )
        await s.commit()

    runs = (await pg_client.get(f"/workflows/{wf_id}/runs")).json()
    assert runs["total"] == 4
    failed = (await pg_client.get(f"/workflows/{wf_id}/runs?status=failed")).json()
    assert failed["total"] == 1

    cost = (await pg_client.get(f"/workflows/{wf_id}/cost")).json()
    assert Decimal(cost["total_cost"]) == Decimal("0.04")
    assert Decimal(cost["steps_cost"]) == Decimal("0.04")  # steps roll up to runs (B-18)
    assert {s["step_name"] for s in cost["cost_by_step"]} == {"classify", "respond"}
    assert cost["cost_by_model"][0]["model"] == "gpt-4o-mini"

    ov = (await pg_client.get(f"/workflows/{wf_id}/overview")).json()
    h = ov["health"]
    assert h["runs"] == 4 and h["succeeded"] == 1 and h["failed"] == 1
    assert Decimal(h["cost_per_success"]) == Decimal("0.04")
    assert h["p95_latency_ms"] is not None
    assert h["avg_eval_score"] == pytest.approx(0.8)
    assert ov["evals"][0]["name"] == "helpfulness"

    listing = (await pg_client.get("/workflows?status=active")).json()
    assert listing["workflows"][0]["stats"]["runs"] == 4

    ctx = (await pg_client.get(f"/context?entity=workflow&id={wf_id}")).json()
    assert ctx["title"] == "Support triage"
    assert ctx["items"][0]["value"] == "4"

    # Archive: stops matching new traffic; restore re-links.
    assert (await pg_client.delete(f"/workflows/{wf_id}")).status_code == 204
    after = await _run_start(pg, pg.ws1, feature_tag="support")
    async with pg.factory() as s:
        assert (await s.get(AgentRun, after)).workflow_id is None  # type: ignore[union-attr]
    restored = await pg_client.put(f"/workflows/{wf_id}", json={"status": "active"})
    assert restored.status_code == 200 and restored.json()["linked_runs"] == 1


@needs_db
@pytest.mark.asyncio
async def test_pg_agent_stats_from_agent_runs(pg: Any, pg_client: AsyncClient) -> None:
    from runledger_api.models.events import AgentRun

    created = await pg_client.post(
        "/agents", json={"name": "triage-bot", "budget_envelope": "0.02"}
    )
    agent_id = created.json()["id"]
    r1 = await _run_start(pg, pg.ws1, agent_name="triage-bot")
    r2 = await _run_start(pg, pg.ws1, agent_id=agent_id)
    foreign = await _run_start(pg, pg.ws2, agent_id=agent_id)
    async with pg.factory() as s:
        for rid in (r1, r2):
            run = await s.get(AgentRun, rid)
            run.status = "succeeded"  # type: ignore[union-attr,assignment]
            run.total_cost_usd = Decimal("0.01")  # type: ignore[union-attr]
        assert (await s.get(AgentRun, foreign)).agent_id is None  # type: ignore[union-attr]
        await s.commit()

    stats = (await pg_client.get(f"/agents/{agent_id}/stats")).json()
    assert stats["total_runs"] == 2 and stats["completed_runs"] == 2
    assert stats["envelope"]["allowed"] is False  # $0.02 spent of $0.02
    runs = (await pg_client.get(f"/agents/{agent_id}/runs")).json()
    assert runs["total"] == 2
    env = (await pg_client.get(f"/agents/{agent_id}/envelope")).json()
    assert env["reason"] == "monthly budget envelope exhausted"
