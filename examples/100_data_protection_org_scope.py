"""
examples/100_data_protection_org_scope.py

Demonstrates data protection org & access scope bridge:

1. Fetch the data protection org posture (users, capture policies, security events, tags)
2. List capture policy scopes
3. List active tags
4. Print a summary of org-scoped data protection

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
        client.get("/analytics/data-protection-org-posture"),
        "Data protection org posture",
    )
    print("=== Data Protection Org & Access Posture ===")
    oc = posture.get("org_context", {})
    uc = posture.get("user_context", {})
    agc = posture.get("access_group_context", {})
    akc = posture.get("api_key_context", {})
    cc = posture.get("capture_context", {})
    sc = posture.get("security_context", {})
    tc = posture.get("tag_context", {})
    mc = posture.get("mcp_context", {})
    print(f"  Organization:         {oc.get('org_name', '—')}")
    print(f"  Workspaces:           {oc.get('workspace_count', 0)}")
    print(f"  Users:                {uc.get('total_users', 0)}")
    print(f"  Access groups:        {agc.get('total_groups', 0)}")
    print(f"  Active API keys:      {akc.get('total_keys', 0)}")
    print(f"  Capture policies:     {cc.get('total_policies', 0)} ({cc.get('active_policies', 0)} active)")
    print(f"  Security events (30d):{sc.get('security_events_30d', 0)}")
    print(f"  Tags:                 {tc.get('total_tags', 0)} ({tc.get('active_tags', 0)} active)")
    print(f"  MCP servers:          {mc.get('total_servers', 0)} ({mc.get('active_servers', 0)} active)")

    scopes = check(client.get("/capture-policy/scopes"), "Capture policy scopes")
    scope_items = scopes.get("items", [])
    print(f"\n=== Capture Policy Scopes ({len(scope_items)}) ===")
    for s in scope_items[:10]:
        print(f"  [{s.get('scope_type', '—')}] {s.get('scope_id', '—')} — "
              f"mode={s.get('privacy_mode', '—')}")

    tags = check(client.get("/tags"), "Tags list")
    tag_items = tags.get("items", [])
    active = [t for t in tag_items if t.get("is_active")]
    print(f"\n=== Active Tags ({len(active)}/{len(tag_items)}) ===")
    for t in active[:10]:
        print(f"  {t['key']}={t.get('value', '—')} — {t.get('description', '')[:50]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
