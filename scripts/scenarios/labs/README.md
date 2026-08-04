# RunLedger Lab — a hands-on workbook

A guided, click-and-run lab that takes you from a **freshly nuked stack** to a
fully exercised RunLedger deployment. You'll play two roles:

1. **The operator** (you, installing RunLedger for a customer) — you set everything
   up in the **dashboard GUI**: the company, its teams, users, pricing, budgets,
   gateway routes, and API keys.
2. **The customer's developers** — you run small **Python agent scripts** that call
   RunLedger the way real apps do, then confirm the data on the dashboard.

Everything runs against **local Ollama**, so you need no cloud API keys.

> This is a manual workbook, not an automated seed. It is intentionally *not* picked
> up by `full_simulate.py`. Work through it top to bottom the first time.

---

## The scenario

You're onboarding one customer company — **Acme Corp** *(rename to whatever you like)* —
which has **three AI teams**. In RunLedger, the company is one **organization** and each
team is a **workspace** with its own API key, data, budgets, and members:

| Team (workspace) | What they do | Instrumentation type they use | Lab |
|---|---|---|---|
| **AI Support Team** | Customer-support bots | Inline SDK | 01, 04, 05 |
| **AI Development Team** | Prototyping new agents | Out-of-band OTLP | 02 |
| **AI Test Team** | QA / regression testing | Gateway proxy | 03 |

People you'll create (roles show off RunLedger's access model):

| User | Role | Sees |
|---|---|---|
| `admin@runledger.local` | **Platform admin** (seeded) | everything — this is *you*, the operator |
| `owner@acme.example` | **Org admin** | all three teams; Gateway, Provider Profiles, Control Plane, Users, Workspace |
| `support-lead@acme.example` | **Workspace admin** — AI Support Team | one team; API Keys, Budgets, Outcomes, Approvals, Audit Log |
| `dev-lead@acme.example` | **Workspace admin** — AI Development Team | one team; API Keys, Budgets, Outcomes, Approvals, Audit Log |
| `qa-lead@acme.example` | **Workspace admin** — AI Test Team | one team; API Keys, Budgets, Outcomes, Approvals, Audit Log |
| `analyst@acme.example` | **Member (read-only)** — AI Support Team | one team, view only |

Role handoff for the workbook:

| Work | Use this role |
|---|---|
| Create organizations or platform Settings | Platform admin |
| Rename org, create workspaces, users, Gateway routes, Provider Profiles, Alert Rules, MCP, Integrations, Data Capture | Org admin |
| Mint a key for the active workspace, manage budgets, review Approvals/Audit Log | Workspace admin |
| Review Runs, Sessions, Analytics, Prompts, Monitoring without edits | Member |

---

## The three instrumentation *types* (the mental model)

RunLedger can capture your agents three ways. The lab does one of each so you can
feel the difference:

| Type | How it works | RunLedger in the request path? | When to use | Lab |
|---|---|---|---|---|
| **Inline SDK** | `rl.instrument()` patches your LLM client in-process | No — events buffered & sent async | You own the code and want the richest data (scores, outcomes, budgets) | 01 |
| **Out-of-band OTLP** | Your app's OpenTelemetry spans are exported to RunLedger by a background thread | No — off the hot path | You already use OTel, or can't add the SDK | 02 |
| **Gateway proxy** | Your client calls RunLedger's OpenAI-compatible `/gateway`; it routes & caches | **Yes** — it can cache and switch models | You want central routing, caching, and model swaps with no redeploy | 03 |

---

## The reusable traffic generator

Almost everything in the workbook is done in the **GUI**. The one piece of code you run is a
single reusable agent — [`agents/traffic_gen.py`](./agents/traffic_gen.py) — that generates
LLM traffic. You never edit it; you **re-point it with environment variables**:

```bash
# 30 runs into whatever team the .env key belongs to, tagged, with scores + outcomes
LAB_FEATURE_TAG=support-chat LAB_RUNS=30 python traffic_gen.py

# route through a gateway alias to exercise a routing policy you configured in the GUI
LAB_GATEWAY_ALIAS=cached-chat LAB_RUNS=30 python traffic_gen.py
```

PowerShell equivalent:

```powershell
$env:LAB_FEATURE_TAG='support-chat'; $env:LAB_RUNS='30'; python traffic_gen.py
$env:LAB_GATEWAY_ALIAS='cached-chat'; $env:LAB_RUNS='30'; python traffic_gen.py
```

Swap `RUNLEDGER_API_KEY` in `.env` to switch which **team/workspace** the traffic lands in.
Whenever a module says *"generate some traffic"*, this is what it means. (The five Part-1
scripts, `lab_01`…`lab_05`, remain as focused demos of each instrumentation *type*.)

Ready-to-load **sample assets** live in [`samples/`](./samples) — a dataset, prompt texts,
gateway routing policies, tool policies, and evaluator configs you paste/import in the GUI.

---

## The workbook, in parts

Work through them in order the first time. Part 1 is the rest of this file; Parts 2–6 are
linked guides.

| Part | Covers |
|---|---|
| **Part 1** (below) | Setup · the three instrumentation types · budgets · outcomes |
| **[Part 2 · Observe & Investigate](./part2_observe.md)** | Runs · Sessions · Analytics · Monitoring/Alerts · Audit Logs |
| **[Part 3 · Quality & Experiments](./part3_quality.md)** | Prompts · **Evaluation vs Experiments vs Replay** · Datasets |
| **[Part 4 · Optimization layer](./part4_optimization.md)** | Exact cache · semantic cache · compiler · compression · routing · MCP tool filtering · flywheel |
| **[Part 5 · Governance & Control](./part5_governance.md)** | Gateway guardrails · Tool Registry · Approvals · Auto-approval policies · Chargeback · Runbooks · Model Scorecards · Policy Dry Run · Governance Audit Pack |
| **[Part 6 · Operations](./part6_operations.md)** | Add workspace · local backup · Qdrant snapshots · restore drills · ledger integrity · S3 restore |
| **[Part 7 - Control Plane & Platform Settings](./part7_settings.md)** | OTLP · MCP · Integrations · Data Capture · Compliance · Retention · Email |
| **[Part 8 · Integrating an existing stack](./part8_integrating_existing_stack.md)** | How customers adopt RunLedger beside an existing AI stack (hub instrumentation, gateway, SDK) |

---

## Prerequisites

- The RunLedger stack (this repo). Dashboard at **http://localhost:3201**, API at **http://localhost:8201**.
- **Ollama** running on your host with a model pulled:
  ```bash
  ollama pull llama3.2
  ```
- **Python 3.11+**.

Quick preflight:

```bash
curl http://localhost:8201/health/live
curl http://localhost:11434/api/tags
docker compose ps runledger-api runledger-web runledger-worker
```

You want the API to return `{"status":"ok"}`, Ollama to list at least one model, and the API/web/worker containers to be up.

---

## Module 0 · Fresh start

**Goal:** an empty stack with nothing but the seeded admin login.

1. Nuke all data and bring the stack back up (from the repo root):
   ```bash
   docker compose down -v && docker compose up -d
   ```
   On boot, RunLedger auto-creates a platform admin and an empty default org.
2. Open **http://localhost:3201** and log in:
   - **Email:** `admin@runledger.local`
   - **Password:** `runledger`
3. Set up the Python environment for the agent scripts:
   ```bash
   cd scripts/scenarios/labs/agents
   python -m venv .venv
   # Windows:  .venv\Scripts\activate       macOS/Linux:  source .venv/bin/activate
   pip install -e "../../../../packages/sdk[openai]"
   pip install -r requirements.txt
   cp .env.example .env
   ```

✅ **Verify:** you're logged into the dashboard and `pip list` shows `runledger-sdk`, `openai`, and `opentelemetry-sdk`.

---

## Module 1 · Provision the company & teams  *(GUI)*

**Goal:** one org, three team-workspaces, users with roles — all by clicking.

1. **Name the company.** As an org admin or platform admin, open **Org Profile** in the sidebar. Rename the default org
   to **Acme Corp** (or create a new org if your build offers it).
2. **Create the three teams.** As an org admin, open **Workspace** and add three workspaces:
   `AI Support Team`, `AI Development Team`, `AI Test Team`.
3. **Invite the people.** As an org admin, open **Users** → invite each user from the table above and
   assign their role (org admin / workspace admin / member).

> 💡 **Local-stack note.** User invites normally send an email. If your local stack
> has no SMTP configured, invited users may not receive a link — that's fine for the
> lab: you (the platform admin) can operate all three teams. The users + roles step is
> there to *show* the governance model; you don't need to log in as each one.

✅ **Verify:** the **Workspace** page lists three teams under Acme Corp; **Users** lists the members with their roles.

---

## Module 2 · Upload the pricing catalog  *(GUI)*

**Goal:** price your local models so cost is tracked (a $0 model never shows spend or trips a budget).

1. As an org admin, open **Provider Profiles** in the sidebar.
2. Use **Import** and upload [`pricing.sample.yaml`](./pricing.sample.yaml) (next to this file).
3. It's **idempotent** — re-importing updates rows in place. The catalog now lives in the database.

✅ **Verify:** the Provider Profiles page lists `llama3.2`, `qwen2.5-coder:14b`, `nomic-embed-text`, etc. with prices and tags.

---

## Module 3 - Mint API keys  *(GUI - org or workspace admin)*

**Goal:** one workspace key per team; the scripts authenticate with these.

> **API-key management is a dashboard function.** Org admins can mint keys for any workspace in their org; workspace admins can mint keys only for their active workspace. A plain API key cannot mint keys.

1. Open **Control Plane -> API Keys**. In the create form, **pick a workspace** - start with
   **AI Support Team** — give the key a name, and **Create Key**. Copy it (shown once).
2. Repeat, picking **AI Development Team**, then **AI Test Team**. The list shows a
   **Workspace** column so you can see which key belongs to which team.
3. Keep all three keys handy.

Each key is scoped to exactly one team; **swapping the key is how you switch teams**.
Put the relevant key in `agents/.env` before running each lab:

```
RUNLEDGER_API_KEY=rl_...      # the team whose lab you're about to run
```

✅ **Verify:** three keys exist — the list's **Workspace** column shows one per team.

---

## Module 4 · Lab 01 — Inline SDK  *(AI Support Team)*

Put the **AI Support Team** key in `.env`, then:

```bash
python lab_01_inline_sdk.py
```

Two lines (`RunLedger()` + `rl.instrument()`) make every Ollama call show up in
RunLedger — tokens, latency, cost — with a quality score attached.

✅ **Verify (dashboard → Runs):** new runs tagged `support-chat`; open one to see the
`provider_call` (model `llama3.2`) and the `helpfulness` score. Cost appears after
Celery enrichment (~30–60s).

📄 [`agents/lab_01_inline_sdk.py`](./agents/lab_01_inline_sdk.py)

---

## Module 5 · Lab 02 — Out-of-band OTLP  *(AI Development Team)*

Swap in the **AI Development Team** key, then:

```bash
python lab_02_otlp_out_of_band.py
```

No SDK patching — a standard OpenTelemetry tracer exports an `agent → tool → llm`
span tree to RunLedger's `/v1/traces` from a background thread.

✅ **Verify (dashboard → Runs):** an `agent.run` trace with a nested LLM call (180
tokens) and a `search_docs` tool call — captured purely from OTel spans.

📄 [`agents/lab_02_otlp_out_of_band.py`](./agents/lab_02_otlp_out_of_band.py)

> **Collector variant (optional).** The stack runs an OTel Collector on `:4318`. Point
> a vanilla `OTLPSpanExporter` at `http://localhost:4318` and it forwards to RunLedger —
> useful when many services already ship to one collector.

---

## Module 6 · Lab 03 — Gateway proxy  *(AI Test Team)*

First, in the GUI as an org admin, open **Gateway** and create a route:

| Field | Value |
|---|---|
| Alias | `qa-chat` |
| Provider | `ollama` |
| Target model | `llama3.2` |
| Base URL | `http://host.docker.internal:11434/v1` ⚠️ **not** `localhost` |
| Priority | `1` |
| Semantic cache | **ON** |

> The Gateway runs *inside Docker*; it reaches your host's Ollama via
> `host.docker.internal`. `localhost` would point at the container itself.

Swap in the **AI Test Team** key, then:

```bash
python lab_03_gateway_proxy.py
```

The client calls the alias `qa-chat` through RunLedger's `/gateway`. We send the same
prompt twice — with semantic cache ON, the second is a cache hit.

✅ **Verify (dashboard → Gateway):** the `qa-chat` route's request count rises and the
cache registers a hit on the second call.

📄 [`agents/lab_03_gateway_proxy.py`](./agents/lab_03_gateway_proxy.py)

---

## Module 7 · Lab 04 — Budget enforcement  *(AI Support Team)*

First, in the GUI (as the AI Support Team's workspace admin), open **Budgets** and create:

| Field | Value |
|---|---|
| Scope | workspace |
| Period | daily |
| Limit | `0.05` (tiny on purpose) |
| Action | **block** |

> Budgets are created in the GUI on purpose — setting a spend cap requires a
> workspace-admin **dashboard session**, which an API key can't provide. (This is the
> one governance action the agent scripts can't do for you.)

Put the **AI Support Team** key back in `.env`, then:

```bash
python lab_04_budget_enforcement.py
```

`budget_check=True` makes the SDK check the budget before each call. As processed spend
crosses \$0.05, a call raises `RunLedgerBudgetExceededError` and the agent stops.

✅ **Verify (dashboard → Budgets):** utilization crosses 100% and the budget blocks. The
console shows the exact call that was refused.

📄 [`agents/lab_04_budget_enforcement.py`](./agents/lab_04_budget_enforcement.py)

---

## Module 8 · Lab 05 — Outcomes & scores  *(AI Support Team)*

```bash
python lab_05_outcomes_scores.py
```

Each run gets a quality **score** and a business **outcome** (`ticket_resolved`, with a
dollar value) — the raw material for ROI and cost-per-outcome analytics.

✅ **Verify:** **Evaluation** shows `resolution_quality` scores; **Outcomes** shows
`ticket_resolved` with \$ values.

📄 [`agents/lab_05_outcomes_scores.py`](./agents/lab_05_outcomes_scores.py)

---

## Module 9 · Read the results  *(GUI)* — what to look for

By now the AI Support Team workspace has runs, cost, scores, outcomes, and a tripped
budget. Explore and interpret:

- **Runs** — filter by `feature_tag` / `end_user_id`. Every call is attributed to a user and feature.
- **Analytics → Economics** — cost by model/feature. Confirm your priced Ollama models show real (small) spend, not \$0.
- **Analytics → Users** — per-end-user cost. Who is expensive?
- **Outcomes** — cost-per-outcome / ROI: are resolved tickets worth more than they cost?
- **Evaluation** — quality trend. Is a cheaper model good enough?
- **Budgets** — the breached cap and its enforcement action.

🔎 **The point:** each team is isolated (its own key, data, budget), yet the org admin
sees them all — that's the multi-team story you'd show a customer.

---

## Reset

- **Wipe everything and start over:** `docker compose down -v && docker compose up -d`
- **Keep the stack, clear only data:** `uv run python scripts/cleanup.py`
  (preserves admin + pricing; use `--hard` to wipe volumes too)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RUNLEDGER_API_KEY is not set` | Mint a key (Module 3) and put it in `agents/.env`. |
| `401 Unauthorized` from a script | Key is for a different/deleted workspace, or you nuked the stack after minting it. Mint a fresh one. |
| Cost stays `$0` on runs | Upload pricing (Module 2) and wait ~60s for Celery to enrich. Local models are $0 until priced. |
| Gateway route 500 / can't reach Ollama | Base URL must be `http://host.docker.internal:11434/v1`, not `localhost`. |
| Budget never blocks (Lab 04) | Lower the limit, confirm `action=block`, and ensure pricing is uploaded so calls cost > $0. |
| Ollama connection refused | `ollama serve` running? `ollama pull llama3.2` done? Check `curl http://localhost:11434/api/tags`. |

---

## Files in this lab

```
labs/
  README.md                       ← this workbook (Part 1)
  part2_observe.md                ← Runs · Sessions · Analytics · Monitoring · Audit
  part3_quality.md                ← Prompts · Evaluation · Datasets · Experiments · Replay
  part4_optimization.md           ← cache · compiler · compression · routing · tool filtering · MCP · flywheel
  part5_governance.md             ← gateway guardrails · Tool Registry · Approvals · Auto-approval · Chargeback · Runbooks · Scorecards · Dry Run · Audit Pack
  part6_operations.md             ← add workspace · backup · snapshots · restore drills
  part7_settings.md               ← OTLP · MCP · Integrations · Data Capture · Retention · Email
  part8_integrating_existing_stack.md  ← adopt RunLedger beside an existing AI stack
  pricing.sample.yaml             ← upload in Provider Profiles (Module 2)
  samples/                        ← ready-to-load GUI assets
    dataset_support_faq.json      ← import in Datasets
    prompts.md                    ← paste in Prompts
    routing_policies.md           ← configure on Gateway routes
    evaluators.md                 ← create on Evaluation
    tools_and_policies.md         ← register in Tool Registry
    tool_filtering_catalog.json   ← sample tool schemas for MCP/tool-filtering labs
  agents/
    requirements.txt              ← pip installs
    .env.example                  ← copy to .env, add your key
    _config.py                    ← shared connection settings + traffic-gen knobs
    traffic_gen.py                ← the reusable traffic generator (Parts 2–6)
    lab_01_inline_sdk.py          ← inline SDK          (AI Support Team)
    lab_02_otlp_out_of_band.py    ← out-of-band OTLP    (AI Development Team)
    lab_03_gateway_proxy.py       ← gateway proxy       (AI Test Team)
    lab_04_budget_enforcement.py  ← budgets             (AI Support Team)
    lab_05_outcomes_scores.py     ← outcomes + scores   (AI Support Team)
```

For more integration examples (LangChain, LangGraph, Anthropic, MCP, semantic cache,
etc.) see the repo-level [`examples/`](../../../../examples) folder.
