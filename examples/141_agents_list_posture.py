"""Fetch Agents list posture (org, provider, observe, finops, eval context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/agents-list-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Workspace: {data['org_context']['workspace_name']}")
print(f"Hub models: {data['org_context']['hub_models']} (active: {data['org_context']['active_models']})")
print(f"Distinct providers: {data['provider_context']['distinct_providers']}")
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Chargeback rules: {data['finops_context']['chargeback_rules']}")
print(f"Spend 30d: ${data['finops_context']['spend_30d']:.2f}")
print(f"Eval datasets: {data['eval_context']['datasets']}")
print(f"Experiments: {data['eval_context']['experiments']}")
