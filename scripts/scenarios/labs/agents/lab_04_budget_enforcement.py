"""
Lab 04 — Budget enforcement.

WHAT THIS IS
────────────
Finance gave the **AI Support Team** a hard spending cap. When the workspace hits
its daily budget, RunLedger should *block* further model calls — not just warn.
With `budget_check=True`, the SDK checks the budget before each call and raises
`RunLedgerBudgetExceededError` once the cap is breached, so your agent fails
closed instead of running up a bill.

IMPORTANT — budgets are created in the GUI, not by this script.
Creating a budget requires a workspace-admin **dashboard session**; an API key
can't do it (by design — spend caps are a human governance control). So:

DO THIS FIRST (dashboard → Budgets)
───────────────────────────────────
Log in as the AI Support Team's workspace admin and create a budget:
    Scope:   workspace
    Period:  daily
    Limit:   0.05        (deliberately tiny so this lab trips it quickly)
    Action:  block
Also make sure you've uploaded pricing (Module 2) so the Ollama calls actually
accrue cost — a $0 model never breaches a budget.

PREREQUISITES
─────────────
  • AI Support Team workspace key in agents/.env  (same key as Lab 01)
  • The daily block budget above
  • pip install -r requirements.txt

RUN
───
    python lab_04_budget_enforcement.py

WHAT YOU'LL SEE
───────────────
  • The first calls succeed. As processed spend crosses $0.05, a call raises
    RunLedgerBudgetExceededError and the agent stops — that's enforcement working.
  • Cost enrichment runs on Celery, so there's a short lag before the cap bites;
    the loop keeps sending until it's blocked (or hits the safety limit).

THEN VERIFY (dashboard → Budgets → your budget)
───────────────────────────────────────────────
  • Utilization crosses 100%; the budget shows as breached/blocking.
"""

from __future__ import annotations

import time

import openai
from _config import OLLAMA_BASE_URL, OLLAMA_MODEL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger
from runledger_sdk.exceptions import RunLedgerBudgetExceededError

MAX_CALLS = 60  # safety stop so the lab never loops forever


def main() -> None:
    banner("Lab 04 · Budget enforcement · AI Support Team")
    require_key()

    # budget_check=True → the SDK enforces the workspace budget before each call.
    rl = RunLedger(budget_check=True)
    rl.instrument()
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    print("Sending support calls until the daily budget blocks us…\n")
    for i in range(1, MAX_CALLS + 1):
        try:
            with rl.context(end_user_id=f"cust_{i}", feature_tag="support-chat"):
                client.chat.completions.create(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": "Give me a 2-sentence status update."}],
                    temperature=0.5,
                )
            print(f"  call {i:>2}  ✓ allowed")
        except RunLedgerBudgetExceededError as exc:
            print(f"  call {i:>2}  ✗ BLOCKED — budget exceeded: {exc}")
            print("\n✓ Enforcement worked: the agent failed closed instead of overspending.")
            break
        time.sleep(1)  # give Celery a moment to enrich cost between calls
    else:
        print(
            "\n(!) Never blocked after "
            f"{MAX_CALLS} calls. Lower the budget limit, confirm action=block, "
            "and make sure pricing is uploaded so Ollama calls cost > $0."
        )

    rl.shutdown()
    print(f"  Review it at {dashboard_url()}/budgets")


if __name__ == "__main__":
    main()
