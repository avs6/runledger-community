"""
Scenario: a local reasoning agent on deepseek-r1 (14B vs 8B).

Reasoning models emit lots of output tokens, so this workspace shows how output-heavy
local workloads accrue cost — and lets the flywheel compare 14B vs 8B on cost × quality.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ollama-reasoning-agent"
DESCRIPTION = "Local reasoning (deepseek-r1 14B vs 8B) — output-heavy, cost × quality."

OLLAMA = "http://host.docker.internal:11434/v1"


def run(sim: Sim) -> None:
    ws = sim.workspace("ThinkLocal", "Reasoning")

    ws.add_route("deep", "deepseek-r1:14b", priority=10, base_url=OLLAMA)
    ws.add_route("fast", "deepseek-r1:8b", priority=20, base_url=OLLAMA)

    runs = ws.ingest_runs(
        90,
        models=["deepseek-r1:14b", "deepseek-r1:8b", "deepseek-r1:8b"],
        features=["math", "planning", "root-cause", "strategy"],
        users=["analyst_a", "analyst_b", "analyst_c"],
        days=21,
        success_rate=0.86,
    )

    ws.add_budget("workspace", 150, period_type="monthly", action="notify")

    for r in ws.sample(runs, 30):
        ws.score(r, "accuracy", round(random.uniform(0.5, 0.97), 2), label="auto")
        if r.success and random.random() < 0.35:
            ws.record_outcome(r, "decision_supported", success=True,
                              value_usd=round(random.uniform(15, 120), 2),
                              labels={"task": r.feature})
