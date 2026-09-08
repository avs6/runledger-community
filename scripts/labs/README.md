# RunLedger Lab Workbook

Hands-on labs and feature guides for RunLedger. Every lab uses the same
canonical scenario so manual work, automated scripts, and guided demos all
tell the same story.

## Canonical Scenario

Platform admin: `admin@runledger.local` / `runledger`

**Org 1 — HomeLab**

- Admin: `admin@homelab.com`
- Users: `user1@homelab.com`, `user2@homelab.com`
- Workspace: `AgentTest`
- Focus: SDK instrumentation, budgets, outcomes, observability

**Org 2 — LocalAIAgentStack**

- Admin: `admin@localstack.com`
- Users: `user1@localstack.com`, `user2@localstack.com`
- Workspaces: `LiteLLM Gateway`, `OpenWebUI`, `Codex`, `Langgraph`, `HermesAgent`, `Claude Desktop`, `OpenAICodes`, `PythonAgents`
- Focus: gateway routing, OTLP, MCP, integration testing

Every account uses password `runledger`.

## Prerequisites

- Stack running: `docker compose up -d`
- Dashboard: `http://localhost:3201`
- API: `http://localhost:8201`
- Local Ollama with `llama3.2` pulled
- Python 3.11+

Quick preflight:

```bash
curl http://localhost:8201/health/live
curl http://localhost:11434/api/tags
docker compose ps runledger-api runledger-web runledger-worker
```

## Getting Started

### Fresh start

```bash
docker compose down -v
docker compose up -d
```

Log in as `admin@runledger.local / runledger`.

### Set up the lab environment

```bash
cd scripts/labs/agents
python -m venv .venv
pip install -e "../../../packages/sdk[openai]"
pip install -r requirements.txt
cp .env.example .env
```

### Create the foundation in the UI

1. Log in as the platform admin.
2. Create org `HomeLab`, add workspace `AgentTest`.
3. Invite `admin@homelab.com`, `user1@homelab.com`, `user2@homelab.com`.
4. Create org `LocalAIAgentStack`, add all 8 workspaces listed above.
5. Invite `admin@localstack.com`, `user1@localstack.com`, `user2@localstack.com`.

Or run the automated seed instead:

```bash
python scripts/run_demo.py seed-demo
```

### Import pricing

Open **Provider Profiles** and import [`pricing.sample.yaml`](./pricing.sample.yaml).

### Mint workspace API keys

Create one key each for:

- `HomeLab / AgentTest`
- `LocalAIAgentStack / Langgraph`
- `LocalAIAgentStack / LiteLLM Gateway`

Update `agents/.env` with the key for each lab.

## Hands-on Labs

| Lab | Script | Workspace | What you learn |
|---|---|---|---|
| Inline SDK | `lab_01_inline_sdk.py` | HomeLab / AgentTest | Auto-capture model calls with the RunLedger SDK |
| OTLP Instrumentation | `lab_02_otlp_out_of_band.py` | LocalAIAgentStack / Langgraph | Send OpenTelemetry spans to RunLedger |
| Gateway Proxy | `lab_03_gateway_proxy.py` | LocalAIAgentStack / LiteLLM Gateway | Route calls through gateway aliases with caching |
| Budget Enforcement | `lab_04_budget_enforcement.py` | HomeLab / AgentTest | Workspace budget blocking |
| Outcomes & Scores | `lab_05_outcomes_scores.py` | HomeLab / AgentTest | Attach quality scores and business outcomes |

## Feature Guides

Deeper walkthroughs for each RunLedger feature area:

**Observability & Investigation**
- [Observability](./observability.md) — explore runs, traces, and request flow in the dashboard

**Quality & Evaluation**
- [Quality & Evaluation](./quality-evaluation.md) — experiments, replay, prompt management, model comparison

**Optimization**
- [Optimization](./optimization.md) — gateway routing, semantic caching, intelligent routing
- [Gateway Scale](./gateway-scale.md) — benchmarking, pass-through analytics, multi-region

**Governance & Security**
- [Governance](./governance.md) — approval flows, audit, and policy management
- [Guardrails](./guardrails.md) — content safety, custom rules, and policy engine

**FinOps**
- [Advanced Budgets](./advanced-budgets.md) — tiered budgets, model budgets, throttle/fallback
- [Billing & Reconciliation](./billing-reconciliation.md) — invoice reconciliation workflow
- [Chargeback](./chargeback.md) — cost allocation across teams and orgs
- [Ledger Closure](./ledger-closure.md) — compliance and period closure

**Intelligence**
- [ML Intelligence](./ml-intelligence.md) — anomaly detection, forecasting, top-K, patterns

**Platform**
- [Platform Settings](./platform-settings.md) — telemetry, providers, and control plane config
- [AI Hub Catalog](./ai-hub-catalog.md) — model catalog management
- [MCP Registry](./mcp-registry.md) — MCP server registration, permissions, and tools
- [Integrating an Existing Stack](./integrating-existing-stack.md) — connect external AI tools to RunLedger

**Demos**
- [Guided Demo Scenarios](./guided_demo_scenarios.md) — before/after storytelling with the simulator
- [Sales Engineering Walkthrough](./sales_engineering_walkthrough.md) — 12–20 minute prospect demo
