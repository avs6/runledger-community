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
    clean.add_argument(
        "--hard-clean", action="store_true", help="wipe every volume before simulating"
    )
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

    # 4. Phase 13 governance & finops seeding (cross-workspace).
    say("\n→ seeding Phase 13 governance & finops features", "b")
    for ws in sim.workspaces:
        if not ws.key:
            continue
        ws.get_governance_audit_pack()

    # 5. Phase 14 guardrails seeding (cross-workspace baseline content filters).
    say("\n→ seeding Phase 14 guardrails across all workspaces", "b")
    baseline_filters = [
        {"filter_name": "code_injection", "severity": "high", "enabled": True},
        {"filter_name": "data_exfiltration", "severity": "high", "enabled": True},
        {"filter_name": "toxicity", "severity": "medium", "enabled": True},
        {"filter_name": "harmful_violence", "severity": "strict", "enabled": True},
        {"filter_name": "harmful_self_harm", "severity": "strict", "enabled": True},
        {"filter_name": "harmful_child_safety", "severity": "strict", "enabled": True},
    ]
    for ws in sim.workspaces:
        if not ws.key:
            continue
        try:
            ws.activate_content_filters(baseline_filters)
            ws.get_guardrail_stats(hours=1)
        except Exception:  # noqa: BLE001
            pass

    # 6. Phase 15 ML intelligence seeding (generate forecasts for each workspace).
    say("\n→ seeding Phase 15 ML intelligence (forecasts, top-K, patterns)", "b")
    for ws in sim.workspaces:
        if not ws.key:
            continue
        try:
            ws.generate_forecast("cost_daily", horizon_days=14)
            ws.generate_forecast("tokens_daily", horizon_days=14)
            ws.get_top_k("model", "cost", k=10)
            ws.list_patterns()
        except Exception:  # noqa: BLE001
            pass

    # 7. Phase 16 agentic operations seeding (agents, workflows, vector stores, playground).
    say("\n→ seeding Phase 16 agentic operations", "b")
    for ws in sim.workspaces:
        if not ws.key:
            continue
        try:
            agent = ws.register_agent(
                f"{ws.name}-triage",
                "autonomous",
                default_model="gpt-4o",
                budget_envelope=50.0,
                owner="platform-team",
            )
            agent_id = agent.get("id")
            if agent_id:
                ws.store_agent_memory(agent_id, "system_config", '{"routing": "auto"}', "long_term", 90)
                ws.store_agent_memory(agent_id, "user_prefs", '{"verbose": true}', "short_term")
                ws.get_agent_memory_stats(agent_id)

                wf = ws.create_workflow(
                    f"{ws.name}-pipeline",
                    description="Triage → research → draft",
                    steps_schema=[
                        {"name": "triage", "type": "agent", "model": "gpt-4o-mini"},
                        {"name": "research", "type": "tool", "tool": "search-api"},
                        {"name": "draft", "type": "agent", "model": "gpt-4o"},
                    ],
                )
                wf_id = wf.get("id")
                if wf_id:
                    run = ws.create_workflow_run(wf_id, agent_id=agent_id, trigger="simulator")
                    run_id = run.get("id")
                    if run_id:
                        ws.create_workflow_step(run_id, 0, "triage", "agent", model="gpt-4o-mini")
                        ws.create_workflow_step(run_id, 1, "research", "tool")

            coll = ws.register_vector_collection(
                f"{ws.name}-kb",
                f"{ws.name.lower().replace(' ', '_')}_v1",
                embedding_model="bge-small-en-v1.5",
                dimensions=384,
                description=f"Knowledge base for {ws.name}",
            )
            coll_id = coll.get("id")
            if coll_id:
                ws.vector_search_test(coll_id, "how does billing work?")
                ws.vector_search_test(coll_id, "what is the refund policy?")

            session = ws.create_playground_session(
                f"{ws.name} - model comparison",
                mode="compare",
                system_prompt="You are a helpful assistant.",
            )
            ws.playground_send("gpt-4o", "What is the capital of France?")
            ws.playground_send("gpt-4o-mini", "Explain quantum computing in one sentence.")
            ws.playground_compare(
                ["gpt-4o", "gpt-4o-mini"],
                "Summarize the benefits of RAG in three bullet points.",
            )
        except Exception:  # noqa: BLE001
            pass

    # 8. Summary.
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
