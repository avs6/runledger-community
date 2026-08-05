"""
Scenario: Advanced budget & rate limit engine demo.

Demonstrates budget tiers, model-specific budgets, temporary overrides,
throttle/fallback enforcement modes, and billing summary through the
advanced budget engine API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scenarios._base import Sim, say

NAME = "ollama-advanced-budgets"
DESCRIPTION = "Advanced budgets — tiers, model budgets, overrides, throttle/fallback, billing."


def run(sim: Sim) -> None:
    ws = sim.workspace("BudgetLabs", "Advanced Budgets")

    # ── 1. Ingest runs to build spend history ─────────────────────────
    runs = ws.ingest_runs(
        150,
        models=["qwen2.5-coder:14b", "deepseek-r1:14b", "llama3.2"],
        features=["coding", "chat", "reasoning"],
        users=["u_alice", "u_bob", "u_carol"],
        days=30,
        success_rate=0.93,
        sessions=15,
    )

    # ── 2. Create workspace budgets with new enforcement modes ────────
    ws.add_budget("workspace", 100, period_type="monthly", action="throttle")
    ws.add_budget("feature_tag", 30, period_type="monthly", action="fallback", scope_id="coding")
    ws.add_budget("feature_tag", 20, period_type="daily", action="notify", scope_id="reasoning")

    # ── 3. Create budget tiers ────────────────────────────────────────
    free_tier = ws.create_budget_tier(
        "Free",
        max_spend_usd=5,
        rpm_limit=10,
        tpm_limit=10000,
        allowed_models=["llama3.2"],
    )
    starter_tier = ws.create_budget_tier(
        "Starter",
        max_spend_usd=25,
        rpm_limit=30,
        tpm_limit=50000,
        allowed_models=["llama3.2", "qwen2.5-coder:14b"],
    )
    ws.create_budget_tier(
        "Pro",
        max_spend_usd=100,
        rpm_limit=120,
        tpm_limit=500000,
    )
    ws.create_budget_tier(
        "Enterprise",
        max_spend_usd=500,
        rpm_limit=600,
        tpm_limit=2000000,
        is_default=True,
    )
    say("    · 4 budget tiers created (Free/Starter/Pro/Enterprise)", "d")

    # ── 4. Outcomes and scores ────────────────────────────────────────
    for r in ws.sample(runs, 40):
        ws.record_outcome(r, "resolved", value_usd=5.0)
        ws.score(r, "quality", 0.88)

    # ── 5. Billing summary ────────────────────────────────────────────
    ws.get_billing_summary(months=3)
    say("    · billing summary retrieved", "d")
