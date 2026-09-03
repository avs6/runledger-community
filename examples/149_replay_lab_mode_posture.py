"""Fetch Replay Lab mode posture (chargeback, replay context)."""

import os, httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.environ["RUNLEDGER_API_KEY"]

r = httpx.get(
    f"{BASE}/analytics/replay-lab-mode-posture",
    headers={"Authorization": f"Bearer {KEY}"},
)
r.raise_for_status()
data = r.json()
print(f"Chargeback rules: {data['chargeback_context']['chargeback_rules']}")
print(f"Cost 30d: ${data['chargeback_context']['cost_30d']:.2f}")
print(f"Replay experiments: {data['replay_context']['replay_experiments']}")
print(f"Replay datasets: {data['replay_context']['replay_datasets']}")
