"""
Ingestion & Integrations hardening (review section 7).

Pipeline reliability and idempotency (I-05, I-07, I-10, I-14, I-20), dead-letter
CRUD, OTLP gating / root / cached tokens / gzip cap / capture policy (M-01, I-09,
I-11, I-12, I-13, I-19, I-24), enrichment and budget sync (I-06, I-08, B-07),
finalizer inactivity (I-16) and the Kafka outbox (I-17).
"""

from __future__ import annotations

import gzip
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

# ── Pipeline helpers ──────────────────────────────────────────────────────────


def test_normalize_event_truncates_and_normalizes_status() -> None:
    from runledger_api.workers.pipeline import _normalize_event

    event = _normalize_event(
        {"event_type": "provider_call", "status": "Succeeded", "model": "m" * 300, "name": "x"}
    )
    assert event["status"] == "success"
    assert len(event["model"]) == 128
    assert (
        _normalize_event({"event_type": "provider_call", "status": "failed"})["status"] == "error"
    )
    span = _normalize_event({"event_type": "span_start", "name": "n" * 400})
    assert len(span["name"]) == 255


def test_stable_ids_dedupe_retries_but_not_distinct_events() -> None:
    from runledger_api.workers.pipeline import _stable_id

    a = {"event_type": "tool_call", "run_id": "r", "tool_name": "t", "duration_ms": 5}
    assert _stable_id("tool_call", dict(a)) == _stable_id("tool_call", dict(a))
    assert _stable_id("tool_call", a) != _stable_id("tool_call", {**a, "duration_ms": 6})
    explicit = str(uuid.uuid4())
    assert str(_stable_id("tool_call", {**a, "tool_call_id": explicit})) == explicit


@asynccontextmanager
async def _savepoint() -> Any:
    yield


@pytest.mark.asyncio
async def test_failing_event_is_dead_lettered_without_aborting_batch() -> None:
    from runledger_api.workers import pipeline

    session = AsyncMock()
    session.begin_nested = MagicMock(side_effect=lambda: _savepoint())
    session.add = MagicMock()

    @asynccontextmanager
    async def _session_cm() -> Any:
        yield session

    factory = MagicMock(return_value=_session_cm())
    good = {
        "event_type": "run_start",
        "run_id": str(uuid.uuid4()),
        "started_at": "2026-01-01T00:00:00+00:00",
    }
    bad = {
        "event_type": "run_start",
        "run_id": str(uuid.uuid4()),
        "started_at": "2026-01-01T00:00:00+00:00",
    }
    calls: list[str] = []

    async def dispatch(_s: Any, _ws: Any, event: dict[str, Any], *args: Any) -> None:
        calls.append(event["run_id"])
        if event is bad or event["run_id"] == bad["run_id"]:
            raise ValueError("boom")

    with (
        patch.object(pipeline, "create_async_engine", return_value=AsyncMock()),
        patch.object(pipeline, "async_sessionmaker", return_value=factory),
        patch.object(
            pipeline, "_get_capture_policy", AsyncMock(return_value=("METADATA_ONLY", 0.0))
        ),
        patch.object(pipeline, "_dispatch", side_effect=dispatch),
    ):
        await pipeline._process_events(str(uuid.uuid4()), [bad, good])

    assert calls == [bad["run_id"], good["run_id"]]  # second event still processed
    dead = [c.args[0] for c in session.add.call_args_list]
    assert len(dead) == 1 and dead[0].run_id == bad["run_id"] and "boom" in dead[0].error
    session.commit.assert_awaited()


# ── Dead-letter endpoints ─────────────────────────────────────────────────────


def _dead_letter(workspace_id: Any, **kw: Any) -> SimpleNamespace:
    now = datetime.now(UTC)
    base = dict(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        event_type="span_start",
        run_id=str(uuid.uuid4()),
        event={"event_type": "span_start"},
        error="IntegrityError",
        attempts=1,
        status="pending",
        created_at=now,
        last_attempt_at=now,
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_dead_letter_replay_requeues_with_marker(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    item = _dead_letter(mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=item)
    with patch("runledger_api.routers.ingest.process_events_task") as task:
        task.delay = MagicMock()
        resp = await authed_client.post(f"/ingest/v1/dead-letters/{item.id}/replay")
    assert resp.status_code == 200 and resp.json() == {"requeued": 1}
    sent = task.delay.call_args.kwargs["events"]
    assert sent[0]["_dead_letter_id"] == str(item.id)


@pytest.mark.asyncio
async def test_dead_letter_of_other_workspace_is_404(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    mock_db_session.get = AsyncMock(return_value=_dead_letter(uuid.uuid4()))
    resp = await authed_client.post(f"/ingest/v1/dead-letters/{uuid.uuid4()}/replay")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dead_letter_discard_marks_status(
    authed_client: AsyncClient, mock_db_session: AsyncMock, mock_workspace: SimpleNamespace
) -> None:
    item = _dead_letter(mock_workspace.id)
    mock_db_session.get = AsyncMock(return_value=item)
    with patch("runledger_api.routers.ingest.emit_audit_event", AsyncMock()):
        resp = await authed_client.delete(f"/ingest/v1/dead-letters/{item.id}")
    assert resp.status_code == 204
    assert item.status == "discarded"


# ── OTLP ──────────────────────────────────────────────────────────────────────


def _trace(*spans: tuple[str, str, str | None, dict[str, Any]]) -> Any:
    from runledger_api.services.otlp_parse import OtlpParsedSpan, OtlpTrace

    parsed = [
        OtlpParsedSpan(
            trace_id_hex="t" * 32,
            span_id_hex=sid,
            parent_span_id_hex=parent,
            name=name,
            span_type=kind,
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            ended_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
            status_code="OK",
            attrs=attrs,
            scope_name=None,
            scope_version=None,
            otel_kind=1,
        )
        for (sid, name, parent, attrs), kind in [
            ((s[0], s[1], s[2], s[3]), s[3].pop("_kind", "chain")) for s in spans
        ]
    ]
    return OtlpTrace("t" * 32, {"service.name": "svc"}, parsed)


def test_llm_span_gating() -> None:
    from runledger_api.services.otlp_parse import trace_should_create_run

    noise = _trace(("a", "fs.get_metadata", None, {}), ("b", "receiving", "a", {}))
    llm = _trace(("a", "agent", None, {}), ("b", "chat", "a", {"_kind": "llm"}))
    genai = _trace(("a", "call", None, {"gen_ai.system": "openai"}))
    assert trace_should_create_run(noise) is False
    assert trace_should_create_run(llm) is True
    assert trace_should_create_run(genai) is True
    assert trace_should_create_run(noise, "all") is True
    noise.resource_attrs["runledger.capture"] = "all"
    assert trace_should_create_run(noise) is True


def test_child_only_batch_does_not_end_run_and_cached_tokens_mapped() -> None:
    from runledger_api.services.otlp_parse import synthesize_canonical_events

    child_only = _trace(
        (
            "b",
            "chat",
            "missing-root",
            {
                "_kind": "llm",
                "gen_ai.request.model": "gpt-4o",
                "gen_ai.usage.cache_read_input_tokens": 40,
            },
        )
    )
    events = synthesize_canonical_events(uuid.uuid4(), child_only)
    assert not [e for e in events if e["event_type"] == "run_end"]
    call = next(e for e in events if e["event_type"] == "provider_call")
    assert call["cached_input_tokens"] == 40

    with_root = _trace(("a", "agent", None, {"_kind": "agent"}))
    assert [
        e
        for e in synthesize_canonical_events(uuid.uuid4(), with_root)
        if e["event_type"] == "run_end"
    ]


def test_gzip_bomb_is_refused() -> None:
    from runledger_api.routers.otlp import _inflate_gzip

    bomb = gzip.compress(b"0" * 2_000_000)
    with pytest.raises(HTTPException) as exc:
        _inflate_gzip(bomb, 1_000_000)
    assert exc.value.status_code == 413
    assert _inflate_gzip(gzip.compress(b'{"a":1}'), 1_000) == b'{"a":1}'


def test_raw_span_payload_attributes_need_full_capture() -> None:
    from runledger_api.routers.otlp import _raw_span_attributes

    attrs = {"gen_ai.prompt.0.content": "secret prompt", "llm.model_name": "gpt-4o"}
    kept = _raw_span_attributes(attrs, capture_full=False) or {}
    assert "gen_ai.prompt.0.content" not in kept and kept["llm.model_name"] == "gpt-4o"
    full = _raw_span_attributes(attrs, capture_full=True) or {}
    assert "gen_ai.prompt.0.content" in full


@pytest.mark.asyncio
async def test_traces_batch_counts_dropped_and_omits_raw_payload(
    authed_client: AsyncClient, mock_db_session: AsyncMock
) -> None:
    import json

    added: list[Any] = []
    mock_db_session.add = MagicMock(side_effect=added.append)
    mock_db_session.flush = AsyncMock()
    existing = MagicMock()
    existing.scalars.return_value = []
    mock_db_session.execute = AsyncMock(return_value=existing)
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "codex"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "0af7651916cd43dd8448eb211c80319c",
                                "spanId": "b7ad6b7169203331",
                                "name": "fs.get_metadata",
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000001000000000",
                            }
                        ]
                    }
                ],
            }
        ]
    }
    with (
        patch("runledger_api.routers.otlp._capture_full", AsyncMock(return_value=False)),
        patch("runledger_api.workers.pipeline.process_events_task") as task,
    ):
        task.delay = MagicMock()
        resp = await authed_client.post(
            "/v1/traces",
            content=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200
    batch = next(a for a in added if a.__class__.__name__ == "OtlpIngestBatch")
    assert batch.traces_dropped == 1 and batch.runs_created == 0
    assert batch.raw_payload is None
    assert batch.resource_summary["services"] == {"codex": 1}
    task.delay.assert_not_called()


# ── Enrichment and budget sync ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrichment_marks_unpriceable_calls() -> None:
    from runledger_api.workers import metering

    pc = SimpleNamespace(id=uuid.uuid4(), run_id=uuid.uuid4(), created_at=datetime.now(UTC))
    select_result = MagicMock()
    select_result.scalars = MagicMock(return_value=[pc])
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[select_result, MagicMock()])

    @asynccontextmanager
    async def _session_cm() -> Any:
        yield session

    with (
        patch.object(metering, "_make_session_factory", return_value=_session_cm),
        patch("redis.asyncio.Redis.from_url", return_value=AsyncMock()),
        patch.object(metering, "_provider_call_cost", AsyncMock(return_value=None)),
    ):
        result = await metering._run_cost_enrichment()
    assert result == {"enriched": 0}
    update_stmt = session.execute.await_args_list[1].args[0]
    assert "cost_checked_at" in str(update_stmt)


@pytest.mark.asyncio
async def test_budget_sync_scope_filters() -> None:
    from runledger_api.workers.budgets import _scope_filters

    def budget(scope: str, sid: str | None) -> Any:
        return SimpleNamespace(scope_type=scope, scope_id=sid)

    session = AsyncMock()
    assert await _scope_filters(session, budget("workspace", None)) == []
    assert await _scope_filters(session, budget("feature_tag", None)) is None
    assert await _scope_filters(session, budget("mystery", "x")) is None
    assert await _scope_filters(session, budget("app", "not-a-uuid")) is None
    feature = await _scope_filters(session, budget("feature_tag", "support"))
    assert feature is not None and "feature_tag" in str(feature[0])
    group = await _scope_filters(session, budget("access_group", str(uuid.uuid4())))
    assert group is not None and "access_group_members" in str(group[0])


# ── Finalizer and Kafka outbox ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finalizer_requires_inactivity_not_age() -> None:
    from runledger_api.workers.otlp_finalize import _close_stale_runs

    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    assert await _close_stale_runs(session) == 0
    sql = str(session.execute.await_args.args[0])
    assert "NOT (EXISTS" in sql and "spans" in sql


@pytest.mark.asyncio
async def test_publish_event_only_writes_outbox() -> None:
    from runledger_api.services import kafka_export

    config = SimpleNamespace(
        id=uuid.uuid4(),
        event_types=["run.started"],
        redaction_mode="none",
        single_topic_mode=True,
        single_topic_name="runledger.events",
        topic_prefix="runledger",
    )
    db = AsyncMock()
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = [config]
    db.execute = AsyncMock(return_value=rows)
    db.add = MagicMock()
    with patch.object(kafka_export, "_send", AsyncMock()) as send:
        deliveries = await kafka_export.publish_event(
            db, workspace_id=uuid.uuid4(), event_type="run.started", payload={"run_id": "r"}
        )
    send.assert_not_awaited()  # nothing leaves the process inside the transaction
    assert [d.status for d in deliveries] == ["pending"]


@pytest.mark.asyncio
async def test_outbox_worker_delivers_pending_with_one_producer_per_config() -> None:
    from runledger_api.services import kafka_export

    config = SimpleNamespace(
        id=uuid.uuid4(), max_retries=3, retry_backoff_seconds=5, dead_letter_topic=None
    )
    deliveries = [
        SimpleNamespace(id=uuid.uuid4(), status="pending", attempt=1, topic="t", payload={"i": i})
        for i in range(3)
    ]
    db = AsyncMock()
    rows = MagicMock()
    rows.all.return_value = [(d, config) for d in deliveries]
    db.execute = AsyncMock(return_value=rows)
    producer = AsyncMock()
    with patch.object(kafka_export, "_new_producer", return_value=producer) as factory:
        processed = await kafka_export.process_pending_deliveries(db)
    assert processed == 3
    assert factory.call_count == 1
    assert producer.send_and_wait.await_count == 3
    assert all(d.status == "success" for d in deliveries)
    producer.stop.assert_awaited_once()


def test_spend_period_follows_call_time() -> None:
    from runledger_api.services.budgets import _period_key

    call_time = datetime(2026, 1, 31, 23, 59, tzinfo=UTC)
    assert _period_key("monthly", call_time) == "2026-01"
    assert Decimal("1") > 0
