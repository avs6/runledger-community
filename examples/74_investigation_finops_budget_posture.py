"""
Example: Investigation FinOps budget posture.

Demonstrates querying the investigation-finops-budget-posture endpoint that
surfaces budget context (count, active budgets, limit, breaches, overrides),
billing context (periods, open periods, chargeback rules), and spend context
(30-day spend and runs).

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


def api(method: str, path: str, params: dict | None = None):
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def main():
    print("--- Investigation FinOps Budget Posture ---")
    posture = api("GET", "/analytics/investigation-finops-budget-posture")
    print(json.dumps(posture, indent=2))

    bc = posture.get("budget_context", {})
    print(f"\nBudgets: {bc.get('budgets', 0)} ({bc.get('active_budgets', 0)} active)")
    print(f"Total limit: ${bc.get('total_limit_usd', 0):.2f}")
    print(f"Breaches: {bc.get('breach_count', 0)}")
    print(f"Overrides: {bc.get('overrides', 0)} ({bc.get('active_overrides', 0)} active)")

    bl = posture.get("billing_context", {})
    print(f"\nBilling periods: {bl.get('billing_periods', 0)} ({bl.get('open_billing_periods', 0)} open)")
    print(f"Chargeback rules: {bl.get('chargeback_rules', 0)}")

    sc = posture.get("spend_context", {})
    print(f"\n30d spend: ${sc.get('total_spend_30d', 0):.2f}")
    print(f"30d runs: {sc.get('total_runs_30d', 0)}")


if __name__ == "__main__":
    main()
