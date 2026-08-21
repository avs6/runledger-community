"""
Example: identity-scoped governance queries.

Demonstrates how to filter governance surfaces by identity primitives:
- User governance summary
- Audit log filtered by access group
- Governance audit pack scoped to an API key
"""

from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ["RUNLEDGER_API_KEY"]
USER_ID = os.environ.get("RUNLEDGER_USER_ID", "")
ACCESS_GROUP_ID = os.environ.get("RUNLEDGER_ACCESS_GROUP_ID", "")
TARGET_API_KEY_ID = os.environ.get("RUNLEDGER_TARGET_API_KEY_ID", "")


def api_get(path: str) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 - local/dev example
        return json.loads(response.read())


def main() -> None:
    if USER_ID:
        print(f"\n--- User Governance Summary ({USER_ID}) ---")
        gov = api_get(f"/users/{USER_ID}/governance")
        print(f"  Approvals: {gov['approval_count']}")
        print(f"  Audit events: {gov['audit_event_count']}")
        for a in gov["recent_approvals"]:
            print(f"    {a['request_type']} -> {a['status']} ({a['created_at']})")

    if ACCESS_GROUP_ID:
        print(f"\n--- Audit Log (Access Group {ACCESS_GROUP_ID}) ---")
        events = api_get(f"/audit/events?access_group_id={ACCESS_GROUP_ID}&limit=5")
        print(f"  Total events: {events['total']}")
        for e in events["items"][:5]:
            print(f"    {e['action']} at {e['created_at']}")

        print(f"\n--- Approvals (Access Group {ACCESS_GROUP_ID}) ---")
        approvals = api_get(f"/approvals?access_group_id={ACCESS_GROUP_ID}&limit=5")
        print(f"  Total approvals: {approvals['total']}")
        for a in approvals["items"][:5]:
            print(f"    {a['request_type']} -> {a['status']} by {a.get('requested_by', 'unknown')}")

    if TARGET_API_KEY_ID:
        print(f"\n--- Governance Pack (API Key {TARGET_API_KEY_ID}) ---")
        pack = api_get(f"/governance/audit-pack?api_key_id={TARGET_API_KEY_ID}")
        s = pack["summary"]
        print(f"  Requests: {s['total_requests']}, Cost: ${s['total_cost_usd']}")
        print(f"  Policies enforced: {s['policies_enforced']}, Approvals: {s['approvals_processed']}")

    print("\n--- Cross-links ---")
    if USER_ID:
        print(f"  Approvals:  /approvals?requested_by=<email>")
        print(f"  Audit log:  /audit/events?actor_user_id={USER_ID}")
        print(f"  Gov pack:   /governance/audit-pack?user_id={USER_ID}")
    if ACCESS_GROUP_ID:
        print(f"  Approvals:  /approvals?access_group_id={ACCESS_GROUP_ID}")
        print(f"  Audit log:  /audit/events?access_group_id={ACCESS_GROUP_ID}")
        print(f"  Gov pack:   /governance/audit-pack?access_group_id={ACCESS_GROUP_ID}")


if __name__ == "__main__":
    main()
