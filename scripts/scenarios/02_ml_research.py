"""
Scenario: an ML research team comparing models on hard tasks.

Exercises the quality story — a mix of frontier and local models, heavy evaluation
scoring across several metrics, and a research-heavy spend profile with fewer but
larger runs. Local (Ollama) runs cost $0, so cost-per-quality contrast is visible.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ml-research"
DESCRIPTION = "Research team — frontier vs local models, heavy eval scoring."


def run(sim: Sim) -> None:
    ws = sim.workspace("Nova Labs", "Research")

    ws.add_route("frontier", "o1", priority=10)
    ws.add_route("balanced", "claude-sonnet-4-6", priority=20)
    ws.add_route("local", "llama3.1:8b", priority=30)

    runs = ws.ingest_runs(
        80,
        models=["o1", "claude-sonnet-4-6", "gpt-4o", "llama3.1:8b", "llama3.2"],
        features=["reasoning-eval", "code-gen", "summarization", "rag-benchmark"],
        users=["researcher_a", "researcher_b", "researcher_c"],
        days=21,
        success_rate=0.88,
    )

    # Dense evaluation scores — this team scores everything on multiple metrics.
    for r in runs:
        ws.score(r, "accuracy", round(random.uniform(0.55, 0.98), 2), label="auto")
        ws.score(r, "faithfulness", round(random.uniform(0.6, 0.99), 2), label="judge")
        if random.random() < 0.4:
            ws.score(r, "helpfulness", round(random.uniform(0.5, 0.95), 2), label="human")

    # A modest research budget that only notifies.
    ws.add_budget("workspace", 1500, period_type="monthly", action="notify")

    # Tie a few successful benchmark runs to an outcome (a shipped model improvement).
    for r in runs:
        if r.success and r.feature == "rag-benchmark" and random.random() < 0.5:
            ws.record_outcome(r, "benchmark_passed", success=True,
                              labels={"suite": "rag-v2"})
