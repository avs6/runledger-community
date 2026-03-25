"""
Pricing credits service — prepaid tokens, credit bundles, minimum commitments.

apply_credits(db, workspace_id, cost_usd)
  → Deducts cost_usd from active credits in priority order (lowest first).
  → Returns {"applied": Decimal, "remaining_cost": Decimal, "credits_used": [...]}
  → Modifies credits in-place (decrements remaining_usd).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import PricingCredit

log = structlog.get_logger()

_VALID_CREDIT_TYPES = {"prepaid_tokens", "credit_bundle", "minimum_commitment"}
_VALID_SOURCES = {"manual", "stripe", "negotiated"}


async def get_active_credits(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    at: datetime | None = None,
) -> list[PricingCredit]:
    """Return active, unexpired credits for workspace ordered by priority (lowest first)."""
    now = at or datetime.now(UTC)
    result = await db.execute(
        select(PricingCredit)
        .where(
            PricingCredit.workspace_id == workspace_id,
            PricingCredit.is_active.is_(True),
            PricingCredit.remaining_usd > 0,
            PricingCredit.effective_from <= now,
            (PricingCredit.effective_until.is_(None)) | (PricingCredit.effective_until >= now),
        )
        .order_by(PricingCredit.priority, PricingCredit.effective_from)
    )
    return list(result.scalars().all())


async def apply_credits(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    cost_usd: Decimal,
) -> dict:
    """
    Deduct cost_usd from active credits, lowest-priority first.

    Returns:
      applied: total amount deducted from credits
      remaining_cost: cost_usd - applied (what still needs to be charged)
      credits_used: [{credit_id, name, deducted_usd}]
    """
    credits = await get_active_credits(db, workspace_id)
    remaining = cost_usd
    applied = Decimal(0)
    used: list[dict] = []

    for credit in credits:
        if remaining <= 0:
            break
        deduct = min(credit.remaining_usd, remaining)
        credit.remaining_usd = credit.remaining_usd - deduct
        if credit.remaining_usd == 0:
            credit.is_active = False
        remaining -= deduct
        applied += deduct
        used.append(
            {
                "credit_id": str(credit.id),
                "name": credit.name,
                "deducted_usd": str(deduct),
            }
        )

    if applied > 0:
        await db.commit()

    log.info(
        "credits_applied",
        workspace_id=str(workspace_id),
        cost_usd=str(cost_usd),
        applied=str(applied),
        remaining=str(remaining),
    )
    return {
        "applied": applied,
        "remaining_cost": remaining,
        "credits_used": used,
    }
