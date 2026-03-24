# RunLedger

[![CI](https://github.com/avs6/runledger/actions/workflows/ci.yml/badge.svg)](https://github.com/avs6/runledger/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

**AI spend system of record and runtime control plane.**

RunLedger is an open-source Agent FinOps Control Plane. It turns LangChain, LangGraph, OpenAI, Anthropic, and any OpenTelemetry-instrumented agent into trace-linked usage accounting, provider invoice reconciliation, internal chargeback, budget enforcement, economics-aware routing, and outcome-to-cost visibility — with payload logging optional by default.

Tracing tools tell you *what happened*. RunLedger tells you *what it cost, who pays, whether you're over budget, how it reconciles against the provider invoice, and what the ROI was.*

---

## The Problem

Every team shipping AI agents in production hits the same wall:

- **Spend explodes** — a retry loop or runaway agent silently burns through API budget overnight
- **Chargeback is guesswork** — you can't attribute cost to a tenant, user, or feature without custom instrumentation
- **Routing isn't tied to economics** — model selection is based on capability, not cost-per-outcome
- **Finance can't trust the numbers** — no audit trail linking an invoice line to the exact agent run

---

## What's Built

**Provider-aware metering** — input vs output tokens (plus cached input) mapped to provider pricing so your internal numbers match the invoice.

**Spend guardrails that change behavior** — budgets with automatic actions (throttle / block / downgrade model) for runaway loops and retry storms.

**Provider invoice reconciliation** — import billing exports from OpenAI, Anthropic, Google; match against internal calls by request ID or fuzzy match; export signed dispute packages.

**Reconciliation + dispute trail** — prove every invoice line item back to the exact agent run and steps, even with payload logging off.

**End-user analytics** — cost per user/tenant/feature, cost-per-outcome, cohorts, top spenders, anomaly detection — built for customer-facing agents.

**Agent unit economics graph** — cost breakdown across steps, tools, retrieval, retries, and human approvals, plus "what changed?" diffs after prompt or model updates.

**Tamper-evident usage ledger** — cryptographic integrity for usage summaries so finance teams can trust chargeback and invoices.

**Model gateway** — OpenAI-compatible proxy with prompt caching, provider fallback, cost-aware routing policies, and full request logging.

**Outcome & ROI ledger** — tie spend to business outcomes: cost-per-success, ROI by workflow, success rate trends.

**Approvals & governance** — require approval for prompt production promotions, budget increases, and sensitive policy changes.

**OTLP / OpenTelemetry ingestion** — accept traces from any OTel or OpenInference instrumented application, no SDK required.

**Privacy-first modes** — payload logging off by default. Errors-only / sampled / full opt-in.

---

## Architecture

```
Application / Agent
  ├── RunLedger SDK (Python or TypeScript) → /ingest/v1/events (richest path)
  ├── OTel SDK + OpenInference → OTel Collector → /v1/traces
  └── OTel SDK + OpenInference → /v1/traces directly

RunLedger Platform
  ├── Collector API (FastAPI)          ← receives events + OTLP traces
  ├── Redis Streams                    ← event buffer
  ├── Celery Workers                   ← cost enrichment, rollups, finalization
  ├── PostgreSQL 16                    ← events, spans, metering, pricing, invoices
  └── Redis Cache                      ← budget hot path (<5ms p99)

RunLedger Dashboard (Next.js 14)
  └── Run Explorer / Analytics / Budgets / Billing / Gateway / Outcomes / Approvals
```

---

## Adoption Modes

| Mode | How | When to use |
|------|-----|-------------|
| **RunLedger SDK** | Wrap your OpenAI / Anthropic / LangChain client with 2 lines | Best finance-native path: budget enforcement, MCP hooks, request ID capture, `rl.score()` |
| **OTLP direct** | Send traces to `POST /v1/traces` | Already emit OTel or OpenInference; want zero instrumentation change |
| **OTLP via Collector** | App → OTel Collector → RunLedger | Production deployments; Collector handles batching, retry, attribute tagging |

All three modes normalize into the same RunLedger domain model. OTLP traces become agent runs with provider calls and tool calls. All privacy modes apply equally.

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

To also start the optional **OTel Collector** (OTLP receiver on ports 4317/4318 → RunLedger):
```bash
docker compose -f infra/docker-compose.yml --profile otel up -d
```

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

---

### Option B — Local dev (no Docker)

Requires Postgres 16, Redis 7, Python 3.13, uv, and Node.js 18+.

**1. Clone and install**

```bash
git clone https://github.com/avs6/runledger
cd runledger
uv sync --all-packages
```

**2. Set environment variables**

```bash
cp apps/api/.env.example        apps/api/.env
cp apps/web/.env.local.example  apps/web/.env.local
```

Key variables in `apps/api/.env`:

```ini
DATABASE_URL=postgresql+asyncpg://runledger:runledger@localhost:5432/runledger
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-change-in-production
ADMIN_SECRET=runledger-admin
ENVIRONMENT=development
```

Key variables in `apps/web/.env.local`:

```ini
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-change-in-production-32chars!!
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_SECRET=runledger-admin
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
pip install -e "/path/to/runledger/packages/sdk[openai]"
pip install -e "/path/to/runledger/packages/sdk[anthropic]"
pip install -e "/path/to/runledger/packages/sdk[langchain]"
pip install -e "/path/to/runledger/packages/sdk[langgraph]"
pip install -e "/path/to/runledger/packages/sdk[all]"
```

**Option B — directly from GitHub** (no clone needed):

```bash
pip install "runledger-sdk[all] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
```

| Extra | What it adds |
|-------|-------------|
| `openai` | `openai>=1.0.0` |
| `anthropic` | `anthropic>=0.40.0` |
| `langchain` | `langchain-core>=0.3.0` |
| `langgraph` | `langchain-core>=0.3.0` + `langgraph>=0.2.0` |
| `otel` | `opentelemetry-sdk>=1.20.0` (for `RunLedgerOTLPExporter`) |
| `all` | everything above + CLI + otel |

### TypeScript / Node.js SDK (`@runledger/sdk`)

Not yet published to npm. Install from the repo:

```bash
npm install ./packages/ts-sdk
```

---

## Running the Examples

The `examples/` directory contains runnable scripts covering every major feature.

```bash
# macOS / Linux
source examples/.venv/bin/activate
cd examples
python 01_openai_basic.py
```

### Example index

| # | Script | Feature |
|---|--------|---------|
| 01 | `01_openai_basic.py` | Basic OpenAI instrumentation |
| 02 | `02_openai_multi_turn.py` | Multi-turn chat with `session_id` |
| 03 | `03_langchain_chain.py` | LangChain `prompt | llm | parser` chain |
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
| 14 | `14_evaluations.py` | Submit quality scores via `rl.score()`, query summary |
| 15 | `15_prompts.py` | Create prompt, commit versions, promote to production |
| 16 | `16_sessions.py` | List sessions, session detail, cost-over-turns chart data |
| 17 | `17_alerts.py` | Create alert rules, toggle, history, cleanup |
| 18 | `18_gateway.py` | Configure provider routes, completions through proxy, cache stats |
| 19 | `19_policy_check.py` | Unified policy decision checks |
| 20 | `20_anthropic_basic.py` | Anthropic Claude instrumentation |
| 21 | `21_mcp_example.py` | MCP tool hooks |
| 22 | `22_otlp_ingest.py` | OTLP/HTTP trace ingestion — no SDK required (comprehensive) |
| — | `otlp_basic.py` | Minimal OTLP quickstart — single LLM span, annotated |
| 23 | `23_gateway_routing.py` | Intelligent routing policies (cost/latency/canary/budget-aware) |
| 24 | `24_openinference_otel.py` | OpenInference + OTel → RunLedgerOTLPExporter |
| 25 | `25_outcomes_roi.py` | Outcome recording, ROI summary, workflow cost-per-success |
| 26 | `26_warehouse_export.py` | S3/GCS/R2 warehouse export destination setup |
| 27 | `27_approvals_workflow.py` | Approval queue: create, approve, deny, cancel |
| 28 | `28_billing_webhook_server.py` | Billing webhook receiver with HMAC-SHA256 verification |
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

rl.shutdown()
```

Streaming and `AsyncAnthropic` are both supported.

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

Other providers:

```typescript
import { GoogleGenerativeAI } from '@google/generative-ai'
import { Mistral } from '@mistralai/mistralai'
import { CohereClientV2 } from 'cohere-ai'

rl.instrumentGemini(new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!))
rl.instrumentMistral(new Mistral({ apiKey: process.env.MISTRAL_API_KEY }))
rl.instrumentCohere(new CohereClientV2({ token: process.env.COHERE_API_KEY }))
```

---

## OTLP / OpenTelemetry / OpenInference

Send traces from any OTel-instrumented application directly to RunLedger — no SDK adoption required.

**Mode 1 — Direct OTLP/HTTP** (app → RunLedger):

```bash
curl -X POST http://localhost:8000/v1/traces \
     -H "Authorization: Bearer rl_dev_..." \
     -H "Content-Type: application/json" \
     -d '{
       "resourceSpans": [{
         "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "my-agent"}}]},
         "scopeSpans": [{
           "scope": {"name": "openinference.instrumentation.openai"},
           "spans": [{
             "traceId": "<base64 16 bytes>",
             "spanId":  "<base64 8 bytes>",
             "name": "chat.completion",
             "kind": 3,
             "startTimeUnixNano": "1700000000000000000",
             "endTimeUnixNano":   "1700000001500000000",
             "attributes": [
               {"key": "openinference.span.kind", "value": {"stringValue": "LLM"}},
               {"key": "llm.model_name",          "value": {"stringValue": "gpt-4o-mini"}},
               {"key": "llm.provider",            "value": {"stringValue": "openai"}},
               {"key": "llm.token_count.prompt",  "value": {"intValue": 128}},
               {"key": "llm.token_count.completion", "value": {"intValue": 64}}
             ],
             "status": {"code": 1}
           }]
         }]
       }]
     }'
# → {"partialSuccess": {}}
```

**Mode 2 — Via OTel Collector** (app → Collector → RunLedger):

```bash
# Start the optional OTel Collector sidecar
docker compose --profile otel -f infra/docker-compose.yml up otel-collector

# Point your OTel SDK at the Collector:
#   OTLP/HTTP → http://localhost:4318
#   OTLP/gRPC → http://localhost:4317
# The Collector batches and forwards to RunLedger automatically.
```

**Attribute priority** — RunLedger normalises in this order:
1. OpenInference (`openinference.span.kind`, `llm.model_name`, `llm.token_count.*`)
2. OTel GenAI (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`)
3. Generic span name / kind heuristics

Span kinds supported: `AGENT` → agent, `CHAIN` → chain, `LLM` → llm, `TOOL` → tool, `RETRIEVER` → retrieval.

**Run-context attributes** — attach to the root span to link traces to sessions and users:

| Attribute | Aliases | Description |
|-----------|---------|-------------|
| `runledger.session_id` | `session.id`, `openinference.session_id` | User session |
| `runledger.end_user_id` | `user.id`, `openinference.user_id`, `enduser.id` | End-user ID |
| `runledger.feature_tag` | `tag.feature`, `feature_tag` | Product feature label |
| `runledger.deployment_version` | `service.version` (resource) | Deployment label |

**Message payload capture** — extracted from LLM spans when privacy mode allows:

| Attribute | Description |
|-----------|-------------|
| `llm.input_messages.N.message.{role,content}` | Numbered prompt messages (OpenInference) |
| `llm.output_messages.0.message.content` | First completion message (OpenInference) |
| `input.value` / `output.value` | Generic fallback |

Each OTLP trace becomes one RunLedger agent run. LLM spans generate `provider_call` records (with cost computed by the pricing engine). Tool spans generate `tool_call` records. All raw OTLP payloads are staged for replay and parser-evolution safety.

Monitor ingest health via **Settings → OTLP** or the management API (`GET /v1/traces/stats`, `GET /v1/traces/batches`).

**Python SDK OTel exporter** — ship traces from any `openinference-instrumentation-*` or OTel `TracerProvider` directly to RunLedger with zero code change:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from runledger_sdk.otel_exporter import RunLedgerOTLPExporter

exporter = RunLedgerOTLPExporter(api_key="rl_dev_...", base_url="http://localhost:8000")
provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(exporter))

# Or attach to an existing provider via the client:
# rl.instrument_otel(provider)
```

Requires `pip install "runledger-sdk[otel]"`.

See `examples/22_otlp_ingest.py` for a full Python demo and `examples/24_openinference_otel.py` for an OpenInference integration walkthrough.

**OTLP documentation:**
- `docs/otlp.md` — integration guide + API reference
- `docs/openinference.md` — OpenInference attribute mapping details
- `docs/collector.md` — OTel Collector configuration examples

---

## Prompt Management

Fetch versioned prompts and render `{{variable}}` placeholders:

```python
rl = RunLedger(api_key="rl_dev_...")

rendered = rl.get_prompt(
    "support-agent",
    environment="production",
    variables={"user_name": "Alice", "company": "Acme"},
)
# rendered["content"]    → "Welcome Alice! How can I assist you at Acme today?"
# rendered["version"]    → 3
# rendered["model_hint"] → "gpt-4o-mini"

with rl.context(
    end_user_id="u_123",
    deployment_version=f"support-agent:{rendered['version']}",
) as run_id:
    resp = client.chat.completions.create(
        model=rendered["model_hint"] or "gpt-4o-mini",
        messages=[{"role": "system", "content": rendered["content"]}],
    )
```

---

## Quality Scores

Submit human, rule-based, or automated quality scores for any run:

```python
with rl.context(feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Is this answer helpful?"}],
    )
    rl.score("helpfulness", 0.9, label="good", source="human")
    rl.score("relevance", 0.8, run_id=str(run_id), confidence=0.95)
```

Scores are fail-silent and will never break application flow.

---

## Model Gateway (OpenAI-compatible proxy)

Point any OpenAI client at the RunLedger gateway for prompt caching, provider fallback, and full request logging:

```python
import openai

client = openai.OpenAI(
    api_key="rl_dev_...",
    base_url="http://localhost:8000/gateway",
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is 2+2?"}],
)
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

---

## Context Manager

`rl.context()` attaches metadata to every event fired inside the block. Contexts nest:

```python
with rl.context(
    end_user_id="u_123",
    session_id="sess_abc",
    feature_tag="support-bot",
    deployment_version="v2.1",
) as run_id:
    ...
```

---

## Cross-service Propagation

```python
# Service A (caller)
with rl.context(end_user_id="u_123", feature_tag="pipeline"):
    headers = rl.propagation_headers()
    # {'X-RunLedger-Run-Id': '...', 'X-RunLedger-End-User-Id': 'u_123', ...}
    response = httpx.post("http://service-b/process", headers=headers)

# Service B (receiver)
@app.post("/process")
async def process(request: Request):
    ctx = RunLedger.from_headers(dict(request.headers))
    async with ctx as run_id:
        ...
```

---

## Local Mode (zero setup)

Skip the API entirely during early development:

```python
rl = RunLedger(local=True)  # no API key, no server needed
```

Events are printed to stdout as structured JSON.

---

## Dashboard Pages

| Page | Path | Description |
|------|------|-------------|
| Run Explorer | `/runs` | Filter + paginate runs; click into DAG viewer; export CSV |
| Analytics | `/analytics` | Spend summary, charts, top spenders |
| User Profiles | `/analytics/users` | Cohorts, anomaly detection, per-user spend |
| Economics | `/analytics/economics` | Unit economics, version comparison, regressions |
| Budgets | `/budgets` | Create budgets, live spend progress, breach history |
| Billing | `/billing` | Billing periods, chargeback breakdown, signed export |
| Invoices | `/invoices` | Provider invoice import, reconciliation, dispute trail |
| Outcomes & ROI | `/outcomes` | Cost-per-outcome, workflow ROI, success rate trend |
| Sessions | `/sessions` | Multi-turn conversations; cost-over-turns chart |
| Evaluations | `/evaluations` | Submit + view quality scores, regressions |
| Evaluator Framework | `/evaluation` | Batch evaluation, LLM judge, drift detection |
| Prompts | `/prompts` | Version-controlled prompt registry, diff viewer, promote |
| Approvals | `/approvals` | Governance queue for sensitive actions |
| Replay | `/replay` | Cost-projection experiments across model configs |
| Ledger | `/ledger` | HMAC-signed snapshots, tool registry, privacy policy |
| Gateway | `/gateway` | Model Gateway stats and routing log |
| Settings | `/settings` | API keys, provider pricing, alerts, integrations, OTLP |
| Admin | `/admin` | Platform stats, tenant + user management (platform admin only) |

---

## What Gets Captured Automatically

| Field | How |
|-------|-----|
| `model` | From the API response |
| `input_tokens` / `output_tokens` | From the API response |
| `cached_input_tokens` | From OpenAI Prompt Caching |
| `provider_request_id` | From response `id` field (for invoice reconciliation) |
| `latency_ms` | Measured wall-clock around the API call |
| `cost_usd` | Computed server-side from the pricing engine |
| `reported_cost_usd` | From upstream OpenInference `llm.cost.total` |
| `end_user_id` | Set by you in `rl.context()` |
| `session_id` | Set by you in `rl.context()` |
| `feature_tag` | Set by you in `rl.context()` |
| `run_id` | Auto-generated UUID (or set by you) |
| Span DAG | Full parent-child tree via LangChain/LangGraph callbacks |

No prompts or completions are sent unless you opt in to `PrivacyMode.FULL`.

---

## Supported Providers

| Provider | Models | SDK |
|----------|--------|-----|
| OpenAI | gpt-4o · gpt-4o-mini · gpt-4-turbo · gpt-3.5-turbo · o1 · o3-mini | Python + TypeScript |
| Anthropic | claude-opus-4-6 · claude-sonnet-4-6 · claude-haiku-4-5 | Python + TypeScript |
| Google | gemini-1.5-pro · gemini-1.5-flash | Python + TypeScript |
| Mistral | Any | Python + TypeScript |
| Cohere | Any | Python + TypeScript |
| Any OpenAI-compatible | Ollama, vLLM, Groq, OpenRouter, Azure OpenAI, etc. | Python + TypeScript |

Add a new model by inserting a row into `provider_pricing` — no code change required.

---

## Metering Engine

The pricing engine runs as a Celery worker and enriches every provider call within 60 seconds:

- **Effective-dated pricing** — prices are versioned by date; retroactive corrections apply correctly
- **Workspace overrides** — per-workspace pricing rows take priority over global defaults
- **Cached input discount** — applies OpenAI Prompt Caching rates (50% off input by default)
- **Free / local providers** — Ollama and any provider without a pricing row are stored as `$0.00`, not skipped
- **Idempotent rollups** — `usage_hourly` and `usage_daily` are fully recomputed per window; replaying produces identical results

| Celery Task | Interval |
|-------------|----------|
| `cost_enrichment` | Every 60s |
| `rollup_hourly` | Every 30 min |
| `rollup_daily` | Daily at 00:05 UTC |
| `data_quality` | Every 1h |
| `runaway_protection` | Every 5 min |
| `budget_spend_sync` | Daily at 00:10 UTC |
| `nightly_analytics` | Daily at 02:00 UTC (anomaly detection) |
| `ledger.daily_snapshots` | Daily at 01:00 UTC |
| `ledger.suspicious_sequences` | Every 60s |
| `score_rollup.run` | Daily at 01:30 UTC |
| `alerts.evaluate_rules` | Every 5 min |
| `otlp_finalize` | Every 3 min (closes stale OTLP traces) |

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

# Cost regressions
curl "$BASE/analytics/regressions" -H "Authorization: Bearer $KEY"
```

All endpoints accept `from` and `to` query params (ISO-8601).

---

## CLI

```bash
export RUNLEDGER_API_KEY=rl_dev_...

# First-time setup — creates admin user, writes .env, prints quickstart curl commands
runledger init

# Health check — DB, Redis, auth, worker status (exits 1 on failure; useful in CI)
runledger doctor

runledger validate                        # sends a test event to verify connectivity
runledger status                          # checks API + DB + Redis health
runledger runs --limit 5                  # lists your 5 most recent agent runs
runledger check-regression --threshold 20 # exits 1 if cost regressions found (CI gate)
```

**Interactive API Reference** is available at `http://localhost:8000/reference` — a Scalar UI powered by your live OpenAPI spec.

---

## Documentation

| Doc | Path | Contents |
|-----|------|----------|
| OTLP integration guide | `docs/otlp.md` | Route reference, attribute priority, error codes |
| OpenInference mapping | `docs/openinference.md` | Full attribute mapping tables |
| OTel Collector config | `docs/collector.md` | Reference configs, processor examples |
| Railway deployment | `docs/deployment.md` | Full production deployment guide |

---

## Development Commands

```bash
# Install all workspace dependencies
uv sync --all-packages

# Run the API (dev)
cd apps/api && uv run fastapi dev runledger_api/main.py

# Run Celery worker
cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo

# Run Celery beat scheduler
cd apps/api && uv run celery -A runledger_api.core.celery_app beat --loglevel=info

# Run frontend (dev)
cd apps/web && npm run dev

# Run database migrations
cd apps/api && uv run alembic upgrade head

# Full local stack
docker compose -f infra/docker-compose.yml up

# Full local stack + OTel Collector
docker compose -f infra/docker-compose.yml --profile otel up

# Run tests
cd apps/api && uv run pytest

# Lint + typecheck
uv run ruff check . && uv run mypy apps/api/runledger_api
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and the PR process.

---

## License

MIT — see [LICENSE](LICENSE) for details.
