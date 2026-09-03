"""Fetch Workflows list posture (org, gateway, observe, eval context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/workflows-list-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Workspace: {data['org_context']['workspace_name']}")
print(f"Hub models: {data['org_context']['hub_models']}")
print(f"Active models: {data['org_context']['active_models']}")
print(f"Gateway routes: {data['gateway_context']['gateway_routes']}")
print(f"Routing policies: {data['gateway_context']['routing_policies']}")
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Spend 30d: ${data['observe_context']['spend_30d']:.2f}")
print(f"Eval datasets: {data['eval_context']['datasets']}")
print(f"Experiments: {data['eval_context']['experiments']}")
