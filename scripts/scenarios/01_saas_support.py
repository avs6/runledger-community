"""
Scenario: a SaaS company running a customer-support bot at scale.

Exercises the cost-control story — a busy workspace with a cheap default model, an
exact + semantic cache on the route, budgets that notify and block, business outcomes
(resolved tickets with a $ value), quality scores, and a spend alert.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "saas-support"
DESCRIPTION = "SaaS support bot — high volume, cost caps, ticket outcomes."


def run(sim: Sim) -> None:
    ws = sim.workspace("Acme SaaS", "Support Bot")

    # Routes: a cheap default with caching, plus an escalation model.
    ws.add_route("chat", "gpt-4o-mini", priority=10, semantic_cache_enabled=True)
    ws.add_route("escalation", "gpt-4o", priority=20)

    # A month of support traffic.
    runs = ws.ingest_runs(
        120,
        models=["gpt-4o-mini", "gpt-4o-mini", "gpt-4o-mini", "gpt-4o"],
        features=["support-chat", "faq-answer", "ticket-triage", "escalation"],
        users=[f"cust_{i}" for i in range(1, 25)],
        days=30,
        success_rate=0.93,
        sessions=20,
    )

    # Budgets: soft monthly notify + hard daily block + a per-user cap.
    ws.add_budget("workspace", 500, period_type="monthly", action="notify")
    ws.add_budget("workspace", 40, period_type="daily", action="block")
    ws.add_budget("end_user", 5, period_type="daily", action="notify", scope_id="cust_1")

    # Outcomes: ~60% of runs resolved a ticket; each resolution has a support-cost value.
    for r in runs:
        if r.success and random.random() < 0.6:
            ws.record_outcome(r, "ticket_resolved", success=True,
                              value_usd=round(random.uniform(6, 18), 2),
                              labels={"channel": random.choice(["email", "chat", "in-app"])})
        ws.score(r, "csat", round(random.uniform(0.7, 0.99), 2))

    ws.add_alert("Support spend spike", "daily_cost_usd", "gt", 60.0)
