#!/usr/bin/env python3
"""End-to-end check of secrets, audit and approvals hardening (review stream W1-A).

  1. Write-only secrets (S-03, S-04, G-05, B-09, F-15): auth-provider client secrets,
     search-provider credentials and webhook URLs come back masked; sending the mask
     back keeps the stored value; an LDAP service bind needs a password (S-25).
  2. Secret inventory (ENH): every stored secret is listed with its age and key;
     "rotate" replaces the value, bumps the rotation count and lands on the secret's
     own audit timeline; "re-wrap" on the current key is a no-op.
  3. Audit (S-02, S-16, S-27): events carry an actor, the workspace hash chain
     verifies, actor / actor-type filters work and lists send X-Total-Count.
  4. Approvals (S-15): a requester can't approve their own request; two concurrent
     decisions on one request give exactly one success (row lock).
  5. Internal channel (tr-security): /gateway/runtime/internal/* refuses callers
     without the internal credential.

Creates throwaway providers, a search tool, a notification channel and approvals in
the signed-in admin's workspace, and deletes them afterwards.

Usage:
    python scripts/run_demo.py verify-secrets [--base-url http://localhost:8201]
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MASK = "••••••••"


class Check:
    def __init__(self) -> None:
        self.passed = 0
        self.failures: list[str] = []

    def __call__(self, ok: bool, label: str, detail: Any = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  ✓ {label}")
        else:
            self.failures.append(label)
            print(f"  ✗ {label} {str(detail)[:300]}")
        return ok


def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    http = httpx.Client(base_url=base, timeout=60)
    check = Check()
    login = http.post("/auth/login", json={"email": args.email, "password": args.password})
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    h = {"Authorization": f"Bearer {login.json()['api_key']}"}
    tag = uuid.uuid4().hex[:6]
    cleanup: list[str] = []

    try:
        print("\n→ write-only secrets (S-03, S-04, F-15, S-25)")
        oidc = http.post(
            "/security/oidc-providers",
            headers=h,
            json={
                "name": f"verify-oidc-{tag}",
                "issuer_url": "https://idp.example.test",
                "client_id": "verify-client",
                "client_secret": "oidc-plain-secret",
            },
        )
        check(oidc.status_code == 201, "OIDC provider created", oidc.text)
        oidc_id = oidc.json().get("id") if oidc.status_code == 201 else None
        if oidc_id:
            cleanup.append(f"/security/oidc-providers/{oidc_id}")
            check(oidc.json().get("client_secret") == MASK, "client secret returned masked")
            check("oidc-plain-secret" not in oidc.text, "plaintext never in the response")
            kept = http.put(
                f"/security/oidc-providers/{oidc_id}",
                headers=h,
                json={"client_secret": MASK, "audience": "verify"},
            )
            check(
                kept.status_code == 200 and kept.json().get("client_secret") == MASK,
                "sending the mask back keeps the stored secret",
                kept.text,
            )

        ldap = http.post(
            "/security/ldap-providers",
            headers=h,
            json={
                "name": f"verify-ldap-{tag}",
                "server_url": "ldap://ldap.example.test",
                "bind_dn": "cn=svc,dc=example,dc=test",
                "user_search_base": "dc=example,dc=test",
            },
        )
        check(
            ldap.status_code == 422, "LDAP service bind without a password → 422", ldap.status_code
        )

        tool = http.post(
            "/search-tools",
            headers=h,
            json={
                "name": f"verify-search-{tag}",
                "tool_type": "web",
                "auth_type": "bearer",
                "auth_config": {"token": "search-plain-token", "header_name": "X-Key"},
            },
        )
        check(tool.status_code == 201, "search provider created", tool.text)
        tool_id = tool.json().get("id") if tool.status_code == 201 else None
        if tool_id:
            cleanup.append(f"/search-tools/{tool_id}")
            cfg = tool.json().get("auth_config", {})
            check(
                cfg.get("token") == MASK and cfg.get("header_name") == "X-Key",
                "search credentials masked, other config visible",
                cfg,
            )
            upd = http.put(
                f"/search-tools/{tool_id}",
                headers=h,
                json={"auth_config": {"token": MASK, "header_name": "X-Key"}},
            )
            check(upd.status_code == 200, "search provider updated with the mask", upd.text)

        notif = http.post(
            "/budgets/notifications",
            headers=h,
            json={
                "channel": "slack",
                "destination_url": "https://hooks.slack.com/services/T0/B0/verify-token",
                "events": ["budget.breach"],
            },
        )
        if notif.status_code == 201:
            cleanup.append(f"/budgets/notifications/{notif.json()['id']}")
            check(
                "verify-token" not in notif.text and notif.json()["destination_url"].endswith(MASK),
                "webhook URL returned masked",
                notif.json().get("destination_url"),
            )
        else:
            check(False, "notification channel created", notif.text)

        print("\n→ secret inventory (ENH)")
        inv = http.get("/security/secrets", headers=h)
        check(inv.status_code == 200, "GET /security/secrets", inv.text)
        items = inv.json().get("items", []) if inv.status_code == 200 else []
        kinds = {i["kind"] for i in items}
        check(
            {"oidc_client_secret", "search_provider_auth", "notification_webhook"} <= kinds,
            "inventory lists the new secrets",
            kinds,
        )
        search_secret = next(
            (i for i in items if i["kind"] == "search_provider_auth" and i["owner_id"] == tool_id),
            None,
        )
        if search_secret:
            check(
                search_secret["rotation_count"] == 0 and search_secret["age_status"] == "fresh",
                "masked update was not counted as a rotation",
                search_secret,
            )
            check(search_secret["key_current"], "secret wrapped by the current key")
            rot = http.post(
                f"/security/secrets/{search_secret['id']}/rotate",
                headers=h,
                json={"values": {"token": "search-new-token"}},
            )
            check(
                rot.status_code == 200 and rot.json()["rotation_count"] == 1,
                "rotate bumps the rotation count",
                rot.text,
            )
            empty = http.post(
                f"/security/secrets/{search_secret['id']}/rotate", headers=h, json={"values": {}}
            )
            check(empty.status_code == 422, "rotate without a value → 422", empty.status_code)
            rw = http.post(f"/security/secrets/{search_secret['id']}/rewrap", headers=h)
            check(rw.status_code == 200, "re-wrap on the current key succeeds", rw.text)
            tl = http.get(
                "/audit/events",
                headers=h,
                params={"target_type": "secret", "target_id": search_secret["id"]},
            )
            actions = sorted(e["action"] for e in tl.json().get("items", []))
            check(
                actions == ["secret.created", "secret.rotated"],
                "per-secret timeline: created then rotated",
                actions,
            )
        else:
            check(False, "search secret present in the inventory", items)

        print("\n→ audit actor, chain and filters (S-02, S-16, S-27)")
        ev = http.get("/audit/events", headers=h, params={"limit": 20})
        check(ev.headers.get("x-total-count") is not None, "audit list sends X-Total-Count")
        events = ev.json().get("items", [])
        check(
            bool(events) and all(e.get("actor_type") for e in events),
            "every recent event has an actor type",
            [e.get("actor_type") for e in events][:5],
        )
        check(all(e.get("hash") for e in events), "recent events are hash-chained")
        mine = http.get(
            "/audit/events", headers=h, params={"actor": args.email, "action": "secret"}
        )
        check(
            mine.status_code == 200 and mine.json().get("total", 0) >= 1,
            "actor filter finds my secret events",
            mine.text[:200],
        )
        sess = http.get("/audit/events", headers=h, params={"actor_type": "session", "limit": 5})
        check(
            sess.status_code == 200
            and all(e["actor_type"] == "session" for e in sess.json().get("items", [])),
            "actor-type filter",
            sess.text[:200],
        )
        actors = http.get("/audit/actors", headers=h)
        check(actors.status_code == 200 and actors.json().get("items"), "GET /audit/actors")
        ver = http.get("/audit/verify", headers=h)
        check(
            ver.status_code == 200 and ver.json().get("ok") is True,
            "workspace hash chain verifies",
            ver.text,
        )

        print("\n→ approvals: separation of duties and locking (S-15)")
        a1 = http.post(
            "/approvals",
            headers=h,
            json={"request_type": "sensitive_export", "request": {"verify": tag}},
        )
        check(a1.status_code == 201, "approval requested", a1.text)
        if a1.status_code == 201:
            aid = a1.json()["id"]
            self_ok = http.put(f"/approvals/{aid}/approve", headers=h, json={"note": "self"})
            check(
                self_ok.status_code == 403,
                "requester can't approve own request",
                self_ok.status_code,
            )

            def deny() -> int:
                with httpx.Client(base_url=base, timeout=60) as c:
                    return c.put(
                        f"/approvals/{aid}/deny", headers=h, json={"note": "race"}
                    ).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                codes = sorted(pool.map(lambda _: deny(), range(2)))
            check(codes == [200, 409], "two concurrent decisions → one 200, one 409", codes)
            trail = http.get(
                "/audit/events", headers=h, params={"target_type": "approval", "target_id": aid}
            )
            acts = sorted(e["action"] for e in trail.json().get("items", []))
            check(
                acts == ["approval.denied", "approval.requested"],
                "approval audit committed with the change (no lost events)",
                acts,
            )

        print("\n→ internal channel (tr-security)")
        internal = http.get(
            "/gateway/runtime/internal/snapshot", params={"workspace_id": str(uuid.uuid4())}
        )
        check(
            internal.status_code == 403,
            "internal endpoint refuses callers without a token",
            internal.status_code,
        )
        bad = http.get(
            "/gateway/runtime/internal/snapshot",
            params={"workspace_id": str(uuid.uuid4())},
            headers={"x-gateway-internal-token": "wrong", "x-admin-secret": "wrong"},
        )
        check(bad.status_code == 403, "wrong internal credential → 403", bad.status_code)
    finally:
        for path in reversed(cleanup):
            http.delete(path, headers=h)

    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
