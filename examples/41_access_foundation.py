"""
examples/41_access_foundation.py

Exercise the core access-management flow with a dashboard session key:
  1. create a user
  2. create a workspace
  3. add the user to the workspace
  4. create an access group and assign the user
  5. create, update, rotate, and revoke an API key

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
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
                json={
                    "email": email,
                    "full_name": "Foundation User",
                    "temporary_password": "ChangeMe123!",
                    "skip_verification": True,
                },
            ),
            "create user",
        )
        print(f"[ok] created user {user['email']}")

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

        group = expect_ok(
            client.post(
                "/access-groups",
                json={
                    "name": group_name,
                    "description": "Foundation smoke group",
                    "budget_usd": 50,
                    "budget_period": "monthly",
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

        created_key = expect_ok(
            client.post(
                "/settings/api-keys",
                json={
                    "name": "Foundation key",
                    "workspace_id": workspace["id"],
                    "ownership_type": "service_account",
                    "owner_reference": "foundation-smoke",
                    "scopes": [],
                },
            ),
            "create api key",
        )
        print(f"[ok] created api key {created_key['key_prefix']}")

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
