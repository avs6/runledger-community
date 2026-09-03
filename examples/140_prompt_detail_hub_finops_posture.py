"""Fetch Prompt detail hub and FinOps posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/prompt-detail-hub-finops-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Hub models: {data['hub_context']['hub_models']}")
print(f"Active models: {data['hub_context']['active_models']}")
print(f"Chargeback rules: {data['chargeback_context']['rules']}")
print(f"Attributed cost 30d: ${data['chargeback_context']['attributed_cost_30d']:.2f}")
