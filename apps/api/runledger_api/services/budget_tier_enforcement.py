"""Per-key budget tier limits in the gateway preflight (review G-02).

A key's tier is the tier assigned to it, or the workspace's active default tier when it
has none. Three limits are enforced here, before any route is chosen:

* ``allowed_models``: the requested alias must be in the list (403 ``model_not_allowed``).
* ``rpm_limit``: requests per key over a sliding 60-second window (429 ``tier_rpm``).
* ``tpm_limit``: estimated tokens per key over the same window (429 ``tier_tpm``). The
  estimate is prompt characters / 4 plus the request's ``max_tokens`` (or 256), taken at
  preflight because the real output size isn't known until the call returns.

``max_spend_usd`` is the FinOps spend cap and is enforced by ``gateway_controls``.

Redis errors fail open with a warning, the same rule as the per-route RPM limit.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.budget_tiers import BudgetTier

log = structlog.get_logger()

_WINDOW_MS = 60_000
DEFAULT_OUTPUT_ESTIMATE = 256

# Sliding window over a sorted set whose members carry a weight ("<ts>:<n>:<nonce>").
# Returns {allowed, used, retry_after_ms}. A refused request takes no capacity.
_WEIGHTED_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local weight = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local used = 0
local members = redis.call('ZRANGE', key, 0, -1, 'WITHSCORES')
for i = 1, #members, 2 do
  local n = tonumber(string.match(members[i], '^[^:]+:([^:]+):'))
  used = used + (n or 1)
end
if used + weight > limit then
  local retry = window
  if members[2] then retry = tonumber(members[2]) + window - now end
  return {0, used, retry}
end
redis.call('ZADD', key, now, ARGV[5])
redis.call('PEXPIRE', key, window)
return {1, used + weight, 0}
"""


async def resolve_key_tier(
    db: AsyncSession, workspace_id: uuid.UUID, budget_tier_id: uuid.UUID | None
) -> BudgetTier | None:
    """The key's active tier, else the workspace's active default tier, else None."""
    if budget_tier_id is not None:
        tier = (
            await db.execute(
                select(BudgetTier).where(
                    BudgetTier.id == budget_tier_id,
                    BudgetTier.workspace_id == workspace_id,
                    BudgetTier.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if tier is not None:
            return tier
    return (
        await db.execute(
            select(BudgetTier)
            .where(
                BudgetTier.workspace_id == workspace_id,
                BudgetTier.is_active.is_(True),
                BudgetTier.is_default.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


def estimate_tokens(messages: list[dict[str, Any]], max_tokens: int | None) -> int:
    chars = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            chars += len(content)
        elif isinstance(content, list):
            chars += sum(
                len(str(part.get("text", ""))) for part in content if isinstance(part, dict)
            )
    return max(1, chars // 4) + (max_tokens if max_tokens else DEFAULT_OUTPUT_ESTIMATE)


async def _take(redis: Any, key: str, limit: int, weight: int) -> tuple[bool, int]:
    now_ms = int(time.time() * 1000)
    try:
        allowed, _used, retry_ms = await redis.eval(
            _WEIGHTED_WINDOW,
            1,
            key,
            now_ms,
            _WINDOW_MS,
            limit,
            weight,
            f"{now_ms}:{weight}:{uuid.uuid4().hex[:8]}",
        )
    except Exception:  # noqa: BLE001
        log.warning("budget_tier_redis_error", key=key)
        return True, 0
    return int(allowed) == 1, int(retry_ms)


def _too_many(reason: str, detail: str, retry_ms: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={
            "Retry-After": str(max(1, -(-retry_ms // 1000))),
            "X-RunLedger-Limit-Reason": reason,
        },
    )


async def enforce_key_tier(
    db: AsyncSession,
    redis: Any,
    *,
    workspace_id: uuid.UUID,
    api_key: Any,
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int | None = None,
) -> BudgetTier | None:
    """Apply the caller's tier limits; raise 403/429 on a breach. Returns the tier used."""
    if api_key is None:
        return None
    tier = await resolve_key_tier(db, workspace_id, getattr(api_key, "budget_tier_id", None))
    if tier is None:
        return None
    if tier.allowed_models and model not in tier.allowed_models:
        log.warning("budget_tier_model_refused", tier_id=str(tier.id), model=model)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Model '{model}' is not allowed by budget tier '{tier.name}'",
            headers={"X-RunLedger-Limit-Reason": "model_not_allowed"},
        )
    if tier.rpm_limit:
        ok, retry = await _take(redis, f"rl:tier:rpm:{api_key.id}", tier.rpm_limit, 1)
        if not ok:
            raise _too_many(
                "tier_rpm", f"Budget tier '{tier.name}' allows {tier.rpm_limit} requests/min", retry
            )
    if tier.tpm_limit:
        tokens = estimate_tokens(messages, max_tokens)
        ok, retry = await _take(redis, f"rl:tier:tpm:{api_key.id}", tier.tpm_limit, tokens)
        if not ok:
            raise _too_many(
                "tier_tpm", f"Budget tier '{tier.name}' allows {tier.tpm_limit} tokens/min", retry
            )
    return tier
