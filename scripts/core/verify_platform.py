#!/usr/bin/env python3
"""End-to-end verification of the platform, infra and auth controls (review W1-I).

Asserts against a running stack:

  1. /health returns 503 exactly when it reports "degraded", and reports migrations
     and Celery beat; /health/ready requires the schema at head; /health/live is 200.
  2. First run: /auth/bootstrap-status says no bootstrap is needed once an admin exists,
     and POST /admin/bootstrap is refused (409) after that (with --admin-secret).
  3. Outside development, the seeded demo account (admin@runledger.local) can't sign in.
  4. The system status page (GET /system/status) is platform-admin only and lists
     workers, the three Celery queues, beat, migrations, backups and version skew.
  5. Sliding-window rate limits are on: management routes return X-RateLimit-* headers.
  6. Sign-out revokes the session key immediately.
  7. Feature flags are gone (no display-only /settings/ops/feature-flags).
  8. Restore drills are refused while BACKUP_ENABLED is false.
  9. With --web-url: the dashboard's BFF proxy refuses requests without a session
     (401) and cross-site mutations (403), and /api/setup answers the first-run check.

Usage:
    python scripts/run_demo.py verify-platform
    python scripts/core/verify_platform.py --base-url http://localhost:8201 \\
        --web-url http://localhost:3201 --admin-email admin@runledger.local \\
        --admin-password runledger --admin-secret "$ADMIN_SECRET"
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEV_SEED_EMAIL = "admin@runledger.local"
DEV_SEED_PASSWORD = "runledger"


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


def run(args: argparse.Namespace) -> int:
    check = Check()
    api = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30)

    def call(method: str, path: str, key: str | None = None, **kw: Any) -> httpx.Response:
        headers = dict(kw.pop("headers", {}) or {})
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return api.request(method, path, headers=headers, **kw)

    print("\n[1] Health, readiness and liveness")
    health = call("GET", "/health")
    body = health.json() if health.headers.get("content-type", "").startswith("application/json") else {}
    check(health.status_code in (200, 503), "/health answers 200 or 503", health.status_code)
    check(
        (health.status_code == 503) == (body.get("status") == "degraded"),
        "/health is 503 exactly when degraded",
        body,
    )
    check({"db", "redis", "migrations", "beat"} <= set(body), "/health reports db, redis, migrations, beat", body)
    if body.get("beat") not in ("ok", "starting"):
        print(f"    note: beat is {body.get('beat')!r} — is runledger-beat running?")
    ready = call("GET", "/health/ready")
    check(ready.status_code == 200, "/health/ready is 200 (schema at head)", ready.text[:200])
    check(call("GET", "/health/live").status_code == 200, "/health/live is 200")

    print("\n[2] First-run bootstrap")
    status = call("GET", "/auth/bootstrap-status")
    check(status.status_code == 200, "/auth/bootstrap-status is public", status.status_code)
    env = status.json().get("environment", "?") if status.status_code == 200 else "?"
    check(status.json().get("needs_bootstrap") is False, "an admin exists, so no bootstrap is needed", status.text)
    if args.admin_secret:
        again = call(
            "POST",
            "/admin/bootstrap",
            headers={"X-Admin-Secret": args.admin_secret},
            json={"email": "second-admin@example.com", "password": "Second-admin-123"},
        )
        check(again.status_code == 409, "a second bootstrap is refused (409)", again.status_code)
    else:
        print("    skipped the second-bootstrap check (pass --admin-secret)")

    print(f"\n[3] Demo account outside development (ENVIRONMENT={env})")
    if env != "development":
        demo = call("POST", "/auth/login", json={"email": DEV_SEED_EMAIL, "password": DEV_SEED_PASSWORD})
        check(demo.status_code in (401, 403), "the dev demo admin can't sign in", demo.status_code)
    else:
        print("    development stack: the demo admin is expected here")

    print("\n[4] System status page")
    login = call("POST", "/auth/login", json={"email": args.admin_email, "password": args.admin_password})
    if login.status_code != 200:
        check(False, "platform admin signs in", f"{login.status_code} {login.text[:200]}")
        return _report(check)
    key = login.json()["api_key"]
    check(call("GET", "/system/status").status_code == 401, "anonymous /system/status is 401")
    sys_status = call("GET", "/system/status", key)
    check(sys_status.status_code == 200, "platform admin reads /system/status", sys_status.status_code)
    if sys_status.status_code == 200:
        data = sys_status.json()
        queues = {q["queue"] for q in data.get("queues", [])}
        check(queues == {"celery", "ingest", "maintenance"}, "the three Celery queues are listed", queues)
        check(isinstance(data.get("versions", {}).get("skew"), bool), "version skew is reported")
        check("status" in data.get("beat", {}), "beat heartbeat is reported")
        check(isinstance(data.get("workers"), list), "workers are listed", data.get("workers"))
        check(data.get("migrations", {}).get("status") == "ok", "schema is at this build's head", data.get("migrations"))
        if data.get("versions", {}).get("skew"):
            print(f"    note: version skew {data['versions']['components']}")

    print("\n[5] Sliding-window rate limits")
    limited = call("GET", "/settings/api-keys", key)
    check(
        "x-ratelimit-limit-requests" in limited.headers,
        "management routes carry X-RateLimit headers",
        dict(limited.headers),
    )

    print("\n[6] Sign-out revokes the session key")
    second = call("POST", "/auth/login", json={"email": args.admin_email, "password": args.admin_password})
    key2 = second.json().get("api_key") if second.status_code == 200 else None
    if key2:
        check(call("GET", "/auth/me", key2).status_code == 200, "a fresh session works")
        check(call("POST", "/auth/logout", key2).status_code == 204, "logout is 204")
        check(call("GET", "/auth/me", key2).status_code == 401, "the revoked key is refused (401)")

    print("\n[7] Feature flags removed")
    check(
        call("GET", "/settings/ops/feature-flags", key).status_code == 404,
        "/settings/ops/feature-flags no longer exists",
    )

    print("\n[8] Restore drill gate")
    ops = call("GET", "/settings/ops/status", key)
    if ops.status_code == 200 and not ops.json().get("backup_enabled"):
        drill = call("POST", "/settings/backups/restore-drill", key)
        check(drill.status_code == 400, "restore drill refused while BACKUP_ENABLED=false", drill.status_code)
    else:
        print("    skipped (backups enabled on this stack)")

    if args.web_url:
        print("\n[9] Dashboard BFF proxy")
        web = httpx.Client(base_url=args.web_url.rstrip("/"), timeout=30, follow_redirects=False)
        anon = web.get("/api/rl/auth/me")
        check(anon.status_code == 401, "BFF without a session is 401", anon.status_code)
        cross = web.post(
            "/api/rl/auth/logout",
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
        )
        check(cross.status_code == 403, "BFF refuses a cross-site mutation", cross.status_code)
        blocked = web.get("/api/rl/admin/tenants")
        check(blocked.status_code == 403, "BFF never proxies /admin/*", blocked.status_code)
        setup = web.get("/api/setup")
        check(
            setup.status_code == 200 and "needs_bootstrap" in setup.json(),
            "/api/setup answers the first-run check",
            setup.text[:200],
        )

    call("POST", "/auth/logout", key)
    return _report(check)


def _report(check: Check) -> int:
    print(f"\n{check.passed} passed, {len(check.failures)} failed")
    for label in check.failures:
        print(f"  FAILED: {label}")
    return 1 if check.failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument("--web-url", default=os.getenv("RUNLEDGER_WEB_URL", "http://localhost:3201"))
    parser.add_argument("--admin-email", default=os.getenv("RUNLEDGER_ADMIN_EMAIL", DEV_SEED_EMAIL))
    parser.add_argument("--admin-password", default=os.getenv("RUNLEDGER_ADMIN_PASSWORD", DEV_SEED_PASSWORD))
    parser.add_argument("--admin-secret", default=os.getenv("ADMIN_SECRET", ""))
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
