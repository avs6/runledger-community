"""Fetch Vector Stores lifecycle posture (workspace, observe, cost, build context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/vector-stores-lifecycle-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Workspace: {data['workspace_context']['workspace_name']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Cost 30d: ${data['cost_context']['cost_30d']:.2f}")
print(f"Chargeback rules: {data['cost_context']['chargeback_rules']}")
print(f"Workflows: {data['build_context']['workflows']}")
print(f"Eval experiments: {data['build_context']['eval_experiments']}")
