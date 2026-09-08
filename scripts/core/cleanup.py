#!/usr/bin/env python3
"""
Reset a running RunLedger stack to a blank slate — no residual data — before a simulation.

Two modes:

  python scripts/cleanup.py            # default: TRUNCATE all DATA tables (fast; stack stays up)
                                       #   PRESERVES admin credentials + provider pricing (see KEEP)
                                       #   also flushes Redis (budget counters / queues)
  python scripts/cleanup.py --hard     # docker compose down -v && up -d && wait healthy,
                                       #   then remove the startup-seeded default org/user/key
                                       #   wipes ALL volumes (Postgres, Redis, Qdrant, memory-db,
                                       #   Kùzu, skills) AND leaves zero orgs / users / keys

Default (truncate) keeps the schema/migration history and, importantly, the identity and
pricing config — users, tenants, workspaces, memberships, API keys, and the provider
pricing catalog — so you never lose your admin login or provider profiles. Everything else
(runs, budgets, routes, outcomes, scores, prompts, alerts, flywheel, invoices, …) is wiped.

`--hard` wipes *every* volume. The API's startup seed (`seed.py`) then re-creates a default
admin + base provider pricing on boot; the hard reset **removes that seeded org / user / key**
so nothing is left, while **keeping the provider pricing** (so you don't lose provider profiles).
Bootstrap or run `full_simulate.py` afterwards to create a fresh admin.

Run from the repo root (or anywhere — the script locates the compose file).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Force UTF-8 so the Unicode console output (→ ✓) never crashes on a non-UTF-8 host
# console (e.g. Windows cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
PG = "runledger-postgres"
REDIS = "runledger-redis"

# Schema tracking + the provider pricing catalog / config. Always preserved — a reset
# should never cost you your provider profiles.
KEEP_PRICING = (
    "alembic_version",
    "provider_pricing", "pricing_sync_config", "pricing_contracts", "pricing_credits",
)
# Identity / auth: admin credentials. Preserved by the DEFAULT (soft) truncate so you
# keep your login, but REMOVED by --hard so every org / user / key is wiped.
KEEP_IDENTITY = (
    "users", "tenants", "workspaces", "tenant_users", "workspace_users", "api_keys",
)


def _truncate_sql(keep: tuple[str, ...]) -> str:
    keep_sql = ", ".join(f"'{t}'" for t in keep)
    return (
        "DO $$ DECLARE r RECORD; BEGIN "
        "FOR r IN SELECT tablename FROM pg_tables "
        f"WHERE schemaname='public' AND tablename NOT IN ({keep_sql}) LOOP "
        "EXECUTE 'TRUNCATE TABLE public.' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE'; "
        "END LOOP; END $$;"
    )


def _compose(*args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args], cwd=REPO, check=check, text=True,
        capture_output=capture,
    )


def _running() -> bool:
    r = _compose("ps", "--services", "--filter", "status=running", check=False, capture=True)
    return PG in (r.stdout or "")


def _run_truncate(keep: tuple[str, ...]) -> None:
    _compose("exec", "-T", PG, "psql", "-U", "runledger", "-d", "runledger",
             "-v", "ON_ERROR_STOP=1", "-c", _truncate_sql(keep))
    _compose("exec", "-T", REDIS, "redis-cli", "FLUSHALL", check=False)


def truncate() -> None:
    if not _running():
        sys.exit("Stack is not running. Start it with `docker compose up -d`, or use --hard.")
    print("→ truncating data tables (preserving admin credentials + provider pricing)…")
    _run_truncate(KEEP_PRICING + KEEP_IDENTITY)
    print("✓ clean — data truncated, Redis flushed.")
    print("  Preserved: users, tenants, workspaces, memberships, API keys, provider pricing.")
    print("  (Qdrant / memory-db / Kùzu / skills untouched — use --hard to clear those too.)")


def hard_reset(base_url: str, timeout: float = 180) -> None:
    print("→ docker compose down -v (wiping ALL volumes)…")
    _compose("down", "-v")
    print("→ docker compose up -d…")
    _compose("up", "-d")
    print(f"→ waiting for {base_url}/health/ready (migrations + startup seed run on API start)…")
    deadline = time.time() + timeout
    ready = False
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health/ready", timeout=3) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3)
    if not ready:
        sys.exit(f"API at {base_url} not ready after {timeout}s")
    # The container's startup seed re-creates a default admin/org/key. Remove it so a
    # hard reset truly leaves zero orgs / users / keys (provider pricing is kept).
    print("→ removing the startup-seeded default org / user / key (keeping provider pricing)…")
    _run_truncate(KEEP_PRICING)
    print("✓ clean — every volume wiped; all orgs, users, and keys removed.")
    print("  Provider pricing kept (re-seeded on boot). Bootstrap or run full_simulate to create an admin.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Reset RunLedger to a blank slate.")
    ap.add_argument("--hard", action="store_true", help="down -v + up (wipe every volume)")
    ap.add_argument("--base-url", default="http://localhost:8201", help="API base URL for --hard health wait")
    args = ap.parse_args()
    if args.hard:
        hard_reset(args.base_url)
    else:
        truncate()


if __name__ == "__main__":
    main()
