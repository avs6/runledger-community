"""Fetch Prompts list observe posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/prompts-list-observe-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Distinct models: {data['observe_context']['distinct_models']}")
print(f"Spend 30d: ${data['observe_context']['spend_30d']:.2f}")
print(f"Eval datasets: {data['eval_context']['datasets']}")
print(f"Eval experiments: {data['eval_context']['experiments']}")
