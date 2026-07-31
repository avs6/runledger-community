#!/usr/bin/env python3
"""
Populate a whole RunLedger cluster from the REST API by running every scenario.

By default it first resets the stack to a blank slate (truncate), then bootstraps a
platform admin and runs every scenario under ``scripts/scenarios/`` — each creates its
own org + workspace and fills it with runs, gateway routes, budgets, outcomes, scores,
and alerts, exactly as a real client would.

    python scripts/full_simulate.py                 # clean (truncate) + simulate local Ollama traffic
    python scripts/full_simulate.py --hard-clean     # wipe every volume AND remove all orgs/users/
                                                     #   keys first, then simulate
    python scripts/full_simulate.py --no-clean       # add data on top of what's already there
    python scripts/full_simulate.py --scenario-set all
    python scripts/full_simulate.py --traffic-multiplier 5

The default clean preserves your admin login + provider pricing; --hard-clean removes every
org / user / key too (provider pricing is kept). A fresh admin is bootstrapped either way.

Requires the stack to be running (`docker compose up -d`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The console output uses Unicode (→ ✓ ▶ ═). Force UTF-8 so it never crashes on a
# non-UTF-8 host console (e.g. Windows cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Make the sibling `scenarios` package and `cleanup` module importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cleanup  # noqa: E402
import scenarios  # noqa: E402
from scenarios._base import Sim, say  # noqa: E402


def _import_pricing(sim: Sim) -> None:
    """Upload scripts/pricing.yaml to the provider-pricing catalog (best-effort)."""
    path = Path(__file__).resolve().parent / "pricing.yaml"
    if not path.exists() or not sim.platform_key:
        return
    try:
        resp = sim.http.post(
            f"{sim.base}/providers/pricing/import",
            headers={"Authorization": f"Bearer {sim.platform_key}"},
            files={"file": ("pricing.yaml", path.read_bytes(), "text/yaml")},
        )
        resp.raise_for_status()
        d = resp.json()
        say(
            f"  ✓ pricing imported — {d.get('inserted', 0)} added, {d.get('updated', 0)} updated",
            "g",
        )
    except Exception as exc:  # noqa: BLE001 — non-fatal
        say(f"  ! pricing import skipped: {exc}", "y")


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulate a full RunLedger cluster via the API.")
    ap.add_argument("--base-url", default="http://localhost:8201")
    ap.add_argument("--admin-secret", default="runledger-admin")
    ap.add_argument("--admin-email", default="admin@runledger.local")
    ap.add_argument("--admin-password", default="runledger")
    ap.add_argument("--org-name", default="RunLedger", help="name for the default (platform) org")
    ap.add_argument(
        "--scenario-set",
        choices=("ollama", "all", "hosted"),
        default="ollama",
        help="scenario category to run; default is local-only Ollama traffic",
    )
    ap.add_argument(
        "--traffic-multiplier",
        type=int,
        default=3,
        help="multiply each scenario's run count; default creates a high-volume local demo",
    )
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
    sim = Sim(
        args.base_url,
        args.admin_secret,
        traffic_multiplier=max(1, args.traffic_multiplier),
    )
    sim.wait_healthy()
    say("\n→ bootstrapping platform admin", "b")
    sim.bootstrap(args.admin_email, args.admin_password, args.org_name)

    # 2b. Import the simulation pricing catalog (prices local Ollama models too) so the
    #     DB catalog matches the cost of the runs each scenario ingests.
    _import_pricing(sim)

    # 3. Run every scenario.
    mods = scenarios.discover(args.scenario_set)
    say(
        f"\n→ running {len(mods)} {args.scenario_set} scenario(s) "
        f"(traffic x{sim.traffic_multiplier})",
        "b",
    )
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
