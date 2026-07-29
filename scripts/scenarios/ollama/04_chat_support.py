"""
Scenario: a customer-support bot on small local models (llama3.2 / gemma3).

High volume, cheap-per-call local models, a hard daily budget, and ticket outcomes —
the local-first version of the hosted SaaS-support scenario, so you can compare the
cost-per-resolved-ticket of local vs hosted.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ollama-chat-support"
DESCRIPTION = "Local support bot (llama3.2 / gemma3) — high volume, ticket outcomes."

OLLAMA = "http://host.docker.internal:11434/v1"


def run(sim: Sim) -> None:
    ws = sim.workspace("HelpDesk Local", "Support Bot")

    ws.add_route("chat", "llama3.2", priority=10, base_url=OLLAMA, semantic_cache_enabled=True)
    ws.add_route("chat", "gemma3:latest", priority=20, base_url=OLLAMA)

    runs = ws.ingest_runs(
        200,
        models=["llama3.2", "llama3.2", "gemma3:latest"],
        features=["support-chat", "faq-answer", "ticket-triage"],
        users=[f"cust_{i}" for i in range(1, 40)],
        days=30,
        success_rate=0.92,
        sessions=30,
    )

    ws.add_budget("workspace", 60, period_type="monthly", action="notify")
    ws.add_budget("workspace", 4, period_type="daily", action="block")

    for r in ws.sample(runs, 30):
        if r.success and random.random() < 0.6:
            ws.record_outcome(r, "ticket_resolved", success=True,
                              value_usd=round(random.uniform(4, 12), 2),
                              labels={"channel": random.choice(["email", "chat", "in-app"])})
        ws.score(r, "csat", round(random.uniform(0.68, 0.98), 2))

    ws.add_alert("Support budget breach", "spend_velocity", "gt", 5.0)
