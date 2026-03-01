"""
Budget service layer — Redis helpers, hot-path check, notification dispatch.

All functions are pure async with no FastAPI dependencies so they can be
imported directly from Celery workers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.budgets import Budget, BudgetBreach, BudgetNotification
from runledger_api.schemas.budgets import BudgetCheckResponse

log = structlog.get_logger()

_BUDGET_CACHE_TTL = 300  # seconds


# ── Period key helpers ────────────────────────────────────────────────────────


def _period_key(period_type: str, dt: datetime) -> str:
    """Return the Redis period string for a given datetime."""
    if period_type == "daily":
        return dt.strftime("%Y-%m-%d")
    if period_type == "monthly":
        return dt.strftime("%Y-%m")
    return "total"


def _spend_key(budget_id: uuid.UUID, period_key: str) -> str:
    return f"rl:budget:{budget_id}:spend:{period_key}"


def _workspace_budgets_cache_key(workspace_id: uuid.UUID) -> str:
    return f"rl:workspace:{workspace_id}:budgets"


# ── Redis spend counter ───────────────────────────────────────────────────────


async def incr_budget_spend(
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
    cost_usd: Decimal,
) -> None:
    """INCRBYFLOAT on the spend key for the current period."""
    pk = _period_key(period_type, datetime.now(UTC))
    key = _spend_key(budget_id, pk)
    await redis.incrbyfloat(key, float(cost_usd))
    # For daily / monthly keys, set expiry so stale counters are cleaned up.
    if period_type == "daily":
        await redis.expire(key, 86400 * 2)  # 2 days
    elif period_type == "monthly":
        await redis.expire(key, 86400 * 35)  # ~5 weeks


async def get_budget_spend(
    redis: Redis,
    budget_id: uuid.UUID,
    period_type: str,
) -> Decimal:
    """GET spend counter from Redis. Returns 0 if key missing."""
    pk = _period_key(period_type, datetime.now(UTC))
    key = _spend_key(budget_id, pk)
    value = await redis.get(key)
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


# ── Workspace budgets cache ───────────────────────────────────────────────────


async def get_workspace_budgets_cached(
    redis: Redis,
    db: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """
    Return active budget defs from Redis cache (TTL 300 s).
    On miss: query Postgres, serialise, and cache the result.
    """
    cache_key = _workspace_budgets_cache_key(workspace_id)
    cached = await redis.get(cache_key)
    if cached is not None:
        return json.loads(cached)  # type: ignore[no-any-return]

    result = await db.execute(
        select(Budget).where(
            Budget.workspace_id == workspace_id,
            Budget.is_active.is_(True),
        )
    )
    budgets: list[Budget] = list(result.scalars())

    serialised = [
        {
            "id": str(b.id),
            "scope_type": b.scope_type,
            "scope_id": b.scope_id,
            "period_type": b.period_type,
            "limit_usd": str(b.limit_usd),
            "action": b.action,
            "downgrade_to_model": b.downgrade_to_model,
        }
        for b in budgets
    ]
    await redis.set(cache_key, json.dumps(serialised), ex=_BUDGET_CACHE_TTL)
    return serialised


async def invalidate_workspace_budgets_cache(
    redis: Redis,
    workspace_id: uuid.UUID,
) -> None:
    """Delete the workspace budget cache key (called on create/delete)."""
    cache_key = _workspace_budgets_cache_key(workspace_id)
    await redis.delete(cache_key)


# ── Scope matching ────────────────────────────────────────────────────────────


def _matching_budgets(
    budgets: list[dict[str, Any]],
    end_user_id: str | None,
    feature_tag: str | None,
) -> list[dict[str, Any]]:
    """
    Filter budget list to those that match this specific call.

    - workspace scope: always matches
    - end_user scope: matches when scope_id == end_user_id
    - feature_tag scope: matches when scope_id == feature_tag
    - app scope: reserved, never matches for now
    """
    matched = []
    for b in budgets:
        scope_type = b["scope_type"]
        if (
            scope_type == "workspace"
            or scope_type == "end_user"
            and end_user_id
            and b["scope_id"] == end_user_id
            or scope_type == "feature_tag"
            and feature_tag
            and b["scope_id"] == feature_tag
        ):
            matched.append(b)
    return matched


# ── Hot-path check ────────────────────────────────────────────────────────────


async def check_budgets(
    redis: Redis,
    db: AsyncSession,
    workspace_id: uuid.UUID,
    end_user_id: str | None,
    feature_tag: str | None,
) -> BudgetCheckResponse:
    """
    Hot-path budget check: reads cache + Redis counters only.

    Returns BudgetCheckResponse with allowed=False when a blocking or
    downgrade budget is exceeded.  Notify-only budgets do not block.
    """
    budgets = await get_workspace_budgets_cached(redis, db, workspace_id)
    matched = _matching_budgets(budgets, end_user_id, feature_tag)

    for b in matched:
        budget_id = uuid.UUID(b["id"])
        spend = await get_budget_spend(redis, budget_id, b["period_type"])
        limit = Decimal(b["limit_usd"])

        if spend >= limit:
            action = b["action"]
            if action == "block":
                return BudgetCheckResponse(
                    allowed=False,
                    action="block",
                    budget_id=b["id"],
                )
            if action == "downgrade":
                return BudgetCheckResponse(
                    allowed=False,
                    action="downgrade",
                    budget_id=b["id"],
                    downgrade_model=b.get("downgrade_to_model"),
                )
            # action == "notify" — log but don't block
            log.info(
                "budget_notify_threshold_exceeded",
                budget_id=b["id"],
                spend=str(spend),
                limit=str(limit),
            )

    return BudgetCheckResponse(allowed=True)


# ── Breach recording + notification dispatch ──────────────────────────────────


async def fire_breach(
    db: AsyncSession,
    redis: Redis,
    budget_dict: dict[str, Any],
    spend: Decimal,
    action_taken: str,
) -> None:
    """
    Record a breach in Postgres and send notifications.

    budget_dict is the serialised dict from the Redis cache (not the ORM obj).
    """
    budget_id = uuid.UUID(budget_dict["id"])

    breach = BudgetBreach(
        budget_id=budget_id,
        spend_at_breach_usd=spend,
        action_taken=action_taken,
    )
    db.add(breach)
    await db.flush()  # get breach.id + occurred_at

    # Fetch active notifications for this workspace
    workspace_id_str = budget_dict.get("workspace_id")
    if workspace_id_str:
        workspace_id = uuid.UUID(workspace_id_str)
        result = await db.execute(
            select(BudgetNotification).where(
                BudgetNotification.workspace_id == workspace_id,
                BudgetNotification.is_active.is_(True),
                BudgetNotification.events.any("budget.breach"),
            )
        )
        notifications: list[BudgetNotification] = list(result.scalars())

        payload = {
            "event": "budget.breach",
            "budget_id": str(budget_id),
            "scope_type": budget_dict.get("scope_type"),
            "scope_id": budget_dict.get("scope_id"),
            "period_type": budget_dict.get("period_type"),
            "limit_usd": budget_dict.get("limit_usd"),
            "spend_usd": str(spend),
            "action_taken": action_taken,
            "occurred_at": datetime.now(UTC).isoformat(),
        }

        for notification in notifications:
            try:
                await send_notification(notification, payload)
                # Mark notified_at on the breach
                await db.execute(
                    update(BudgetBreach)
                    .where(BudgetBreach.id == breach.id)
                    .values(notified_at=datetime.now(UTC))
                )
            except Exception as exc:
                log.warning(
                    "budget_notification_failed",
                    notification_id=str(notification.id),
                    error=str(exc),
                )

    await db.commit()
    log.info(
        "budget_breach_recorded",
        budget_id=str(budget_id),
        spend=str(spend),
        action_taken=action_taken,
    )


async def send_notification(
    notification: BudgetNotification,
    payload: dict[str, Any],
) -> None:
    """
    Dispatch a notification via Slack Block Kit or HMAC-signed generic webhook.

    For Slack channels: POST Block Kit JSON to the destination_url (no HMAC).
    For all other channels: HMAC-SHA256 signed JSON POST.
    """
    if notification.channel == "slack":
        from runledger_api.services.notifications import (
            build_budget_breach_blocks,
            send_slack_message,
        )

        blocks = build_budget_breach_blocks(
            budget_id=payload.get("budget_id", ""),
            scope_type=payload.get("scope_type"),
            scope_id=payload.get("scope_id"),
            spend_usd=payload.get("spend_usd", "0"),
            limit_usd=payload.get("limit_usd", "0"),
            action=payload.get("action_taken"),
        )
        fallback = (
            f"Budget breach: ${payload.get('spend_usd', '0')} "
            f"/ ${payload.get('limit_usd', '0')} limit"
        )
        await send_slack_message(notification.destination_url, blocks, fallback)
        return

    body = json.dumps(payload, sort_keys=True).encode()
    sig = hmac.new(
        settings.secret_key.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            notification.destination_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-RunLedger-Signature": f"sha256={sig}",
                "X-RunLedger-Event": payload.get("event", "budget.breach"),
            },
        )
