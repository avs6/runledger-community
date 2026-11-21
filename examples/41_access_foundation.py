"""
examples/41_access_foundation.py

Exercise the core access-management flow with a dashboard session key
(an org admin's key from signing in):
  1. create a user (RunLedger generates a temporary password, shown once)
  2. create a workspace and add the user to it
  3. add the user to the current workspace, create an access group, assign the user,
     and attach a budget policy scoped to the group
  4. create (with expiry), update, rotate, and revoke an API key
  5. sign the user out everywhere

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")

if not SESSION_KEY:
    print("Error: RUNLEDGER_SESSION_KEY not set", file=sys.stderr)
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"Bearer {SESSION_KEY}",
    "Content-Type": "application/json",
}


def expect_ok(resp: httpx.Response, label: str, allowed: tuple[int, ...] = (200, 201, 204)) -> dict:
    if resp.status_code not in allowed:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"foundation-{suffix}@example.com"
    workspace_name = f"Foundation Workspace {suffix}"
    group_name = f"Foundation Group {suffix}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        user = expect_ok(
            client.post(
                "/users",
                # No password: one is generated and returned once; the user must
                # change it at first sign-in.
                json={"email": email, "full_name": "Foundation User", "skip_verification": True},
            ),
            "create user",
        )
        print(
            f"[ok] created user {user['email']} (must_change_password={user['must_change_password']})"
        )
        current = expect_ok(client.get("/auth/me"), "current session")

        workspace = expect_ok(
            client.post("/org/workspaces", json={"name": workspace_name}),
            "create workspace",
        )
        print(f"[ok] created workspace {workspace['name']}")

        expect_ok(
            client.post(
                f"/org/workspaces/{workspace['id']}/members",
                json={"user_id": user["id"], "role": "member"},
            ),
            "add workspace member",
        )
        print("[ok] added user to workspace")

        # Access-group members must have access to the group's workspace.
        expect_ok(
            client.post(
                f"/org/workspaces/{current['workspace_id']}/members",
                json={"user_id": user["id"], "role": "member"},
            ),
            "add current-workspace member",
        )

        group = expect_ok(
            client.post(
                "/access-groups",
                json={
                    "name": group_name,
                    "description": "Foundation smoke group",
                    "guardrail_profile": "default",
                },
            ),
            "create access group",
        )
        print(f"[ok] created access group {group['name']}")

        expect_ok(
            client.post(
                f"/access-groups/{group['id']}/members",
                json={"user_id": user["id"]},
            ),
            "add access group member",
        )
        print("[ok] assigned user to access group")

        # Group spend limits are ordinary budget policies scoped to the group.
        budget = expect_ok(
            client.post(
                "/budgets",
                json={
                    "scope_type": "access_group",
                    "scope_id": group["id"],
                    "period_type": "monthly",
                    "limit_usd": "50.00",
                    "action": "notify",
                },
            ),
            "create access-group budget",
        )
        print(f"[ok] created access-group budget {budget['id']}")

        created_key = expect_ok(
            client.post(
                "/settings/api-keys",
                json={
                    "name": "Foundation key",
                    "workspace_id": workspace["id"],
                    "ownership_type": "service_account",
                    "owner_reference": "foundation-smoke",
                    # Only what an SDK integration needs. [] would mean full access.
                    "scopes": ["read", "ingest"],
                    "expires_at": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
                },
            ),
            "create api key",
        )
        print(
            f"[ok] created api key {created_key['key_prefix']} scopes={created_key['scopes']} "
            f"(expires {created_key['expires_at']})"
        )

        # The scoped key can ingest telemetry but cannot change workspace content.
        scoped = {"Authorization": f"Bearer {created_key['key']}"}
        ingest = httpx.post(
            f"{BASE_URL}/ingest/v1/batch", headers=scoped, json={"events": []}, timeout=20
        )
        write = httpx.post(
            f"{BASE_URL}/prompts", headers=scoped, json={"name": f"x-{suffix}"}, timeout=20
        )
        print(
            f"[ok] scoped key: ingest -> {ingest.status_code}, create prompt -> {write.status_code} (403 expected)"
        )

        updated_key = expect_ok(
            client.put(
                f"/settings/api-keys/{created_key['id']}",
                json={
                    "name": "Foundation key updated",
                    "ownership_type": "agent",
                    "owner_reference": "foundation-agent",
                },
            ),
            "update api key",
        )
        print(f"[ok] updated api key metadata to {updated_key['ownership_type']}")

        rotated = expect_ok(
            client.post(
                f"/security/api-keys/{created_key['id']}/rotate",
                json={"grace_hours": 1},
            ),
            "rotate api key",
        )
        print(f"[ok] rotated api key to {rotated['key_prefix']}")

        expect_ok(
            client.delete(f"/settings/api-keys/{rotated['key_id']}"),
            "revoke api key",
        )
        print("[ok] revoked rotated api key")

        footprint = expect_ok(
            client.get(f"/analytics/api-key-footprint/{created_key['id']}"),
            "api key observe footprint",
        )
        print(
            f"[ok] api key footprint: {footprint['run_count']} runs, ${footprint['total_cost_usd']:.4f}"
        )

        posture = expect_ok(
            client.get("/analytics/workspace-observe-posture"),
            "workspace observe posture",
        )
        print(
            f"[ok] workspace posture: {posture['run_count']} runs, {posture['model_count']} models"
        )

        gov_posture = expect_ok(
            client.get("/analytics/workspace-governance-posture"),
            "workspace governance posture",
        )
        print(
            f"[ok] governance posture: {gov_posture['tool_policy_count']} policies, {gov_posture['approval_count']} approvals, {gov_posture['audit_event_count']} audit events"
        )

        scoped_runs = expect_ok(
            client.get(f"/runs?api_key_id={created_key['id']}&limit=5"),
            "api-key-scoped runs",
        )
        print(f"[ok] api-key-scoped runs: {len(scoped_runs['items'])}")

        ag_gateway = expect_ok(
            client.get(f"/analytics/access-group-gateway-posture?access_group_id={group['id']}"),
            "access group gateway posture",
        )
        print(
            f"[ok] access group gateway: {ag_gateway['active_route_count']} active routes, {ag_gateway['active_guardrail_count']} active guardrails, profile={ag_gateway['guardrail_profile']}"
        )

        ak_gateway = expect_ok(
            client.get(f"/analytics/api-key-gateway-posture?api_key_id={created_key['id']}"),
            "api key gateway posture",
        )
        print(
            f"[ok] api key gateway: {ak_gateway['active_route_count']} active routes, {ak_gateway['distinct_providers']} providers, {ak_gateway['active_guardrail_count']} active guardrails"
        )

        tel_downstream = expect_ok(
            client.get("/analytics/telemetry-downstream-posture"),
            "telemetry downstream posture",
        )
        print(
            f"[ok] telemetry downstream: finops budgets={tel_downstream['finops']['budget_count']}, safety alerts={tel_downstream['safety']['active_alert_count']}"
        )

        mcp_posture = expect_ok(
            client.get("/analytics/mcp-registry-posture"),
            "mcp registry posture",
        )
        print(
            f"[ok] mcp registry: {mcp_posture['active_server_count']} active servers, {mcp_posture['tool_call_count_30d']} calls 30d, gateway routes={mcp_posture['gateway']['route_count']}"
        )

        hub_posture = expect_ok(
            client.get("/analytics/ai-hub-runtime-posture"),
            "ai hub runtime posture",
        )
        print(
            f"[ok] ai hub runtime: {hub_posture['model_count']} models, {hub_posture['observe']['run_count_30d']} runs 30d, finops budgets={hub_posture['finops']['budget_count']}"
        )

        expect_ok(client.post(f"/users/{user['id']}/sessions/revoke"), "revoke user sessions")
        print("[ok] signed the user out everywhere")

        expect_ok(client.delete(f"/budgets/{budget['id']}"), "delete budget")
        print("[ok] removed the access-group budget")

        expect_ok(
            client.delete(f"/access-groups/{group['id']}/members/{user['id']}"),
            "remove access group member",
        )
        expect_ok(client.delete(f"/access-groups/{group['id']}"), "deactivate access group")
        expect_ok(
            client.delete(f"/org/workspaces/{workspace['id']}/members/{user['id']}"),
            "remove workspace member",
        )
        expect_ok(client.delete(f"/org/members/{user['id']}"), "remove org member")
        expect_ok(client.delete(f"/org/workspaces/{workspace['id']}"), "delete workspace")
        print("[ok] cleaned up created entities")

    print("[done] Access foundation example completed")


if __name__ == "__main__":
    main()
