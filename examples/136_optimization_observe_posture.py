"""Fetch optimization observe posture."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/optimization-observe-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Runs 30d: {data['runs_context']['runs_30d']} (total: {data['runs_context']['total_runs']})")
print(f"Provider calls 30d: {data['request_flow_context']['provider_calls_30d']}")
print(f"  Input tokens: {data['request_flow_context']['total_input_tokens']}")
print(f"  Output tokens: {data['request_flow_context']['total_output_tokens']}")
print(f"Distinct models 30d: {data['model_usage_context']['distinct_models_30d']}")
print(f"Total cost 30d: ${data['cost_savings_context']['total_cost_30d']:.2f}")
print(f"  Cache configs: {data['cost_savings_context']['cache_configs']}")
print(f"  Estimated savings: ${data['cost_savings_context']['estimated_savings']:.2f}")
