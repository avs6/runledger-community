"""
Pricing engine for RunLedger.

``calculate_cost()`` looks up the effective price for a provider/model at a
given point in time, applies the cached-input discount, and returns the total
cost in USD as a ``Decimal``.

Lookup priority:
  1. Workspace-specific override (workspace_id matches)
  2. Global row (workspace_id IS NULL)
  3. None → returns None (no pricing data available)

Cached input discount:
  If ``cached_input_cost_per_1m`` is set on the pricing row, it is used
  directly.  If NULL, the discount defaults to 50 % of ``input_cost_per_1m``
  (matching OpenAI Prompt Caching behaviour).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.metering import ProviderPricing

if TYPE_CHECKING:
    pass

log = structlog.get_logger()

_MILLION = Decimal("1_000_000")
_HALF = Decimal("0.5")
_QUANTIZE = Decimal("0.00000001")  # 8 decimal places


async def calculate_cost(
    session: AsyncSession,
    *,
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None = None,
    at_time: datetime | None = None,
    workspace_id: uuid.UUID | None = None,
) -> Decimal | None:
    """
    Return the USD cost for a provider call, or ``None`` if no pricing row
    exists for the provider/model combination.

    Parameters
    ----------
    session:
        Active async SQLAlchemy session.
    provider:
        Normalised provider name (``"openai"``, ``"anthropic"``, ``"google"``).
    model:
        Model identifier as received in the provider_call event.
    input_tokens:
        Prompt tokens (not counting cached tokens separately).
    output_tokens:
        Completion tokens.
    cached_input_tokens:
        Tokens served from prompt cache (subset of input_tokens).
    at_time:
        The timestamp of the call — used to select the effective price row.
        Defaults to now (UTC).
    workspace_id:
        If provided, a workspace-specific override row is checked first.
    """
    if input_tokens is None and output_tokens is None:
        return None

    effective_at = at_time or datetime.now(UTC)
    pricing = await _get_pricing(session, provider, model, effective_at, workspace_id)
    if pricing is None:
        log.debug("no_pricing_row", provider=provider, model=model)
        return None

    in_tok = Decimal(input_tokens or 0)
    out_tok = Decimal(output_tokens or 0)
    cached_tok = Decimal(cached_input_tokens or 0)

    # Billable (non-cached) input tokens
    billable_input = in_tok - cached_tok

    # Cost for non-cached input
    input_cost = (billable_input * pricing.input_cost_per_1m) / _MILLION

    # Cost for cached input
    if pricing.cached_input_cost_per_1m is not None:
        cached_rate = pricing.cached_input_cost_per_1m
    else:
        cached_rate = pricing.input_cost_per_1m * _HALF
    cached_cost = (cached_tok * cached_rate) / _MILLION

    # Output cost
    output_cost = (out_tok * pricing.output_cost_per_1m) / _MILLION

    total = (input_cost + cached_cost + output_cost).quantize(
        _QUANTIZE, rounding=ROUND_HALF_UP
    )
    return total


async def _get_pricing(
    session: AsyncSession,
    provider: str,
    model: str,
    effective_at: datetime,
    workspace_id: uuid.UUID | None,
) -> ProviderPricing | None:
    """
    Fetch the best-matching ProviderPricing row.

    Workspace-specific rows take precedence over global rows.
    Within the same scope, the most-recently-effective row wins.
    """
    conditions = [
        ProviderPricing.provider == provider,
        ProviderPricing.model == model,
        ProviderPricing.effective_from <= effective_at,
        or_(
            ProviderPricing.effective_to.is_(None),
            ProviderPricing.effective_to > effective_at,
        ),
    ]

    # Try workspace-specific override first
    if workspace_id is not None:
        ws_stmt = (
            select(ProviderPricing)
            .where(and_(*conditions, ProviderPricing.workspace_id == workspace_id))
            .order_by(ProviderPricing.effective_from.desc())
            .limit(1)
        )
        result = await session.execute(ws_stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            return row

    # Fall back to global pricing
    global_stmt = (
        select(ProviderPricing)
        .where(and_(*conditions, ProviderPricing.workspace_id.is_(None)))
        .order_by(ProviderPricing.effective_from.desc())
        .limit(1)
    )
    result = await session.execute(global_stmt)
    return result.scalar_one_or_none()
