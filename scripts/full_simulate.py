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
import random
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


def _seed_demo_breadth(ws) -> None:
    """Expand seeded entities so demo workspaces show broad enterprise coverage."""
    if not ws.key:
        return

    model_pool = sorted({run.model for run in ws.runs}) or [
        "qwen2.5-coder:14b",
        "deepseek-r1:14b",
        "llama3.2",
    ]
    workflows = [
        {
            "feature": "support-escalation",
            "agent": "support-triage-agent",
            "skill": "support-routing",
            "tool": "crm.lookup",
            "tool_type": "read",
            "team": "Support",
            "application": "Customer Portal",
            "route": "support-router",
            "prompt_name": "support-triage",
            "intent": "support escalation",
            "outcome_type": "resolved",
            "cache_rate": 0.28,
        },
        {
            "feature": "finance-reconciliation",
            "agent": "finance-ops-agent",
            "skill": "ledger-analysis",
            "tool": "billing.export",
            "tool_type": "write",
            "team": "Finance",
            "application": "Ops Console",
            "route": "finance-router",
            "prompt_name": "finance-summary",
            "intent": "invoice reconciliation",
            "outcome_type": "reconciled",
            "cache_rate": 0.14,
        },
        {
            "feature": "security-review",
            "agent": "trust-review-agent",
            "skill": "policy-review",
            "tool": "policy.diff",
            "tool_type": "review",
            "team": "Trust",
            "application": "Trust Desk",
            "route": "trust-router",
            "prompt_name": "trust-check",
            "intent": "policy review",
            "outcome_type": "approved",
            "cache_rate": 0.1,
        },
        {
            "feature": "sales-assist",
            "agent": "revenue-copilot",
            "skill": "account-research",
            "tool": "search.accounts",
            "tool_type": "read",
            "team": "Sales",
            "application": "Sales Copilot",
            "route": "sales-router",
            "prompt_name": "sales-brief",
            "intent": "account research",
            "outcome_type": "conversion",
            "cache_rate": 0.22,
        },
        {
            "feature": "backup-ops",
            "agent": "platform-ops-agent",
            "skill": "backup-automation",
            "tool": "s3.snapshot",
            "tool_type": "write",
            "team": "Platform",
            "application": "Admin Console",
            "route": "ops-router",
            "prompt_name": "backup-ops",
            "intent": "backup verification",
            "outcome_type": "completed",
            "cache_rate": 0.08,
        },
    ]

    for app_name, env in (
        ("Customer Portal", "prod"),
        ("Ops Console", "staging"),
        ("Sales Copilot", "prod"),
        ("Admin Console", "dev"),
    ):
        try:
            ws.create_application(app_name, environment=env)
        except Exception:  # noqa: BLE001
            pass

    for team_name, model_name, budget_usd in (
        ("Support", model_pool[0], 120.0),
        ("Finance", model_pool[min(1, len(model_pool) - 1)], 180.0),
        ("Trust", model_pool[min(2, len(model_pool) - 1)], 150.0),
        ("Sales", model_pool[-1], 200.0),
    ):
        try:
            ws.add_team_model(
                team_name,
                model_name,
                description=f"{team_name} default model for demo traffic",
                budget_usd=budget_usd,
                logging_opt_out=team_name == "Trust",
                config={"routing_mode": "guided", "workspace": ws.name},
            )
        except Exception:  # noqa: BLE001
            pass

    try:
        seeded_runs = ws.ingest_rich_runs(
            36,
            models=model_pool[: min(4, len(model_pool))],
            workflows=workflows,
            users=[f"{ws.name.lower().replace(' ', '-')}-user-{i:02d}" for i in range(1, 25)],
            days=14,
            success_rate=0.9,
            sessions=18,
            batch_runs=36,
        )
        ws.ingest_otlp_traces(
            10,
            models=model_pool[: min(3, len(model_pool))],
            workflows=workflows,
        )
    except Exception:  # noqa: BLE001
        seeded_runs = []

    for run in ws.sample(seeded_runs, 18):
        try:
            ws.record_outcome(
                run,
                random.choice(["resolved", "conversion", "escalated", "retained"]),
                success=run.success,
                value_usd=round(random.uniform(4, 160), 2),
                labels={
                    "workspace": ws.name,
                    "org": ws.org,
                    "segment": random.choice(["enterprise", "growth", "startup"]),
                },
            )
            ws.score(run, "quality", round(random.uniform(0.58, 0.97), 3))
        except Exception:  # noqa: BLE001
            pass

    for alert_name, metric, operator, threshold in (
        ("High error rate", "error_rate", "gt", 0.12),
        ("Gateway overhead target", "gateway_overhead_p95", "gt", 900.0),
        ("Model availability", "model_availability", "lt", 0.85),
        ("Spend velocity", "spend_velocity", "gt", 75.0),
    ):
        try:
            ws.add_alert(f"{ws.name} {alert_name}", metric, operator, threshold)
        except Exception:  # noqa: BLE001
            pass

    for tool_name, policy, runtime_enforcement, description in (
        ("shell.exec", "block", True, "Production shell access requires approval"),
        ("search.docs", "allow", False, "Knowledge-base lookups are allowed"),
        ("billing.export", "audit", False, "Exports remain visible for operator review"),
    ):
        try:
            ws.upsert_tool_policy(
                tool_name,
                policy=policy,
                runtime_enforcement=runtime_enforcement,
                description=description,
            )
        except Exception:  # noqa: BLE001
            pass
    try:
        ws.check_tool("shell.exec")
    except Exception:  # noqa: BLE001
        pass
    try:
        ws.list_tool_registry()
        ws.list_tool_security_events()
    except Exception:  # noqa: BLE001
        pass

    try:
        server = ws.register_mcp_server(
            f"{ws.name} MCP Gateway",
            description="Simulator-seeded MCP server for permission and filtering demos.",
            transport="http",
            url="https://mcp.demo.runledger.local",
            auth_type="bearer",
            auth_config={"token": "demo-token"},
        )
        server_id = server.get("id")
        if server_id:
            ws.grant_mcp_permission(
                server_id,
                scope_type="workspace",
                allowed_tools=["search.docs", "crm.lookup"],
            )
            ws.list_mcp_permissions()
            ws.list_mcp_tools()
    except Exception:  # noqa: BLE001
        pass

    approval_specs = [
        (
            "tool_allow",
            "Allow a sensitive tool for a supervised ops demo.",
            {"tool_name": "shell.exec", "requested_policy": "allow"},
            "approve",
        ),
        (
            "shadow_routing",
            "Enable shadow routing for side-by-side provider evaluation.",
            {"alias": "support-router", "mirror_provider": "demo-shadow"},
            "approve",
        ),
        (
            "capture_policy_full",
            "Temporary full capture for a troubleshooting drill.",
            {"scope": "workspace", "duration_hours": 2},
            "deny",
        ),
    ]
    for request_type, reason, metadata, decision in approval_specs:
        try:
            approval = ws.create_approval_request(request_type, reason, metadata=metadata)
            approval_id = approval.get("id")
            if approval_id and decision == "approve":
                ws.approve_request(approval_id, "Approved by simulator for demo coverage.")
            elif approval_id and decision == "deny":
                ws.deny_request(approval_id, "Denied by simulator to show decision workflow.")
        except Exception:  # noqa: BLE001
            pass
    try:
        ws.list_approvals()
        ws.get_approval_summary()
    except Exception:  # noqa: BLE001
        pass

    try:
        ws.update_email_preferences(
            report_frequency="weekly",
            report_hour=8,
            report_timezone="America/Chicago",
            report_recipient_mode="workspace_admins",
            report_template="detailed",
            alerts_enabled=True,
            approvals_enabled=True,
            budget_alerts_enabled=True,
            score_regression_enabled=True,
        )
        ws.send_test_email()
        ws.send_test_report()
        ws.get_email_history()
    except Exception:  # noqa: BLE001
        pass

    try:
        slug = ws.name.lower().replace(" ", "-")
        ws.update_backup_config(
            provider="s3",
            bucket="runledger-backups",
            prefix=f"demos/{slug}",
            region="us-east-1",
            endpoint_url="http://runledger-minio:9000",
            access_key_id="minioadmin",
            secret_access_key="minioadmin",
            force_path_style=True,
            schedule_enabled=True,
            cadence="daily",
            run_hour_utc=2,
            retention_days=14,
            include_memory_db=True,
            include_qdrant=False,
            include_kuzu=True,
            include_skills=True,
            encryption_mode="server_side",
        )
        ws.test_backup_connection()
        ws.run_backup_now()
        ws.run_restore_drill()
        ws.get_backup_history()
        ws.get_backup_snapshots()
        ws.get_backup_status()
    except Exception:  # noqa: BLE001
        pass

    try:
        if ws.runs:
            ws.generate_runbook(ws.runs[0])
    except Exception:  # noqa: BLE001
        pass


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
    ap.add_argument(
        "--streaming-demo",
        action="store_true",
        help="also seed Kafka/Redpanda export configs for live streaming demos",
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

    # 7b. Broaden one-click demo seeds across control-plane and operator-facing entities.
    say("\n-> expanding demo breadth across apps, teams, tools, approvals, backups, email, OTLP, and MCP", "b")
    for ws in sim.workspaces:
        try:
            _seed_demo_breadth(ws)
        except Exception as exc:  # noqa: BLE001
            say(f"  ! demo breadth seed skipped for {ws.name}: {exc}", "y")

    if args.streaming_demo:
        say("\n-> enabling Kafka/Redpanda demo exports", "b")
        for ws in sim.workspaces:
            if not ws.key:
                continue
            try:
                ws.enable_kafka_export_demo()
            except Exception as exc:  # noqa: BLE001
                say(f"  ! kafka export setup skipped for {ws.name}: {exc}", "y")

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
