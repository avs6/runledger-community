"""
Example 88 — Request Analysis Scope and Evidence Refresh

Demonstrates the posture endpoints used by Request Flow and Request Explorer
to surface approvals, data capture, and governance scope context.
"""

import os
import httpx

BASE = os.getenv("RUNLEDGER_API_URL", "http://localhost:8000")
KEY = os.getenv("RUNLEDGER_API_KEY", "rl_test_key")
HEADERS = {"Authorization": f"Bearer {KEY}"}


def get_overview_scope_posture():
    r = httpx.get(f"{BASE}/analytics/overview-scope-posture", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    tc = data["tool_context"]
    print(f"Pending approvals:  {tc['pending_approvals']}")
    print(f"Capture policies:   {tc['capture_policies']}")
    print(f"Tool policies:      {tc['tool_policies']} ({tc['active_tool_policies']} active)")
    print(f"Tool registry:      {tc['tool_registry_entries']} entries")
    return data


def get_investigation_governance_posture():
    r = httpx.get(f"{BASE}/analytics/investigation-governance-posture", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    print(f"Filtered runs:      {data['filtered_runs']}")
    print(f"Security events:    {data['security']['events']}")
    print(f"Governance audits:  {data['audit_log']['governance_events']}")
    return data


def get_request_explorer(q=None):
    params = {"page_size": 5}
    if q:
        params["q"] = q
    r = httpx.get(f"{BASE}/runs/explorer", headers=HEADERS, params=params)
    r.raise_for_status()
    data = r.json()
    print(f"Total requests:     {data['total']}")
    for item in data["items"][:3]:
        print(f"  {item['run_id'][:12]}  {item['model']}  {item['cost_usd']}")
    return data


if __name__ == "__main__":
    print("=== Overview Scope Posture (approvals + capture) ===")
    get_overview_scope_posture()
    print()

    print("=== Investigation Governance Posture ===")
    get_investigation_governance_posture()
    print()

    print("=== Request Explorer (first 5) ===")
    get_request_explorer()
