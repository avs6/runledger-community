"""
Traffic generator — the ONE reusable agent for the whole workbook.

Most of the lab is done in the dashboard GUI. Whenever a module says
"generate some traffic", you run THIS script. It's the same agentic code every
time; you just re-point it with environment variables — no code edits.

WHAT IT DOES
────────────
Simulates a support agent making LLM calls, and (optionally) attaches a quality
score and a business outcome to each run. Calls go either:
  • direct to Ollama              (default), or
  • through the RunLedger Gateway (set LAB_GATEWAY_ALIAS) — so it exercises whatever
    routing policies you configured on that alias (fallback, semantic cache,
    intelligent routing, cost caps, PII redaction, per-user limits…).

RE-POINT IT WITH ENV (in agents/.env or inline)
───────────────────────────────────────────────
  RUNLEDGER_API_KEY   which team/workspace the traffic lands in (swap = switch team)
  LAB_FEATURE_TAG     feature_tag stamped on every run (filter by it in the GUI)
  LAB_RUNS            number of runs (default 25)
  LAB_GATEWAY_ALIAS   e.g. "qa-chat" → route through the gateway alias; empty → direct Ollama
  LAB_SCORE           attach a quality score to each run   (default true)
  LAB_OUTCOME         attach a business outcome to each run (default true)
  LAB_BUDGET_CHECK    enforce the workspace budget, stop when blocked (default false)
  OLLAMA_MODEL        model for direct calls (default llama3.2)

EXAMPLES
────────
  # 25 runs into whatever workspace the .env key belongs to
  python traffic_gen.py

  # 50 runs, tagged, through a gateway alias to test routing policies
  LAB_RUNS=50 LAB_FEATURE_TAG=policy-test LAB_GATEWAY_ALIAS=qa-chat python traffic_gen.py

  # drive a budget until it blocks (Module: Budgets / Monitoring)
  LAB_BUDGET_CHECK=true LAB_RUNS=100 python traffic_gen.py
"""

from __future__ import annotations

import random
import sys
import time

import openai
from _config import (
    LAB_BUDGET_CHECK,
    LAB_FEATURE_TAG,
    LAB_GATEWAY_ALIAS,
    LAB_OUTCOME,
    LAB_RUNS,
    LAB_SCORE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    RUNLEDGER_BASE_URL,
    banner,
    dashboard_url,
    require_key,
)
from runledger_sdk import RunLedger
from runledger_sdk.exceptions import RunLedgerBudgetExceededError

# A small pool of realistic support prompts so runs vary (good for analytics/eval).
PROMPTS = [
    "How long do refunds take?",
    "I forgot my password — how do I reset it?",
    "Do you offer weekend support?",
    "How do I export my invoices?",
    "My payment failed, what should I do?",
    "Can I upgrade my plan mid-cycle?",
    "Where do I change my billing email?",
    "The dashboard won't load — any tips?",
]
USERS = [f"cust_{i}" for i in range(1, 16)]
FEATURES = ["support-chat", "faq-answer", "ticket-triage"]


def main() -> None:
    key = require_key()
    via = f"gateway alias '{LAB_GATEWAY_ALIAS}'" if LAB_GATEWAY_ALIAS else "direct Ollama"
    banner(f"Traffic generator · {LAB_RUNS} runs · feature '{LAB_FEATURE_TAG}' · via {via}")

    rl = RunLedger(budget_check=LAB_BUDGET_CHECK)
    rl.instrument()

    # Route through the gateway (to exercise policies) or straight to Ollama.
    if LAB_GATEWAY_ALIAS:
        client = openai.OpenAI(base_url=f"{RUNLEDGER_BASE_URL}/gateway", api_key=key)
        model = LAB_GATEWAY_ALIAS
    else:
        client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        model = OLLAMA_MODEL

    made = 0
    for i in range(1, LAB_RUNS + 1):
        user = random.choice(USERS)
        feature = LAB_FEATURE_TAG if LAB_FEATURE_TAG != "lab-traffic" else random.choice(FEATURES)
        try:
            with rl.context(end_user_id=user, feature_tag=feature) as run_id:
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a concise support agent."},
                        {"role": "user", "content": random.choice(PROMPTS)},
                    ],
                    temperature=0.4,
                )
                if LAB_SCORE:
                    rl.score(
                        "helpfulness",
                        round(random.uniform(0.7, 0.98), 2),
                        label="judged",
                        source="llm",
                    )
                if LAB_OUTCOME:
                    resolved = random.random() < 0.7
                    rl.outcome(
                        "ticket_resolved",
                        success=resolved,
                        end_user_id=user,
                        value_usd=round(random.uniform(5, 18), 2) if resolved else None,
                        labels={"channel": random.choice(["email", "chat", "in-app"])},
                    )
            made += 1
            if i % 10 == 0 or i == LAB_RUNS:
                print(f"  … {i}/{LAB_RUNS} runs")
        except RunLedgerBudgetExceededError as exc:
            print(f"\n  ✗ BLOCKED at run {i} — budget exceeded: {exc}")
            print("  (This is enforcement working: budget_check stopped the agent.)")
            break
        except openai.APIError as exc:
            print(f"  ! run {i} failed: {exc}", file=sys.stderr)
            time.sleep(1)

    rl.shutdown()
    print(f"\n✓ Generated {made} runs. Explore them at {dashboard_url()}/runs")
    print("  Cost enrichment + rollups run on Celery — give analytics ~60s.")


if __name__ == "__main__":
    main()
