"""W1-D FinOps: pricing edge cases (F-25), scope validation (F-12), override
lifecycle (F-13) and the cost-cap pricing path (F-14)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from runledger_api.routers.budgets import _validate_budget_payload
from runledger_api.services.budgets import model_matches, scope_filters
from runledger_api.services.pricing import price_tokens


def _price(**kw: object) -> SimpleNamespace:
    base = dict(
        input_cost_per_1m=Decimal("2"),
        output_cost_per_1m=Decimal("8"),
        cached_input_cost_per_1m=Decimal("0.5"),
        cache_write_cost_per_1m=None,
    )
    return SimpleNamespace(**{**base, **kw})


def test_cached_subset_of_input_is_discounted() -> None:
    # 1M input of which 400k cached: 600k at $2 + 400k at $0.5
    cost = price_tokens(
        _price(), input_tokens=1_000_000, output_tokens=0, cached_input_tokens=400_000
    )
    assert cost == Decimal("1.40000000")


def test_cached_more_than_input_is_additive_not_negative() -> None:
    # Anthropic-style usage: 100k input + 900k cache reads reported separately.
    cost = price_tokens(
        _price(), input_tokens=100_000, output_tokens=0, cached_input_tokens=900_000
    )
    assert cost == Decimal("0.65000000")  # 100k*$2 + 900k*$0.5
    assert cost > 0


def test_negative_counts_are_clamped() -> None:
    assert price_tokens(_price(), input_tokens=-5, output_tokens=-1) == Decimal("0E-8")


def test_cache_writes_use_write_rate_or_input_rate() -> None:
    kw = dict(input_tokens=0, output_tokens=0, cache_write_tokens=1_000_000)
    assert price_tokens(_price(), **kw) == Decimal("2.00000000")
    assert price_tokens(_price(cache_write_cost_per_1m=Decimal("2.5")), **kw) == Decimal(
        "2.50000000"
    )


def test_missing_cached_rate_defaults_to_half_input() -> None:
    cost = price_tokens(
        _price(cached_input_cost_per_1m=None),
        input_tokens=1_000_000,
        output_tokens=0,
        cached_input_tokens=1_000_000,
    )
    assert cost == Decimal("1.00000000")


@pytest.mark.parametrize(
    ("kwargs", "ok"),
    [
        ({"scope_type": "workspace", "scope_id": None}, True),
        ({"scope_type": "workspace", "scope_id": "x"}, False),
        ({"scope_type": "app", "scope_id": "not-a-uuid"}, False),
        ({"scope_type": "app", "scope_id": str(uuid.uuid4())}, True),
        ({"scope_type": "feature_tag", "scope_id": "  "}, False),
        ({"scope_type": "model", "scope_id": "gpt-4*"}, True),
        ({"scope_type": "model", "scope_id": "gp*t-4"}, False),
        ({"scope_type": "model", "scope_id": "gpt-4o", "api_key_id": str(uuid.uuid4())}, True),
        ({"scope_type": "api_key", "scope_id": str(uuid.uuid4()), "api_key_id": "x"}, False),
    ],
)
def test_budget_scope_validation(kwargs: dict, ok: bool) -> None:
    call = dict(action="block", downgrade_to_model=None, **kwargs)
    if ok:
        _validate_budget_payload(**call)
    else:
        with pytest.raises(HTTPException) as exc:
            _validate_budget_payload(**call)
        assert exc.value.status_code == 422


def test_model_pattern_matching() -> None:
    assert model_matches("gpt-4*", "gpt-4o-mini")
    assert model_matches("gpt-4o", "gpt-4o")
    assert not model_matches("gpt-4o", "gpt-4o-mini")
    assert not model_matches("gpt-4*", None)


def test_scope_filters_reject_malformed_ids() -> None:
    assert scope_filters("app", "nope") is None
    assert scope_filters("workspace", None) == []
    assert scope_filters("model", "gpt-4*", str(uuid.uuid4())) is not None


@pytest.mark.asyncio
async def test_override_worker_activates_and_expires() -> None:
    from runledger_api.workers.budget_overrides import advance_overrides

    ws = uuid.uuid4()

    def _scalars(items: list) -> MagicMock:
        result = MagicMock()
        result.scalars.return_value = items
        return result

    b1, b2 = uuid.uuid4(), uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_scalars([b1]), _scalars([b2]), _scalars([ws])])
    activated, expired, workspaces = await advance_overrides(session, datetime.now(UTC))
    assert (activated, expired, workspaces) == (1, 1, {ws})


@pytest.mark.asyncio
async def test_cost_cap_prices_with_workspace_aware_calculate_cost() -> None:
    """F-14: caps go through calculate_cost (workspace override first)."""
    from runledger_api.services import gateway_controls

    route = SimpleNamespace(
        id=uuid.uuid4(),
        provider="openai",
        target_model="gpt-4o",
        daily_cost_limit_usd=Decimal("1"),
        monthly_cost_limit_usd=None,
    )
    ws = uuid.uuid4()
    row = MagicMock()
    row.one.return_value = SimpleNamespace(total_input=10, total_output=0, oldest=None)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=row)
    with (
        patch.object(
            gateway_controls,
            "_lookup_model_rates",
            AsyncMock(return_value=(Decimal(1), Decimal(1))),
        ),
        patch(
            "runledger_api.services.pricing.calculate_cost", AsyncMock(return_value=Decimal("2"))
        ) as calc,
        pytest.raises(HTTPException) as exc,
    ):
        await gateway_controls.check_cost_cap(db, route, ws)
    assert exc.value.status_code == 429
    assert calc.await_args.kwargs["workspace_id"] == ws
