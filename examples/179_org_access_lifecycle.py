"""
examples/179_org_access_lifecycle.py

The org membership and session lifecycle, end to end:

  1. An org admin invites a new teammate. RunLedger creates the account with a
     generated temporary password (shown once) that must be changed at first sign-in.
  2. The teammate signs in, sets their own password, and lists their sessions.
  3. The admin suspends the teammate. Their live session stops working immediately.
  4. The admin reactivates them, then removes them from the org.

Inviting an email that already has an account works differently: it creates a
pending invitation that the person accepts with
POST /org/invitations/{tenant_id}/accept. The inviting org can never change that
account's password.

Required env vars:
  RUNLEDGER_BASE_URL     (default http://localhost:8201)
  RUNLEDGER_SESSION_KEY  an org admin's dashboard session key
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201")
ADMIN_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")


def call(method: str, path: str, key: str | None = None, body: dict | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    return httpx.request(method, f"{BASE_URL}{path}", headers=headers, json=body, timeout=20)


def ok(resp: httpx.Response, label: str) -> dict:
    if resp.status_code >= 400:
        raise SystemExit(f"{label} failed: {resp.status_code} {resp.text}")
    print(f"[ok] {label}")
    return resp.json() if resp.content else {}


def main() -> None:
    if not ADMIN_KEY:
        print("Error: RUNLEDGER_SESSION_KEY not set", file=sys.stderr)
        raise SystemExit(1)

    email = f"teammate-{uuid.uuid4().hex[:8]}@example.com"
    new_password = f"teammate-{uuid.uuid4().hex[:6]}-pass1"

    # 1. Invite a brand-new email (skip_verification: no SMTP in local setups).
    member = ok(
        call(
            "POST",
            "/org/members/invite",
            ADMIN_KEY,
            {"email": email, "role": "org_member", "skip_verification": True},
        ),
        f"invite {email}",
    )
    temp_password = member["temporary_password"]
    print(f"     status={member['status']}; temporary password returned once")

    # 2. First sign-in: forced password change.
    login = ok(call("POST", "/auth/login", body={"email": email, "password": temp_password}), "sign in")
    user_key = login["api_key"]
    print(f"     must_change_password={login['must_change_password']}")
    ok(
        call("PUT", "/users/me", user_key, {"current_password": temp_password, "password": new_password}),
        "set own password",
    )
    sessions = ok(call("GET", "/auth/sessions", user_key), "list my sessions")
    print(f"     {len(sessions)} live session(s)")

    # 3. Suspension takes effect on the next request.
    user_id = member["user_id"]
    ok(call("PUT", f"/org/members/{user_id}/status", ADMIN_KEY, {"status": "suspended"}), "suspend")
    print(f"     teammate's session now returns {call('GET', '/auth/me', user_key).status_code}")

    # 4. Reactivate, then remove (removal also revokes sessions).
    ok(call("PUT", f"/org/members/{user_id}/status", ADMIN_KEY, {"status": "active"}), "reactivate")
    resp = call("DELETE", f"/org/members/{user_id}", ADMIN_KEY)
    if resp.status_code != 204:
        raise SystemExit(f"remove failed: {resp.status_code} {resp.text}")
    print("[ok] removed from org")

    audit = ok(call("GET", "/org/audit-log?limit=20", ADMIN_KEY), "read org audit log")
    for row in audit[:6]:
        print(f"     {row['created_at']}  {row['action']}")


if __name__ == "__main__":
    main()
