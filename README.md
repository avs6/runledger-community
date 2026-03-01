# RunLedger

**Billing-grade observability for AI agents.**

RunLedger is an open-source Agent FinOps Control Plane. It turns LangChain, LangGraph, and OpenAI agent runs into trace-linked usage accounting, budgets, chargeback, and economics-aware routing — with payload logging optional by default.

Tracing tools tell you *what happened*. RunLedger tells you *what it cost, who pays, whether you're over budget, and why that model was chosen.*

---

## The Problem

Every team shipping AI agents in production hits the same wall:

- **Spend explodes** — a retry loop or runaway agent silently burns through API budget overnight
- **Chargeback is guesswork** — you can't attribute cost to a tenant, user, or feature without custom instrumentation
- **Routing isn't tied to economics** — model selection is based on capability, not cost-per-outcome
- **Finance can't trust the numbers** — no audit trail linking an invoice line to the exact agent run

---

## What You Get

**Provider-aware metering** — input vs output tokens (plus cached input where available) mapped to provider pricing so your internal numbers match the invoice.

**Spend guardrails that change behavior** — budgets with automatic actions (throttle / block / downgrade model) for runaway loops and retry storms.

**Reconciliation + dispute trail** — prove every invoice line item back to the exact agent run and steps, even with payload logging off.

**End-user analytics** — cost per user/tenant/feature, cost-per-outcome, cohorts, top spenders, anomaly detection — built for customer-facing agents.

**Agent unit economics graph** — cost breakdown across steps, tools, retrieval, retries, and human approvals, plus "what changed?" diffs after prompt or model updates.

**Tamper-evident usage ledger** — cryptographic integrity for usage summaries so finance teams can trust chargeback and invoices.

**Privacy-first modes** — payload logging off by default. Errors-only / sampled / full opt-in. Deploy safely from day one.

---

## Current Status

| Phase | What ships | Status |
|-------|------------|--------|
| 0 | Monorepo · infrastructure · health API · CI | ✅ Complete |
| 1 | Ingestion API · multi-tenancy · API-key auth · event pipeline | ✅ Complete |
| 2 | SDK — OpenAI wrapper · context propagation · local mode | ✅ Complete |
| 3 | SDK — LangChain · LangGraph · CLI · example agents | ✅ Complete |
| 4 | Billing-grade metering · pricing engine · analytics API | ✅ Complete |
| 5 | Run Explorer + DAG viewer UI (Next.js dashboard) | ✅ Complete |
| 6 | Metering dashboard (spend by model/user/feature) | ✅ Complete |
| 7 | Budgets + spend guardrails with automatic actions | ✅ Complete |
| 8 | Chargeback engine + reconciliation + dispute trail | ✅ Complete |
| 9 | Unit economics graph + change impact diffs | ✅ Complete |
| 10 | End-user analytics + replay harness | ✅ Complete |
| 11 | Tamper-evident ledger + security boundaries + privacy governance | ✅ Complete |
| 12 | Settings console · API key management · provider pricing · dark mode | ✅ Complete |
| 14 | Integrations — Slack alerts · analytics export · CI regression gate | ✅ Complete |
| 16 | Production hardening — rate limiting · PII scrubbing · health probes · UI polish | ✅ Complete |

---

## Setup from Scratch

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker + Docker Compose | Latest | Required for the full stack |
| Git | Any | |
| Node.js | 18+ | Only if running the web app outside Docker |
| Python | 3.13+ | Only if running the API outside Docker |
| uv | Latest | Only if running the API outside Docker |

---

### Option A — Docker Compose (recommended)

This is the fastest path. Docker runs Postgres, Redis, the API, the Celery worker, and the dashboard — and automatically runs migrations and seeds the database on first start.

**1. Clone the repo**

```bash
git clone https://github.com/avs6/runledger
cd runledger
```

**2. Start all services**

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts:
- `postgres` — PostgreSQL 16 on port 5432
- `redis` — Redis 7 on port 6379
- `api` — FastAPI on port 8000 (runs migrations + seed automatically on startup)
- `worker` — Celery worker
- `web` — Next.js dashboard on port 3000

On first start the API container prints:

```
→ Running database migrations...
→ Seeding database (idempotent — safe to run on every start)...
Tenant:    default  (a1b2c3d4-...)
Workspace: default  (e5f6g7h8-...)
API Key:   rl_dev_xxxxxxxxxxxxxxxxxxxx

Save the API key — it won't be shown again.

Dashboard login:
  Email:    admin@runledger.local
  Password: runledger
  URL:      http://localhost:3000
→ Starting API...
```

Save the API key — it is shown once and stored hashed. View the logs with:

```bash
docker compose -f infra/docker-compose.yml logs api
```

**3. Verify**

| URL | What it is |
|-----|------------|
| `http://localhost:3000` | Dashboard — Run Explorer + DAG viewer |
| `http://localhost:8000/docs` | Interactive API docs (Swagger UI) |
| `http://localhost:8000/health` | Combined health check — DB + Redis status |
| `http://localhost:8000/health/live` | Liveness probe — always 200 if process is up |
| `http://localhost:8000/health/ready` | Readiness probe — 503 if DB or Redis unreachable |

Sign in at `http://localhost:3000` with `admin@runledger.local` / `runledger`.

**Admin secret** — the Settings page at `http://localhost:3000/settings` lets you manage
tenants. The admin secret for the local stack is `runledger-admin` (set via `ADMIN_SECRET`
in `infra/docker-compose.yml`). The field is pre-filled if you copy `apps/web/.env.local.example`
to `apps/web/.env.local`.

---

### Option B — Local dev (no Docker)

Run each service directly on your machine. Requires Postgres 16, Redis 7, Python 3.13, uv, and Node.js 18+.

**1. Clone and install**

```bash
git clone https://github.com/avs6/runledger
cd runledger
uv sync --all-packages
```

**2. Set environment variables**

Copy the example env files:

```bash
cp apps/api/.env.example        apps/api/.env
cp apps/web/.env.local.example  apps/web/.env.local
```

Key variables in `apps/api/.env`:

```ini
DATABASE_URL=postgresql+asyncpg://runledger:runledger@localhost:5432/runledger
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-change-in-production
ADMIN_SECRET=runledger-admin      # used for /admin/* endpoints and the Settings page
ENVIRONMENT=development
```

Key variables in `apps/web/.env.local`:

```ini
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-change-in-production-32chars!!
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_SECRET=runledger-admin   # pre-fills the admin secret field in Settings
```

**3. Run migrations and seed**

```bash
cd apps/api && uv run alembic upgrade head && uv run python scripts/seed.py
```

**4. Start the API**

```bash
cd apps/api
uv run fastapi dev runledger_api/main.py
```

**5. Start the Celery worker** (separate terminal)

```bash
cd apps/api
uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
uv run celery -A runledger_api.core.celery_app beat --loglevel=info
```

**6. Start the dashboard** (separate terminal)

```bash
cd apps/web
npm install
npm run dev
```

Dashboard runs at `http://localhost:3000`.

---

## Install the SDK

The SDK is not yet published to PyPI. Install directly from the repo.

**Option A — local path** (if you have the repo cloned):

```bash
# Pick the extras you need
pip install -e "/path/to/runledger/packages/sdk[openai]"
pip install -e "/path/to/runledger/packages/sdk[langchain]"
pip install -e "/path/to/runledger/packages/sdk[langgraph]"
pip install -e "/path/to/runledger/packages/sdk[all]"
```

**Option B — directly from GitHub** (no clone needed):

```bash
pip install "runledger-sdk[openai]    @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[langchain] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[langgraph] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[all]       @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
```

Each extra pulls in the right peer dependencies:

| Extra | What it adds |
|-------|-------------|
| `openai` | `openai>=1.0.0` |
| `langchain` | `langchain-core>=0.3.0` |
| `langgraph` | `langchain-core>=0.3.0` + `langgraph>=0.2.0` |
| `all` | everything above + CLI |

---

## Running the Examples

The `examples/` directory contains 13 runnable scripts covering every major feature.
There is also a standalone companion repo — [runledger-samples](https://github.com/avs6/runledger-samples) —
which is an independent Python project you can clone and run without the full monorepo.

### Option A — Run from this repo

**1. Start the infra** (Postgres + Redis + API, from the repo root):

```bash
make dev-d          # full stack in background (includes dashboard)
# or just the infrastructure services:
make dev-infra      # Postgres + Redis only, then run make dev-api in another terminal
```

**2. Set up the examples environment**:

```bash
make samples-setup  # creates examples/.venv and installs all deps
make samples-env    # creates examples/.env from examples/.env.example (if not yet done)
```

Edit `examples/.env` and set your API key (printed by `make logs-api` on first start):

```ini
RUNLEDGER_API_KEY=rl_dev_xxxx...
RUNLEDGER_BASE_URL=http://localhost:8000
RUNLEDGER_LOCAL=false
OPENAI_API_KEY=sk-...
```

**3. Activate the venv and run**:

```bash
# macOS / Linux
source examples/.venv/bin/activate
cd examples
python 01_openai_basic.py

# Windows (PowerShell)
examples\.venv\Scripts\Activate.ps1
cd examples
python 01_openai_basic.py
```

### Option B — Use the standalone runledger-samples repo

```bash
# 1. Clone the samples repo (no need to clone the full monorepo)
git clone https://github.com/avs6/runledger-samples
cd runledger-samples

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install httpx python-dotenv openai langchain langchain-openai langgraph

# 4. Install the RunLedger SDK (from the main repo or directly from GitHub)
pip install "runledger-sdk[all] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

# 5. Create your .env file
cp .env.example .env
# Edit .env: set RUNLEDGER_API_KEY, RUNLEDGER_BASE_URL, OPENAI_API_KEY

# 6. Start the RunLedger infrastructure (from the runledger main repo)
cd /path/to/runledger
make dev-d          # or: docker compose -f infra/docker-compose.yml up -d

# 7. Run any example
cd /path/to/runledger-samples
python 01_openai_basic.py
```

### Example index

| # | Script | Feature |
|---|--------|---------|
| 01 | `01_openai_basic.py` | Basic OpenAI instrumentation |
| 02 | `02_openai_multi_turn.py` | Multi-turn chat with `session_id` |
| 03 | `03_langchain_chain.py` | LangChain `prompt \| llm \| parser` chain |
| 04 | `04_langgraph_agent.py` | LangGraph ReAct agent with `instrument_graph()` |
| 05 | `05_fastapi_service.py` | FastAPI service with per-request async context |
| 06 | `06_ollama_local.py` | Local Ollama via OpenAI-compatible endpoint |
| 07 | `07_analytics_query.py` | Query analytics endpoints, print spend tables |
| 08 | `08_budget_enforcement.py` | Create budget, run until blocked, catch exception |
| 09 | `09_economics_query.py` | Per-run cost, version compare, regression detection |
| 10 | `10_replay_experiment.py` | Create dataset, cost-projection experiment, results |
| 11 | `11_ledger_verify.py` | Generate + verify tamper-evident daily snapshots |
| 12 | `12_settings.py` | API key management, provider pricing overrides |
| 13 | `13_integrations.py` | Slack webhook test, CSV/JSON export, regressions |

---

## Instrument Your Code

### OpenAI (2 lines)

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_dev_...")   # or set RUNLEDGER_API_KEY env var
rl.instrument()                         # wraps openai.OpenAI + AsyncOpenAI

client = openai.OpenAI()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )

rl.shutdown()  # flush before process exits
```

Every call inside the `with` block is tracked: model, tokens, latency, and cost in USD.

### LangChain

```python
from runledger_sdk import RunLedger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

rl = RunLedger(api_key="rl_dev_...")

chain = (
    ChatPromptTemplate.from_template("Explain {topic} in one sentence.")
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)

handler = rl.callback_handler()

with rl.context(end_user_id="u_456", feature_tag="explainer") as run_id:
    result = chain.invoke({"topic": "gradient descent"}, config={"callbacks": [handler]})

rl.shutdown()
```

> If you also call `rl.instrument()`, avoid double-counting:
> ```python
> handler = rl.callback_handler(track_llm_cost=False)
> ```

### LangGraph

```python
from runledger_sdk import RunLedger
from runledger_sdk.langgraph import instrument_graph

rl = RunLedger(api_key="rl_dev_...")

graph = builder.compile()
instrumented = instrument_graph(graph, rl._get_sync_transport())

with rl.context(end_user_id="u_789", feature_tag="qa-agent") as run_id:
    result = instrumented.invoke({"question": "What is 2+2?"})

rl.shutdown()
```

### Local mode (zero setup)

Skip the API entirely during early development. Events are printed to stdout as structured JSON:

```python
rl = RunLedger(local=True)  # no API key, no server needed
```

### Async

```python
import asyncio
import openai
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_dev_...")
rl.instrument()
client = openai.AsyncOpenAI()

async def main():
    async with rl.context(end_user_id="u_async") as run_id:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello!"}],
        )
    await rl.aflush()

asyncio.run(main())
```

---

## Context Manager

`rl.context()` attaches metadata to every event fired inside the block. Contexts nest — inner blocks inherit outer values and can override:

```python
with rl.context(
    end_user_id="u_123",        # who triggered this run
    session_id="sess_abc",      # groups multiple runs into a session
    feature_tag="support-bot",  # which feature/product area
    deployment_version="v2.1",  # your app deployment version
) as run_id:
    # run_id is a UUID you can log, return to the client, etc.
    ...
```

---

## Cross-service Propagation

Preserve run context when calling downstream services:

**Service A (caller)**
```python
with rl.context(end_user_id="u_123", feature_tag="pipeline"):
    headers = rl.propagation_headers()
    # {'X-RunLedger-Run-Id': '...', 'X-RunLedger-End-User-Id': 'u_123', ...}
    response = httpx.post("http://service-b/process", headers=headers)
```

**Service B (receiver)**
```python
@app.post("/process")
async def process(request: Request):
    ctx = RunLedger.from_headers(dict(request.headers))
    async with ctx as run_id:
        # run_id, end_user_id, feature_tag are all restored
        ...
```

All spans from both services share the same `run_id` and appear together in the Run Explorer.

---

## Dashboard

The dashboard at `http://localhost:3000` has two main areas:

### Run Explorer (`/runs`)
- **Runs list** — searchable, filterable by status/feature/user, time-window presets (1h / 6h / 24h / 7d)
- **Run detail** — cost + tokens + duration summary, full execution DAG
- **DAG viewer** — interactive graph of every span (LLM, tool, chain, agent, retrieval) with cost per node; click any node to see full span metadata in a slide-in panel

### Analytics Dashboard (`/analytics`)
- **Summary cards** — total spend, run count, avg cost/run, total tokens; each card shows period-over-period delta %
- **Spend over time** — line chart with 24h / 7d / 30d preset buttons; URL-persisted time window
- **Spend by model** — horizontal stacked bar chart (input vs output split, top 10 models)
- **Spend by feature** — donut chart of cost by `feature_tag`
- **Top spenders** (`/analytics/users`) — table of end-users sorted by spend with avg cost/run and last active date; rows link to individual user profiles
- **User profile** (`/analytics/users/[id]`) — per-user spend trend, models used, and features used

### Budgets (`/budgets`)
- **Budget list** — each budget shows scope (workspace / end-user / feature tag), period, limit, live spend progress bar (green → yellow → red), action badge (block / notify / downgrade)
- **New Budget modal** — create a budget: pick scope type and ID, period (daily / monthly / total), USD limit, enforcement action, and optional downgrade model
- **Breach history** (`/budgets/[id]`) — table of every breach: occurred at, spend at breach, action taken, notified at
- **Delete** — soft-deactivates the budget; Redis cache invalidated immediately

### Billing (`/billing`)
- **Billing periods** — list of periods with status (open / closing / closed), total cost, and snapshot hash
- **Period detail** — summary cards, chargeback breakdown by application and end-user, reconciliation status panel
- **Evidence export** — download line-item CSV or HMAC-signed JSON verifiable offline

### Economics (`/analytics/economics`)
- **Top Workflows** — table of `feature_tag` groups ranked by average cost, p95 cost, total cost, and call count
- **Version Compare** — enter baseline and comparison version strings; renders 3 delta cards (cost Δ%, input token Δ%, latency Δ%) and a per-span-type cost shift table
- **Cost Regressions** — workflows where average cost increased >20% vs prior 7 days; shows change %, current/prior averages, and run count
- **Annotations** — inline form to attach team notes to a date and optional deployment version; runs list chronologically below

### Users (`/analytics/users`)
- **Spend tiers** — cohort badges: P0 (<$1/mo), P1 ($1–$10), P2 ($10–$100), P3 ($100+)
- **Anomaly alerts** — users whose daily spend Z-score exceeds 3σ vs their 30-day mean are flagged automatically
- **Segmentation tabs** — All / Heavy users / Anomalous / New this week

### Replay (`/replay`)
- **Datasets** — save a named set of run IDs for re-testing
- **Experiments** — run the same dataset against multiple model configs; projected cost shown before confirming
- **Results** (`/replay/[id]`) — side-by-side per-config cost, token, and call-count comparison with Δ% badges

### Ledger (`/ledger`)
- **Daily snapshots table** — date, total cost, call count, hash preview, per-row "Verify" button; "Generate snapshot" button triggers immediate signing for yesterday
- **Integrity status** — inline ✓ ok / ⚠ tampered badge after verification; re-computed hash compared against stored HMAC-SHA256
- **Tool Registry panel** — register tools with allow/audit/block policy; colour-coded policy badges; delete button per row
- **Security Events panel** — read-only feed of suspicious sequences flagged by the Celery worker (>5 identical tool calls in 60s)
- **Privacy / Capture Policy panel** — per-workspace privacy mode selector (METADATA\_ONLY / ERRORS\_ONLY / SAMPLED / FULL) + sampled rate input

---

## CLI

```bash
export RUNLEDGER_API_KEY=rl_dev_...

runledger validate        # sends a test event to verify connectivity
runledger status          # checks API + DB + Redis health
runledger runs --limit 5  # lists your 5 most recent agent runs
```

---

## Analytics API

```bash
BASE=http://localhost:8000
KEY=rl_dev_...

# Total cost + tokens for the last 7 days
curl "$BASE/analytics/summary" -H "Authorization: Bearer $KEY"

# Daily spend time-series
curl "$BASE/analytics/spend-over-time?granularity=daily" -H "Authorization: Bearer $KEY"

# Cost breakdown by model
curl "$BASE/analytics/spend-by-model" -H "Authorization: Bearer $KEY"

# Top 10 spenders
curl "$BASE/analytics/spend-by-user?limit=10" -H "Authorization: Bearer $KEY"

# Cost by feature tag
curl "$BASE/analytics/spend-by-feature" -H "Authorization: Bearer $KEY"
```

All endpoints accept `from` and `to` query params (ISO-8601).

---

## What Gets Captured Automatically

| Field | How |
|-------|-----|
| `model` | From the API response |
| `input_tokens` / `output_tokens` | From the API response |
| `cached_input_tokens` | From OpenAI Prompt Caching header |
| `latency_ms` | Measured wall-clock around the API call |
| `cost_usd` | Computed server-side from the pricing engine |
| `end_user_id` | Set by you in `rl.context()` |
| `session_id` | Set by you in `rl.context()` |
| `feature_tag` | Set by you in `rl.context()` |
| `run_id` | Auto-generated UUID (or set by you) |
| Span DAG | Full parent-child tree via LangChain/LangGraph callbacks |

No prompts or completions are sent unless you opt in to `PrivacyMode.FULL`.

---

## Supported Providers

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4o · gpt-4o-mini · gpt-4-turbo · gpt-3.5-turbo · o1 · o3-mini |
| Anthropic | claude-opus-4-6 · claude-sonnet-4-6 · claude-haiku-4-5 |
| Google | gemini-1.5-pro · gemini-1.5-flash |

Add a new model by inserting a row into `provider_pricing` — no code change required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Agent App                          │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ OpenAI SDK   │  │ LangChain/Graph│  │  Custom Tools  │   │
│  └──────┬───────┘  └───────┬────────┘  └───────┬────────┘   │
│         └──────────────────┼───────────────────┘            │
│                   runledger-sdk (async)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP batch (non-blocking)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RunLedger Platform                       │
│                                                             │
│  ┌────────────────┐    ┌──────────────────────────────────┐ │
│  │  Collector API │──▶ │  Redis Streams (event buffer)     │ 
│  │  (FastAPI)     │    └──────────────┬───────────────────┘ │
│  └────────────────┘                  │                      │
│                             ┌────────▼────────┐             │
│  ┌────────────────┐         │  Celery Workers   │           │
│  │  Business API  │         │  · cost enrich    │           │
│  │  (FastAPI)     │◀───────│  · hourly rollup  │           │
│  └───────┬────────┘         │  · data quality   │           │
│          │                  └────────┬──────────┘           │
│  ┌───────▼────────────────────────────────────┐             │
│  │              PostgreSQL 16                 │             │
│  │  events · spans · metering · pricing       │             │
│  │  usage_hourly · usage_daily · budgets      │             │
│  └────────────────────────────────────────────┘             │
│                                                             │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │  Redis (cache) │   │  Budget Enforcement (hot path)   │  │
│  │  idempotency   │   │  <5ms p99 spend check            │  │
│  └────────────────┘   └──────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┬─┘
                                                            │
                            ┌───────────────────────────────▼──┐
                            │        RunLedger Dashboard        │
                            │        (Next.js 14)               │
                            │                                   │
                            │  Run Explorer · DAG Viewer        │
                            │  Metering · Budgets · Chargeback  │
                            └───────────────────────────────────┘
```

---

## Metering Engine

The pricing engine runs as a Celery worker and enriches every provider call within 60 seconds:

- **Effective-dated pricing** — prices are versioned by date, so retroactive corrections apply correctly
- **Workspace overrides** — per-workspace pricing rows take priority over global defaults
- **Cached input discount** — applies OpenAI Prompt Caching rates (50% off input by default)
- **Idempotent rollups** — `usage_hourly` and `usage_daily` are fully recomputed per window; replaying produces identical results

| Task | Interval |
|------|----------|
| `cost_enrichment` | Every 60s |
| `rollup_hourly` | Every 30 min |
| `rollup_daily` | Daily at 00:05 UTC |
| `data_quality` | Every 1h |
| `runaway_protection` | Every 5 min |
| `budget_spend_sync` | Daily at 00:10 UTC |
| `nightly_reconciliation` | Daily at 00:15 UTC |
| `auto_create_billing_periods` | Daily at 00:01 UTC |
| `nightly_analytics` | Daily at 02:00 UTC (anomaly detection) |
| `ledger.daily_snapshots` | Daily at 01:00 UTC |
| `ledger.suspicious_sequences` | Every 60s |

---

## API Reference

All endpoints require `Authorization: Bearer <api_key>` and are workspace-scoped.

### Runs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/runs` | List runs (cursor pagination + filters) |
| `GET` | `/runs/{id}` | Run detail — spans + provider calls + tool calls |
| `GET` | `/runs/{id}/graph` | DAG nodes + edges for the dashboard viewer |

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/v1/events` | Ingest a single event |
| `POST` | `/ingest/v1/batch` | Ingest up to 100 events |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/login` | Dashboard login (returns session API key) |
| `POST` | `/auth/workspaces` | Create a workspace |
| `POST` | `/auth/api-keys` | Generate an API key |
| `GET`  | `/auth/api-keys` | List active keys |
| `DELETE` | `/auth/api-keys/{id}` | Revoke a key |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/analytics/summary` | Total cost, tokens, run count + period-over-period delta |
| `GET` | `/analytics/spend-over-time` | Time-series (`granularity=hourly\|daily`) |
| `GET` | `/analytics/spend-by-model` | Cost breakdown by model |
| `GET` | `/analytics/spend-by-user` | Top spenders with avg cost/run + last active (`limit=N`) |
| `GET` | `/analytics/spend-by-feature` | Cost breakdown by feature tag |
| `GET` | `/analytics/users/{end_user_id}` | User profile: spend trend + models + features used |
| `GET` | `/analytics/economics/{run_id}` | Per-run cost breakdown by span type and model + retry cost |
| `GET` | `/analytics/workflows/top` | Top workflows by avg cost or latency (`metric=cost\|latency&limit=N`) |
| `GET` | `/analytics/compare` | Version cost/token/latency delta (`baseline_version=&comparison_version=`) |
| `GET` | `/analytics/regressions` | Workflows with >20% cost increase vs prior period |
| `POST` | `/analytics/annotations` | Create a team note anchored to a date and optional version |
| `GET` | `/analytics/annotations` | List annotations (`from=&to=&version=`) |

### Billing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/billing/periods` | Open a new billing period |
| `GET` | `/billing/periods` | List billing periods |
| `GET` | `/billing/periods/{id}` | Period detail |
| `POST` | `/billing/periods/{id}/close` | Close period and generate signed usage snapshot |
| `GET` | `/billing/periods/{id}/reconciliation` | Consistency check — provider_calls vs usage_daily sums |
| `GET` | `/billing/periods/{id}/breakdown` | Hierarchical cost breakdown by app → user → model |
| `GET` | `/billing/periods/{id}/export` | Download CSV or HMAC-signed JSON (`format=csv\|signed_json`) |
| `POST` | `/billing/chargeback-rules` | Create a weight-based cost allocation rule |
| `GET` | `/billing/chargeback-rules` | List chargeback rules |

### Ledger

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ledger/snapshots` | List HMAC-signed daily spend snapshots (limit 30) |
| `POST` | `/ledger/snapshots/generate` | Trigger immediate snapshot for yesterday |
| `GET` | `/ledger/verify/{date}` | Re-compute hash and verify integrity (`status: ok\|tampered\|not_found`) |

### Tools

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tools/registry` | List registered tools with policies |
| `POST` | `/tools/registry` | Register or upsert a tool (policy: allow\|audit\|block) |
| `PATCH` | `/tools/registry/{tool_name}` | Update policy or description |
| `DELETE` | `/tools/registry/{tool_name}` | Remove a tool entry |
| `GET` | `/tools/security-events` | List flagged suspicious sequences (limit 100) |

### Privacy

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/privacy/capture-policy` | Current workspace capture policy (404 if not set) |
| `PUT` | `/privacy/capture-policy` | Upsert capture policy (METADATA\_ONLY / ERRORS\_ONLY / SAMPLED / FULL) |

### Budgets

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/budgets` | Create a budget |
| `GET` | `/budgets` | List budgets with live Redis spend |
| `GET` | `/budgets/check` | Hot-path enforcement check (Redis only, <5ms p99) |
| `GET` | `/budgets/{id}/breaches` | Breach history |
| `DELETE` | `/budgets/{id}` | Deactivate a budget |
| `POST` | `/budgets/notifications` | Create a webhook or Slack notification channel |
| `GET` | `/budgets/notifications` | List notification channels |

Interactive docs: `http://localhost:8000/docs`

---

## Example Agents

```bash
export OPENAI_API_KEY=sk-...
export RUNLEDGER_API_KEY=rl_dev_...   # optional — examples use local=True by default

python examples/01_openai_basic.py          # OpenAI instrumentation (2 lines)
python examples/02_openai_multi_turn.py     # multi-turn chat with session tracking
python examples/03_langchain_chain.py       # LangChain chain with callback handler
python examples/04_langgraph_agent.py       # LangGraph ReAct agent with tools
python examples/06_ollama_local.py          # local Ollama (OpenAI-compatible endpoint)
python examples/07_analytics_query.py       # query the analytics API (summary + spend breakdown)
python examples/08_budget_enforcement.py    # create a budget, exceed it, catch RunLedgerBudgetExceededError
python examples/09_economics_query.py       # per-run economics, version compare, regressions, annotations
python examples/10_replay_experiment.py     # create a dataset, run a replay experiment, compare models
python examples/11_ledger_verify.py         # generate a snapshot, verify integrity, register tools, set privacy policy

# FastAPI service with per-request context
uvicorn examples.05_fastapi_service:app --reload
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -H "X-User-Id: user-alice" \
     -d '{"message": "What is Python?"}'
```

---

## Troubleshooting

**Events not appearing in the API**

1. Check connectivity: `runledger validate`
2. Check service health: `runledger status`
3. Confirm `rl.shutdown()` (sync) or `await rl.aflush()` (async) is called before process exit.

**Dashboard login fails**

Migrations and seed run automatically when the API container starts. Check that the container started cleanly: `docker compose -f infra/docker-compose.yml logs api`. The seed script is idempotent — safe to run again manually if needed.

**`cost_usd` is NULL**

Cost enrichment runs every 60 seconds via Celery. Make sure both the worker and beat scheduler are running:

```bash
celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
celery -A runledger_api.core.celery_app beat --loglevel=info
```

**"No pricing row" in logs**

The seed script runs automatically on startup, but if you need to force it:

```bash
docker compose -f infra/docker-compose.yml exec api python /app/scripts/seed.py
```

**Duplicate `provider_call` events**

If you use both `rl.instrument()` and `rl.callback_handler()`, pass `track_llm_cost=False` to the handler:

```python
handler = rl.callback_handler(track_llm_cost=False)
```

---

## Development

```bash
# Install all workspace dependencies
uv sync --all-packages

# Start full local stack (migrations + seed run automatically on first start)
docker compose -f infra/docker-compose.yml up -d

# API with hot reload
cd apps/api && uv run fastapi dev runledger_api/main.py

# Celery worker + beat
cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
cd apps/api && uv run celery -A runledger_api.core.celery_app beat --loglevel=info

# Dashboard
cd apps/web && npm run dev

# Tests
cd apps/api && uv run pytest
cd packages/sdk && uv run pytest

# Lint + type check
uv run ruff check .
uv run mypy apps/api
```

---

## Deployment

**Self-hosted** — follow [Setup from Scratch → Option A](#option-a--docker-compose-recommended) above.

**Cloud (Railway, Render, Fly.io):**

Set these on your services:

```
DATABASE_URL  = postgresql+asyncpg://...
REDIS_URL     = redis://...
SECRET_KEY    = <random 32 bytes hex>
ENVIRONMENT   = production
```

For the dashboard, also set:

```
NEXTAUTH_URL    = https://your-dashboard-domain.com
NEXTAUTH_SECRET = <random 32 bytes hex>
NEXT_PUBLIC_API_URL = https://your-api-domain.com
```

---

## OSS vs Paid

**Open source (free forever):**
- SDK — OpenAI, LangChain, LangGraph
- Collector + event pipeline
- Metering + pricing engine + analytics API
- Run Explorer + DAG viewer
- Spend dashboard (Phase 6)
- Local replay harness (Phase 10)

**Paid (production FinOps):**
- Budget enforcement with automatic model downgrade / block
- Multi-tenant chargeback + billing portal
- Reconciliation + dispute tooling
- Tamper-evident ledger + evidence packs
- Advanced integrations (Stripe, data warehouse, CI gates)
- RBAC + SSO (enterprise)

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).

The core SDK and collector are open source. The paid tier (enforcement, ledger, chargeback, enterprise integrations) is offered as a hosted service and under a commercial license.
