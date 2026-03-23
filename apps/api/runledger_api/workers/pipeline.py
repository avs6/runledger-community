"""
Celery pipeline worker for processing ingest events.

Uses asyncio.run() + NullPool so each task creates a fresh DB connection —
safe with Celery's --pool=solo and avoids event-loop reuse across tasks.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import (
    AgentRun,
    OutcomeEvent,
    ProviderCall,
    RunStatusEnum,
    Span,
    SpanStatusEnum,
    SpanTypeEnum,
    ToolCall,
    ToolTypeEnum,
)
from runledger_api.models.ledger import CapturePolicy
from runledger_api.services.scrubbing import scrub_dict

log = structlog.get_logger()


@celery_app.task(name="pipeline.process_events", max_retries=3, default_retry_delay=5)  # type: ignore[untyped-decorator]
def process_events_task(workspace_id: str, events: list[dict[str, Any]]) -> None:
    """Persist a batch of ingest events to PostgreSQL."""
    asyncio.run(_process_events(workspace_id, events))


async def _process_events(workspace_id: str, events: list[dict[str, Any]]) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            privacy_mode, sampled_rate = await _get_capture_policy(session, workspace_id)
            for raw in events:
                try:
                    await _dispatch(session, workspace_id, raw, privacy_mode, sampled_rate)
                except Exception:
                    log.exception("event_dispatch_error", event_type=raw.get("event_type"))
            await session.commit()
    finally:
        await engine.dispose()


async def _get_capture_policy(
    session: AsyncSession, workspace_id: str
) -> tuple[str, float]:
    """Return (privacy_mode, sampled_rate) for the workspace.

    Falls back to ('METADATA_ONLY', 0.0) when no policy row exists.
    Errors are swallowed — fail open to avoid blocking ingest.
    """
    try:
        result = await session.execute(
            select(CapturePolicy).where(
                CapturePolicy.workspace_id == uuid.UUID(workspace_id)
            )
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
            await _handle_provider_call(session, workspace_id, event)
        case "tool_call":
            await _handle_tool_call(session, workspace_id, event)
        case "outcome":
            await _handle_outcome(session, event)
        case unknown:
            log.warning("unknown_event_type", event_type=unknown)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _dec(value: str | float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


# ── Event handlers ────────────────────────────────────────────────────────────


async def _handle_run_start(session: AsyncSession, workspace_id: str, e: dict[str, Any]) -> None:
    stmt = (
        insert(AgentRun)
        .values(
            id=uuid.UUID(e["run_id"]),
            workspace_id=uuid.UUID(workspace_id),
            application_id=_uuid(e.get("application_id")),
            end_user_id=e.get("end_user_id"),
            session_id=e.get("session_id"),
            feature_tag=e.get("feature_tag"),
            deployment_version=e.get("deployment_version"),
            status=RunStatusEnum.running,
            started_at=_dt(e["started_at"]),
            run_metadata=scrub_dict(e.get("metadata")),
            # OTLP source-provenance (populated only for OTLP-ingested runs)
            source_type=e.get("source_type"),
            external_trace_id=e.get("external_trace_id"),
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)


async def _handle_run_end(session: AsyncSession, e: dict[str, Any]) -> None:
    await session.execute(
        update(AgentRun)
        .where(AgentRun.id == uuid.UUID(e["run_id"]))
        .values(
            status=RunStatusEnum(e["status"]),
            ended_at=_dt(e["ended_at"]),
            total_cost_usd=_dec(e.get("total_cost_usd")),
            total_input_tokens=e.get("total_input_tokens"),
            total_output_tokens=e.get("total_output_tokens"),
        )
    )


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
        .where(Span.id == uuid.UUID(e["span_id"]))
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
    session: AsyncSession, workspace_id: str, e: dict[str, Any]
) -> None:
    span_id = e.get("span_id")
    pc_id = _provider_call_id(e["run_id"], span_id)
    stmt = (
        insert(ProviderCall)
        .values(
            id=pc_id,
            run_id=uuid.UUID(e["run_id"]),
            span_id=_uuid(span_id),
            workspace_id=uuid.UUID(workspace_id),
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
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)


async def _handle_tool_call(session: AsyncSession, workspace_id: str, e: dict[str, Any]) -> None:
    session.add(
        ToolCall(
            run_id=uuid.UUID(e["run_id"]),
            span_id=_uuid(e.get("span_id")),
            workspace_id=uuid.UUID(workspace_id),
            tool_name=e["tool_name"],
            tool_type=ToolTypeEnum(e.get("tool_type", "read")),
            risk_score=e.get("risk_score"),
            duration_ms=e.get("duration_ms"),
            status=e["status"],
        )
    )


async def _handle_outcome(session: AsyncSession, e: dict[str, Any]) -> None:
    session.add(
        OutcomeEvent(
            run_id=uuid.UUID(e["run_id"]),
            event_type=e["outcome_type"],
            success=e["success"],
            labels=e.get("labels"),
        )
    )
