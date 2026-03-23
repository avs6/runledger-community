"""
Data retention and purge service.

All purge logic lives here so the router and the Celery worker both
call the same code path.  Functions are pure async — no Celery dependency.

Purge dispatch matrix
---------------------
resource_type   action   notes
─────────────────────────────────────────────────────────────────────────────
runs            delete   DELETE agent_runs; Postgres cascades to spans,
                         provider_calls, tool_calls, outcome_events
spans           delete   DELETE spans; agent_runs are preserved
payloads        scrub    UPDATE spans.metadata / agent_runs.metadata to
spans           scrub    remove 'messages' and 'response' keys (identical paths)
provider_calls  delete   DELETE provider_calls; no cascade needed
─────────────────────────────────────────────────────────────────────────────

Scope
-----
workspace  — filter by workspace_id + started_at/created_at < cutoff
end_user   — filter by workspace_id + end_user_id == scope_value
             (max_age_days is ignored for end_user scope)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.events import AgentRun, ProviderCall, Span

log = structlog.get_logger()


def _cutoff(max_age_days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=max_age_days)


async def purge_resource(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    resource_type: str,
    action: str,
    scope: str = "workspace",
    scope_value: str | None = None,
    max_age_days: int | None = None,
    dry_run: bool = False,
) -> tuple[int, datetime | None]:
    """
    Execute (or simulate) a data purge.

    Returns (affected_rows, cutoff_datetime).
    cutoff is None for end_user scope.
    """
    if scope == "end_user":
        return await _purge_end_user(
            db,
            workspace_id=workspace_id,
            resource_type=resource_type,
            action=action,
            scope_value=scope_value or "",
            dry_run=dry_run,
        )

    # workspace scope — max_age_days required
    if max_age_days is None:
        raise ValueError("max_age_days required for workspace scope")

    cut = _cutoff(max_age_days)

    if resource_type == "runs":
        count = await _purge_runs(db, workspace_id=workspace_id, cutoff=cut, dry_run=dry_run)
    elif resource_type == "spans":
        if action == "scrub":
            count = await _scrub_payloads(db, workspace_id=workspace_id, cutoff=cut, dry_run=dry_run)
        else:
            count = await _purge_spans(db, workspace_id=workspace_id, cutoff=cut, dry_run=dry_run)
    elif resource_type == "payloads":
        count = await _scrub_payloads(db, workspace_id=workspace_id, cutoff=cut, dry_run=dry_run)
    elif resource_type == "provider_calls":
        count = await _purge_provider_calls(db, workspace_id=workspace_id, cutoff=cut, dry_run=dry_run)
    else:
        raise ValueError(f"Unknown resource_type: {resource_type!r}")

    return count, cut


# ── Workspace-scope purge helpers ─────────────────────────────────────────────

async def _purge_runs(
    db: AsyncSession, *, workspace_id: uuid.UUID, cutoff: datetime, dry_run: bool
) -> int:
    if dry_run:
        result = await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.started_at < cutoff,
            )
        )
        return result.scalar() or 0

    result = await db.execute(
        delete(AgentRun).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.started_at < cutoff,
        )
    )
    return result.rowcount


async def _purge_spans(
    db: AsyncSession, *, workspace_id: uuid.UUID, cutoff: datetime, dry_run: bool
) -> int:
    # Span has no workspace_id — must join via run_id subquery
    run_subq = (
        select(AgentRun.id)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.started_at < cutoff)
        .scalar_subquery()
    )

    if dry_run:
        result = await db.execute(
            select(func.count(Span.id)).where(Span.run_id.in_(run_subq))
        )
        return result.scalar() or 0

    result = await db.execute(delete(Span).where(Span.run_id.in_(run_subq)))
    return result.rowcount


async def _scrub_payloads(
    db: AsyncSession, *, workspace_id: uuid.UUID, cutoff: datetime, dry_run: bool
) -> int:
    """Remove 'messages' and 'response' keys from span metadata and agent_run metadata."""
    run_subq = (
        select(AgentRun.id)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.started_at < cutoff)
        .scalar_subquery()
    )

    if dry_run:
        # Count spans that have payload data
        result = await db.execute(
            select(func.count(Span.id)).where(
                Span.run_id.in_(run_subq),
                Span.span_metadata.isnot(None),
            )
        )
        span_count = result.scalar() or 0

        result2 = await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.started_at < cutoff,
                AgentRun.run_metadata.isnot(None),
            )
        )
        run_count = result2.scalar() or 0
        return span_count + run_count

    # Scrub span payload keys (JSONB - operator removes a key)
    span_result = await db.execute(
        update(Span)
        .where(Span.run_id.in_(run_subq))
        .values({Span.span_metadata: Span.span_metadata.op("-")("messages").op("-")("response")})
    )

    # Scrub agent_run metadata
    run_result = await db.execute(
        update(AgentRun)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.started_at < cutoff)
        .values({AgentRun.run_metadata: AgentRun.run_metadata.op("-")("messages").op("-")("response")})
    )

    return span_result.rowcount + run_result.rowcount


async def _purge_provider_calls(
    db: AsyncSession, *, workspace_id: uuid.UUID, cutoff: datetime, dry_run: bool
) -> int:
    if dry_run:
        result = await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.created_at < cutoff,
            )
        )
        return result.scalar() or 0

    result = await db.execute(
        delete(ProviderCall).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.created_at < cutoff,
        )
    )
    return result.rowcount


# ── End-user scope (GDPR erasure) ─────────────────────────────────────────────

async def _purge_end_user(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    resource_type: str,
    action: str,
    scope_value: str,
    dry_run: bool,
) -> tuple[int, None]:
    if resource_type == "runs":
        count = await _purge_runs_end_user(db, workspace_id=workspace_id, end_user_id=scope_value, dry_run=dry_run)
    elif resource_type in ("spans", "payloads"):
        if action == "scrub":
            count = await _scrub_payloads_end_user(db, workspace_id=workspace_id, end_user_id=scope_value, dry_run=dry_run)
        else:
            count = await _purge_spans_end_user(db, workspace_id=workspace_id, end_user_id=scope_value, dry_run=dry_run)
    elif resource_type == "provider_calls":
        count = await _purge_provider_calls_end_user(db, workspace_id=workspace_id, end_user_id=scope_value, dry_run=dry_run)
    else:
        raise ValueError(f"Unknown resource_type: {resource_type!r}")

    return count, None


async def _purge_runs_end_user(
    db: AsyncSession, *, workspace_id: uuid.UUID, end_user_id: str, dry_run: bool
) -> int:
    if dry_run:
        result = await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.end_user_id == end_user_id,
            )
        )
        return result.scalar() or 0

    result = await db.execute(
        delete(AgentRun).where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.end_user_id == end_user_id,
        )
    )
    return result.rowcount


async def _purge_spans_end_user(
    db: AsyncSession, *, workspace_id: uuid.UUID, end_user_id: str, dry_run: bool
) -> int:
    run_subq = (
        select(AgentRun.id)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.end_user_id == end_user_id)
        .scalar_subquery()
    )

    if dry_run:
        result = await db.execute(
            select(func.count(Span.id)).where(Span.run_id.in_(run_subq))
        )
        return result.scalar() or 0

    result = await db.execute(delete(Span).where(Span.run_id.in_(run_subq)))
    return result.rowcount


async def _scrub_payloads_end_user(
    db: AsyncSession, *, workspace_id: uuid.UUID, end_user_id: str, dry_run: bool
) -> int:
    run_subq = (
        select(AgentRun.id)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.end_user_id == end_user_id)
        .scalar_subquery()
    )

    if dry_run:
        result = await db.execute(
            select(func.count(Span.id)).where(
                Span.run_id.in_(run_subq),
                Span.span_metadata.isnot(None),
            )
        )
        return result.scalar() or 0

    span_result = await db.execute(
        update(Span)
        .where(Span.run_id.in_(run_subq))
        .values({Span.span_metadata: Span.span_metadata.op("-")("messages").op("-")("response")})
    )
    run_result = await db.execute(
        update(AgentRun)
        .where(AgentRun.workspace_id == workspace_id, AgentRun.end_user_id == end_user_id)
        .values({AgentRun.run_metadata: AgentRun.run_metadata.op("-")("messages").op("-")("response")})
    )
    return span_result.rowcount + run_result.rowcount


async def _purge_provider_calls_end_user(
    db: AsyncSession, *, workspace_id: uuid.UUID, end_user_id: str, dry_run: bool
) -> int:
    if dry_run:
        result = await db.execute(
            select(func.count(ProviderCall.id)).where(
                ProviderCall.workspace_id == workspace_id,
                ProviderCall.end_user_id == end_user_id,
            )
        )
        return result.scalar() or 0

    result = await db.execute(
        delete(ProviderCall).where(
            ProviderCall.workspace_id == workspace_id,
            ProviderCall.end_user_id == end_user_id,
        )
    )
    return result.rowcount
