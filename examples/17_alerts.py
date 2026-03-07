"""
Example 17 — Advanced Alerting

Demonstrates:
  1. POST /alerts/rules      — create an alert rule (error_rate threshold)
  2. GET  /alerts/rules      — list all rules (including inactive)
  3. PUT  /alerts/rules/{id} — toggle a rule on/off
  4. GET  /alerts/history    — recent alert firings with rule name + metric value
  5. DELETE /alerts/rules/{id} — delete rule

Alert rules fire automatically every 5 minutes via the Celery beat scheduler.
When a threshold is crossed, a GatewayRequest log entry is recorded and (if
channel_id is configured) a Slack Block Kit notification is sent.

Metrics
───────
  error_rate      — ratio of failed runs in the window (e.g. > 0.05 = >5% errors)
  p95_latency     — 95th-percentile run latency in ms (e.g. > 5000 = >5s)
  avg_score       — average score from /evaluations/scores (e.g. < 0.6)
  spend_velocity  — total cost_usd in the window in USD (e.g. > 10.0 = >$10/hour)

Install
───────
    pip install httpx python-dotenv

Run it
──────
    python 17_alerts.py
"""

from __future__ import annotations

import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def sep(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


# ── Step 1 — Create alert rules ────────────────────────────────────────────────

sep("Step 1 — POST /alerts/rules (create alert rules)")

rules_to_create = [
    {
        "name": "High error rate",
        "metric": "error_rate",
        "operator": "gt",
        "threshold": 0.05,
        "window_minutes": 60,
    },
    {
        "name": "Slow responses",
        "metric": "p95_latency",
        "operator": "gt",
        "threshold": 5000,
        "window_minutes": 30,
    },
    {
        "name": "Low quality scores",
        "metric": "avg_score",
        "operator": "lt",
        "threshold": 0.6,
        "window_minutes": 60,
    },
    {
        "name": "Spend spike",
        "metric": "spend_velocity",
        "operator": "gt",
        "threshold": 5.0,
        "window_minutes": 60,
    },
]

created_ids: list[str] = []
with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    for payload in rules_to_create:
        resp = client.post("/alerts/rules", json=payload)
        if resp.status_code == 201:
            rule = resp.json()
            created_ids.append(rule["id"])
            op = ">" if payload["operator"] == "gt" else "<"
            print(
                f"  ✓ Created [{rule['name']}]  {rule['metric']} {op} {rule['threshold']}"
                f"  (window={rule['window_minutes']}m)"
            )
        else:
            print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 2 — List rules ────────────────────────────────────────────────────────

sep("Step 2 — GET /alerts/rules (list all rules)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/alerts/rules", params={"include_inactive": "true"})

if resp.status_code == 200:
    data = resp.json()
    rules = data["items"]
    print(f"  {len(rules)} rule(s):")
    print(f"  {'Name':<25} {'Metric':<16} {'Condition':<12} {'Window':>6}  {'Active'}")
    print(f"  {'─'*25} {'─'*16} {'─'*12} {'─'*6}  {'─'*6}")
    for r in rules:
        op = ">" if r["operator"] == "gt" else "<"
        cond = f"{op} {float(r['threshold'])}"
        status = "✓" if r["is_active"] else "✗"
        print(f"  {r['name']:<25} {r['metric']:<16} {cond:<12} {r['window_minutes']:>5}m  {status}")
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 3 — Toggle a rule ─────────────────────────────────────────────────────

sep("Step 3 — PUT /alerts/rules/{id} (toggle active/inactive)")

if created_ids:
    rule_id = created_ids[0]
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.put(f"/alerts/rules/{rule_id}", json={"is_active": False})

    if resp.status_code == 200:
        updated = resp.json()
        print(f"  Toggled [{updated['name']}] → is_active={updated['is_active']}")
    else:
        print(f"  ERROR {resp.status_code}: {resp.text}")

    # Re-enable it
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.put(f"/alerts/rules/{rule_id}", json={"is_active": True})
    if resp.status_code == 200:
        updated = resp.json()
        print(f"  Re-enabled [{updated['name']}] → is_active={updated['is_active']}")
else:
    print("  (No rules created in Step 1 — skipping)")


# ── Step 4 — Alert history ─────────────────────────────────────────────────────

sep("Step 4 — GET /alerts/history (recent firings)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    resp = client.get("/alerts/history", params={"limit": 10})

if resp.status_code == 200:
    history = resp.json()["items"]
    if not history:
        print(
            "  No firings yet — rules evaluate every 5 minutes via Celery Beat.\n"
            "  Lower thresholds (e.g. error_rate > 0.001) to trigger firings immediately."
        )
    else:
        print(f"  {len(history)} recent firing(s):")
        for f in history[:5]:
            print(
                f"    [{f['rule_name']:<25}]"
                f"  value={float(f['metric_value']):.4f}"
                f"  fired={f['fired_at'][:19]}"
            )
else:
    print(f"  ERROR {resp.status_code}: {resp.text}")


# ── Step 5 — Cleanup (delete created rules) ────────────────────────────────────

sep("Step 5 — DELETE /alerts/rules/{id} (cleanup demo rules)")

with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
    for rule_id in created_ids:
        resp = client.delete(f"/alerts/rules/{rule_id}")
        status = "✓ deleted" if resp.status_code == 204 else f"ERROR {resp.status_code}"
        print(f"  {rule_id[:8]}…  {status}")

print(f"\n  Cleaned up {len(created_ids)} rule(s).")
print("\n✓ Example 17 complete.\n")
