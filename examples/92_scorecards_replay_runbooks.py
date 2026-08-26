"""
Example 92 — Scorecards Replay and Runbooks Support Refresh

Demonstrates the API contracts used by Model Scorecards, Replay Lab, and
Runbooks pages, highlighting the gateway, workspace, and audit context
that operators can pivot into from each surface.
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_API_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "rl_test_key")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        # Model scorecards — workspace-scoped quality/cost/latency comparison
        sc = c.get("/analytics/model-scorecards", params={"days": 30}).json()
        print("=== Model Scorecards ===")
        print(f"  Models scored: {len(sc.get('items', []))}")
        for item in sc.get("items", [])[:3]:
            print(f"    {item['model_id']}: cost=${item.get('total_cost_usd', '?')}, "
                  f"latency_p50={item.get('latency_p50_ms', '?')}ms")
        print("  Drill-through: Workspaces, Model Usage, Evaluation Studio")

        # Replay lab — datasets and experiments
        ds = c.get("/replay/datasets").json()
        ex = c.get("/replay/experiments").json()
        print(f"\n=== Replay Lab ===")
        print(f"  Datasets: {len(ds.get('items', []))}")
        print(f"  Experiments: {len(ex.get('items', []))}")
        print("  Drill-through: Model Gateway, Provider Profiles, Routes")

        # Runbooks — auto-generated post-mortems
        rb = c.get("/runs/runbooks", params={"limit": 5}).json()
        print(f"\n=== Runbooks ===")
        print(f"  Total runbooks: {rb.get('total', 0)}")
        for item in rb.get("items", [])[:3]:
            print(f"    Run {item['run_id'][:8]}... severity={item['severity']}")
        print("  Drill-through: Model Gateway, Audit Log, Runs")


if __name__ == "__main__":
    main()
