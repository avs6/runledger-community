# Simulation scenarios

Each scenario module (`NAME` + `run(sim)`) populates a RunLedger workspace through
the public REST API. The simulator mirrors the real product path: platform admin
creates an org, the seeded org admin creates routes/API keys/budgets, and agent
traffic lands through `/ingest/v1/batch`.

## Default demo mode

`scripts/full_simulate.py` now defaults to local-only Ollama scenarios and a 3x
traffic multiplier:

```bash
uv run python scripts/full_simulate.py
```

That creates four org/workspace pairs and roughly 1,770 synthetic local-model runs.
It imports `scripts/pricing.yaml`, which is intentionally Ollama-only, so the demo
does not need OpenAI, Anthropic, Gemini, or any other hosted-provider key.

Default simulator logins:

| Account | Password | Notes |
|---|---|---|
| `admin@runledger.local` | `runledger` | Platform admin created by `full_simulate.py`. |
| `admin@<scenario-slug>.example.com` | `Sim-Passw0rd!` | Org admin for each scenario org. Example: `admin@helpdesk-local.example.com`. |

Use these only when you intentionally want broader coverage:

```bash
uv run python scripts/full_simulate.py --traffic-multiplier 5
uv run python scripts/full_simulate.py --scenario-set all
uv run python scripts/full_simulate.py --scenario-set hosted
```

This is the primary automated demo profile surfaced by the dashboard's Phase 13
`Demo Mode`. The manual labs remain separate on purpose, and the quick REST-only
seed is available from `scripts/seed_demo.py` when you want the canonical
HomeLab + LocalAIAgentStack foundation quickly.

For presenter-friendly paths after seeding, use:

- [`labs/guided_demo_scenarios.md`](./labs/guided_demo_scenarios.md)
- [`labs/sales_engineering_walkthrough.md`](./labs/sales_engineering_walkthrough.md)

## Bundled local scenarios

| Scenario | Org / Workspace | Models | Demonstrates |
|---|---|---|---|
| `ollama/01_coding_assistant` | Acme Dev Tools / Coding Assistant | `qwen2.5-coder:14b`, `deepseek-r1:14b`, `deepseek-r1:8b` | Priced local coding/reasoning, semantic cache, compiler, tool filtering, intelligent routing, budgets, alerts |
| `ollama/02_local_rag` | DataCo / Knowledge Base | `llama3.1:8b`, `nomic-embed-text` | RAG generation vs embedding cost, relevance and faithfulness scores, helpful-answer outcomes |
| `ollama/03_reasoning_agent` | ThinkLocal / Reasoning | `deepseek-r1:14b`, `deepseek-r1:8b` | Output-heavy reasoning spend, cost vs quality comparisons, decision-supported outcomes |
| `ollama/04_chat_support` | HelpDesk Local / Support Bot | `llama3.2`, `gemma3:latest` | High-volume support traffic, local ticket outcomes, daily/monthly budgets, approval requests, auto-approval policies, chargeback rules, runbook generation |
| `ollama/05_guardrails` | SafeGuard AI / Content Safety | (API-only, no model traffic) | Custom guardrails, 13 built-in content filters, PII detection, prompt injection guard, partner integrations (Presidio, Lakera, OpenAI Moderation), test playground, regression testing |
| `ollama/06_intelligence` | IntelliOps / ML Intelligence | `qwen2.5-coder:14b`, `deepseek-r1:14b`, `llama3.2` | Anomaly detection, cost/token forecasting, Top-K analysis, pattern recognition, complexity scoring, cost-per-outcome, adaptive alerts, ML dashboard |
| `ollama/07_advanced_budgets` | BudgetLabs / Advanced Budgets | `qwen2.5-coder:14b`, `deepseek-r1:14b`, `llama3.2` | Budget tiers (Free/Starter/Pro/Enterprise), model-specific budgets with wildcards, temporary overrides with auto-expiry, throttle/fallback enforcement, billing summary |

## Hosted scenarios

The `hosted/` folder is kept as optional reference material for mixed-provider demos.
Those scenarios are no longer part of the default run because the current local demo
uses only `scripts/pricing.yaml`, and that catalog is Ollama-only.

## LocalAI Agent Stack integration scenarios

The LocalAI integration is separate from the default scenario library because it is
meant to connect to another local repo and keep its generated API keys private.

Use these helpers from the repo root:

```powershell
python scripts\localai\bootstrap_runledger_org.py
python scripts\localai\inject_mcp_configs.py
python scripts\localai\localai_s3_backup.py backup
python scripts\localai\generate_agent_traffic.py --workspace "Python Console" --source python-console
python scripts\localai\generate_otlp_traffic.py --workspace "Open WebUI" --source open-webui-otel
```

That creates the `LocalAI Agent Stack` org and separate workspaces for LiteLLM,
Open WebUI, OpenHands, LangGraph, Hermes Agent, Claude Desktop, OpenAI Codex,
Python Console, and Backup Restore Lab. See [`../README.md`](../README.md) for the
full runbook, including S3 backup/restore, SDK-style traffic, OTLP trace ingestion,
and why Claude/Codex use MCP or wrappers for out-of-band telemetry unless a spawned
tool can be routed through the Gateway.

## Writing a scenario

Create a file in any folder, usually under `scripts/scenarios/ollama/`:

```python
from scenarios._base import Sim

NAME = "my-local-scenario"
DESCRIPTION = "One line describing what this simulates."

def run(sim: Sim) -> None:
    ws = sim.workspace("My Org", "My Workspace")
    ws.add_route("chat", "llama3.2", base_url="http://host.docker.internal:11434/v1")
    runs = ws.ingest_runs(
        100,
        models=["llama3.2"],
        features=["chat"],
        users=["u_1", "u_2"],
        days=30,
        success_rate=0.94,
        sessions=10,
    )
    ws.add_budget("workspace", 50, period_type="monthly", action="notify")
    for r in ws.sample(runs, 20):
        ws.record_outcome(r, "resolved", value_usd=6.0)
        ws.score(r, "quality", 0.9)
```

## Helper API

Defined in `_base.py`; every method maps to a real API call and is best-effort.

| Method | Populates |
|---|---|
| `ingest_runs(n, models=, features=, users=, days=, success_rate=, sessions=)` | Runs, spans, and provider calls via `/ingest/v1/batch`; run count is multiplied by `--traffic-multiplier` |
| `ingest_rich_runs(n, models=, workflows=, users=, days=, success_rate=, sessions=)` | Runs with workflow metadata (agent, skill, tool, team, route, prompt) |
| `ingest_otlp_traces(n, models=, workflows=)` | OTLP traces with agent→LLM→tool span trees |
| `seed_prompt_eval_assets(prompts=, dataset_name=, models=)` | Prompt versions, evaluation datasets, and experiment records |
| `add_route(alias, model, priority=, **flags)` | Gateway routes, including Ollama `base_url`, cache, compiler, routing, and policy flags |
| `add_budget(scope_type, limit_usd, period_type=, action=, scope_id=)` | Workspace, feature, or user budgets |
| `record_outcome(run, outcome_type, success=, value_usd=, labels=)` | Business outcomes for ROI dashboards |
| `score(run, metric_name, value, label=)` | Evaluation score events |
| `add_alert(name, metric, operator, threshold)` | Alert rules |
| `create_approval_request(request_type, reason, metadata=)` | Approval requests (budget increase, premium model use, etc.) |
| `add_auto_approval_policy(request_type, max_amount=, conditions=)` | Auto-approval policies for low-risk requests |
| `add_chargeback_rule(name, match_field, match_value, cost_center, split_percent=)` | Chargeback rules for cost attribution to business units |
| `generate_runbook(run)` | Incident-style runbook for a run |
| `create_route_recommendation(experiment_id, config_index, reason)` | Route recommendations from replay experiments |
| `get_governance_audit_pack()` | Governance audit pack (compliance evidence export) |
| `upsert_capture_policy_scope(scope_type, scope_id, privacy_mode, sampled_rate=)` | Data-capture scoped overrides |
| `create_oidc_provider(name, issuer_url, audience=)` | Enterprise OIDC provider setup |
| `create_ip_acl_rule(cidr, scope_type=, action=, priority=)` | IP allow/deny controls |
| `create_tag(category, key, value, description=)` | Taxonomy tag creation |
| `create_auto_tag_rule(name, match_field, match_pattern, tag_key, tag_value)` | Auto-tagging rule lifecycle |
| `create_guardrail_rule(name, mode, rule_type, logic, ...)` | Custom/template guardrail rule |
| `activate_content_filters(filters)` | Activate built-in content filters with severity |
| `create_partner_guardrail(provider, name, mode, ...)` | Partner guardrail integration |
| `test_guardrail(guardrail_id, texts, metadata)` | Test a single guardrail |
| `test_all_guardrails(texts, model, metadata)` | Test all active guardrails |
| `create_guardrail_test_case(rule_id, name, input_text, expected)` | Regression test case |
| `run_guardrail_regression(guardrail_id)` | Run regression test suite |
| `get_guardrail_stats(hours)` | Guardrail monitoring stats |
| `list_guardrail_events(limit)` | Guardrail event log |
| `submit_guardrail_feedback(event_id, is_false_positive, reason)` | Mark event as false positive |
| `evaluate_guardrail_alerts(window_hours, baseline_hours)` | Trigger alert evaluation |
| `list_guardrail_alerts(alert_type, status, limit)` | List guardrail alerts |
| `acknowledge_guardrail_alert(alert_id)` | Acknowledge a guardrail alert |
| `list_anomalies(severity=)` | List detected ML anomalies |
| `get_anomaly_summary(hours=)` | Anomaly summary counts by severity |
| `generate_forecast(forecast_type=, horizon_days=)` | Generate on-demand cost/token forecast |
| `get_cost_forecast()` | Get latest cost forecast |
| `get_top_k(dimension=, metric=, k=)` | Top-K ranking with change detection |
| `list_patterns()` | List detected usage patterns |
| `get_cost_per_outcome()` | Cost-per-outcome with Pareto frontier |
| `retrain_complexity()` | Trigger complexity model retraining |
| `get_complexity_scores(hours=)` | Recent request complexity scores |
| `get_feature_importances()` | Complexity model feature importances |
| `get_adaptive_suggestions()` | Adaptive alert threshold suggestions |
| `train_isolation_forest(days=)` | Train Isolation Forest for multivariate anomaly detection |
| `get_ml_dashboard()` | ML observability dashboard |
| `create_budget_tier(name, max_spend_usd=, rpm_limit=, tpm_limit=, allowed_models=, is_default=)` | Budget tiers with RPM/TPM/spend/model-access limits |
| `assign_tier_to_key(key_id, tier_id=)` | Assign or unassign a budget tier to an API key |
| `create_model_budget(key_id, model_pattern, max_spend_usd=, rpm_limit=, tpm_limit=, action=)` | Per-model spend/rate limits with trailing * wildcards |
| `create_budget_override(budget_id, override_limit_usd, starts_at, expires_at, reason=)` | Temporary budget increases with auto-expiry |
| `list_budget_overrides(budget_id)` | List overrides for a budget |
| `revoke_budget_override(budget_id, override_id)` | Revoke an active override immediately |
| `get_billing_summary(months=)` | Billable vs non-billable cost breakdown by period |
