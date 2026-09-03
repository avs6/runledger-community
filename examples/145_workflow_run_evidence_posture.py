"""Fetch Workflow run evidence posture (gateway, observe, finops, audit context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/workflow-run-evidence-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Guardrail rules: {data['gateway_context']['guardrail_rules']}")
print(f"Cache configs: {data['gateway_context']['cache_configs']}")
print(f"Rate-limited routes: {data['gateway_context']['rate_limited_routes']}")
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Budgets: {data['finops_context']['budgets']}")
print(f"Cost 30d: ${data['finops_context']['cost_30d']:.2f}")
print(f"Audit events 30d: {data['safety_context']['audit_events_30d']}")
