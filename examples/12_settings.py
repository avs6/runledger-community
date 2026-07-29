"""
examples/12_settings.py — Phase 12: Settings Console

Demonstrates:
  1. POST /settings/api-keys      → create key (ORG-ADMIN session only)
  2. GET  /settings/api-keys      → list keys across the org (with workspace)
  3. DELETE /settings/api-keys    → revoke key (org-admin only)
  4. GET  /providers/pricing      → list all pricing (global + workspace)
  5. POST /providers/pricing      → add workspace override
  6. DELETE /providers/pricing    → remove workspace override

NOTE — API-key management is now an **org-admin** function performed by a logged-in
user (a dashboard session), not by a bare API key. Running steps 1–3 with a plain
RUNLEDGER_API_KEY returns 401/403; this script detects that and skips them. To mint
keys programmatically, use POST /admin/workspaces/{id}/api-keys with the
X-Admin-Secret header instead.

Install
───────
    pip install httpx python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    python 12_settings.py

Key .env variables used here:
    RUNLEDGER_API_KEY   — your workspace API key
    RUNLEDGER_BASE_URL  — http://localhost:8000  (local Docker stack)
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


def _check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"  ERROR {label}: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:

        # ── 1–3. API keys (org-admin session only) ─────────────────────────────
        # A plain API key can't manage keys anymore, so probe first and skip if gated.
        print("\n[1] Creating API key…")
        resp = client.post("/settings/api-keys", json={"name": "Example key", "scopes": []})
        if resp.status_code in (401, 403):
            print("  Skipped — key management requires an org-admin dashboard session.")
            print("  Create keys in the dashboard (Settings → API Keys), or for automation")
            print("  use POST /admin/workspaces/{id}/api-keys with the X-Admin-Secret header.")
        else:
            created = _check(resp, "create api-key")
            print(f"  Created: prefix={created['key_prefix']}  workspace={created.get('workspace_name')}")
            print(f"  Raw key (save now — shown once): {created['key']}")
            new_key_id: str = created["id"]

            print("\n[2] Listing API keys (org-wide)…")
            keys = _check(client.get("/settings/api-keys"), "list api-keys")
            for k in keys:
                print(f"  {k['key_prefix']}…  name={k['name']}  workspace={k.get('workspace_name')}")

            print(f"\n[3] Revoking key {new_key_id}…")
            _check(client.delete(f"/settings/api-keys/{new_key_id}"), "revoke api-key")
            print("  Revoked.")

        # ── 4. List provider pricing ───────────────────────────────────────────
        print("\n[4] Listing provider pricing (global + workspace)…")
        resp = client.get("/providers/pricing")
        plist = _check(resp, "list pricing")
        for p in plist.get("items", []):
            scope = "workspace" if p["workspace_id"] else "global"
            print(
                f"  [{scope}] {p['provider']}/{p['model']}  "
                f"in=${p['input_cost_per_1m']} out=${p['output_cost_per_1m']}"
            )

        # ── 5. Add workspace pricing override ─────────────────────────────────
        print("\n[5] Adding workspace pricing override…")
        pricing_body = {
            "provider": "openai",
            "model": "gpt-4o-custom-negotiated",
            "input_cost_per_1m": "1.80",
            "output_cost_per_1m": "7.20",
            "cached_input_cost_per_1m": "0.90",
        }
        resp = client.post("/providers/pricing", json=pricing_body)
        created_pricing = _check(resp, "create pricing")
        print(
            f"  Created: {created_pricing['provider']}/{created_pricing['model']}  "
            f"id={created_pricing['id']}"
        )
        pricing_id: str = created_pricing["id"]

        # ── 6. Delete workspace pricing override ───────────────────────────────
        print(f"\n[6] Deleting pricing override {pricing_id}…")
        resp = client.delete(f"/providers/pricing/{pricing_id}")
        _check(resp, "delete pricing")
        print("  Deleted.")

        print("\nDone.")


if __name__ == "__main__":
    main()
