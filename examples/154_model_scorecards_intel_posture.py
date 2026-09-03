"""Fetch Model Scorecards intelligence posture (model, cost, optimization context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/model-scorecards-intel-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Hub models: {data['model_context']['hub_models']}")
print(f"Distinct models 30d: {data['model_context']['distinct_models_30d']}")
print(f"Cost 30d: ${data['cost_context']['cost_30d']:.2f}")
print(f"Score events 30d: {data['optimization_context']['score_events_30d']}")
print(f"Eval experiments: {data['optimization_context']['eval_experiments']}")
