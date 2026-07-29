"""
Scenario: an e-commerce company running multiple agent workflows.

Exercises breadth — several feature tags (product Q&A, recommendations, returns,
fraud review), a multi-provider route set with fallback priority, conversion outcomes
with real dollar value, and a high-value fraud budget that hard-blocks.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ecommerce-agents"
DESCRIPTION = "E-commerce — multiple agent workflows, conversion ROI, fraud review."


def run(sim: Sim) -> None:
    ws = sim.workspace("Shopwave", "Agents")

    # Multi-provider route set (priority = fallback order).
    ws.add_route("shopper", "gpt-4o-mini", priority=10, semantic_cache_enabled=True)
    ws.add_route("shopper", "claude-haiku-4-5", priority=20)
    ws.add_route("fraud", "gpt-4o", priority=10)

    runs = ws.ingest_runs(
        150,
        models=["gpt-4o-mini", "claude-haiku-4-5", "gpt-4o", "gemini-1.5-pro"],
        features=["product-qa", "recommendations", "returns-agent", "fraud-review"],
        users=[f"shopper_{i}" for i in range(1, 40)],
        days=30,
        success_rate=0.95,
        sessions=35,
    )

    ws.add_budget("workspace", 800, period_type="monthly", action="notify")
    ws.add_budget("feature", 100, period_type="daily", action="block", scope_id="fraud-review")

    # Conversions: recommendations + product-qa drive revenue.
    for r in ws.sample(runs, 30):
        if r.success and r.feature in ("recommendations", "product-qa") and random.random() < 0.35:
            ws.record_outcome(r, "conversion", success=True,
                              value_usd=round(random.uniform(20, 240), 2),
                              labels={"segment": random.choice(["new", "returning", "vip"])})
        if r.feature == "fraud-review":
            ws.record_outcome(r, "fraud_flagged", success=r.success,
                              labels={"risk": random.choice(["low", "medium", "high"])})
        ws.score(r, "relevance", round(random.uniform(0.6, 0.98), 2))

    ws.add_alert("Fraud model cost", "spend_velocity", "gt", 80.0)
