"""
examples/12_settings.py — Phase 12: Settings Console

Demonstrates:
  1. POST /settings/api-keys      → create key, print prefix + raw key
  2. GET  /settings/api-keys      → list active keys
  3. DELETE /settings/api-keys    → revoke key
  4. GET  /providers/pricing      → list all pricing (global + workspace)
  5. POST /providers/pricing      → add workspace override
  6. DELETE /providers/pricing    → remove workspace override

Usage:
  export RUNLEDGER_API_KEY=rl_test_...
  export RUNLEDGER_BASE_URL=http://localhost:8000   # optional
  python examples/12_settings.py
"""

from __future__ import annotations

import os
import sys

import httpx

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

        # ── 1. Create API key ──────────────────────────────────────────────────
        print("\n[1] Creating API key…")
        body = {"name": "Example key", "environment": "dev", "scopes": []}
        resp = client.post("/settings/api-keys", json=body)
        created = _check(resp, "create api-key")
        print(f"  Created: prefix={created['key_prefix']}  id={created['id']}")
        print(f"  Raw key (save now — shown once): {created['key']}")
        new_key_id: str = created["id"]

        # ── 2. List API keys ───────────────────────────────────────────────────
        print("\n[2] Listing API keys…")
        resp = client.get("/settings/api-keys")
        keys = _check(resp, "list api-keys")
        for k in keys:
            print(f"  {k['key_prefix']}…  name={k['name']}  id={k['id']}")

        # ── 3. Revoke the key ──────────────────────────────────────────────────
        print(f"\n[3] Revoking key {new_key_id}…")
        resp = client.delete(f"/settings/api-keys/{new_key_id}")
        _check(resp, "revoke api-key")
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
