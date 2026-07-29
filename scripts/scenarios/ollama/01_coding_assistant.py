"""
Scenario: an internal coding assistant running entirely on local Ollama models.

Shows that **local inference still costs money** — qwen2.5-coder and deepseek-r1 are
priced in scripts/pricing.yaml (GPU/infra cost), so this workspace accrues real spend,
budgets bite, and cost-per-outcome is measurable even with no hosted provider.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ollama-coding-assistant"
DESCRIPTION = "Local coding assistant (qwen2.5-coder / deepseek-r1) — priced local inference."

OLLAMA = "http://host.docker.internal:11434/v1"


def run(sim: Sim) -> None:
    ws = sim.workspace("Acme Dev Tools", "Coding Assistant")

    ws.add_route("code", "qwen2.5-coder:14b", priority=10, base_url=OLLAMA, semantic_cache_enabled=True)
    ws.add_route("reason", "deepseek-r1:14b", priority=20, base_url=OLLAMA)

    runs = ws.ingest_runs(
        140,
        models=["qwen2.5-coder:14b", "qwen2.5-coder:14b", "deepseek-r1:14b", "deepseek-r1:8b"],
        features=["code-complete", "bug-fix", "code-review", "refactor"],
        users=[f"dev_{i}" for i in range(1, 12)],
        days=30,
        success_rate=0.9,
    )

    # Local isn't free — a GPU-cost budget that notifies, and a daily cap that blocks.
    ws.add_budget("workspace", 200, period_type="monthly", action="notify")
    ws.add_budget("workspace", 15, period_type="daily", action="block")

    for r in ws.sample(runs, 30):
        if r.success and r.feature in ("bug-fix", "code-review") and random.random() < 0.5:
            ws.record_outcome(r, "bug_resolved", success=True,
                              value_usd=round(random.uniform(8, 40), 2),
                              labels={"severity": random.choice(["low", "medium", "high"])})
        ws.score(r, "correctness", round(random.uniform(0.6, 0.98), 2))

    ws.add_alert("Local GPU spend spike", "spend_velocity", "gt", 20.0)
