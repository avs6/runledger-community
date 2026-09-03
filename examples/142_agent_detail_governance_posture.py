"""Fetch Agent detail governance posture (guardrail, observe, safety, eval context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/agent-detail-governance-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Guardrail rules: {data['guardrail_context']['rules']}")
print(f"Guardrail events 30d: {data['guardrail_context']['events_30d']}")
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Capture policies: {data['safety_context']['capture_policies']}")
print(f"Security events 30d: {data['safety_context']['security_events_30d']}")
print(f"Eval datasets: {data['eval_context']['datasets']}")
print(f"Experiments: {data['eval_context']['experiments']}")
