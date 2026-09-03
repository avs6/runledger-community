"""Fetch Workflow detail loop posture (runs, chargeback, optimization, eval context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/workflow-detail-loop-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Runs 30d: {data['runs_context']['runs_30d']}")
print(f"Distinct workflows: {data['runs_context']['distinct_workflows']}")
print(f"Chargeback rules: {data['chargeback_context']['rules']}")
print(f"Cost 30d: ${data['chargeback_context']['cost_30d']:.2f}")
print(f"Replay experiments: {data['optimization_context']['replay_experiments']}")
print(f"Eval experiments: {data['eval_context']['experiments']}")
