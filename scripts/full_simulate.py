#!/usr/bin/env python3
"""
Populate a whole RunLedger cluster from the REST API by running every scenario.

By default it first resets the stack to a blank slate (truncate), then bootstraps a
platform admin and runs every scenario under ``scripts/scenarios/`` — each creates its
own org + workspace and fills it with runs, gateway routes, budgets, outcomes, scores,
and alerts, exactly as a real client would.

    python scripts/full_simulate.py                 # clean (truncate) + simulate everything
    python scripts/full_simulate.py --hard-clean     # wipe every volume AND remove all orgs/users/
                                                     #   keys first, then simulate
    python scripts/full_simulate.py --no-clean       # add data on top of what's already there

The default clean preserves your admin login + provider pricing; --hard-clean removes every
org / user / key too (provider pricing is kept). A fresh admin is bootstrapped either way.

Requires the stack to be running (`docker compose up -d`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the sibling `scenarios` package and `cleanup` module importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cleanup  # noqa: E402
import scenarios  # noqa: E402
from scenarios._base import Sim, say  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulate a full RunLedger cluster via the API.")
    ap.add_argument("--base-url", default="http://localhost:8201")
    ap.add_argument("--admin-secret", default="runledger-admin")
    ap.add_argument("--admin-email", default="admin@runledger.local")
    ap.add_argument("--admin-password", default="runledger")
    ap.add_argument("--org-name", default="RunLedger", help="name for the default (platform) org")
    clean = ap.add_mutually_exclusive_group()
    clean.add_argument("--no-clean", action="store_true", help="don't reset first")
    clean.add_argument("--hard-clean", action="store_true", help="wipe every volume before simulating")
    args = ap.parse_args()

    # 1. Reset to a blank slate.
    if args.hard_clean:
        cleanup.hard_reset(args.base_url)
    elif not args.no_clean:
        cleanup.truncate()

    # 2. Connect + bootstrap.
    sim = Sim(args.base_url, args.admin_secret)
    sim.wait_healthy()
    say("\n→ bootstrapping platform admin", "b")
    sim.bootstrap(args.admin_email, args.admin_password, args.org_name)

    # 3. Run every scenario.
    mods = scenarios.discover()
    say(f"\n→ running {len(mods)} scenario(s)", "b")
    for mod in mods:
        say(f"\n▶ {mod.NAME} — {getattr(mod, 'DESCRIPTION', '')}", "b")
        try:
            mod.run(sim)
        except Exception as exc:  # noqa: BLE001 — one scenario shouldn't sink the rest
            say(f"  ! scenario {mod.NAME} failed: {exc}", "y")

    # 4. Summary.
    say("\n" + "═" * 60, "d")
    say("Simulation complete.", "g")
    total_runs = sum(len(w.runs) for w in sim.workspaces)
    say(f"  {len(sim.workspaces)} workspace(s), {total_runs} runs ingested.\n", "g")
    say(f"  {'ORG / WORKSPACE':<34}{'API KEY':<20}RUNS", "d")
    for w in sim.workspaces:
        keyp = (w.key[:16] + "…") if w.key else "(none)"
        say(f"  {w.org + ' / ' + w.name:<34}{keyp:<20}{len(w.runs)}")
    say(f"\n  Dashboard: {args.base_url.replace('8201', '3201')}", "b")
    say(f"  Admin login: {args.admin_email} / {args.admin_password}", "b")
    say("  Cost enrichment + rollups run on Celery — give analytics ~60s to populate.", "d")
    sim.close()


if __name__ == "__main__":
    main()
