"""
Pricing contracts service — per-workspace negotiated rate resolution.

get_effective_contract(db, workspace_id, provider, model, at)
  → Returns the active PricingContract for this workspace+provider+model at `at`,
    or None if none applies (most-specific match wins: model > all-models).

apply_contract_rate(contract, input_per_1m, output_per_1m)
  → Returns (effective_input, effective_output) after applying discount/override.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import PricingContract

log = structlog.get_logger()


async def get_effective_contract(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    provider: str,
    model: str,
    at: datetime | None = None,
) -> PricingContract | None:
    """
    Return the most-specific active contract for (workspace, provider, model) at `at`.

    Priority: model-specific > provider-wide (model IS NULL).
    """
    now = at or datetime.now(UTC)
    result = await db.execute(
        select(PricingContract)
        .where(
            PricingContract.workspace_id == workspace_id,
            PricingContract.provider == provider,
            PricingContract.is_active.is_(True),
            PricingContract.effective_from <= now,
            (PricingContract.effective_until.is_(None)) | (PricingContract.effective_until >= now),
        )
        .order_by(
            # model-specific rows sort before NULL (provider-wide)
            PricingContract.model.nulls_last(),
            PricingContract.effective_from.desc(),
        )
    )
    contracts = list(result.scalars().all())
    # Prefer exact model match
    for c in contracts:
        if c.model == model:
            return c
    # Fall back to provider-wide
    for c in contracts:
        if c.model is None:
            return c
    return None


def apply_contract_rate(
    contract: PricingContract,
    base_input_per_1m: Decimal,
    base_output_per_1m: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Apply contract discount or fixed override to base rates.

    Returns (effective_input_per_1m, effective_output_per_1m).
    Fixed rates take precedence over discount_pct.
    """
    if contract.fixed_input_per_1m is not None and contract.fixed_output_per_1m is not None:
        return contract.fixed_input_per_1m, contract.fixed_output_per_1m

    if contract.discount_pct is not None and contract.discount_pct > 0:
        factor = Decimal(1) - (contract.discount_pct / Decimal(100))
        return (base_input_per_1m * factor).quantize(Decimal("0.00000001")), \
               (base_output_per_1m * factor).quantize(Decimal("0.00000001"))

    return base_input_per_1m, base_output_per_1m
