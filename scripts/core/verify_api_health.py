#!/usr/bin/env python3
"""Call every read endpoint the dashboard can load and assert none fails with a 5xx.

Signs in as the platform admin, reads the OpenAPI spec, and sends GET to every path
that has no path parameters and no required query parameters (about 290 routes:
analytics and posture views, settings, lists). Any 5xx or dropped connection is a
failure. Catches stale column names, missing tables and response-schema mismatches,
which only surface when the endpoint is actually called.

Each request uses a fresh connection: after a 500 the server closes the connection,
and reusing it would turn the next request into a spurious failure.

Usage:
    python scripts/run_demo.py verify-api-health
    python scripts/run_demo.py verify-api-health -- --prefix /analytics
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Never exercised here: side effects, streaming, or separate auth.
# List endpoints on the pagination standard (core/pagination.py).
PAGED = [
    "/settings/email/log",
    "/settings/email/history",
    "/settings/api-keys",
    "/tools/security-events",
    "/users",
    "/users/all",
    "/org/members",
    "/prompts",
    "/gateway/routes",
    "/billing/chargeback-report",
    "/analytics/annotations",
    "/analytics/regressions",
    "/alerts/rules",
    "/budgets",
    "/budgets/notifications",
    "/billing/periods",
    "/replay/datasets",
    "/replay/experiments",
    "/evaluations/evaluators",
    "/mcp-registry",
    "/mcp-registry/tools",
    "/hub/models",
]

SKIP_PREFIXES = ("/admin/backup", "/mcp", "/gateway/", "/v1/chat", "/ingest/v1/signed")


def run(args: argparse.Namespace) -> int:
    base = args.base_url.rstrip("/")
    login = httpx.post(
        f"{base}/auth/login", json={"email": args.email, "password": args.password}, timeout=30
    )
    if login.status_code != 200:
        print(f"Sign-in failed ({login.status_code}): {login.text}")
        return 2
    headers = {"Authorization": f"Bearer {login.json()['api_key']}", "Connection": "close"}
    spec = httpx.get(f"{base}/openapi.json", timeout=30).json()

    checked, failures = 0, []
    for path, ops in sorted(spec["paths"].items()):
        get = ops.get("get")
        if get is None or "{" in path or path.startswith(SKIP_PREFIXES):
            continue
        if args.prefix and not path.startswith(args.prefix):
            continue
        if any(p.get("required") and p.get("in") == "query" for p in get.get("parameters", [])):
            continue
        checked += 1
        try:
            resp = httpx.get(base + path, headers=headers, timeout=args.timeout)
            if resp.status_code >= 500:
                failures.append(f"{path} → {resp.status_code}")
        except httpx.HTTPError as exc:
            failures.append(f"{path} → {type(exc).__name__}: {exc}")

    print(f"{checked - len(failures)} of {checked} read endpoints returned without a server error")

    # Pagination standard: list endpoints honour ?limit and report X-Total-Count.
    paged_ok = 0
    for path in PAGED:
        try:
            resp = httpx.get(
                base + path, headers=headers, params={"limit": 1}, timeout=args.timeout
            )
        except httpx.HTTPError as exc:
            failures.append(f"{path} paging → {exc}")
            continue
        body = resp.json() if resp.status_code == 200 else None
        items = body if isinstance(body, list) else (body or {}).get("items")
        if path == "/billing/chargeback-report" and isinstance(items, list) and items:
            items = items[0].get("breakdown", [])
        ok = (
            resp.status_code == 200
            and "x-total-count" in resp.headers
            and isinstance(items, list)
            and len(items) <= 1
        )
        if ok:
            paged_ok += 1
        else:
            failures.append(
                f"{path} paging → status {resp.status_code}, headers/limit not honoured"
            )
    print(f"{paged_ok} of {len(PAGED)} list endpoints honour ?limit and report X-Total-Count")
    for line in failures:
        print(f"  FAILED: {line}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.getenv("RUNLEDGER_URL", "http://localhost:8201"))
    parser.add_argument(
        "--email", default=os.getenv("RUNLEDGER_PLATFORM_EMAIL", "admin@runledger.local")
    )
    parser.add_argument("--password", default=os.getenv("RUNLEDGER_PLATFORM_PASSWORD", "runledger"))
    parser.add_argument("--prefix", default="", help="Only check paths starting with this.")
    parser.add_argument("--timeout", type=float, default=60.0)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
