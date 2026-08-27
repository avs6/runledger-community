"""
examples/98_exception_workflows_org.py

Demonstrates exception workflows org & access scope bridge:

1. Fetch the exception workflows org posture (users, access groups, approvals, alerts)
2. List pending approvals
3. List active alert rules
4. Print a summary of org-scoped exception workflows

Requires RUNLEDGER_API_KEY.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=30)

    posture = check(
        client.get("/analytics/exception-workflows-org-posture"),
        "Exception workflows org posture",
    )
    print("=== Exception Workflows Org & Access Posture ===")
    oc = posture.get("org_context", {})
    uc = posture.get("user_context", {})
    agc = posture.get("access_group_context", {})
    akc = posture.get("api_key_context", {})
    apc = posture.get("approval_context", {})
    alc = posture.get("alert_context", {})
    mc = posture.get("mcp_context", {})
    print(f"  Organization:         {oc.get('org_name', '—')}")
    print(f"  Workspaces:           {oc.get('workspace_count', 0)}")
    print(f"  Users:                {uc.get('total_users', 0)}")
    print(f"  Access groups:        {agc.get('total_groups', 0)}")
    print(f"  Active API keys:      {akc.get('total_keys', 0)}")
    print(f"  Approvals:            {apc.get('total_approvals', 0)} ({apc.get('pending_approvals', 0)} pending)")
    print(f"    Last 30d:           {apc.get('approvals_30d', 0)}")
    print(f"  Alert rules:          {alc.get('total_alert_rules', 0)} ({alc.get('active_alert_rules', 0)} active)")
    print(f"    Firings (30d):      {alc.get('alert_firings_30d', 0)}")
    print(f"  MCP servers:          {mc.get('total_servers', 0)} ({mc.get('active_servers', 0)} active)")

    approvals = check(
        client.get("/approvals", params={"status": "pending", "limit": 10}),
        "Pending approvals",
    )
    items = approvals.get("items", [])
    print(f"\n=== Pending Approvals ({len(items)}) ===")
    for a in items[:10]:
        print(f"  {a.get('request_type', '—')} — {a.get('reason', '—')[:60]}")

    alerts = check(client.get("/alert-rules"), "Alert rules list")
    alert_items = alerts.get("items", [])
    active = [a for a in alert_items if a.get("is_active")]
    print(f"\n=== Active Alert Rules ({len(active)}/{len(alert_items)}) ===")
    for a in active[:10]:
        print(f"  {a['name']} — {a.get('metric', '—')} {a.get('operator', '—')} {a.get('threshold', '—')}")

    print("\nDone.")


if __name__ == "__main__":
    main()
