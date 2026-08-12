"""
Lab 04 - Budget enforcement.

This uses HomeLab / AgentTest to show that a workspace budget can block new calls.
"""

from __future__ import annotations

import time

import openai
from _config import OLLAMA_BASE_URL, OLLAMA_MODEL, banner, dashboard_url, require_key
from runledger_sdk import RunLedger
from runledger_sdk.exceptions import RunLedgerBudgetExceededError

MAX_CALLS = 60


def main() -> None:
    banner("Lab 04 - Budget enforcement - HomeLab / AgentTest")
    require_key()

    rl = RunLedger(budget_check=True)
    rl.instrument()
    client = openai.OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    print("Sending support calls until the daily budget blocks us...\n")
    for i in range(1, MAX_CALLS + 1):
        try:
            with rl.context(end_user_id=f"cust_{i}", feature_tag="support-chat"):
                client.chat.completions.create(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": "Give me a 2-sentence status update."}],
                    temperature=0.5,
                )
            print(f"  call {i:>2}  allowed")
        except RunLedgerBudgetExceededError as exc:
            print(f"  call {i:>2}  blocked - budget exceeded: {exc}")
            print("\nEnforcement worked: the agent failed closed instead of overspending.")
            break
        time.sleep(1)
    else:
        print(
            "\nNever blocked after "
            f"{MAX_CALLS} calls. Lower the budget limit and confirm pricing is loaded."
        )

    rl.shutdown()
    print(f"Review the result at {dashboard_url()}/budgets")


if __name__ == "__main__":
    main()
