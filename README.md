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

## Architecture

```mermaid
flowchart TB

  subgraph LLM["LLM Backends / Providers"]
    direction LR
    OAI["OpenAI API"]
    ANT["Anthropic API"]
    VLLM["Self-hosted vLLM (OpenAI-compatible)"]
    OTH["Other Providers (Azure OpenAI, Bedrock, etc.)"]
  end

  subgraph A["Your Agent App"]
    direction LR
    OA["OpenAI SDK"]
    LC["LangChain / LangGraph"]
    CT["Custom Tools"]
    SDK["runledger-sdk (async)\n(batch + non-blocking)"]
    OA --> SDK
    LC --> SDK
    CT --> SDK
  end

  OA -->|"LLM requests"| OAI
  LC -->|"LLM requests"| ANT
  LC -->|"OpenAI-compatible"| VLLM
  CT -->|"provider adapters"| OTH

  SDK -->|"HTTP batch (non-blocking)"| CA

  subgraph P["RunLedger Platform"]
    direction TB
    CA["Collector API (FastAPI)"]
    RS["Redis Streams\n(event buffer)"]
    CW["Celery Workers\n- cost enrich\n- hourly rollup\n- data quality"]
    BA["Business API (FastAPI)"]
    PG["PostgreSQL 16\n(events, spans, metering, pricing)\n(usage_hourly, usage_daily, budgets)"]
    RC["Redis (cache)\n(idempotency)"]
    BE["Budget Enforcement (hot path)\n<5ms p99 spend check"]

    CA --> RS
    RS --> CW
    CW --> PG
    BA --> PG
    BA <--> RC
    BA <--> BE
  end

  subgraph D["RunLedger Dashboard (Next.js 14)"]
    direction TB
    UI["Run Explorer / DAG Viewer\nMetering / Budgets / Chargeback"]
  end

  BA --> D
```

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

### Python SDK (`runledger-sdk`)

Not yet published to PyPI. Install directly from the repo.

**Option A — local path** (if you have the repo cloned):

```bash
# Pick the extras you need
pip install -e "/path/to/runledger/packages/sdk[openai]"
pip install -e "/path/to/runledger/packages/sdk[anthropic]"
pip install -e "/path/to/runledger/packages/sdk[langchain]"
pip install -e "/path/to/runledger/packages/sdk[langgraph]"
pip install -e "/path/to/runledger/packages/sdk[all]"
```

**Option B — directly from GitHub** (no clone needed):

```bash
pip install "runledger-sdk[openai]    @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[anthropic] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[langchain] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[langgraph] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
pip install "runledger-sdk[all]       @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
```

Each extra pulls in the right peer dependencies:

| Extra | What it adds |
|-------|-------------|
| `openai` | `openai>=1.0.0` |
| `anthropic` | `anthropic>=0.25.0` |
| `langchain` | `langchain-core>=0.3.0` |
| `langgraph` | `langchain-core>=0.3.0` + `langgraph>=0.2.0` |
| `all` | everything above + CLI |

### TypeScript / Node.js SDK (`@runledger/sdk`)

Not yet published to npm. Install from the repo:

```bash
# from the repo root
npm install ./packages/ts-sdk
# or with pnpm / yarn:
pnpm add ./packages/ts-sdk
```

Peer dependency (optional — only needed if using `rl.instrument(openai)`):

```bash
npm install openai
```

---

## Running the Examples

The `examples/` directory contains 19 runnable scripts covering every major feature.
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
| 14 | `14_evaluations.py` | Submit quality scores via `rl.score()`, query score summary and regressions |
| 15 | `15_prompts.py` | Create prompt, commit versions, promote to production, `rl.get_prompt()` with variable substitution, per-version metrics |
| 16 | `16_sessions.py` | List sessions, session detail with turn order, cost-over-turns chart data, run payload inspection |
| 17 | `17_alerts.py` | Create alert rules (error_rate / p95_latency / avg_score / spend_velocity), toggle, history, cleanup |
| 18 | `18_gateway.py` | Configure provider routes, send completions through the proxy, observe cache hit vs miss, stats |
| 19 | `19_policy_check.py` | Unified policy decision checks (budgets + tools + gateway + eval gate) |
| 20 | `20_anthropic_basic.py` | Anthropic Claude instrumentation with `rl.instrument_anthropic()` |
| 21 | `20_tool_registry_ollama.py` | Tool registry + Ollama local model (OpenAI-compatible, cost = $0) |
| — | `ts/01_openai_basic.ts` | TypeScript: OpenAI instrumentation with `@runledger/sdk` |
| — | `ts/02_multi_turn.ts` | TypeScript: multi-turn chat with `withContext` |
| — | `ts/03_vercel_ai.ts` | TypeScript: Vercel AI SDK integration |

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

### Anthropic Claude

```python
from runledger_sdk import RunLedger
import anthropic

rl = RunLedger(api_key="rl_dev_...")
rl.instrument_anthropic()          # patches anthropic.Anthropic + AsyncAnthropic

client = anthropic.Anthropic()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=256,
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print(message.content[0].text)

rl.shutdown()
```

Streaming and `AsyncAnthropic` are both supported. Tokens, latency, and cost are captured automatically from `usage.input_tokens` / `usage.output_tokens`.

### TypeScript / Node.js

```typescript
import OpenAI from 'openai'
import { RunLedger } from '@runledger/sdk'

const rl = new RunLedger({ apiKey: process.env.RUNLEDGER_API_KEY })
const openai = new OpenAI()

rl.instrument(openai)   // wraps chat.completions.create — streaming + non-streaming

const result = await rl.withContext(
  { endUserId: 'u_123', featureTag: 'support-chat' },
  async (runId) => {
    return await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [{ role: 'user', content: 'Hello!' }],
    })
  },
)

await rl.flush()
```

Other providers are supported via dedicated instrument methods:

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai'
import { Mistral } from '@mistralai/mistralai'
import { CohereClientV2 } from 'cohere-ai'

rl.instrumentGemini(new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!))
rl.instrumentMistral(new Mistral({ apiKey: process.env.MISTRAL_API_KEY }))
rl.instrumentCohere(new CohereClientV2({ token: process.env.COHERE_API_KEY }))
```

Context propagates across service boundaries via HTTP headers:

```typescript
// Service A — outgoing request
const headers = rl.propagationHeaders()
// { 'x-runledger-run-id': '...', 'x-runledger-session-id': '...' }

// Service B — incoming request
const ctx = RunLedger.contextFromHeaders(incomingHeaders)
await rl.withContext(ctx, async () => { /* all calls tagged with same run */ })
```

### Prompt management

Fetch versioned prompts and render `{{variable}}` placeholders in one call:

```python
rl = RunLedger(api_key="rl_dev_...")

# Pull the latest production version (60s in-memory cache — safe per request)
rendered = rl.get_prompt(
    "support-agent",
    environment="production",
    variables={"user_name": "Alice", "company": "Acme"},
)
# rendered["content"]  → "Welcome Alice! How can I assist you at Acme today?"
# rendered["version"]  → 3
# rendered["model_hint"] → "gpt-4o-mini"

# Link the run to this prompt version for per-version cost + quality metrics:
with rl.context(
    end_user_id="u_123",
    deployment_version=f"support-agent:{rendered['version']}",
) as run_id:
    resp = client.chat.completions.create(
        model=rendered["model_hint"] or "gpt-4o-mini",
        messages=[{"role": "system", "content": rendered["content"]}],
    )
```

**Prompt API (HTTP):**

```bash
KEY=rl_dev_...
BASE=http://localhost:8000

# Create a prompt
curl -X POST "$BASE/prompts" -H "Authorization: Bearer $KEY" \
     -d '{"name":"support-agent","default_environment":"production"}'

# Commit a new version to staging
curl -X POST "$BASE/prompts/support-agent/versions" -H "Authorization: Bearer $KEY" \
     -d '{"content":"Hello {{user_name}}!","environment":"staging","commit_message":"Add greeting"}'

# Promote staging → production
curl -X POST "$BASE/prompts/support-agent/promote" -H "Authorization: Bearer $KEY" \
     -d '{"source_environment":"staging","target_environment":"production"}'

# Per-version metrics (run count + avg cost + avg score)
curl "$BASE/prompts/support-agent/metrics" -H "Authorization: Bearer $KEY"
```

### Quality scores

Submit human, rule-based, or automated quality scores for any run:

```python
with rl.context(feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Is this answer helpful?"}],
    )
    # Rate the response — run_id is picked up from context automatically
    rl.score("helpfulness", 0.9, label="good", source="human")
    rl.score("relevance", 0.8, run_id=str(run_id), confidence=0.95)
```

Scores are posted synchronously and fail silently — they will never break application flow.

### Model Gateway (OpenAI-compatible proxy)

Point any OpenAI client at the RunLedger gateway to get prompt caching, provider fallback, and full request logging — with zero code changes:

```python
import openai

# Replace api.openai.com with your RunLedger API
client = openai.OpenAI(
    api_key="rl_dev_...",                      # your RunLedger API key
    base_url="http://localhost:8000/gateway",   # RunLedger gateway
)

# Use the alias you configured in Settings → Model Gateway (e.g. "gpt-4o-mini")
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is 2+2?"}],
)
print(resp.choices[0].message.content)
# First call → forwarded to OpenAI, response cached.
# Identical second call → served from cache in <1ms.
```

Configure routes via the API or Settings page:

```bash
KEY=rl_dev_...
BASE=http://localhost:8000

curl -X POST "$BASE/gateway/routes" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "alias": "gpt-4o-mini",
       "provider": "openai",
       "target_model": "gpt-4o-mini",
       "api_key_env_var": "OPENAI_API_KEY",
       "priority": 10
     }'
```

Add a second route with higher priority number for automatic fallback:

```bash
curl -X POST "$BASE/gateway/routes" -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "alias": "gpt-4o-mini",
       "provider": "groq",
       "target_model": "llama-3.3-70b-versatile",
       "base_url": "https://api.groq.com/openai/v1",
       "api_key_env_var": "GROQ_API_KEY",
       "priority": 20
     }'
```

If the priority-10 OpenAI route returns 429 or 5xx, the gateway automatically retries via the priority-20 Groq route.

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
- **Runs list** — filterable by status, feature tag, end-user ID, model (substring match), cost range (min/max USD); time-window presets (5m / 15m / 30m / 1h / 3h / 6h / 12h / 24h / 7d / 30d) or custom datetime-local range with second-level granularity
- **Export CSV** — "Export CSV" button downloads filtered runs as `runs.csv` (up to 5 000 rows, same filters as list view)
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

### Evaluations (`/evaluations`)
- **Submit Score form** — attach a quality score to any run; fields: Run ID (optional), Score Name, Value (0–100), Label (good/neutral/bad/pass/fail), Source (human/llm/rule/telemetry), Confidence
- **Score Summary** — per-score-name cards showing avg value with ↑/↓ period-over-period delta badge
- **Recent Scores table** — Name, Value, Label, Source, Run ID (truncated link), Confidence, Created; skeleton while loading, empty state with icon

### Sessions (`/sessions`)
- **Session list** — all `session_id` groups with user, turn count, total cost, duration; filter by `end_user_id`
- **Session detail** (`/sessions/[id]`) — turn-ordered run list with cost + duration per turn; Recharts `LineChart` showing per-turn and cumulative cost over conversation turns
- **Payload Viewer** — inline in run detail (`/runs/[id]`): shows captured messages with role colour-coding (system / user / assistant / tool) and the assistant completion when `capture_policy = SAMPLED | FULL`

### Prompts (`/prompts`)
- **Prompt list** — all named prompts with description, default environment, created date; click to detail
- **Create Prompt** — toggle form: name, description, default environment; 409 shown as user-friendly error
- **Delete** — removes the prompt and all its versions
- **Prompt detail** (`/prompts/[name]`) — version history list showing environment badge, model hint, commit message, run count, avg cost, avg score per version (pulled from metrics endpoint)
- **Commit form** — textarea for template content (supports `{{variable}}` syntax), commit message, environment, model hint
- **Side-by-side diff viewer** — select any two versions as "before"/"after"; highlights changed lines in red (removed) / green (added)
- **Promote button** — one click to copy latest staging version to production

### Settings (`/settings`) — API Keys
- **User keys only** — session keys (auto-created on dashboard login) are hidden; the table shows only workspace API keys created by users
- **Created At + Created By** — full timestamp and creator email visible per key; helps audit who provisioned which key
- **Revoke** — permanently deletes a key; takes effect on the next request

### Alert Rules (Settings → Alert Rules)
- **Create rule** — pick metric (error_rate / p95_latency / avg_score / spend_velocity), operator (> / <), threshold, and evaluation window (5 min – 24 h)
- **Rules table** — active/paused toggle per rule; delete
- **Recent Firings** — table of threshold breaches with metric value and timestamp
- Rules evaluate every 5 minutes via Celery Beat; Slack notifications fire when a `channel_id` is set on the rule

### Model Gateway (Settings → Model Gateway)
- **Stats strip** — total requests, cache hits, hit rate, avg latency (shown when traffic exists)
- **Add Route form** — alias (what clients use as model name), provider, target model, base URL, API key env var, priority
- **Routes table** — active/disabled toggle per route; delete; priority column controls fallback order

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

## Metering Engine

The pricing engine runs as a Celery worker and enriches every provider call within 60 seconds:

- **Effective-dated pricing** — prices are versioned by date, so retroactive corrections apply correctly
- **Workspace overrides** — per-workspace pricing rows take priority over global defaults
- **Cached input discount** — applies OpenAI Prompt Caching rates (50% off input by default)
- **Free / local providers** — Ollama and any provider without a pricing row are stored as `$0.00` (not skipped), so they appear correctly in analytics and economics views
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
| `score_rollup.run` | Daily at 01:30 UTC |
| `alerts.evaluate_rules` | Every 5 min |

---

## API Reference

All endpoints require `Authorization: Bearer <api_key>` and are workspace-scoped.

### Runs

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/runs` | List runs — cursor pagination; filters: `status`, `feature_tag`, `end_user_id`, `search`, `from`, `to`, `model`, `min_cost`, `max_cost` |
| `GET` | `/runs/export` | Download filtered runs as CSV (up to 5 000 rows; same filter params as `/runs`) |
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
| `GET` | `/analytics/scores/summary` | Avg score per score name + period-over-period delta % |
| `GET` | `/analytics/scores/regressions` | Score names where avg dropped >20% vs prior period |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sessions` | List sessions grouped by `session_id` (`end_user_id=`, `from=`, `to=`, `limit=`) |
| `GET` | `/sessions/{session_id}` | Session detail — ordered run list with `turn_number` assigned |
| `GET` | `/sessions/{session_id}/cost-over-turns` | Per-turn and cumulative cost for chart rendering |

### Evaluations

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/evaluations/scores` | Submit a quality score for a run, span, session, or end-user |
| `GET` | `/evaluations/scores` | List scores (`run_id=`, `name=`, `source=`, `from=`, `to=`, `limit=`) |

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/alerts/rules` | Create an alert rule (metric, operator, threshold, window_minutes) |
| `GET` | `/alerts/rules` | List alert rules (`include_inactive=true` to include paused) |
| `PUT` | `/alerts/rules/{id}` | Update / toggle a rule (`is_active`, `threshold`, `window_minutes`) |
| `DELETE` | `/alerts/rules/{id}` | Delete an alert rule |
| `GET` | `/alerts/history` | Recent alert firings with `rule_name` + `metric_value` (`limit=`) |

### Gateway

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/gateway/chat/completions` | OpenAI-compatible proxy — cache lookup → provider route → cache store |
| `POST` | `/gateway/routes` | Add a provider route (alias, provider, target_model, priority) |
| `GET` | `/gateway/routes` | List routes (`include_inactive=true`) |
| `PUT` | `/gateway/routes/{id}` | Update or disable a route |
| `DELETE` | `/gateway/routes/{id}` | Remove a route |
| `GET` | `/gateway/stats` | Aggregate stats — total requests, cache hits, hit rate, avg latency per route |

### Prompts

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/prompts` | Create a named prompt template |
| `GET` | `/prompts` | List prompts for workspace |
| `GET` | `/prompts/{name}` | Get prompt metadata |
| `DELETE` | `/prompts/{name}` | Delete prompt + all versions |
| `POST` | `/prompts/{name}/versions` | Commit a new version (content, variables, environment, model_hint) |
| `GET` | `/prompts/{name}/versions` | List all versions descending (`environment=` filter) |
| `GET` | `/prompts/{name}/latest` | Latest version for an environment — SDK pull endpoint (`environment=production`) |
| `GET` | `/prompts/{name}/versions/{v}` | Get a specific version by number |
| `POST` | `/prompts/{name}/promote` | Copy latest from `source_environment` → new version in `target_environment` |
| `GET` | `/prompts/{name}/metrics` | Per-version run count, avg cost, avg score (join via `deployment_version="{name}:{v}"`) |

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

### Policies

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/policies/check` | Unified policy decision check across budgets, tool policy, gateway route readiness, and optional score gate |

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
python examples/14_evaluations.py           # submit quality scores, query score summary and regressions
python examples/15_prompts.py               # create prompt, commit versions, promote, rl.get_prompt(), metrics
python examples/16_sessions.py             # list sessions, turn order, cost chart, payload inspection
python examples/17_alerts.py               # create alert rules, toggle, history, cleanup
python examples/18_gateway.py              # configure gateway routes, proxy completions, cache stats
python examples/19_policy_check.py         # unified policy decision check for admission control and release gates

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
- SDK — OpenAI, Anthropic Claude, LangChain, LangGraph (Python)
- TypeScript SDK — OpenAI, Gemini, Mistral, Cohere (`@runledger/sdk`)
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
| 15 | Anthropic SDK — `rl.instrument_anthropic()` · streaming · async · budget enforcement | ✅ Complete |
| 16 | Production hardening — rate limiting · PII scrubbing · health probes · UI polish | ✅ Complete |
| 17 | Evaluations & Scores — `rl.score()` · score CRUD · analytics summary + regressions · `/evaluations` dashboard page | ✅ Complete |
| 18 | Prompt Management — `rl.get_prompt()` · CRUD + version history · environment promotion · diff viewer · per-version metrics · `/prompts` dashboard | ✅ Complete |
| 19 | Sessions UI + Payload Viewer — multi-turn session grouping · cost-over-turns chart · inline prompt/completion display · `/sessions` dashboard | ✅ Complete |
| 21A | Advanced Alerting — threshold rules · error rate / latency / quality / spend metrics · Celery beat evaluation · Slack notifications · Alert Rules in Settings | ✅ Complete |
| 21B | Model Gateway — OpenAI-compatible proxy · prompt caching · priority-ordered routing · fallback · per-route stats · Gateway section in Settings | ✅ Complete |
| 21C | Runs enhancements — model + cost range filters · `GET /runs/export` CSV download · seconds-granularity datetime picker · Ollama `cost_usd=$0` fix · session API key UX | ✅ Complete |
| 21D | Unified policy checks — `/policies/check` combines budget guardrails, tool policy, gateway readiness, and optional score gates | ✅ Complete |
| 20 | TypeScript / Node.js SDK — `@runledger/sdk` · OpenAI · Gemini · Mistral · Cohere · `AsyncLocalStorage` context · multi-provider detection | ✅ Complete |

**Validation Snapshot (2026-03-21)**
- API tests: `233/233` passing
- Python SDK tests: `61/61` passing
- TypeScript SDK tests: `9/9` passing (vitest)
- Web lint: clean (`next lint`)
- Repo lint: clean (`ruff check .`)
- Core API typing: clean (`mypy apps/api/runledger_api`)

**Recent Audit Fixes**
- Budgets: fixed breach-notification fan-out by including `workspace_id` in cached budget rows.
- Gateway: corrected overall latency metric to use weighted averaging by request volume.
- Gateway: added retry-once behavior for transient provider failures before route fallback.
- SDK: restored backward-compatible OpenAI provider-call builder signatures.
- Web UI: fixed prompts diff-view lint/UX text escaping issue.
- Core API typing hardening: fixed source-level typing issues in `runs`, `sessions`, `policies`, `gateway` model, and alert block typing.
- UI polish pass: upgraded typography, refined dashboard shell (sidebar/topbar/main), improved login visual hierarchy, and refreshed color tokens for a cleaner, more premium look.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).

The core SDK and collector are open source. The paid tier (enforcement, ledger, chargeback, enterprise integrations) is offered as a hosted service and under a commercial license.
