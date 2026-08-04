"""
Scenario: a customer-support bot on local Ollama models.

High volume, cheap-per-call local models, hard budgets, ticket outcomes, OTLP traces,
prompt versions, datasets, and model bakeoff experiments. This is the main demo org for
dense Runs, Request Flow, Model Usage, Prompts, Datasets, Experiments, and OTLP pages.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ollama-chat-support"
DESCRIPTION = "Local support bot — dense Ollama traffic, OTLP, prompts, datasets, and eval experiments."

OLLAMA = "http://host.docker.internal:11434/v1"


def run(sim: Sim) -> None:
    ws = sim.workspace("HelpDesk Local", "Support Bot")

    models = [
        "llama3.1:8b",
        "llama3.2",
        "llama3.2:3b",
        "gemma3:latest",
        "qwen3.5:latest",
        "qwen2.5-coder:14b",
        "deepseek-r1:8b",
        "deepseek-r1:14b",
        "nomic-embed-text",
    ]

    workflows = [
        {
            "feature": "support-chat",
            "agent": "Support Chat",
            "skill": "answer_customer",
            "tool": "customer_context",
            "team": "Support",
            "route": "fast-lane",
            "prompt_name": "support-chat-agent",
            "cache_rate": 0.26,
            "outcome_type": "ticket_resolved",
        },
        {
            "feature": "ticket-triage",
            "agent": "Ticket Triage",
            "skill": "classify_ticket",
            "tool": "ticket_router",
            "team": "Support",
            "route": "low-cost-local",
            "prompt_name": "ticket-triage-agent",
            "cache_rate": 0.18,
            "outcome_type": "triaged",
        },
        {
            "feature": "faq-answer",
            "agent": "FAQ Answer",
            "skill": "knowledge_search",
            "tool": "help_center_search",
            "team": "Support",
            "route": "cached-support",
            "prompt_name": "support-chat-agent",
            "cache_rate": 0.46,
            "outcome_type": "deflected",
        },
        {
            "feature": "escalation-review",
            "agent": "Escalation Review",
            "skill": "policy_check",
            "tool": "risk_review",
            "team": "Customer Success",
            "route": "reasoning-local",
            "prompt_name": "escalation-review-agent",
            "cache_rate": 0.08,
            "outcome_type": "escalated",
        },
        {
            "feature": "refund-policy",
            "agent": "Refund Policy",
            "skill": "policy_lookup",
            "tool": "billing_policy",
            "team": "Billing",
            "route": "privacy-first",
            "prompt_name": "billing-help-agent",
            "cache_rate": 0.22,
            "outcome_type": "refund_explained",
        },
        {
            "feature": "sentiment-routing",
            "agent": "Sentiment Router",
            "skill": "detect_sentiment",
            "tool": "sentiment_classifier",
            "team": "Support",
            "route": "low-cost-local",
            "prompt_name": "ticket-triage-agent",
            "cache_rate": 0.16,
            "outcome_type": "routed",
        },
        {
            "feature": "knowledge-search",
            "agent": "Knowledge Search",
            "skill": "rag_search",
            "tool": "vector_search",
            "team": "Support",
            "route": "cached-support",
            "prompt_name": "support-chat-agent",
            "cache_rate": 0.42,
            "outcome_type": "article_used",
        },
        {
            "feature": "billing-help",
            "agent": "Billing Helper",
            "skill": "invoice_lookup",
            "tool": "invoice_reader",
            "team": "Billing",
            "route": "privacy-first",
            "prompt_name": "billing-help-agent",
            "cache_rate": 0.14,
            "outcome_type": "billing_resolved",
        },
        {
            "feature": "fraud-check",
            "agent": "Fraud Check",
            "skill": "risk_screening",
            "tool": "risk_score",
            "tool_type": "privileged",
            "team": "Trust",
            "route": "reasoning-local",
            "prompt_name": "escalation-review-agent",
            "cache_rate": 0.06,
            "outcome_type": "risk_cleared",
        },
    ]

    for alias, model, priority in [
        ("fast-lane", "llama3.2", 10),
        ("low-cost-local", "llama3.2:3b", 20),
        ("cached-support", "gemma3:latest", 30),
        ("reasoning-local", "deepseek-r1:14b", 40),
        ("privacy-first", "qwen3.5:latest", 50),
        ("coding-helper", "qwen2.5-coder:14b", 60),
    ]:
        ws.add_route(alias, model, priority=priority, base_url=OLLAMA, semantic_cache_enabled=alias == "cached-support")

    ws.seed_prompt_eval_assets(
        prompts=[
            {
                "name": "support-chat-agent",
                "description": "Grounded support assistant prompt for HelpDesk Local.",
                "versions": [
                    {
                        "content": "You are a concise support agent. Answer using known policy, cite article ids, and escalate if risk is high. Customer: {{customer_message}}",
                        "variables": [{"name": "customer_message", "type": "string"}],
                        "commit_message": "Initial local support prompt",
                        "model_hint": "llama3.2",
                    },
                    {
                        "content": "You are HelpDesk Local's support agent. Resolve the issue in under five bullets, include policy caveats, and explain next action. Customer: {{customer_message}}",
                        "variables": [{"name": "customer_message", "type": "string"}],
                        "commit_message": "Tighter resolution format",
                        "model_hint": "gemma3:latest",
                    },
                ],
            },
            {
                "name": "ticket-triage-agent",
                "description": "Classifies tickets into intent, urgency, owner, and route.",
                "versions": [
                    {
                        "content": "Classify this ticket into intent, urgency, team, and whether automation is safe. Ticket: {{ticket}}",
                        "variables": [{"name": "ticket", "type": "string"}],
                        "commit_message": "Seed triage prompt",
                        "model_hint": "llama3.2:3b",
                    },
                ],
            },
            {
                "name": "billing-help-agent",
                "description": "Handles refund, invoice, and subscription support.",
                "versions": [
                    {
                        "content": "Review the billing question, summarize the policy, and identify the safe next step. Question: {{question}}",
                        "variables": [{"name": "question", "type": "string"}],
                        "commit_message": "Seed billing support prompt",
                        "model_hint": "qwen3.5:latest",
                    },
                ],
            },
            {
                "name": "escalation-review-agent",
                "description": "Reviews sensitive support tickets before escalation.",
                "versions": [
                    {
                        "content": "Assess escalation risk, summarize key facts, and recommend next owner. Case: {{case_summary}}",
                        "variables": [{"name": "case_summary", "type": "string"}],
                        "commit_message": "Seed escalation prompt",
                        "model_hint": "deepseek-r1:14b",
                    },
                ],
            },
        ],
        dataset_name="HelpDesk support quality set",
        models=["llama3.2", "gemma3:latest", "qwen3.5:latest", "deepseek-r1:8b", "llama3.2:3b"],
    )

    runs = ws.ingest_rich_runs(
        600,
        models=models,
        workflows=workflows,
        users=[f"cust_{i}" for i in range(1, 86)],
        days=7,
        success_rate=0.93,
        sessions=140,
    )

    ws.ingest_otlp_traces(80, models=models, workflows=workflows)

    ws.add_budget("workspace", 60, period_type="monthly", action="notify")
    ws.add_budget("workspace", 4, period_type="daily", action="block")

    for r in ws.sample(runs, 45):
        if r.success and random.random() < 0.6:
            ws.record_outcome(r, "ticket_resolved", success=True,
                              value_usd=round(random.uniform(4, 12), 2),
                              labels={"channel": random.choice(["email", "chat", "in-app"])})
        ws.score(r, "csat", round(random.uniform(0.68, 0.98), 2))

    ws.add_alert("Support budget breach", "spend_velocity", "gt", 5.0)

    # ── Phase 13: governance & finops ───────────────────────────────────────
    ws.create_approval_request(
        "budget_increase",
        "Black Friday traffic — raise daily cap to $20",
        metadata={"current_limit": 4, "requested_limit": 20},
    )
    ws.create_approval_request(
        "premium_model_use",
        "Need deepseek-r1:14b for escalation reviews",
        metadata={"model": "deepseek-r1:14b", "duration": "7d"},
    )
    ws.create_approval_request(
        "external_mcp_tool",
        "Connect Slack MCP for real-time ticket alerts",
    )
    ws.add_auto_approval_policy(
        "budget_increase",
        max_amount=10.0,
        conditions={"scope": "workspace", "period_type": "daily"},
    )

    ws.add_chargeback_rule(
        "Support team — all chat",
        "feature_tag", "support-chat",
        "SUPPORT-OPS",
    )
    ws.add_chargeback_rule(
        "Billing team — refund + billing",
        "feature_tag", "billing-help",
        "BILLING-OPS",
        split_percent=80.0,
    )
    ws.add_chargeback_rule(
        "Trust team — fraud checks",
        "feature_tag", "fraud-check",
        "TRUST-SAFETY",
    )

    for r in ws.sample(runs, 8):
        if r.cost > 0.001:
            ws.generate_runbook(r)
