"""
Pricing engine for RunLedger.

``calculate_cost()`` looks up the effective price for a provider/model at a
given point in time, applies the cached-input discount, and returns the total
cost in USD as a ``Decimal``.

Lookup priority:
  1. Workspace-specific override (workspace_id matches) effective at the call time
  2. Global row (workspace_id IS NULL) effective at the call time
  3. If the model had no price yet at that time: its first published price
     (workspace, then global), so newly added pricing covers earlier calls
  4. None → returns None (no pricing data available)

Cached input discount:
  If ``cached_input_cost_per_1m`` is set on the pricing row, it is used
  directly.  If NULL, the discount defaults to 50 % of ``input_cost_per_1m``
  (matching OpenAI Prompt Caching behaviour).

Cached-token edge cases (review F-25):
  - OpenAI-style usage reports cached tokens as a subset of input tokens; Anthropic
    reports cache reads separately from input. When ``cached_input_tokens`` exceeds
    ``input_tokens`` the cached tokens are treated as additional (never as a negative
    billable input), and negative counts are clamped to 0.
  - Cache writes (``cache_write_tokens``, e.g. Anthropic cache creation) are charged
    at ``cache_write_cost_per_1m`` when set, otherwise at the input rate.
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
    cache_write_tokens: int | None = None,
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
    cache_write_tokens:
        Tokens written to the prompt cache, billed at the cache-write rate.
    """
    if input_tokens is None and output_tokens is None:
        return None

    effective_at = at_time or datetime.now(UTC)
    pricing = await _get_pricing(session, provider, model, effective_at, workspace_id)
    if pricing is None:
        log.debug("no_pricing_row", provider=provider, model=model)
        return None

    return price_tokens(
        pricing,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
    )


def price_tokens(
    pricing: ProviderPricing,
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None = None,
    cache_write_tokens: int | None = None,
) -> Decimal:
    """Cost of token counts under one pricing row (see the module docstring)."""
    in_tok = Decimal(max(input_tokens or 0, 0))
    out_tok = Decimal(max(output_tokens or 0, 0))
    cached_tok = Decimal(max(cached_input_tokens or 0, 0))
    write_tok = Decimal(max(cache_write_tokens or 0, 0))

    # Cached tokens are normally a subset of input; if they exceed it the provider
    # reported them separately, so all input tokens are billable.
    billable_input = in_tok - cached_tok if cached_tok <= in_tok else in_tok

    input_cost = (billable_input * pricing.input_cost_per_1m) / _MILLION
    cached_rate_set = getattr(pricing, "cached_input_cost_per_1m", None)
    if cached_rate_set is not None:
        cached_rate = cached_rate_set
    else:
        cached_rate = pricing.input_cost_per_1m * _HALF
    cached_cost = (cached_tok * cached_rate) / _MILLION
    write_rate = getattr(pricing, "cache_write_cost_per_1m", None)
    if write_rate is None:
        write_rate = pricing.input_cost_per_1m
    write_cost = (write_tok * write_rate) / _MILLION
    output_cost = (out_tok * pricing.output_cost_per_1m) / _MILLION

    return (input_cost + cached_cost + write_cost + output_cost).quantize(
        _QUANTIZE, rounding=ROUND_HALF_UP
    )


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
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    # No price was in effect when the call was made: the model had no pricing yet.
    # Use the first price published for it (workspace override first), so adding
    # pricing for a model also prices the calls recorded before it existed. Calls
    # that had a price at the time keep that historical price.
    first_conditions = [
        ProviderPricing.provider == provider,
        ProviderPricing.model == model,
        ProviderPricing.effective_from > effective_at,
    ]
    scopes = [ProviderPricing.workspace_id.is_(None)]
    if workspace_id is not None:
        scopes.insert(0, ProviderPricing.workspace_id == workspace_id)
    for scope in scopes:
        first = await session.execute(
            select(ProviderPricing)
            .where(and_(*first_conditions, scope))
            .order_by(ProviderPricing.effective_from.asc())
            .limit(1)
        )
        row = first.scalar_one_or_none()
        if row is not None:
            return row
    return None
