"""Fetch Runbooks Remediation posture (observe, alert, cost, optimization context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/runbooks-remediation-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Runs 30d: {data['observe_context']['runs_30d']}")
print(f"Provider calls 30d: {data['observe_context']['provider_calls_30d']}")
print(f"Alert rules: {data['alert_context']['alert_rules']}")
print(f"Alert firings 30d: {data['alert_context']['alert_firings_30d']}")
print(f"Cost 30d: ${data['cost_context']['cost_30d']:.2f}")
print(f"Billing periods: {data['cost_context']['billing_periods']}")
print(f"Eval experiments: {data['optimization_context']['eval_experiments']}")
