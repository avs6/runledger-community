"""Built-in intelligent routing classifier (review G-04)."""

from __future__ import annotations

import pytest
from runledger_api.services import intelligent_router as ir

TIERS = {"cheap": "small-alias", "mid": "mid-alias", "frontier": "big-alias"}


@pytest.mark.asyncio
async def test_simple_low_risk_goes_cheap() -> None:
    d = await ir.classify(
        [{"role": "user", "content": "summarize this meeting"}],
        {"classifier_mode": "heuristic", "tiers": TIERS},
    )
    assert d and d["complexity"] == "simple" and d["risk"] == "low"
    assert d["tier"] == "cheap" and d["alias"] == "small-alias" and d["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_short_but_risky_goes_up_a_tier() -> None:
    d = await ir.classify(
        [{"role": "user", "content": "does this contract create regulatory exposure?"}],
        {"classifier_mode": "heuristic", "tiers": TIERS},
    )
    assert d and d["risk"] == "high" and d["alias"] == "mid-alias"


@pytest.mark.asyncio
async def test_long_multi_step_is_complex() -> None:
    text = "Design and analyze the trade-offs of this architecture. " + ("detail " * 2500)
    d = await ir.classify(
        [{"role": "user", "content": text}], {"classifier_mode": "heuristic", "tiers": TIERS}
    )
    assert (
        d
        and d["complexity"] == "complex"
        and d["alias"] == "big-alias"
        and d["reasoning_effort"] == "high"
    )


@pytest.mark.asyncio
async def test_missing_tier_keeps_alias_and_custom_matrix() -> None:
    d = await ir.classify([{"role": "user", "content": "hi"}], {"classifier_mode": "heuristic"})
    assert d and d["alias"] is None
    d = await ir.classify(
        [{"role": "user", "content": "hi"}],
        {
            "classifier_mode": "heuristic",
            "tiers": {"x": "x-alias"},
            "matrix": {"simple": {"low": "x"}},
        },
    )
    assert d and d["alias"] == "x-alias"


@pytest.mark.asyncio
async def test_llm_mode_falls_back_without_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    d = await ir.classify(
        [{"role": "user", "content": "hi"}], {"classifier_mode": "llm", "tiers": TIERS}
    )
    assert d and d["tier"] == "cheap" and "llm unavailable" in d["reason"]


def test_always_enabled() -> None:
    assert ir.enabled()
