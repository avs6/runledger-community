"""
Example: org-level posture rollup queries.

Demonstrates the three org posture summary endpoints:
- GET /org/finance  — financial posture (budgets, billing, chargeback, ledger)
- GET /org/runtime  — runtime posture (routes, providers, guardrails, rate limits)
- GET /org/observe  — observability posture (runs, requests, models, errors, alerts)

Requires an org-admin API key.
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    print("=== Org Posture Rollups ===\n")

    print("--- Financial Posture ---")
    fin = api_get("/org/finance")
    print(f"  30d spend: ${float(fin.get('org_spend_30d_usd', 0)):.2f}")
    print(f"  Budgets: {fin.get('active_budget_count', 0)} active")
    print(f"  Billing: {fin.get('overdue_billing_period_count', 0)} overdue")
    print(f"  Chargeback: {fin.get('chargeback_ready_workspace_count', 0)}/{len(fin.get('workspaces', []))} ready")
    print(f"  Ledger: {fin.get('ledger_readiness_status', 'unknown')}")

    print("\n--- Runtime Posture ---")
    rt = api_get("/org/runtime")
    print(f"  Routes: {rt.get('total_active_routes', 0)} active")
    print(f"  Providers: {rt.get('total_distinct_providers', 0)} distinct")
    print(f"  Routing policies: {rt.get('total_routing_policies', 0)}")
    print(f"  Guardrails: {rt.get('total_active_guardrails', 0)} active")
    print(f"  Rate-limited routes: {rt.get('total_rate_limited_routes', 0)}")
    for ws in rt.get("workspaces", []):
        print(f"    {ws['workspace_name']}: {ws['active_route_count']} routes, {ws['active_guardrail_count']} guardrails")

    print("\n--- Observability Posture ---")
    obs = api_get("/org/observe")
    print(f"  30d runs: {obs.get('total_run_count_30d', 0)}")
    print(f"  30d requests: {obs.get('total_request_count_30d', 0)}")
    print(f"  Models in use: {obs.get('total_distinct_models', 0)}")
    print(f"  30d errors: {obs.get('total_error_count_30d', 0)}")
    total_req = obs.get("total_request_count_30d", 0)
    total_err = obs.get("total_error_count_30d", 0)
    if total_req > 0:
        print(f"  Error rate: {(total_err / total_req) * 100:.1f}%")
    print(f"  Alert rules: {obs.get('total_active_alert_rules', 0)} active")
    for ws in obs.get("workspaces", []):
        print(f"    {ws['workspace_name']}: {ws['run_count_30d']} runs, {ws['request_count_30d']} requests")

    print("\nDone.")


if __name__ == "__main__":
    main()
