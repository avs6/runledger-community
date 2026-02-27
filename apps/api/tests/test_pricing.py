"""
Tests for the pricing service.

All DB interactions are mocked — no live database required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from runledger_api.services.pricing import calculate_cost

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_pricing_row(
    *,
    input_cost: str = "2.50",
    output_cost: str = "10.00",
    cached_cost: str | None = "1.25",
    provider: str = "openai",
    model: str = "gpt-4o",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        provider=provider,
        model=model,
        input_cost_per_1m=Decimal(input_cost),
        output_cost_per_1m=Decimal(output_cost),
        cached_input_cost_per_1m=Decimal(cached_cost) if cached_cost else None,
        effective_from=datetime(2025, 1, 1, tzinfo=UTC),
        effective_to=None,
        workspace_id=None,
    )


def _mock_session(pricing_row: SimpleNamespace | None) -> AsyncMock:
    """Return a mock AsyncSession that yields pricing_row from scalar_one_or_none."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=pricing_row)
    session.execute = AsyncMock(return_value=result_mock)
    return session


# ── calculate_cost ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_cost_basic() -> None:
    """Standard gpt-4o call without caching."""
    pricing = _make_pricing_row()
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
    )

    # input:  1000 / 1_000_000 * 2.50 = 0.0025
    # output:  500 / 1_000_000 * 10.0 = 0.005
    # total = 0.0075
    assert cost == Decimal("0.00750000")


@pytest.mark.asyncio
async def test_calculate_cost_with_cached_tokens() -> None:
    """Call with cached input tokens — uses cached_input_cost_per_1m rate."""
    pricing = _make_pricing_row()  # cached rate = 1.25 / 1M
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        cached_input_tokens=600,  # 600 cached, 400 non-cached
    )

    # non-cached input: 400 / 1M * 2.50  = 0.001
    # cached input:     600 / 1M * 1.25  = 0.00075
    # output:           500 / 1M * 10.0  = 0.005
    # total = 0.00675
    assert cost == Decimal("0.00675000")


@pytest.mark.asyncio
async def test_calculate_cost_default_cached_rate_is_half_input() -> None:
    """When cached_input_cost_per_1m is NULL, default to 50% of input rate."""
    pricing = _make_pricing_row(cached_cost=None)  # no explicit cached rate
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=0,
        cached_input_tokens=1000,
    )

    # All tokens are cached. Default rate = 2.50 * 0.5 = 1.25 / 1M
    # cached cost = 1000 / 1_000_000 * 1.25 = 0.00125
    assert cost == Decimal("0.00125000")


@pytest.mark.asyncio
async def test_calculate_cost_no_pricing_returns_none() -> None:
    """If no pricing row exists, returns None."""
    session = _mock_session(None)

    cost = await calculate_cost(
        session,
        provider="unknown",
        model="unknown-model",
        input_tokens=1000,
        output_tokens=500,
    )

    assert cost is None


@pytest.mark.asyncio
async def test_calculate_cost_both_tokens_none_returns_none() -> None:
    """Short-circuits immediately when both token counts are None."""
    session = AsyncMock()  # should never be called

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=None,
        output_tokens=None,
    )

    assert cost is None
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_calculate_cost_only_output_tokens() -> None:
    """input_tokens=None defaults to 0, only output is billed."""
    pricing = _make_pricing_row()
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=None,
        output_tokens=1000,
    )

    # output: 1000 / 1_000_000 * 10.0 = 0.01
    assert cost == Decimal("0.01000000")


@pytest.mark.asyncio
async def test_calculate_cost_zero_tokens() -> None:
    """Zero tokens produces zero cost (not None)."""
    pricing = _make_pricing_row()
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=0,
        output_tokens=0,
    )

    assert cost == Decimal("0.00000000")


@pytest.mark.asyncio
async def test_calculate_cost_workspace_override_checked_first() -> None:
    """Workspace-specific pricing is preferred over global pricing."""
    ws_id = uuid.uuid4()

    # First call (workspace) returns a row; second call (global) should NOT run
    ws_pricing = _make_pricing_row(input_cost="1.00", output_cost="4.00")
    session = AsyncMock()

    # session.execute() is called twice: once for workspace lookup, once for global
    # We make the first call return the ws_pricing row
    result_with_row = MagicMock()
    result_with_row.scalar_one_or_none = MagicMock(return_value=ws_pricing)
    session.execute = AsyncMock(return_value=result_with_row)

    cost = await calculate_cost(
        session,
        provider="openai",
        model="gpt-4o",
        input_tokens=1_000_000,
        output_tokens=0,
        workspace_id=ws_id,
    )

    # 1M input * (1.00 / 1M) = 1.00
    assert cost == Decimal("1.00000000")
    # Only called once — workspace row found, global not needed
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_calculate_cost_anthropic_large_values() -> None:
    """Spot-check Anthropic pricing."""
    pricing = _make_pricing_row(
        provider="anthropic",
        model="claude-opus-4-6",
        input_cost="15.00",
        output_cost="75.00",
        cached_cost=None,
    )
    session = _mock_session(pricing)

    cost = await calculate_cost(
        session,
        provider="anthropic",
        model="claude-opus-4-6",
        input_tokens=10_000,
        output_tokens=2_000,
    )

    # input:  10_000 / 1_000_000 * 15.0 = 0.15
    # output:  2_000 / 1_000_000 * 75.0 = 0.15
    # total = 0.30
    assert cost == Decimal("0.30000000")
