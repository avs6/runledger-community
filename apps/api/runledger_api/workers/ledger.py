"""
Celery ledger workers for RunLedger.

Workers
-------
daily_snapshots
    For each workspace active yesterday, builds a HMAC-signed daily snapshot
    and upserts it into ledger_snapshots. Runs at 1am UTC.

suspicious_sequences
    Detects bursts of >5 identical tool calls within 60 seconds per
    (workspace_id, tool_name, end_user_id). Inserts SecurityEvent rows.
    Runs every 60 seconds.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.events import ProviderCall, ToolCall
from runledger_api.models.ledger import LedgerSnapshot, SecurityEvent
from runledger_api.models.tenant import Workspace
from runledger_api.services.ledger import (
    build_daily_snapshot,
    compute_snapshot_hash,
    get_or_create_active_key,
)

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
    factory = _make_session_factory()
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    snapshotted = 0

    async with factory() as session:
        # Find workspaces active yesterday
        ws_result = await session.execute(
            select(ProviderCall.workspace_id)
            .where(func.date(ProviderCall.created_at) == yesterday)
            .distinct()
        )
        workspace_ids = [row[0] for row in ws_result.all()]

        for workspace_id in workspace_ids:
            try:
                snapshot_data = await build_daily_snapshot(session, workspace_id, yesterday)
                key = await get_or_create_active_key(session, workspace_id)
                snapshot_hash = compute_snapshot_hash(snapshot_data, key.key_value)

                from decimal import Decimal  # noqa: PLC0415

                total_cost = Decimal(snapshot_data["total_cost_usd"])
                call_count = snapshot_data["call_count"]
                model_breakdown = snapshot_data["model_breakdown"]

                existing_result = await session.execute(
                    select(LedgerSnapshot).where(
                        LedgerSnapshot.workspace_id == workspace_id,
                        LedgerSnapshot.snapshot_date == yesterday,
                    )
                )
                existing = existing_result.scalar_one_or_none()

                if existing is not None:
                    await session.execute(
                        update(LedgerSnapshot)
                        .where(LedgerSnapshot.id == existing.id)
                        .values(
                            total_cost_usd=total_cost,
                            model_breakdown=model_breakdown,
                            call_count=call_count,
                            hash=snapshot_hash,
                            key_id=key.id,
                        )
                    )
                else:
                    snap = LedgerSnapshot(
                        workspace_id=workspace_id,
                        snapshot_date=yesterday,
                        total_cost_usd=total_cost,
                        model_breakdown=model_breakdown,
                        call_count=call_count,
                        hash=snapshot_hash,
                        key_id=key.id,
                    )
                    session.add(snap)

                await session.commit()
                snapshotted += 1
                log.info(
                    "ledger_snapshot_upserted",
                    workspace_id=str(workspace_id),
                    snapshot_date=str(yesterday),
                )
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "ledger_snapshot_error",
                    workspace_id=str(workspace_id),
                    error=str(exc),
                )
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
                ToolCall.end_user_id,
                func.count(ToolCall.id).label("cnt"),
            )
            .where(ToolCall.created_at >= window_start)
            .group_by(ToolCall.workspace_id, ToolCall.tool_name, ToolCall.end_user_id)
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
