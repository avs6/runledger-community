"""
Example: Budget control build posture.

Queries the budget-control-build-posture analytics endpoint and prints
budget policy, override context, scope distribution, and spend context.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def api(method: str, path: str, payload: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload) if payload is not None else None,
        timeout=30,
    )
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def main() -> None:
    posture = api("GET", "/analytics/budget-control-build-posture")
    print("Budget Control — Build Posture")
    print("=" * 50)

    bp = posture["budget_policy"]
    print(f"\nBudget Policy:")
    print(f"  Total budgets:      {bp['total_budgets']}")
    print(f"  Active budgets:     {bp['active_budgets']}")
    print(f"  Breached:           {bp['breached_budgets']}")
    print(f"  Avg utilization:    {bp['avg_utilization_pct']:.1f}%")
    print(f"  Total limit:        ${bp['total_limit_usd']:.2f}")

    oc = posture["override_context"]
    print(f"\nOverride Context:")
    print(f"  Total overrides:  {oc['total_overrides']}")
    print(f"  Active overrides: {oc['active_overrides']}")

    sc = posture["scope_context"]
    print(f"\nScope Distribution:")
    for scope_type, count in sc.items():
        print(f"  {scope_type}: {count}")

    sp = posture["spend_context"]
    print(f"\nSpend Context:")
    print(f"  30d spend:   ${sp['total_spend_30d']:.2f}")
    print(f"  30d models:  {sp['distinct_models_30d']}")


if __name__ == "__main__":
    main()
