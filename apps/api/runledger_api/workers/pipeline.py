"""
Celery pipeline worker for processing ingest events.

Uses asyncio.run() + NullPool so each task creates a fresh DB connection —
safe with Celery's --pool=solo and avoids event-loop reuse across tasks.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.services.scrubbing import scrub_dict
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
            for raw in events:
                try:
                    await _dispatch(session, workspace_id, raw)
                except Exception:
                    log.exception("event_dispatch_error", event_type=raw.get("event_type"))
            await session.commit()
    finally:
        await engine.dispose()


async def _dispatch(session: AsyncSession, workspace_id: str, event: dict[str, Any]) -> None:
    match event.get("event_type"):
        case "run_start":
            await _handle_run_start(session, workspace_id, event)
        case "run_end":
            await _handle_run_end(session, event)
        case "span_start":
            await _handle_span_start(session, event)
        case "span_end":
            await _handle_span_end(session, event)
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
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(stmt)


async def _handle_span_end(session: AsyncSession, e: dict[str, Any]) -> None:
    await session.execute(
        update(Span)
        .where(Span.id == uuid.UUID(e["span_id"]))
        .values(
            status=SpanStatusEnum(e["status"]),
            ended_at=_dt(e["ended_at"]),
            cost_usd=_dec(e.get("cost_usd")),
            span_metadata=scrub_dict(e.get("metadata")),
        )
    )


async def _handle_provider_call(
    session: AsyncSession, workspace_id: str, e: dict[str, Any]
) -> None:
    session.add(
        ProviderCall(
            run_id=uuid.UUID(e["run_id"]),
            span_id=_uuid(e.get("span_id")),
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
        )
    )


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
