"""Fetch Replay Result Analysis posture (gateway, observe, cost context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/replay-result-analysis-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Guardrail rules: {data['gateway_context']['guardrail_rules']}")
print(f"Cache configs: {data['gateway_context']['cache_configs']}")
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Cost 30d: ${data['cost_context']['cost_30d']:.2f}")
print(f"Replay experiments: {data['cost_context']['replay_experiments']}")
