"""
Example: Workflow detail cross-feature posture — org, gateway, observe, and FinOps context.

Demonstrates querying the workflow-detail-cross-feature-posture endpoint that surfaces
org scope (workspace, access groups, API keys, hub models), gateway configuration
(providers, routes, guardrails, cache, rate limits), observe metrics (runs, provider
calls, distinct models, cost), and FinOps context (budgets, billing periods, limits,
spend) for workflow operational awareness.

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_API_KEY
"""

from __future__ import annotations

import json
import os

import requests

BASE = os.environ["RUNLEDGER_BASE_URL"]
KEY = os.environ["RUNLEDGER_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def main() -> None:
    resp = requests.get(
        f"{BASE}/analytics/workflow-detail-cross-feature-posture",
        headers=HEADERS,
    )
    resp.raise_for_status()
    data = resp.json()

    print("=== Workflow Detail Cross-Feature Posture ===")
    print(f"Workspace: {data['workspace_id']}")
    print(f"Period: {data['period_days']}d\n")

    oc = data["org_context"]
    print(f"Workspace: {oc['workspace_name']}  |  Users: {oc['workspace_users']}")
    print(f"Access groups: {oc['access_groups']}  |  API keys: {oc['api_keys']}  |  Hub models: {oc['hub_models']}")

    gc = data["gateway_context"]
    print(f"\nProviders: {gc['distinct_providers']}  |  Routes: {gc['active_routes']}")
    print(f"Guardrails: {gc['guardrail_rules']}  |  Cache configs: {gc['cache_configs']}  |  Rate-limited: {gc['rate_limited_routes']}")

    ob = data["observe_context"]
    print(f"\nRuns (30d): {ob['runs_30d']}  |  Provider calls: {ob['provider_calls_30d']}")
    print(f"Distinct models: {ob['distinct_models_30d']}  |  Cost: ${ob['total_cost_30d']:.4f}")

    fc = data["finops_context"]
    print(f"\nActive budgets: {fc['active_budgets']}  |  Billing periods: {fc['billing_periods']}")
    print(f"Budget limit: ${fc['total_budget_limit']:.2f}  |  30d spend: ${fc['total_spend_30d']:.4f}")

    print(f"\nFull response:\n{json.dumps(data, indent=2)}")


if __name__ == "__main__":
    main()
