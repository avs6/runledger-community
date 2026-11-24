"""
Celery pipeline worker for processing ingest events.

Uses asyncio.run() + NullPool so each task creates a fresh DB connection —
safe with Celery's --pool=solo and avoids event-loop reuse across tasks.

Reliability:
- Each event is applied in its own savepoint. An event that fails (bad data, FK
  race, constraint) is stored in ``ingest_dead_letters`` instead of aborting the
  batch; workspace admins replay or discard it via ``/ingest/v1/dead-letters``.
- Infrastructure failures (database or broker unreachable) retry the whole task
  with exponential backoff; when retries run out the batch is dead-lettered.
- Inserts are idempotent (deterministic ids + ON CONFLICT DO NOTHING), so retries
  and replays never duplicate runs, spans, provider calls, tool calls or outcomes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import (
    AgentRun,
    ProviderCall,
    RunStatusEnum,
    Span,
    SpanStatusEnum,
    SpanTypeEnum,
    ToolCall,
    ToolTypeEnum,
)
from runledger_api.models.ingest_dead_letters import IngestDeadLetter
from runledger_api.models.ledger import CapturePolicy
from runledger_api.models.outcomes import Outcome
from runledger_api.services import kafka_export
from runledger_api.services.scrubbing import scrub_dict
from runledger_api.services.workflow_attribution import attribution_from_event

log = structlog.get_logger()


_INFRA_ERRORS = (OperationalError, DBAPIError, ConnectionError, OSError, TimeoutError)


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="pipeline.process_events",
    max_retries=5,
    acks_late=True,
)
def process_events_task(self: Any, workspace_id: str, events: list[dict[str, Any]]) -> None:
    """Persist a batch of ingest events to PostgreSQL.

    Retries with exponential backoff (5s, 10s, … max 5 min) when the database or
    broker is unreachable; dead-letters the batch once retries are exhausted.
    """
    try:
        asyncio.run(_process_events(workspace_id, events))
    except _INFRA_ERRORS as exc:
        if self.request.retries >= self.max_retries:
            log.error("pipeline_batch_retries_exhausted", workspace_id=workspace_id, error=str(exc))
            try:
                asyncio.run(_dead_letter_batch(workspace_id, events, f"retries exhausted: {exc}"))
            except Exception:
                log.exception("pipeline_dead_letter_batch_failed", workspace_id=workspace_id)
            raise
        raise self.retry(exc=exc, countdown=min(300, 5 * 2**self.request.retries)) from exc


async def _dead_letter_batch(workspace_id: str, events: list[dict[str, Any]], error: str) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            for raw in events:
                await _dead_letter(session, workspace_id, raw, error)
            await session.commit()
    finally:
        await engine.dispose()


async def _process_events(workspace_id: str, events: list[dict[str, Any]]) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            privacy_mode, sampled_rate = await _get_capture_policy(session, workspace_id)
            priced_calls: list[dict[str, Any]] = []
            owned_runs: dict[str, bool] = {}
            for raw in events:
                dead_letter_id = raw.pop("_dead_letter_id", None)
                event = _normalize_event(raw)
                try:
                    if not await _event_run_in_workspace(session, workspace_id, event, owned_runs):
                        log.warning(
                            "event_run_not_in_workspace",
                            event_type=event.get("event_type"),
                            run_id=event.get("run_id"),
                            workspace_id=workspace_id,
                        )
                        continue
                    batch_priced: list[dict[str, Any]] = []
                    async with session.begin_nested():
                        await _dispatch(
                            session, workspace_id, event, privacy_mode, sampled_rate, batch_priced
                        )
                    priced_calls.extend(batch_priced)
                    if dead_letter_id:
                        await _mark_dead_letter(session, dead_letter_id, "replayed")
                    if event.get("event_type") == "run_start":
                        # A new run now exists in this workspace (or already did).
                        owned_runs.pop(str(event.get("run_id")), None)
                except Exception as exc:
                    log.warning(
                        "event_dispatch_error",
                        event_type=event.get("event_type"),
                        run_id=event.get("run_id"),
                        error=str(exc),
                    )
                    await _dead_letter(session, workspace_id, event, repr(exc), dead_letter_id)
            if priced_calls:
                await _record_budget_spend(session, workspace_id, priced_calls)
            await session.commit()
    finally:
        await engine.dispose()


async def _dead_letter(
    session: AsyncSession,
    workspace_id: str,
    event: dict[str, Any],
    error: str,
    existing_id: str | None = None,
) -> None:
    """Store a failed event for replay (or bump the attempt count on a replay)."""
    from datetime import UTC  # noqa: PLC0415

    now = datetime.now(UTC)
    try:
        if existing_id:
            await session.execute(
                update(IngestDeadLetter)
                .where(IngestDeadLetter.id == uuid.UUID(str(existing_id)))
                .values(
                    attempts=IngestDeadLetter.attempts + 1,
                    error=error[:4000],
                    status="pending",
                    last_attempt_at=now,
                )
            )
            return
        session.add(
            IngestDeadLetter(
                workspace_id=uuid.UUID(workspace_id),
                event_type=str(event.get("event_type") or "")[:64] or None,
                run_id=str(event.get("run_id") or "")[:64] or None,
                event=json.loads(json.dumps(event, default=str)),
                error=error[:4000],
            )
        )
        await session.flush()
    except Exception:
        log.exception("dead_letter_store_failed", event_type=event.get("event_type"))


async def _mark_dead_letter(session: AsyncSession, dead_letter_id: str, status: str) -> None:
    from datetime import UTC  # noqa: PLC0415

    await session.execute(
        update(IngestDeadLetter)
        .where(IngestDeadLetter.id == uuid.UUID(str(dead_letter_id)))
        .values(status=status, last_attempt_at=datetime.now(UTC))
    )


# Column limits of the tables events land in; longer values are truncated so one
# oversized field (e.g. an OTLP span name) cannot fail an event.
_FIELD_LIMITS = {
    "name": 255,
    "tool_name": 255,
    "end_user_id": 255,
    "session_id": 255,
    "feature_tag": 255,
    "deployment_version": 255,
    "intent": 64,
    "provider": 64,
    "model": 128,
    "error_type": 128,
    "savings_category": 64,
    "optimization_applied": 64,
    "outcome_type": 128,
}
# Provider-call status vocabulary used by analytics: success | error | <other>.
_CALL_STATUS_ALIASES = {
    "succeeded": "success",
    "successful": "success",
    "ok": "success",
    "completed": "success",
    "complete": "success",
    "failed": "error",
    "failure": "error",
    "errored": "error",
}


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Truncate oversized fields and normalize the provider-call status vocabulary."""
    for field, limit in _FIELD_LIMITS.items():
        value = event.get(field)
        if isinstance(value, str) and len(value) > limit:
            event[field] = value[:limit]
    if event.get("event_type") in {"provider_call", "tool_call"}:
        status = str(event.get("status") or "").strip().lower()
        event["status"] = _CALL_STATUS_ALIASES.get(status, status)[:32] or "success"
    return event


def _stable_id(kind: str, event: dict[str, Any]) -> uuid.UUID:
    """Deterministic id for events without one, so retries and replays dedupe."""
    explicit = event.get("event_id") or event.get(f"{kind}_id")
    if explicit:
        try:
            return uuid.UUID(str(explicit))
        except ValueError:
            pass
    canonical = json.dumps(
        {k: v for k, v in event.items() if k not in {"api_key_id"}},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{kind}:{digest}")


async def _event_run_in_workspace(
    session: AsyncSession, workspace_id: str, event: dict[str, Any], cache: dict[str, bool]
) -> bool:
    """Tenant isolation: an event may only touch a run owned by the sending workspace.

    ``run_start`` creates the run (an existing run id from another workspace is left
    untouched by its ON CONFLICT DO NOTHING). Every other event must reference a run
    that already belongs to ``workspace_id``; otherwise it is dropped, so one tenant
    cannot end, annotate or add spans and cost to another tenant's run by id.
    """
    if event.get("event_type") == "run_start":
        return True
    run_id = event.get("run_id")
    if not run_id:
        return True
    key = str(run_id)
    if key not in cache:
        try:
            owner = (
                await session.execute(
                    select(AgentRun.workspace_id).where(AgentRun.id == uuid.UUID(key))
                )
            ).scalar_one_or_none()
        except ValueError:
            owner = None
        cache[key] = owner is not None and str(owner) == str(workspace_id)
    return cache[key]


async def _get_capture_policy(session: AsyncSession, workspace_id: str) -> tuple[str, float]:
    """Return (privacy_mode, sampled_rate) for the workspace.

    Falls back to ('METADATA_ONLY', 0.0) when no policy row exists.
    Errors are swallowed — fail open to avoid blocking ingest.
    """
    try:
        result = await session.execute(
            select(CapturePolicy).where(CapturePolicy.workspace_id == uuid.UUID(workspace_id))
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            return ("METADATA_ONLY", 0.0)
        rate = float(policy.sampled_rate) if policy.sampled_rate is not None else 0.1
        return (policy.privacy_mode, rate)
    except Exception:
        log.warning("capture_policy_lookup_failed", workspace_id=workspace_id)
        return ("METADATA_ONLY", 0.0)


async def _dispatch(
    session: AsyncSession,
    workspace_id: str,
    event: dict[str, Any],
    privacy_mode: str,
    sampled_rate: float,
    priced_calls: list[dict[str, Any]] | None = None,
) -> None:
    match event.get("event_type"):
        case "run_start":
            await _handle_run_start(session, workspace_id, event)
        case "run_end":
            await _handle_run_end(session, event)
        case "span_start":
            await _handle_span_start(session, event)
        case "span_end":
            await _handle_span_end(session, event, privacy_mode, sampled_rate)
        case "provider_call":
            await _handle_provider_call(session, workspace_id, event, priced_calls)
        case "tool_call":
            await _handle_tool_call(session, workspace_id, event)
        case "outcome":
            await _handle_outcome(session, workspace_id, event)
        case unknown:
            log.warning("unknown_event_type", event_type=unknown)


async def _record_budget_spend(
    session: AsyncSession, workspace_id: str, priced_calls: list[dict[str, Any]]
) -> None:
    """Count provider calls that arrived with a cost against matching budgets.

    Fails open: a Redis or lookup error never drops the ingest batch.
    """
    from redis.asyncio import Redis  # noqa: PLC0415

    from runledger_api.services.budgets import record_budget_spend  # noqa: PLC0415

    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        for call in priced_calls:
            try:
                run = await session.get(AgentRun, call["run_id"])
                async with session.begin_nested():
                    await record_budget_spend(
                        session,
                        redis,
                        workspace_id=uuid.UUID(workspace_id),
                        provider_call_id=call["provider_call_id"],
                        cost_usd=call["cost_usd"],
                        run_id=call["run_id"],
                        api_key_id=call["api_key_id"] or (run.api_key_id if run else None),
                        end_user_id=call["end_user_id"] or (run.end_user_id if run else None),
                        feature_tag=run.feature_tag if run else None,
                        app_id=run.application_id if run else None,
                        provider=call["provider"],
                        model=call["model"],
                    )
            except Exception:
                log.exception(
                    "budget_spend_record_failed", provider_call_id=str(call["provider_call_id"])
                )
    finally:
        await redis.aclose()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _dec(value: str | float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


# ── Event handlers ────────────────────────────────────────────────────────────


async def _handle_run_start(session: AsyncSession, workspace_id: str, e: dict[str, Any]) -> None:
    # Workflow spine: resolve workflow + agent inside this workspace (never across).
    attribution = await attribution_from_event(session, uuid.UUID(workspace_id), e)
    stmt = insert(AgentRun).values(
        id=uuid.UUID(e["run_id"]),
        workspace_id=uuid.UUID(workspace_id),
        application_id=_uuid(e.get("application_id")),
        api_key_id=_uuid(e.get("api_key_id")),
        end_user_id=e.get("end_user_id"),
        session_id=e.get("session_id"),
        feature_tag=e.get("feature_tag") or attribution.feature_tag,
        workflow_id=attribution.workflow_id,
        agent_id=attribution.agent_id,
        deployment_version=e.get("deployment_version"),
        status=RunStatusEnum.running,
        started_at=_dt(e["started_at"]),
        run_metadata=scrub_dict(e.get("metadata")),
        intent=e.get("intent"),
        # OTLP source-provenance (populated only for OTLP-ingested runs)
        source_type=e.get("source_type"),
        external_trace_id=e.get("external_trace_id"),
    )
    # A trace can arrive in several batches, children first. Keep the earliest start
    # and fill context the first batch lacked; never touch another workspace's run.
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "started_at": func.least(AgentRun.started_at, excluded.started_at),
            "feature_tag": func.coalesce(AgentRun.feature_tag, excluded.feature_tag),
            "end_user_id": func.coalesce(AgentRun.end_user_id, excluded.end_user_id),
            "session_id": func.coalesce(AgentRun.session_id, excluded.session_id),
            "deployment_version": func.coalesce(
                AgentRun.deployment_version, excluded.deployment_version
            ),
            "intent": func.coalesce(AgentRun.intent, excluded.intent),
            "api_key_id": func.coalesce(AgentRun.api_key_id, excluded.api_key_id),
            "application_id": func.coalesce(AgentRun.application_id, excluded.application_id),
            "workflow_id": func.coalesce(AgentRun.workflow_id, excluded.workflow_id),
            "agent_id": func.coalesce(AgentRun.agent_id, excluded.agent_id),
        },
        where=AgentRun.workspace_id == excluded.workspace_id,
    )
    await session.execute(stmt)
    try:
        await kafka_export.publish_event(
            session,
            workspace_id=uuid.UUID(workspace_id),
            event_type="run.started",
            payload={
                "run_id": e["run_id"],
                "trace_id": e.get("external_trace_id"),
                "end_user_id": e.get("end_user_id"),
                "session_id": e.get("session_id"),
                "feature_tag": e.get("feature_tag") or attribution.feature_tag,
                "workflow_id": str(attribution.workflow_id) if attribution.workflow_id else None,
                "deployment_version": e.get("deployment_version"),
                "started_at": e.get("started_at"),
                "source": e.get("source_type") or "runledger.ingest",
                "event_summary": "Run started",
            },
        )
    except Exception:
        log.exception("kafka_export.run_start_unexpected_error", run_id=e.get("run_id"))


async def _handle_run_end(session: AsyncSession, e: dict[str, Any]) -> None:
    status = e["status"]
    run_id = uuid.UUID(e["run_id"])
    values: dict[str, Any] = {
        "status": RunStatusEnum(status),
        # A run can receive several run_end events (e.g. one per Claude Code API
        # request in a prompt); only ever move ended_at forward. GREATEST ignores NULL.
        "ended_at": func.greatest(AgentRun.ended_at, _dt(e["ended_at"])),
    }
    # Totals are usually filled in later by the cost rollup; don't overwrite
    # them with NULL when the event doesn't carry them.
    if e.get("total_cost_usd") is not None:
        values["total_cost_usd"] = _dec(e["total_cost_usd"])
    if e.get("total_input_tokens") is not None:
        values["total_input_tokens"] = e["total_input_tokens"]
    if e.get("total_output_tokens") is not None:
        values["total_output_tokens"] = e["total_output_tokens"]
    await session.execute(update(AgentRun).where(AgentRun.id == run_id).values(**values))
    run = await session.get(AgentRun, run_id)
    if run is None:
        return
    event_type = "run.completed" if status == RunStatusEnum.succeeded else "run.failed"
    try:
        await kafka_export.publish_event(
            session,
            workspace_id=run.workspace_id,
            event_type=event_type,
            payload={
                "run_id": str(run.id),
                "status": status,
                "end_user_id": run.end_user_id,
                "session_id": run.session_id,
                "feature_tag": run.feature_tag,
                "total_cost_usd": str(e.get("total_cost_usd") or ""),
                "total_input_tokens": e.get("total_input_tokens"),
                "total_output_tokens": e.get("total_output_tokens"),
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "ended_at": e.get("ended_at"),
            },
        )
    except Exception:
        log.exception("kafka_export.run_end_unexpected_error", run_id=str(run_id))


async def _handle_span_start(session: AsyncSession, e: dict[str, Any]) -> None:
    stmt = (
        insert(Span)
        .values(
            id=uuid.UUID(e["span_id"]),
            run_id=uuid.UUID(e["run_id"]),
            parent_span_id=_uuid(e.get("parent_span_id")),
            span_type=SpanTypeEnum(e["span_type"]),
            name=e["name"],
            started_at=_dt(e["started_at"]),
            status=SpanStatusEnum.running,
            # OTLP source-provenance (populated only for OTLP-ingested spans)
            external_span_id=e.get("external_span_id"),
            external_parent_span_id=e.get("external_parent_span_id"),
            instrumentation_scope_name=e.get("instrumentation_scope_name"),
            instrumentation_scope_version=e.get("instrumentation_scope_version"),
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)


def _apply_capture_policy(
    privacy_mode: str,
    sampled_rate: float,
    raw_metadata: dict[str, Any] | None,
    status: str,
) -> dict[str, Any] | None:
    """Filter span metadata according to the workspace's CapturePolicy.

    FULL         — always persist (after PII scrub)
    ERRORS_ONLY  — persist only on failed/error spans
    SAMPLED      — persist at the configured sampling rate
    METADATA_ONLY (default) — never persist payload
    """
    if privacy_mode == "FULL":
        return scrub_dict(raw_metadata)
    if privacy_mode == "ERRORS_ONLY":
        return scrub_dict(raw_metadata) if status in ("failed", "error") else None
    if privacy_mode == "SAMPLED":
        return scrub_dict(raw_metadata) if random.random() < sampled_rate else None
    # METADATA_ONLY — drop payload
    return None


async def _handle_span_end(
    session: AsyncSession,
    e: dict[str, Any],
    privacy_mode: str,
    sampled_rate: float,
) -> None:
    span_metadata = _apply_capture_policy(
        privacy_mode, sampled_rate, e.get("metadata"), e.get("status", "")
    )
    await session.execute(
        update(Span)
        # Match the run too: the run's ownership was checked, the span id alone was not.
        .where(Span.id == uuid.UUID(e["span_id"]), Span.run_id == uuid.UUID(e["run_id"]))
        .values(
            status=SpanStatusEnum(e["status"]),
            ended_at=_dt(e["ended_at"]),
            cost_usd=_dec(e.get("cost_usd")),
            span_metadata=span_metadata,
        )
    )


def _provider_call_id(run_id: str, span_id: str | None) -> uuid.UUID:
    """Deterministic UUID when span_id is present so retries are idempotent."""
    if span_id:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"pc:{run_id}:{span_id}")
    return uuid.uuid4()


async def _handle_provider_call(
    session: AsyncSession,
    workspace_id: str,
    e: dict[str, Any],
    priced_calls: list[dict[str, Any]] | None = None,
) -> None:
    span_id = e.get("span_id")
    pc_id = _provider_call_id(e["run_id"], span_id)
    end_user_id = e.get("end_user_id")
    if end_user_id is None:
        # Denormalize the run's end user so per-user analytics and budgets see it.
        end_user_id = (
            await session.execute(
                select(AgentRun.end_user_id).where(AgentRun.id == uuid.UUID(e["run_id"]))
            )
        ).scalar_one_or_none()
    stmt = (
        insert(ProviderCall)
        .values(
            id=pc_id,
            run_id=uuid.UUID(e["run_id"]),
            span_id=_uuid(span_id),
            workspace_id=uuid.UUID(workspace_id),
            api_key_id=_uuid(e.get("api_key_id")),
            end_user_id=end_user_id,
            provider=e["provider"],
            model=e["model"],
            input_tokens=e.get("input_tokens"),
            output_tokens=e.get("output_tokens"),
            cached_input_tokens=e.get("cached_input_tokens"),
            latency_ms=e.get("latency_ms"),
            cost_usd=_dec(e.get("cost_usd")),
            status=e["status"],
            error_type=e.get("error_type"),
            # Reconciliation-grade fields (populated for OTLP + future SDK enrichment)
            provider_request_id=e.get("provider_request_id"),
            reported_cost_usd=_dec(e.get("reported_cost_usd")),
            cost_source=e.get("cost_source"),
            model_provider=e.get("model_provider"),
            input_tokens_details=e.get("input_tokens_details"),
            output_tokens_details=e.get("output_tokens_details"),
            savings_usd=_dec(e.get("savings_usd")),
            savings_category=e.get("savings_category"),
            savings_reason=e.get("savings_reason"),
            baseline_cost_usd=_dec(e.get("baseline_cost_usd")),
            optimization_applied=e.get("optimization_applied"),
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)
    cost = _dec(e.get("cost_usd"))
    if priced_calls is not None and cost is not None and e.get("status") == "success":
        # Calls without a cost are counted later by metering.enrich_costs.
        priced_calls.append(
            {
                "provider_call_id": pc_id,
                "run_id": uuid.UUID(e["run_id"]),
                "cost_usd": cost,
                "api_key_id": _uuid(e.get("api_key_id")),
                "end_user_id": end_user_id,
                "provider": e.get("provider"),
                "model": e.get("model"),
            }
        )
    if e.get("optimization_applied"):
        try:
            await kafka_export.publish_event(
                session,
                workspace_id=uuid.UUID(workspace_id),
                event_type="optimization.applied",
                payload={
                    "run_id": e["run_id"],
                    "trace_id": e.get("external_trace_id"),
                    "provider_call_id": str(pc_id),
                    "provider": e.get("provider"),
                    "model": e.get("model"),
                    "optimization_applied": e.get("optimization_applied"),
                    "savings_usd": e.get("savings_usd"),
                    "savings_category": e.get("savings_category"),
                    "savings_reason": e.get("savings_reason"),
                    "source": "runledger.ingest",
                    "event_summary": f"Optimization applied: {e.get('optimization_applied')}",
                },
            )
        except Exception:
            log.exception("kafka_export.optimization_unexpected_error", run_id=e.get("run_id"))


async def _handle_tool_call(session: AsyncSession, workspace_id: str, e: dict[str, Any]) -> None:
    await session.execute(
        insert(ToolCall)
        .values(
            id=_stable_id("tool_call", e),
            run_id=uuid.UUID(e["run_id"]),
            span_id=_uuid(e.get("span_id")),
            workspace_id=uuid.UUID(workspace_id),
            tool_name=e["tool_name"],
            tool_type=ToolTypeEnum(e.get("tool_type", "read")),
            risk_score=e.get("risk_score"),
            duration_ms=e.get("duration_ms"),
            status=e["status"],
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    event_type = (
        "mcp.tool.blocked"
        if str(e.get("status")).lower() in {"blocked", "denied"}
        else "mcp.tool.called"
    )
    try:
        await kafka_export.publish_event(
            session,
            workspace_id=uuid.UUID(workspace_id),
            event_type=event_type,
            payload={
                "run_id": e["run_id"],
                "trace_id": e.get("external_trace_id"),
                "tool_name": e.get("tool_name"),
                "tool_type": e.get("tool_type", "read"),
                "status": e.get("status"),
                "risk_score": e.get("risk_score"),
                "duration_ms": e.get("duration_ms"),
                "source": "runledger.ingest",
                "event_summary": f"Tool {e.get('tool_name')} {e.get('status')}",
            },
        )
    except Exception:
        log.exception("kafka_export.tool_call_unexpected_error", run_id=e.get("run_id"))


async def _handle_outcome(session: AsyncSession, workspace_id: str, e: dict[str, Any]) -> None:
    # One outcomes table for SDK, MCP, ingest and the Outcomes API (review O-03).
    run_id = uuid.UUID(e["run_id"])
    run = (
        await session.execute(
            select(AgentRun.session_id, AgentRun.end_user_id).where(
                AgentRun.id == run_id, AgentRun.workspace_id == uuid.UUID(workspace_id)
            )
        )
    ).one_or_none()
    await session.execute(
        insert(Outcome)
        .values(
            id=_stable_id("outcome", e),
            workspace_id=uuid.UUID(workspace_id),
            run_id=run_id,
            session_id=run.session_id if run else None,
            end_user_id=run.end_user_id if run else None,
            outcome_type=e["outcome_type"],
            success=e["success"],
            labels=e.get("labels") or {},
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
