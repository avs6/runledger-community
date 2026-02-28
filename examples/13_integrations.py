"""
Example 13 — Integrations: Slack Alerts + Analytics Export

Demonstrates:
  1. POST /integrations/slack/test  — fire a test Slack message
  2. GET  /analytics/export?format=json  — print first 5 rows
  3. GET  /analytics/export?format=csv   — save to export.csv
  4. GET  /analytics/regressions         — print regressions (same data as check-regression CLI)

Run with:
    RUNLEDGER_API_KEY=rl_test_... python examples/13_integrations.py
"""

from __future__ import annotations

import os
import sys

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("ERROR: RUNLEDGER_API_KEY env var is required", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10.0)


# ── 1. Slack test ─────────────────────────────────────────────────────────────

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

if SLACK_WEBHOOK_URL:
    print("─── 1. Slack webhook test ───")
    with _client() as client:
        resp = client.post(
            "/integrations/slack/test",
            json={"webhook_url": SLACK_WEBHOOK_URL},
        )
        resp.raise_for_status()
        result = resp.json()
        if result["ok"]:
            print("  ✓ Test message sent to Slack.")
        else:
            print(f"  ✗ Failed: {result['error']}")
else:
    print("─── 1. Slack webhook test (skipped — set SLACK_WEBHOOK_URL to enable) ───")


# ── 2. Analytics export — JSON ────────────────────────────────────────────────

print("\n─── 2. Analytics export (JSON — first 5 rows) ───")
with _client() as client:
    resp = client.get("/analytics/export?format=json")
    resp.raise_for_status()
    data = resp.json()

items = data.get("items", [])
print(f"  Total rows: {len(items)}")
for row in items[:5]:
    print(
        f"  {row['date']}  {row['provider']}/{row['model']}"
        f"  ${row['cost_usd']}  calls={row['call_count']}"
    )


# ── 3. Analytics export — CSV ─────────────────────────────────────────────────

print("\n─── 3. Analytics export (CSV → export.csv) ───")
with _client() as client:
    resp = client.get("/analytics/export?format=csv")
    resp.raise_for_status()

csv_path = "export.csv"
with open(csv_path, "w", encoding="utf-8") as f:
    f.write(resp.text)
print(f"  Saved to {csv_path} ({len(resp.text.splitlines())} lines including header)")


# ── 4. Regressions (same data as `runledger check-regression`) ───────────────

print("\n─── 4. Cost regressions (last 7d vs prior 7d) ───")
with _client() as client:
    resp = client.get("/analytics/regressions")
    resp.raise_for_status()
    reg_data = resp.json()

regressions = reg_data.get("items", [])
if not regressions:
    print("  ✓ No regressions detected.")
else:
    print(f"  Found {len(regressions)} regression(s):")
    for r in regressions:
        print(
            f"  [{r.get('feature_tag', '—')}]  "
            f"current avg ${r['current_avg_cost']}  "
            f"prior avg ${r['prior_avg_cost']}  "
            f"change +{r['change_pct']}%"
        )
