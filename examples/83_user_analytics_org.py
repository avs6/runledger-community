"""
Example 83 — User analytics with workspace context

Lists the top-spending end users, then opens the workspace's related context
(runs, spend, routes, budgets) from GET /context.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/83_user_analytics_org.py
"""

import os

import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== Top Spenders ===")
        r = c.get("/analytics/spend-by-user", params={"limit": 5})
        r.raise_for_status()
        for u in r.json()["items"]:
            print(f"  {u['end_user_id']}: ${float(u['cost_usd']):.4f} ({u['run_count']} runs)")

        print("\n=== Workspace context ===")
        r = c.get("/context", params={"entity": "workspace"})
        r.raise_for_status()
        for item in r.json()["items"]:
            print(f"  {item['label']}: {item['value']}")


if __name__ == "__main__":
    main()
