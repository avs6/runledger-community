"""
examples/185_gateway_admin_safe_changes.py

Change a gateway route safely, then put a per-key tier on a workflow's key:

  1. Ask the role matrix what you may change (GET /gateway/role-matrix).
  2. Test request: dry-run an alias through route selection and see the chosen
     route, its estimated cost and its recent latency (POST /gateway/routes/preview).
  3. Preview a route change: the field diff a save would apply, without saving
     (POST /gateway/routes/{id}/preview-change).
  4. Save it in merge mode, so config keys you didn't send are kept.
  5. Put a budget tier on an API key: allowed models plus requests and tokens per
     minute, enforced by the gateway for that key.
  6. Read the audit trail those changes left.

Required env vars:
  RUNLEDGER_ADMIN_KEY      a dashboard session key of an org admin
                           (the "api_key" returned by POST /auth/login)
  RUNLEDGER_BASE_URL       control plane (default http://localhost:8201)
  RUNLEDGER_GATEWAY_ALIAS  an existing route alias (default "default")
Optional:
  RUNLEDGER_KEY_ID         a workload API key id to put on the tier
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
ALIAS = os.getenv("RUNLEDGER_GATEWAY_ALIAS", "default")
ADMIN_KEY = os.getenv("RUNLEDGER_ADMIN_KEY", "")
KEY_ID = os.getenv("RUNLEDGER_KEY_ID")


def main() -> int:
    if not ADMIN_KEY:
        print("Set RUNLEDGER_ADMIN_KEY (an org admin's dashboard session key).")
        return 1
    api = httpx.Client(
        base_url=BASE_URL, headers={"Authorization": f"Bearer {ADMIN_KEY}"}, timeout=30
    )

    # 1. What may I change?
    matrix = api.get("/gateway/role-matrix").json()
    print(f"caller level: {matrix['caller_level']}")
    if not matrix["capabilities"]["routes"]["write"]:
        print("This key can't change routes (org admin needed).")
        return 1

    # 2. Test request (dry run, no provider call).
    preview = api.post(
        "/gateway/routes/preview",
        json={
            "model": ALIAS,
            "prompt": "Summarise this ticket in two sentences.",
            "expected_output_tokens": 200,
        },
    ).json()
    print(
        f"'{ALIAS}' -> route {preview['selected_route_id']} ({preview['decision_reason']}), "
        f"est. ${preview['est_cost_usd']}, p50 {preview['p50_latency_ms']} ms"
    )
    route_id = preview["selected_route_id"]
    if route_id is None:
        print("No active route for this alias.")
        return 1

    # 3. Preview a change: add a context-window fallback.
    change = {
        "merge_configs": True,
        "fallback_config": {"fallbacks": [{"alias": f"{ALIAS}-long", "on": ["context_window"]}]},
    }
    diff = api.post(f"/gateway/routes/{route_id}/preview-change", json=change).json()
    for c in diff["changes"]:
        print(f"  {c['field']}: {json.dumps(c['before'])} -> {json.dumps(c['after'])}")
    for w in diff["warnings"]:
        print(f"  ! {w}")

    # 4. Save it (merge mode keeps the rest of fallback_config).
    saved = api.put(f"/gateway/routes/{route_id}", json=change)
    saved.raise_for_status()
    print("route saved")

    # 5. A per-key tier, enforced in the gateway preflight.
    tier = api.post(
        "/budget-tiers",
        json={
            "name": f"example-{uuid.uuid4().hex[:6]}",
            "rpm_limit": 60,
            "tpm_limit": 50_000,
            "allowed_models": [ALIAS],
        },
    ).json()
    print(f"tier {tier['name']}: 60 req/min, 50k tokens/min, models {tier['allowed_models']}")
    if KEY_ID:
        api.put(f"/budget-tiers/assign/{KEY_ID}", params={"tier_id": tier["id"]}).raise_for_status()
        print(
            f"assigned to key {KEY_ID}: other models now get 403, bursts get 429 with Retry-After"
        )

    # 6. The audit trail.
    for action in ("gateway_route.updated", "budget_tier.created"):
        events = api.get("/audit/events", params={"action": action, "limit": 1}).json()["items"]
        if events:
            print(f"audit: {events[0]['action']} at {events[0]['created_at']}")

    # Clean up the tier (soft delete: inactive, not default, unassigned).
    api.delete(f"/budget-tiers/{tier['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
