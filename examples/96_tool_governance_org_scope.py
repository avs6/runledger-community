"""
examples/96_tool_governance_org_scope.py

Demonstrates tool governance org & access scope bridge:

1. Fetch the tool governance org posture (users, access groups, API keys, policy scope)
2. List tool policies grouped by scope type
3. List access groups with tool-policy associations
4. Print a summary of scope-aware tool governance

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
        client.get("/analytics/tool-governance-org-posture"),
        "Tool governance org posture",
    )
    print("=== Tool Governance Org & Access Posture ===")
    oc = posture.get("org_context", {})
    uc = posture.get("user_context", {})
    agc = posture.get("access_group_context", {})
    akc = posture.get("api_key_context", {})
    rc = posture.get("registry_context", {})
    pc = posture.get("policy_context", {})
    mc = posture.get("mcp_context", {})
    print(f"  Organization:         {oc.get('org_name', '—')}")
    print(f"  Workspaces:           {oc.get('workspace_count', 0)}")
    print(f"  Users:                {uc.get('total_users', 0)}")
    print(f"  Access groups:        {agc.get('total_groups', 0)}")
    print(f"    w/ tool policies:   {agc.get('tool_policy_groups', 0)}")
    print(f"  Active API keys:      {akc.get('total_keys', 0)}")
    print(f"  Registry entries:     {rc.get('total_entries', 0)} ({rc.get('active_entries', 0)} enforced)")
    print(f"  Tool policies:        {pc.get('total_policies', 0)} ({pc.get('active_policies', 0)} active)")
    print(f"    Org scope:          {pc.get('org_scope', 0)}")
    print(f"    Workspace scope:    {pc.get('workspace_scope', 0)}")
    print(f"    Access group scope: {pc.get('access_group_scope', 0)}")
    print(f"  MCP servers:          {mc.get('total_servers', 0)} ({mc.get('active_servers', 0)} active)")

    policies = check(
        client.get("/tool-policies", params={"include_inactive": True}),
        "Tool policies list",
    )
    items = policies.get("items", [])
    print(f"\n=== Tool Policies by Scope ({len(items)}) ===")
    by_scope: dict[str, list[dict]] = {}
    for p in items:
        scope = p.get("scope_type", "workspace")
        by_scope.setdefault(scope, []).append(p)
    for scope, pols in sorted(by_scope.items()):
        print(f"  [{scope}] ({len(pols)} policies)")
        for p in pols[:5]:
            status = "active" if p.get("is_active") else "inactive"
            print(f"    {p['name']} — tool={p['tool_name']} action={p['action']} [{status}]")

    groups = check(client.get("/access-groups"), "Access groups list")
    group_items = groups.get("items", [])
    print(f"\n=== Access Groups ({len(group_items)}) ===")
    for g in group_items[:10]:
        print(f"  {g['name']} — {g.get('member_count', 0)} members")

    print("\nDone.")


if __name__ == "__main__":
    main()
