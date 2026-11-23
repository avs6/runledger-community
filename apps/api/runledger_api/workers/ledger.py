"""
Celery ledger workers for RunLedger.

Workers
-------
daily_snapshots
    For each workspace active yesterday, seals a signed, chained daily snapshot
    with a per-call manifest (services.ledger.seal_snapshot). Sealed snapshots are
    never overwritten. Runs at 1am UTC.

suspicious_sequences
    Detects bursts of >5 identical tool calls within 60 seconds per
    (workspace_id, tool_name, end_user_id). Inserts SecurityEvent rows.
    Runs every 60 seconds.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import AgentRun, ProviderCall, ToolCall
from runledger_api.models.ledger import SecurityEvent
from runledger_api.services.ledger import seal_snapshot

log = structlog.get_logger()


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ── daily_snapshots ───────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="ledger.daily_snapshots",
    max_retries=1,
)
def daily_snapshots_worker() -> dict[str, int]:
    """Sign and store daily spend snapshots for all active workspaces."""
    return asyncio.run(_run_daily_snapshots())


async def _run_daily_snapshots() -> dict[str, int]:
    """Seal yesterday's snapshot for every workspace with calls that day (cd:M-02)."""
    factory = _make_session_factory()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    start = datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
    snapshotted = 0

    async with factory() as session:
        workspace_ids = [
            row[0]
            for row in (
                await session.execute(
                    select(ProviderCall.workspace_id)
                    .where(
                        ProviderCall.created_at >= start,
                        ProviderCall.created_at < start + timedelta(days=1),
                    )
                    .distinct()
                )
            ).all()
        ]
        for workspace_id in workspace_ids:
            try:
                _, created = await seal_snapshot(session, workspace_id, yesterday)
                await session.commit()
                snapshotted += int(created)
            except Exception as exc:  # noqa: BLE001
                log.error("ledger_snapshot_error", workspace_id=str(workspace_id), error=str(exc))
                await session.rollback()

    return {"workspaces_snapshotted": snapshotted}


# ── suspicious_sequences ──────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="ledger.suspicious_sequences",
    max_retries=1,
)
def suspicious_sequences_worker() -> dict[str, int]:
    """Detect >5 identical tool calls in 60 seconds and log security events."""
    return asyncio.run(_run_suspicious_sequences())


async def _run_suspicious_sequences() -> dict[str, int]:
    factory = _make_session_factory()
    flagged = 0
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=60)
    dedup_window = now - timedelta(minutes=5)

    async with factory() as session:
        # Find bursts: >5 calls for same (workspace, tool_name, end_user_id) in last 60s
        burst_result = await session.execute(
            select(
                ToolCall.workspace_id,
                ToolCall.tool_name,
                AgentRun.end_user_id,
                func.count(ToolCall.id).label("cnt"),
            )
            .join(AgentRun, AgentRun.id == ToolCall.run_id)
            .where(ToolCall.created_at >= window_start)
            .group_by(ToolCall.workspace_id, ToolCall.tool_name, AgentRun.end_user_id)
            .having(func.count(ToolCall.id) > 5)
        )
        bursts = burst_result.all()

        for row in bursts:
            workspace_id = row.workspace_id
            tool_name = row.tool_name
            end_user_id = row.end_user_id
            cnt = row.cnt

            # Dedup: skip if event already logged in last 5 minutes
            existing_event_result = await session.execute(
                select(SecurityEvent.id).where(
                    SecurityEvent.workspace_id == workspace_id,
                    SecurityEvent.event_type == "suspicious_sequence",
                    SecurityEvent.tool_name == tool_name,
                    SecurityEvent.end_user_id == end_user_id,
                    SecurityEvent.detected_at > dedup_window,
                )
            )
            if existing_event_result.scalar_one_or_none() is not None:
                continue

            event = SecurityEvent(
                workspace_id=workspace_id,
                event_type="suspicious_sequence",
                tool_name=tool_name,
                end_user_id=end_user_id,
                details={"count": cnt, "window_seconds": 60},
                detected_at=now,
            )
            session.add(event)
            flagged += 1

        if flagged > 0:
            await session.commit()
            log.info("suspicious_sequences_flagged", count=flagged)

    return {"suspicious_sequences_flagged": flagged}
