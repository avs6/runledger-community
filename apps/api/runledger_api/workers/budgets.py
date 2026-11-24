"""
Celery budget workers for RunLedger.

Workers
-------
runaway_protection
    Detects retry storms (more than RUNAWAY_STORM_CALLS calls in 2 minutes for one
    run or one gateway session) and token spikes (a call with more than
    RUNAWAY_SPIKE_TOKENS input tokens in a running run). It places a *hold* on the run
    or session (budget_runaway_holds); the gateway refuses held subjects with 429
    and /budgets/check reports them as blocked (review cd:B-09). Running runs are
    also marked cancelled. Every 5 minutes.

budget_spend_sync
    Recomputes each active budget's current-period spend from provider_calls and
    reconciles budget_spend (Postgres, the source of truth) and its Redis cache.
    Daily.

deliver_notifications
    Sends queued budget webhook / Slack deliveries with retry and backoff (F-22).
    Every 60 seconds, and kicked right after a breach is recorded.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.budgets import (
    Budget,
    BudgetBreach,
    BudgetNotification,
    BudgetNotificationDelivery,
    RunawayHold,
)
from runledger_api.models.events import AgentRun, ProviderCall
from runledger_api.models.tenant import Workspace
from runledger_api.services.billable import billable_filters
from runledger_api.services.budgets import (
    DELIVERY_MAX_ATTEMPTS,
    delivery_backoff,
    invalidate_runaway_holds_cache,
    period_window,
    queue_notifications,
    resolve_scope_filters,
    send_notification,
    set_budget_spend,
)
from runledger_api.services.email import send_budget_breach_email
from runledger_api.services.email_utils import get_email_preference, get_workspace_admin_users

log = structlog.get_logger()

RUNAWAY_WINDOW = timedelta(minutes=2)
RUNAWAY_STORM_CALLS = 20
RUNAWAY_SPIKE_TOKENS = 100_000
RUNAWAY_HOLD_MINUTES = 30


def _make_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _make_redis() -> Redis:
    return cast(Redis, Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True))


# ── runaway_protection ────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="budgets.runaway_protection",
    max_retries=2,
    default_retry_delay=30,
)
def runaway_protection() -> dict[str, int]:
    """Detect retry storms and token spikes, and hold the offending run or session."""
    return asyncio.run(_run_runaway_protection())


async def detect_runaways(session: AsyncSession, now: datetime) -> list[dict[str, Any]]:
    """Runaway candidates: ``{workspace_id, subject_type, subject_id, reason, calls}``.

    - run retry storm: any run (whatever its status, so gateway and OTLP runs count)
      with more than RUNAWAY_STORM_CALLS calls in the window;
    - session retry storm: a session whose runs made that many calls (the gateway
      records one run per request, so loops show up per session);
    - token spike: a running run with one call above RUNAWAY_SPIKE_TOKENS input tokens.
    """
    since = now - RUNAWAY_WINDOW
    found: list[dict[str, Any]] = []
    runs = await session.execute(
        select(ProviderCall.workspace_id, ProviderCall.run_id, func.count(ProviderCall.id))
        .where(ProviderCall.created_at >= since)
        .group_by(ProviderCall.workspace_id, ProviderCall.run_id)
        .having(func.count(ProviderCall.id) > RUNAWAY_STORM_CALLS)
    )
    for ws, run_id, calls in runs.all():
        found.append(
            {
                "workspace_id": ws,
                "subject_type": "run",
                "subject_id": str(run_id),
                "reason": "retry_storm",
                "calls": int(calls),
            }
        )
    sessions = await session.execute(
        select(AgentRun.workspace_id, AgentRun.session_id, func.count(ProviderCall.id))
        .join(ProviderCall, ProviderCall.run_id == AgentRun.id)
        .where(ProviderCall.created_at >= since, AgentRun.session_id.is_not(None))
        .group_by(AgentRun.workspace_id, AgentRun.session_id)
        .having(func.count(ProviderCall.id) > RUNAWAY_STORM_CALLS)
    )
    for ws, session_id, calls in sessions.all():
        found.append(
            {
                "workspace_id": ws,
                "subject_type": "session",
                "subject_id": str(session_id),
                "reason": "retry_storm",
                "calls": int(calls),
            }
        )
    spikes = await session.execute(
        select(AgentRun.workspace_id, AgentRun.id)
        .join(ProviderCall, ProviderCall.run_id == AgentRun.id)
        .where(
            AgentRun.status == "running",
            ProviderCall.input_tokens > RUNAWAY_SPIKE_TOKENS,
        )
        .distinct()
    )
    seen = {(f["subject_type"], f["subject_id"]) for f in found}
    for ws, run_id in spikes.all():
        if ("run", str(run_id)) not in seen:
            found.append(
                {
                    "workspace_id": ws,
                    "subject_type": "run",
                    "subject_id": str(run_id),
                    "reason": "token_spike",
                    "calls": 0,
                }
            )
    return found


async def place_hold(
    session: AsyncSession, candidate: dict[str, Any], now: datetime
) -> RunawayHold | None:
    """Create a hold unless the subject already has an active one (or was released
    in this window, so an admin's release isn't immediately undone)."""
    existing = await session.execute(
        select(RunawayHold.id).where(
            RunawayHold.workspace_id == candidate["workspace_id"],
            RunawayHold.subject_type == candidate["subject_type"],
            RunawayHold.subject_id == candidate["subject_id"],
            (RunawayHold.released_at.is_(None) & (RunawayHold.expires_at > now))
            | (RunawayHold.released_at > now - RUNAWAY_WINDOW),
        )
    )
    if existing.first() is not None:
        return None
    hold = RunawayHold(
        workspace_id=candidate["workspace_id"],
        subject_type=candidate["subject_type"],
        subject_id=candidate["subject_id"],
        reason=candidate["reason"],
        details={"calls_in_window": candidate["calls"], "window_s": 120},
        expires_at=now + timedelta(minutes=RUNAWAY_HOLD_MINUTES),
    )
    session.add(hold)
    if candidate["subject_type"] == "run":
        await session.execute(
            update(AgentRun)
            .where(AgentRun.id == uuid.UUID(candidate["subject_id"]), AgentRun.status == "running")
            .values(status="cancelled", ended_at=now)
        )
    return hold


async def _run_runaway_protection() -> dict[str, int]:
    factory = _make_session_factory()
    redis = _make_redis()
    held = 0
    try:
        async with factory() as session:
            now = datetime.now(UTC)
            for candidate in await detect_runaways(session, now):
                hold = await place_hold(session, candidate, now)
                if hold is None:
                    continue
                await session.flush()
                held += 1
                log.warning("runaway_hold_placed", **{k: str(v) for k, v in candidate.items()})
                await queue_notifications(
                    session,
                    candidate["workspace_id"],
                    "runaway.detected",
                    {
                        "event": "runaway.detected",
                        "hold_id": str(hold.id),
                        "workspace_id": str(candidate["workspace_id"]),
                        "subject_type": candidate["subject_type"],
                        "subject_id": candidate["subject_id"],
                        "run_id": candidate["subject_id"]
                        if candidate["subject_type"] == "run"
                        else None,
                        "reason": candidate["reason"],
                        "call_count_last_2min": candidate["calls"],
                        "hold_expires_at": hold.expires_at.isoformat(),
                        "detected_at": now.isoformat(),
                    },
                )
                await invalidate_runaway_holds_cache(redis, candidate["workspace_id"])
                await _email_admins(session, candidate)
            if held:
                await session.commit()
    finally:
        await redis.aclose()
    if held:
        log.info("runaway_protection_held", count=held)
    return {"held": held}


async def _email_admins(session: AsyncSession, candidate: dict[str, Any]) -> None:
    workspace_id = candidate["workspace_id"]
    try:
        prefs = await get_email_preference(session, workspace_id)
        if prefs is not None and not prefs.budget_alerts_enabled:
            return
        ws = await session.get(Workspace, workspace_id)
        admins = await get_workspace_admin_users(session, workspace_id)
        await asyncio.gather(
            *[
                send_budget_breach_email(
                    to_email=u.email,
                    full_name=u.full_name,
                    scope_type="runaway_protection",
                    scope_id=f"{candidate['subject_type']}:{candidate['subject_id']}",
                    period_type="realtime",
                    limit_usd="N/A",
                    spent_usd="N/A",
                    action="held",
                    workspace_name=ws.name if ws else str(workspace_id),
                )
                for u in admins
            ],
            return_exceptions=True,
        )
    except Exception as exc:
        log.warning("runaway_email_failed", error=str(exc))


# ── budget_spend_sync ─────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="budgets.budget_spend_sync",
    max_retries=2,
    default_retry_delay=60,
)
def budget_spend_sync() -> dict[str, int]:
    """Reconcile every active budget's current-period spend from provider_calls."""
    return asyncio.run(_run_budget_spend_sync())


async def _scope_filters(session: AsyncSession, budget: Budget) -> list[Any] | None:
    """SQL filters selecting the provider calls a budget's scope covers (I-08); the
    same resolver as live enforcement and the simulator. None means "can't evaluate":
    the caller keeps the live total instead of overwriting it."""
    return await resolve_scope_filters(
        session, budget.scope_type, budget.scope_id, getattr(budget, "api_key_id", None)
    )


async def _run_budget_spend_sync() -> dict[str, int]:
    factory = _make_session_factory()
    redis = _make_redis()
    synced = 0
    try:
        async with factory() as session:
            budgets = list(
                (await session.execute(select(Budget).where(Budget.is_active.is_(True)))).scalars()
            )
            now = datetime.now(UTC)
            for budget in budgets:
                scope_filter = await _scope_filters(session, budget)
                if scope_filter is None:
                    continue
                start, end = period_window(budget.period_type, now)
                window = (
                    [ProviderCall.created_at >= start, ProviderCall.created_at < end]
                    if start is not None and end is not None
                    else []
                )
                row = (
                    await session.execute(
                        select(
                            func.coalesce(func.sum(ProviderCall.cost_usd), Decimal(0)),
                            func.count(ProviderCall.id),
                        )
                        .select_from(ProviderCall)
                        .outerjoin(AgentRun, AgentRun.id == ProviderCall.run_id)
                        .where(
                            ProviderCall.workspace_id == budget.workspace_id,
                            *scope_filter,
                            *window,
                            *billable_filters(),
                        )
                    )
                ).one()
                await set_budget_spend(
                    session,
                    redis,
                    budget.id,
                    budget.period_type,
                    Decimal(row[0] or 0),
                    int(row[1] or 0),
                    now,
                )
                synced += 1
            await session.commit()
    finally:
        await redis.aclose()
    log.info("budget_spend_sync_done", synced=synced)
    return {"synced": synced}


# ── deliver_notifications (review F-22) ───────────────────────────────────────


@celery_app.task(name="budgets.deliver_notifications")  # type: ignore[untyped-decorator]
def deliver_notifications() -> dict[str, int]:
    """Send due queued budget notification deliveries."""
    return asyncio.run(_run_deliver_notifications())


async def deliver_due(session: AsyncSession, now: datetime, limit: int = 100) -> dict[str, int]:
    """One delivery pass: send each due pending delivery once; retry with backoff,
    give up after DELIVERY_MAX_ATTEMPTS. Rows are locked (SKIP LOCKED) so parallel
    workers never send the same delivery twice."""
    rows = list(
        (
            await session.execute(
                select(BudgetNotificationDelivery, BudgetNotification)
                .join(
                    BudgetNotification,
                    BudgetNotification.id == BudgetNotificationDelivery.notification_id,
                )
                .where(
                    BudgetNotificationDelivery.status == "pending",
                    BudgetNotificationDelivery.next_attempt_at <= now,
                )
                .order_by(BudgetNotificationDelivery.next_attempt_at)
                .limit(limit)
                .with_for_update(skip_locked=True, of=BudgetNotificationDelivery)
            )
        ).all()
    )
    sent = failed = retried = 0
    for delivery, notification in rows:
        try:
            if not notification.is_active:
                raise RuntimeError("destination is disabled")
            result = await send_notification(notification, delivery.payload or {})
        except Exception as exc:
            delivery.error_detail = str(exc)[:1000]
            if delivery.attempt >= DELIVERY_MAX_ATTEMPTS or not notification.is_active:
                delivery.status = "failed"
                delivery.next_attempt_at = None
                failed += 1
            else:
                delivery.next_attempt_at = now + delivery_backoff(delivery.attempt)
                delivery.attempt += 1
                retried += 1
            continue
        delivery.status = "success"
        delivery.response_status = result.get("response_status")
        delivery.delivered_at = result.get("delivered_at") or now
        delivery.error_detail = None
        delivery.next_attempt_at = None
        sent += 1
        if delivery.breach_id is not None:
            await session.execute(
                update(BudgetBreach)
                .where(BudgetBreach.id == delivery.breach_id, BudgetBreach.notified_at.is_(None))
                .values(notified_at=now)
            )
    await session.commit()
    return {"sent": sent, "retried": retried, "failed": failed}


async def _run_deliver_notifications() -> dict[str, int]:
    factory = _make_session_factory()
    async with factory() as session:
        result = await deliver_due(session, datetime.now(UTC))
    if any(result.values()):
        log.info("budget_notifications_delivered", **result)
    return result
