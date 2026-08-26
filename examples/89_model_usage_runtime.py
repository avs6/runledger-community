"""
Example 89 — Model Usage Economics and Runtime Refresh

Demonstrates the posture endpoints used by the Model Usage page to surface
guardrail, rate limit, and budget context alongside model traffic analysis.
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_API_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "rl_test_key")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def get_model_usage_gateway_posture():
    r = httpx.get(f"{BASE}/analytics/model-usage-gateway-posture", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    gc = data["gateway_context"]
    print(f"Active routes:      {gc['active_routes']} / {gc['total_routes']}")
    print(f"Distinct models:    {gc['distinct_models']}")
    print(f"Routing policies:   {gc['routing_policies']}")
    return data


def get_gateway_runtime_posture():
    r = httpx.get(f"{BASE}/analytics/investigation-gateway-runtime-posture", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    gr = data["guardrail_context"]
    rl = data["rate_limit_context"]
    print(f"Guardrail rules:    {gr['active_rules']} active")
    print(f"Guardrail events:   {gr['events_30d']} (30d), {gr['blocks_30d']} blocks")
    print(f"RPM-limited routes: {rl['routes_with_rpm_limits']}")
    print(f"Cost-limited routes:{rl['routes_with_cost_limits']}")
    return data


def get_model_budget_utilization():
    r = httpx.get(f"{BASE}/analytics/model-budget-utilization", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    print(f"Active model budgets: {data['active_model_budgets']}")
    for m in data["models"][:3]:
        limit = f"${m['budget_limit_usd']:.2f}" if m["budget_limit_usd"] else "no limit"
        print(f"  {m['model']}  spend=${m['spend_30d']:.4f}  limit={limit}")
    return data


if __name__ == "__main__":
    print("=== Model Usage Gateway Posture ===")
    get_model_usage_gateway_posture()
    print()

    print("=== Gateway Runtime Posture (guardrails + rate limits) ===")
    get_gateway_runtime_posture()
    print()

    print("=== Model Budget Utilization ===")
    get_model_budget_utilization()
