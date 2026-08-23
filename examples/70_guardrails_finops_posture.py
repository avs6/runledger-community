"""
Example: Guardrails FinOps posture.

Demonstrates querying the guardrails-finops-posture endpoint that surfaces
guardrail enforcement context (active rules, evaluations, blocks, active routes)
and FinOps context (budgets, budget notifications, billing periods, chargeback
rules).

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
    print("--- Guardrails FinOps Posture ---")
    posture = api("GET", "/analytics/guardrails-finops-posture")
    print(json.dumps(posture, indent=2))

    gc = posture.get("guardrail_context", {})
    print(f"\nActive rules: {gc.get('active_rules', 0)}")
    print(f"Evaluations (30d): {gc.get('evaluations_30d', 0)}")
    print(f"Blocks (30d): {gc.get('blocks_30d', 0)}")
    print(f"Active routes: {gc.get('active_routes', 0)}")

    fc = posture.get("finops_context", {})
    print(f"\nBudgets: {fc.get('budgets', 0)}")
    print(f"Budget notifications: {fc.get('budget_notifications', 0)}")
    print(f"Billing periods: {fc.get('billing_periods', 0)}")
    print(f"Chargeback rules: {fc.get('chargeback_rules', 0)}")


if __name__ == "__main__":
    main()
