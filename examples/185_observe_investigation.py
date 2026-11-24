"""
Example 185 — Investigate a workflow's runs (Observe APIs)

Demonstrates, for one workflow (feature tag):
  1. GET /runs/facets            — models, providers and workflows this workspace recorded
  2. GET /runs/stats             — server-side totals and success rate for the filters
  3. GET /runs (keyset cursor)   — page through every failed run, no COUNT(*)
  4. GET /runs/compare           — the newest failure next to the newest success
  5. GET /analytics/request-explorer — the failing provider calls (status=failed works)
  6. GET /runs/stream            — follow new runs live for a few seconds (SSE)
  7. GET /analytics/summary      — the KPI success rate, from the API

Run it
──────
    pip install httpx python-dotenv
    RUNLEDGER_API_KEY=... python examples/185_observe_investigation.py --workflow support-chat

Saved views (`/runs/saved-views`) need a dashboard session, so they are not shown here;
use the "Views" menu on Runs, Request Explorer or Sessions.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigate a workflow's runs")
    parser.add_argument("--workflow", default=None, help="feature_tag to investigate")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    if not API_KEY:
        print("Set RUNLEDGER_API_KEY")
        return 2

    http = httpx.Client(
        base_url=BASE_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=30
    )
    since = (datetime.now(UTC) - timedelta(hours=args.hours)).isoformat()

    facets = http.get("/runs/facets").raise_for_status().json()
    workflow = args.workflow or (facets["feature_tags"][0] if facets["feature_tags"] else None)
    print(f"Models seen: {', '.join(facets['models'][:8]) or 'none'}")
    print(f"Workflow: {workflow or '(all)'}\n")
    filters = {"from": since, **({"feature_tag": workflow} if workflow else {})}

    stats = http.get("/runs/stats", params=filters).raise_for_status().json()
    rate = stats["success_rate"]
    print(
        f"{stats['total']} runs · {stats['failed']} failed · success {float(rate) * 100:.1f}%"
        if rate
        else f"{stats['total']} runs · no finished runs"
    )
    print(f"cost ${stats['total_cost_usd']} · p95 {stats['p95_duration_ms']} ms\n")

    failed: list[dict] = []
    cursor = None
    while True:
        params = {**filters, "status": "failed", "limit": 50, "include_total": "false"}
        if cursor:
            params["cursor"] = cursor
        page = http.get("/runs", params=params).raise_for_status().json()
        failed += page["items"]
        cursor = page["next_cursor"]
        if not cursor or len(failed) >= 200:
            break
    print(f"Failed runs paged with the cursor: {len(failed)}")

    ok = http.get(
        "/runs", params={**filters, "status": "succeeded", "limit": 1, "include_total": "false"}
    ).json()
    if failed and ok["items"]:
        cmp = http.get(
            "/runs/compare", params={"a": ok["items"][0]["id"], "b": failed[0]["id"]}
        ).json()
        print("Compare newest success → newest failure:")
        for name, delta in cmp["delta"].items():
            print(f"  {name:15} {delta}")
        print(f"  tools: {cmp['a']['tools']} → {cmp['b']['tools']}\n")

    calls = http.get(
        "/analytics/request-explorer", params={**filters, "status": "failed", "page_size": 5}
    ).json()
    for call in calls["items"]:
        print(
            f"  {call['created_at'][:19]}  {call['model']:24} {call['status']}  run {call['run_id'][:8]}"
        )

    print("\nLive runs for 5 seconds:")
    with http.stream(
        "GET",
        "/runs/stream",
        params={**filters, "since": datetime.now(UTC).isoformat(), "max_seconds": 5},
    ) as stream:
        for line in stream.iter_lines():
            if line.startswith("data: "):
                print("  ", line[6:120])

    summary = http.get("/analytics/summary", params={"from": since}).json()
    print(f"\nWorkspace success rate (API): {summary.get('success_rate')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
