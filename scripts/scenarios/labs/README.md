# RunLedger Lab Workbook

This workbook uses the same fixed foundation as the normalized demo seed so the
manual labs, scenarios, and scripts all tell the same story.

## Foundation

Platform admin:

- `admin@runledger.local`
- Password: `runledger`

Org 1: `HomeLab`

- Admin: `admin@homelab.com`
- Users: `user1@homelab.com`, `user2@homelab.com`
- Workspace: `AgentTest`
- Main purpose: inline SDK, budgets, outcomes, and observability drills

Org 2: `LocalAIAgentStack`

- Admin: `admin@localstack.com`
- Users: `user1@localstack.com`, `user2@localstack.com`
- Workspaces:
  - `LiteLLM Gateway`
  - `OpenWebUI`
  - `Codex`
  - `Langgraph`
  - `HermesAgent`
  - `Claude Desktop`
  - `OpenAICodes`
  - `PythonAgents`
- Main purpose: gateway, OTLP, MCP, and integration drills

Every local account in this workbook uses password `runledger`.

## Lab mapping

| Lab | Workspace | Why |
|---|---|---|
| Lab 01 - Inline SDK | `HomeLab / AgentTest` | Small workspace for core runtime validation |
| Lab 02 - OTLP | `LocalAIAgentStack / Langgraph` | Best fit for traced application traffic |
| Lab 03 - Gateway | `LocalAIAgentStack / LiteLLM Gateway` | Best fit for route aliases and cache behavior |
| Lab 04 - Budgets | `HomeLab / AgentTest` | Simple workspace budget enforcement story |
| Lab 05 - Outcomes | `HomeLab / AgentTest` | Keeps quality and ROI review in one place |

## Prerequisites

- Dashboard: `http://localhost:3201`
- API: `http://localhost:8201`
- Local Ollama running with `llama3.2` pulled
- Python 3.11+

Quick preflight:

```bash
curl http://localhost:8201/health/live
curl http://localhost:11434/api/tags
docker compose ps runledger-api runledger-web runledger-worker
```

## Module 0 - Fresh start

```bash
docker compose down -v
docker compose up -d
```

Log in as `admin@runledger.local / runledger`.

Set up the lab environment:

```bash
cd scripts/scenarios/labs/agents
python -m venv .venv
pip install -e "../../../../packages/sdk[openai]"
pip install -r requirements.txt
cp .env.example .env
```

## Module 1 - Create the foundation in the UI

1. Log in as the platform admin.
2. Create or rename the first org to `HomeLab`.
3. Add workspace `AgentTest`.
4. Invite `admin@homelab.com`, `user1@homelab.com`, and `user2@homelab.com`.
5. Create the second org `LocalAIAgentStack`.
6. Add these workspaces:
   - `LiteLLM Gateway`
   - `OpenWebUI`
   - `Codex`
   - `Langgraph`
   - `HermesAgent`
   - `Claude Desktop`
   - `OpenAICodes`
   - `PythonAgents`
7. Invite `admin@localstack.com`, `user1@localstack.com`, and `user2@localstack.com`.

Verify that both orgs, all workspaces, and all users appear in the dashboard.

## Module 2 - Import pricing

Open **Provider Profiles** and import [`pricing.sample.yaml`](./pricing.sample.yaml).

Verify that local models like `llama3.2` appear with prices.

## Module 3 - Mint workspace API keys

Create one key each for:

- `HomeLab / AgentTest`
- `LocalAIAgentStack / Langgraph`
- `LocalAIAgentStack / LiteLLM Gateway`

Swap the key in `agents/.env` as you move between labs.

## Module 4 - Lab 01: Inline SDK

Use the `HomeLab / AgentTest` key.

```bash
python lab_01_inline_sdk.py
```

Verify new `support-chat` runs under `AgentTest`.

## Module 5 - Lab 02: OTLP

Use the `LocalAIAgentStack / Langgraph` key.

```bash
python lab_02_otlp_out_of_band.py
```

Verify new traced runs from `agent.run`.

## Module 6 - Lab 03: Gateway

As an org admin, create route alias `qa-chat` on `LocalAIAgentStack / LiteLLM Gateway`:

- Provider: `ollama`
- Model: `llama3.2`
- Base URL: `http://host.docker.internal:11434/v1`
- Semantic cache: on

Use the `LocalAIAgentStack / LiteLLM Gateway` key.

```bash
python lab_03_gateway_proxy.py
```

Verify gateway requests and a cache hit on the repeated prompt.

## Module 7 - Lab 04: Budgets

In `HomeLab / AgentTest`, create a daily workspace budget:

- Limit: `0.05`
- Action: `block`

Use the `HomeLab / AgentTest` key.

```bash
python lab_04_budget_enforcement.py
```

Verify the workspace budget blocks later requests.

## Module 8 - Lab 05: Outcomes and scores

Use the `HomeLab / AgentTest` key.

```bash
python lab_05_outcomes_scores.py
```

Verify seeded scores in **Evaluation** and outcomes in **Outcomes**.

## Workbook continuation

Work through the rest of the guided parts from this same foundation:

- [Part 2 - Observe & Investigate](./part2_observe.md)
- [Part 3 - Quality & Experiments](./part3_quality.md)
- [Part 4 - Optimization Layer](./part4_optimization.md)
- [Part 5 - Governance & Control](./part5_governance.md)
- [Part 6 - Operations](./part6_operations.md)
- [Part 7 - Control Plane & Platform Settings](./part7_settings.md)
- [Part 7B - MCP Registry](./part7_mcp_registry.md)
- [Part 7A - AI Hub Model Catalog](./part7_ai_hub_model_catalog.md)
- [Part 8 - Integrating an Existing Stack](./part8_integrating_existing_stack.md)
- [Part 9 - Guardrails & Content Safety](./part9_guardrails.md)
- [Guided Demo Scenarios](./guided_demo_scenarios.md)
- [Sales Engineering Walkthrough](./sales_engineering_walkthrough.md)
