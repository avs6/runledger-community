#!/usr/bin/env python3
"""End-to-end verification of Org & Access controls against a running API.

Replays the org lifecycle a real operator goes through and asserts every control:

  1. Platform admin creates two orgs; org admins get generated temporary passwords
     and ``must_change_password``.
  2. Self-service password change requires the current password and enforces policy.
  3. Inviting a brand-new email creates an account (temporary password, active).
  4. Inviting an account that belongs to another org creates a *pending* invitation
     that grants no access until accepted, and never lets the inviting org change
     the account's password or flags (cross-tenant takeover guard).
  5. The invitee accepts from their own session; identity edits stay forbidden
     because the account is shared between orgs.
  6. Removing a member revokes their live sessions immediately.
  7. Sign-out revokes the session key.
  8. Workspace roles are enforced: a viewer can read but not write (403), an editor can
     create content but not governance config.
  9. API key scopes are enforced: unknown scopes are rejected, a read key cannot write or
     ingest, an ingest key cannot read, and an unscoped key keeps full access.
 10. Backups and the global pricing import are platform-admin only, and ingest from one
     org cannot change another org's run.
 11. Unauthenticated surfaces stay closed (analytics posture, removed unsigned ingest).
 12. Repeated failed sign-ins for one account are throttled (429).

Both orgs are deleted at the end (pass --keep to inspect them in the UI).

Usage:
    python scripts/run_demo.py verify-org-access
    python scripts/core/verify_org_access.py --base-url http://localhost:8201 \\
        --admin-email admin@runledger.local --admin-password runledger
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSWORD = "verify-org-access-1"


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passed = 0

    def __call__(self, ok: bool, label: str, detail: Any = "") -> None:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {detail}")


class Api:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=30)

    def call(
        self, method: str, path: str, key: str | None = None, body: dict[str, Any] | None = None
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.http.request(method, path, headers=headers, json=body)

    def login(self, email: str, password: str) -> httpx.Response:
        return self.call("POST", "/auth/login", body={"email": email, "password": password})


def _create_org(api: Api, platform_key: str, name: str, admin_email: str) -> dict[str, Any]:
    resp = api.call(
        "POST",
        "/org/tenants",
        platform_key,
        {"name": name, "admin_email": admin_email, "skip_verification": True},
    )
    resp.raise_for_status()
    return resp.json()


class _Abort(Exception):
    """A step failed in a way later steps depend on; skip to the summary and cleanup."""


def _first_sign_in(api: Api, check: Check, email: str, temp_password: str) -> str:
    """Sign in with a temporary password and set the real one; returns a session key."""
    login = api.login(email, temp_password)
    check(login.status_code == 200, f"{email} signs in with the temporary password", login.text)
    if login.status_code != 200:
        raise _Abort
    data = login.json()
    check(data.get("must_change_password") is True, f"{email} must change the password")
    key = data["api_key"]
    weak = api.call(
        "PUT", "/users/me", key, {"current_password": temp_password, "password": "short"}
    )
    check(weak.status_code == 422, "weak password rejected by policy", weak.status_code)
    wrong = api.call("PUT", "/users/me", key, {"current_password": "nope", "password": PASSWORD})
    check(wrong.status_code == 403, "password change without the current password refused")
    ok = api.call(
        "PUT", "/users/me", key, {"current_password": temp_password, "password": PASSWORD}
    )
    check(ok.status_code == 200, "password changed", ok.text)
    me = api.call("GET", "/auth/me", key).json()
    check(me.get("must_change_password") is False, "forced-change flag cleared")
    return key


def run(args: argparse.Namespace) -> int:
    api = Api(args.base_url)
    check = Check()
    suffix = uuid.uuid4().hex[:8]
    org_a_name, org_b_name = f"Verify Org A {suffix}", f"Verify Org B {suffix}"
    admin_a, admin_b = f"admin-a-{suffix}@verify.test", f"admin-b-{suffix}@verify.test"
    new_user = f"member-{suffix}@verify.test"

    login = api.login(args.admin_email, args.admin_password)
    if login.status_code != 200:
        print(f"Platform admin sign-in failed ({login.status_code}): {login.text}")
        return 2
    platform_key = login.json()["api_key"]
    created: list[dict[str, Any]] = []

    try:
        print("\n→ org creation and first sign-in")
        org_a = _create_org(api, platform_key, org_a_name, admin_a)
        org_b = _create_org(api, platform_key, org_b_name, admin_b)
        created += [org_a, org_b]
        check(bool(org_a.get("temporary_password")), "org admin password generated (no default)")
        key_a = _first_sign_in(api, check, admin_a, org_a["temporary_password"])
        key_b = _first_sign_in(api, check, admin_b, org_b["temporary_password"])

        print("\n→ inviting a brand-new email")
        weak = api.call(
            "POST",
            "/org/members/invite",
            key_a,
            {"email": new_user, "temporary_password": "weak", "skip_verification": True},
        )
        check(weak.status_code == 422, "weak temporary password rejected", weak.status_code)
        invited = api.call(
            "POST", "/org/members/invite", key_a, {"email": new_user, "skip_verification": True}
        )
        check(invited.status_code == 201, "new account created", invited.text)
        member = invited.json()
        check(member.get("status") == "active", "new account membership is active")
        check(bool(member.get("temporary_password")), "temporary password returned once")
        # Org membership alone grants no workspace: sign-in needs a workspace membership.
        early = api.login(new_user, member["temporary_password"])
        check(early.status_code == 403, "org member without a workspace cannot sign in yet")
        added = api.call(
            "POST", "/users/invite", key_a, {"email": new_user, "role": "workspace_editor"}
        )
        check(added.status_code == 201, "member added to the workspace", added.text)
        member_key = _first_sign_in(api, check, new_user, member["temporary_password"])

        print("\n→ inviting an account owned by another org")
        cross = api.call("POST", "/org/members/invite", key_a, {"email": admin_b})
        check(cross.status_code == 201, "invitation recorded", cross.text)
        check(cross.json().get("status") == "invited", "membership is pending (invited)")
        check(cross.json().get("temporary_password") is None, "no password set on existing account")
        admin_b_id = cross.json()["user_id"]
        takeover = api.call("PUT", f"/users/{admin_b_id}", key_a, {"password": "attacker-pass-123"})
        check(
            takeover.status_code == 403,
            "org A cannot reset org B admin's password",
            takeover.status_code,
        )
        still_ok = api.login(admin_b, PASSWORD)
        check(still_ok.status_code == 200, "org B admin password unchanged")

        print("\n→ accepting the invitation")
        pending = api.call("GET", "/org/invitations", key_b).json()
        tenant_a_id = org_a["id"]
        check(
            any(i["tenant_id"] == tenant_a_id for i in pending), "invitee sees the pending invite"
        )
        accepted = api.call("POST", f"/org/invitations/{tenant_a_id}/accept", key_b)
        check(
            accepted.status_code == 200 and accepted.json().get("status") == "active",
            "invite accepted",
        )
        deactivate = api.call("PUT", f"/users/{admin_b_id}", key_a, {"is_active": False})
        check(
            deactivate.status_code == 403,
            "shared identity still not editable by org A",
            deactivate.status_code,
        )

        print("\n→ removing a member revokes their sessions")
        check(api.call("GET", "/auth/me", member_key).status_code == 200, "member session works")
        member_id = member["user_id"]
        removed = api.call("DELETE", f"/org/members/{member_id}", key_a)
        check(removed.status_code == 204, "member removed", removed.text)
        after = api.call("GET", "/auth/me", member_key)
        check(after.status_code == 401, "removed member's session rejected", after.status_code)

        print("\n→ sign-out")
        out = api.call("POST", "/auth/logout", key_b)
        check(out.status_code == 204, "logout accepted")
        check(api.call("GET", "/auth/me", key_b).status_code == 401, "signed-out key rejected")

        print("\n→ audit trail")
        audit = api.call("GET", "/org/audit-log?limit=100", key_a)
        actions = {row.get("action") for row in audit.json()} if audit.status_code == 200 else set()
        for action in ("org.member.created", "org.member.invited", "org.member.removed"):
            check(action in actions, f"audit event {action}", sorted(a for a in actions if a))

        print("\n→ workspace roles: viewer is read-only, editor can write")
        role_keys: dict[str, str] = {}
        for role in ("viewer", "workspace_editor"):
            email = f"{role}-{suffix}@verify.test"
            added = api.call(
                "POST",
                "/users/invite",
                key_a,
                {"email": email, "role": role, "skip_verification": True},
            )
            check(added.status_code == 201, f"{role} added to workspace", added.text)
            if added.status_code == 201:
                role_keys[role] = _first_sign_in(
                    api, check, email, added.json()["temporary_password"]
                )
        if "viewer" in role_keys:
            viewer = role_keys["viewer"]
            check(api.call("GET", "/prompts", viewer).status_code == 200, "viewer can read prompts")
            denied = api.call("POST", "/prompts", viewer, {"name": f"viewer-{suffix}"})
            check(denied.status_code == 403, "viewer cannot create a prompt", denied.status_code)
            denied = api.call("POST", "/agents", viewer, {"name": f"viewer-agent-{suffix}"})
            check(denied.status_code == 403, "viewer cannot register an agent", denied.status_code)
        if "workspace_editor" in role_keys:
            prompt = api.call(
                "POST", "/prompts", role_keys["workspace_editor"], {"name": f"editor-{suffix}"}
            )
            check(prompt.status_code == 201, "editor can create a prompt", prompt.text)
            guard = api.call(
                "POST",
                "/guardrails",
                role_keys["workspace_editor"],
                {"name": f"editor-guard-{suffix}", "mode": "pre_call", "rule_type": "custom"},
            )
            check(guard.status_code == 403, "editor cannot create guardrails (admin only)")

        print("\n→ API key scopes")
        bad = api.call("POST", "/settings/api-keys", key_a, {"name": "bad", "scopes": ["root"]})
        check(bad.status_code == 422, "unknown scope rejected", bad.status_code)
        scoped: dict[str, str] = {}
        for label, scopes in (("read", ["read"]), ("ingest", ["ingest"]), ("full", [])):
            made = api.call(
                "POST",
                "/settings/api-keys",
                key_a,
                {"name": f"verify-{label}-{suffix}", "scopes": scopes},
            )
            check(made.status_code in (200, 201), f"{label} key created", made.text)
            if made.status_code in (200, 201):
                check(made.json().get("scopes") == scopes, f"{label} key stores its scopes")
                scoped[label] = made.json()["key"]
        if "read" in scoped:
            check(api.call("GET", "/prompts", scoped["read"]).status_code == 200, "read key reads")
            denied = api.call("POST", "/prompts", scoped["read"], {"name": f"ro-{suffix}"})
            check(denied.status_code == 403, "read key cannot write", denied.status_code)
            denied = api.call("POST", "/ingest/v1/batch", scoped["read"], {"events": []})
            check(denied.status_code == 403, "read key cannot ingest", denied.status_code)
        if "ingest" in scoped:
            sent = api.call("POST", "/ingest/v1/batch", scoped["ingest"], {"events": []})
            check(sent.status_code == 202, "ingest key ingests", sent.status_code)
            denied = api.call("GET", "/prompts", scoped["ingest"])
            check(denied.status_code == 403, "ingest key cannot read", denied.status_code)
        if "full" in scoped:
            made = api.call("POST", "/prompts", scoped["full"], {"name": f"full-{suffix}"})
            check(made.status_code == 201, "unscoped key keeps full access", made.status_code)

        print("\n→ installation-wide controls are platform-admin only")
        backups = api.call("GET", "/settings/backups/config", key_a)
        check(
            backups.status_code == 403, "org admin cannot read backup config", backups.status_code
        )
        run_backup = api.call("POST", "/settings/backups/run", key_a)
        check(
            run_backup.status_code == 403, "org admin cannot run a backup", run_backup.status_code
        )
        pricing = api.http.post(
            "/providers/pricing/import",
            headers={"Authorization": f"Bearer {key_a}"},
            files={"file": ("p.yml", b"models: []\n", "text/yaml")},
        )
        check(
            pricing.status_code == 403,
            "org admin cannot import global pricing",
            pricing.status_code,
        )

        print("\n→ ingest cannot touch another org's runs")
        if "full" in scoped:
            run_id = str(uuid.uuid4())
            now = "2026-01-01T00:00:00Z"
            start = {"event_type": "run_start", "run_id": run_id, "started_at": now}
            api.call("POST", "/ingest/v1/batch", scoped["full"], {"events": [start]})
            relog = api.login(admin_b, PASSWORD)
            key_b2 = relog.json().get("api_key") if relog.status_code == 200 else None
            if key_b2:
                end = {
                    "event_type": "run_end",
                    "run_id": run_id,
                    "status": "failed",
                    "ended_at": now,
                }
                api.call("POST", "/ingest/v1/batch", key_b2, {"events": [end]})
            run = {}
            for _ in range(20):
                got = api.call("GET", f"/runs/{run_id}", key_a)
                if got.status_code == 200:
                    run = got.json()
                    break
                time.sleep(1)
            check(bool(run), "org A's run was ingested", run)
            time.sleep(3)
            run = api.call("GET", f"/runs/{run_id}", key_a).json()
            check(
                run.get("status") == "running", "org B could not end org A's run", run.get("status")
            )

        print("\n→ unauthenticated surfaces closed")
        anon = api.call("GET", "/analytics/agents-list-posture")
        check(anon.status_code in (401, 403), "analytics posture needs auth", anon.status_code)
        webhook = api.call(
            "POST", "/ingest/v1/webhook", body={"workspace_id": org_a["id"], "events": []}
        )
        check(
            webhook.status_code in (404, 405),
            "unsigned ingest webhook removed",
            webhook.status_code,
        )

        print("\n→ brute-force throttling")
        target = f"nobody-{suffix}@verify.test"
        codes = [
            api.login(target, "wrong-password-1").status_code for _ in range(args.max_failures)
        ]
        check(all(c == 401 for c in codes), f"first {args.max_failures} failures return 401", codes)
        locked = api.login(target, "wrong-password-1")
        check(locked.status_code == 429, "further attempts throttled (429)", locked.status_code)
    except _Abort:
        print("  ! aborted after a failed prerequisite step")
    finally:
        if not args.keep:
            for org in created:
                api.call(
                    "DELETE",
                    f"/org/tenants/{org['id']}",
                    platform_key,
                    {"confirmation": org["name"]},
                )

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--admin-email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument(
        "--admin-password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger")
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=int(os.getenv("LOGIN_MAX_FAILURES_PER_ACCOUNT", "10")),
        help="Server's LOGIN_MAX_FAILURES_PER_ACCOUNT (default 10).",
    )
    parser.add_argument("--keep", action="store_true", help="Keep the test orgs afterwards.")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
