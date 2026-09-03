"""Fetch Datasets eval asset posture (org, observe, chargeback, build context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/datasets-eval-asset-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Workspace: {data['org_context']['workspace_name']}")
print(f"Datasets: {data['org_context']['datasets']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Chargeback rules: {data['finops_context']['chargeback_rules']}")
print(f"Cost 30d: ${data['finops_context']['cost_30d']:.2f}")
print(f"Eval experiments: {data['build_context']['eval_experiments']}")
print(f"Replay experiments: {data['build_context']['replay_experiments']}")
