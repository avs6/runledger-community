"""
Example 83 — User Analytics & Overview Org Links

Demonstrates the WU-011 posture endpoint that connects Analytics Users
to org and workspace context.

Usage:
    export RUNLEDGER_API_KEY="rl_test_..."
    python examples/83_user_analytics_org.py
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def main() -> None:
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        print("=== User Analytics Org Posture ===")
        r = c.get("/analytics/user-analytics-org-posture")
        r.raise_for_status()
        p = r.json()
        org = p["org_context"]
        usr = p["user_context"]
        ws = p["workspace_context"]
        print(f"  Org: {org['org_name']}  Workspaces: {org['workspace_count']}")
        print(f"  Workspace users: {org['workspace_users']}")
        print(f"  End users: {usr['active_end_users_30d']} active / {usr['total_end_users']} total")
        print(f"  API keys: {usr['active_api_keys']}/{usr['api_keys']}")
        print(f"  Telemetry batches 30d: {ws['telemetry_batches_30d']}")

        print("\n=== Top Spenders ===")
        r = c.get("/analytics/spend-by-user", params={"limit": 5})
        r.raise_for_status()
        for u in r.json()["items"]:
            print(f"  {u['end_user_id']}: ${float(u['cost_usd']):.4f} ({u['run_count']} runs)")


if __name__ == "__main__":
    main()
