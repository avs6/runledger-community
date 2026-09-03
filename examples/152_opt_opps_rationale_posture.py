"""Fetch Optimization Opportunities rationale posture (cost, evaluation, optimization context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/opt-opps-rationale-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Cost 30d: ${data['cost_context']['cost_30d']:.2f}")
print(f"Eval experiments: {data['optimization_context']['eval_experiments']}")
print(f"Replay experiments: {data['optimization_context']['replay_experiments']}")
print(f"Score events 30d: {data['optimization_context']['score_events_30d']}")
