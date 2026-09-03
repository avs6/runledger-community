"""Fetch Evaluation Studio parent posture (billing, chargeback, eval self context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/eval-studio-parent-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Billing periods: {data['billing_context']['billing_periods']}")
print(f"Open periods: {data['billing_context']['open_periods']}")
print(f"Chargeback rules: {data['chargeback_context']['chargeback_rules']}")
print(f"Cost 30d: ${data['chargeback_context']['cost_30d']:.2f}")
print(f"Datasets: {data['eval_self_context']['datasets']}")
print(f"Experiments: {data['eval_self_context']['experiments']}")
print(f"Replay experiments: {data['eval_self_context']['replay_experiments']}")
