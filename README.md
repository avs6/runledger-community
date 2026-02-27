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

Phases 0–4 are complete and production-ready. The SDK ships with OpenAI, LangChain, and LangGraph support, and the metering engine automatically prices every call within 60 seconds.

| Phase | What ships | Status |
|-------|------------|--------|
| 0 | Monorepo · infrastructure · health API · CI | ✅ Complete |
| 1 | Ingestion API · multi-tenancy · API-key auth · event pipeline | ✅ Complete |
| 2 | SDK — OpenAI wrapper · context propagation · local mode | ✅ Complete |
| 3 | SDK — LangChain · LangGraph · CLI · example agents | ✅ Complete |
| 4 | Billing-grade metering · pricing engine · analytics API | ✅ Complete |
| 5 | Run Explorer + DAG viewer UI (Next.js) | Planned |
| 6 | Metering dashboard (spend by model/user/feature) | Planned |
| 7 | Budgets + spend guardrails with automatic actions | Planned |
| 8 | Chargeback engine + reconciliation + dispute trail | Planned |
| 9 | Unit economics graph + change impact diffs | Planned |
| 10 | End-user analytics + replay harness | Planned |
| 11 | Tamper-evident ledger + production polish + OSS release | Planned |

**103 tests** across all completed phases (ruff + mypy clean).

---

## Quick Start

See **[QUICKSTART.md](./QUICKSTART.md)** for the full 5-minute guide including LangChain, LangGraph, async, and FastAPI patterns.

### 1. Install

```bash
# OpenAI only
pip install "runledger-sdk[openai]"

# LangChain + LangGraph + CLI
pip install "runledger-sdk[all]"
```

### 2. Run the local stack

```bash
git clone https://github.com/yourorg/runledger
cd runledger
docker compose up -d                            # Postgres + Redis + API + Worker
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python scripts/seed.py
# → prints: API Key: rl_test_xxxxxxxxxxxxxxxxxxxx
```

### 3. Instrument your agent (2 lines)

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_test_...")   # or set RUNLEDGER_API_KEY
rl.instrument()                          # wraps openai.OpenAI + AsyncOpenAI

client = openai.OpenAI()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(resp.choices[0].message.content)

rl.shutdown()  # flush before process exits
```

Every call inside the `with` block is automatically tracked: model, tokens, latency, and cost in USD.

### 4. Try local mode (zero setup)

No API key, no server — events are logged as structured JSON to stdout:

```python
rl = RunLedger(local=True)
rl.instrument()

with rl.context(end_user_id="u_test", feature_tag="dev") as run_id:
    # ... your OpenAI / LangChain / LangGraph code
```

---

## SDK Integration

### OpenAI

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_test_...")
rl.instrument()

client = openai.OpenAI()

with rl.context(end_user_id="u_123", session_id="sess_abc", feature_tag="chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Explain transformers in one sentence."}],
    )

rl.shutdown()
```

### LangChain

```python
from runledger_sdk import RunLedger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

rl = RunLedger(api_key="rl_test_...")

chain = ChatPromptTemplate.from_template("Explain {topic} in one sentence.") \
      | ChatOpenAI(model="gpt-4o-mini") \
      | StrOutputParser()

handler = rl.callback_handler()

with rl.context(end_user_id="u_456", feature_tag="explainer") as run_id:
    result = chain.invoke({"topic": "gradient descent"}, config={"callbacks": [handler]})

rl.shutdown()
```

### LangGraph

```python
from runledger_sdk import RunLedger
from runledger_sdk.langgraph import instrument_graph

rl = RunLedger(api_key="rl_test_...")

# Build and compile your graph normally
graph = builder.compile()

# Instrument once — returns a new configured view, original graph unchanged
instrumented = instrument_graph(graph, rl._get_sync_transport())

with rl.context(end_user_id="u_789", feature_tag="qa-agent") as run_id:
    result = instrumented.invoke({"question": "What is 2+2?"})

rl.shutdown()
```

### Context manager

`rl.context()` is a context manager (sync and async). Contexts nest and inherit:

```python
with rl.context(end_user_id="u_123"):
    # tagged to u_123

    with rl.context(feature_tag="checkout"):
        # tagged to u_123 + checkout

    with rl.context(feature_tag="search"):
        # tagged to u_123 + search
```

---

## Analytics API

Once events are flowing, query spend data with your API key:

```bash
BASE=http://localhost:8000
KEY=rl_test_...

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

All endpoints accept `from` and `to` query params (ISO-8601):

```bash
curl "$BASE/analytics/summary?from=2026-01-01T00:00:00Z&to=2026-01-31T23:59:59Z" \
     -H "Authorization: Bearer $KEY"
```

---

## Supported Providers

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4o · gpt-4o-mini · gpt-4-turbo · gpt-3.5-turbo · o1 · o3-mini |
| Anthropic | claude-opus-4-6 · claude-sonnet-4-6 · claude-haiku-4-5 |
| Google | gemini-1.5-pro · gemini-1.5-flash |

Add a new model by inserting a row into `provider_pricing` — no code change required.

---

## What Gets Captured

| Field | Source |
|-------|--------|
| `model` | API response |
| `input_tokens` / `output_tokens` | API response |
| `cached_input_tokens` | OpenAI Prompt Caching header |
| `latency_ms` | Measured wall-clock around the call |
| `cost_usd` | Computed server-side from the pricing engine |
| `end_user_id` | Set by you in `rl.context()` |
| `session_id` | Set by you in `rl.context()` |
| `feature_tag` | Set by you in `rl.context()` |
| `run_id` | Auto-generated UUID (or set by you) |
| Span DAG | Full parent-child tree via LangChain/LangGraph callbacks |

No prompts or completions are sent unless you opt in to `PrivacyMode.FULL`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Agent App                          │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ OpenAI SDK   │  │ LangChain/Graph│  │  Custom Tools  │  │
│  └──────┬───────┘  └───────┬────────┘  └───────┬────────┘  │
│         └──────────────────┼───────────────────┘           │
│                   runledger-sdk (async)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP batch (non-blocking)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RunLedger Platform                       │
│                                                             │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │  Collector API │──▶│  Redis Streams (event buffer)    │  │
│  │  (FastAPI)     │   └──────────────┬───────────────────┘  │
│  └────────────────┘                  │                      │
│                             ┌────────▼────────┐             │
│  ┌────────────────┐         │  Celery Workers  │             │
│  │  Business API  │         │  · cost enrich   │             │
│  │  (FastAPI)     │◀────────│  · hourly rollup │             │
│  └───────┬────────┘         │  · data quality  │             │
│          │                  └────────┬──────────┘            │
│  ┌───────▼────────────────────────────────────┐             │
│  │              PostgreSQL 16                  │             │
│  │  events · spans · metering · pricing        │             │
│  │  usage_hourly · usage_daily · budgets        │             │
│  └─────────────────────────────────────────────┘            │
│                                                             │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │  Redis (cache) │   │  Budget Enforcement (hot path)   │  │
│  │  idempotency   │   │  <5ms p99 spend check            │  │
│  └────────────────┘   └──────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┬─┘
                                                            │
                            ┌───────────────────────────────▼──┐
                            │        RunLedger UI               │
                            │        (Next.js 14 — Phase 5+)    │
                            │                                   │
                            │  Run Explorer · DAG Viewer        │
                            │  Metering · Budgets · Chargeback  │
                            │  Unit Economics · Analytics       │
                            └───────────────────────────────────┘
```

---

## Metering Engine

The pricing engine (Phase 4) runs as a Celery worker and enriches every provider call within 60 seconds:

- **Effective-dated pricing** — prices are versioned by date, so retroactive corrections work correctly
- **Workspace overrides** — per-workspace pricing rows take priority over global defaults
- **Cached input discount** — applies OpenAI Prompt Caching rates (50% off input by default, or a custom rate)
- **Idempotent rollups** — `usage_hourly` and `usage_daily` tables are fully recomputed per window; replaying produces identical results
- **Replay backfill** — re-run cost enrichment + rollups for any historical time range after a pricing correction

Beat schedule:

| Task | Interval |
|------|----------|
| `cost_enrichment` | Every 60s |
| `rollup_hourly` | Every 30 min |
| `rollup_daily` | Daily at 00:05 UTC |
| `data_quality` | Every 1h |

---

## API Reference

All endpoints require `Authorization: Bearer <api_key>` and are workspace-scoped to the key used.

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/v1/events` | Ingest a single event |
| `POST` | `/ingest/v1/batch` | Ingest up to 100 events |

**Event types:** `run_start` · `run_end` · `span_start` · `span_end` · `provider_call` · `tool_call` · `outcome`

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/workspaces` | Create a workspace |
| `POST` | `/auth/api-keys` | Generate an API key |
| `GET`  | `/auth/api-keys` | List active keys (prefix + last_used only) |
| `DELETE` | `/auth/api-keys/{id}` | Revoke a key |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/analytics/summary` | Total cost, tokens, run count |
| `GET` | `/analytics/spend-over-time` | Time-series (`granularity=hourly\|daily`) |
| `GET` | `/analytics/spend-by-model` | Cost breakdown by model |
| `GET` | `/analytics/spend-by-user` | Top spenders (`limit=N`) |
| `GET` | `/analytics/spend-by-feature` | Cost breakdown by feature tag |

All analytics endpoints accept `from` and `to` (ISO-8601) query params.

Interactive docs: `http://localhost:8000/docs`

---

## Example Agents

Runnable examples in `examples/`:

```bash
export OPENAI_API_KEY=sk-...
export RUNLEDGER_API_KEY=rl_test_...   # optional — examples use local=True by default

# Basic OpenAI call
python examples/01_openai_basic.py

# Multi-turn conversation with session tracking
python examples/02_openai_multi_turn.py

# LangChain chain
python examples/03_langchain_chain.py

# LangGraph ReAct agent with search + calculator tools
python examples/04_langgraph_agent.py

# FastAPI service (per-request context + propagation headers)
uvicorn examples.05_fastapi_service:app --reload
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -H "X-User-Id: user-alice" \
     -d '{"message": "What is Python?"}'
```

---

## CLI

```bash
export RUNLEDGER_API_KEY=rl_test_...

runledger validate        # send a synthetic test event, confirm receipt
runledger status          # check API + DB + Redis health
runledger runs --limit 5  # list your most recent agent runs
```

---

## Cross-service Propagation

Preserve run context across service boundaries:

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

All spans from both services share the same `run_id` and appear together in the run explorer.

---

## Development

```bash
# Install dependencies
uv sync --all-packages

# Run API with hot reload
cd apps/api && uv run uvicorn runledger_api.main:app --reload

# Run Celery worker
cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo

# Run all tests
cd apps/api && uv run pytest
cd packages/sdk && uv run pytest

# Lint + type check
uv run ruff check .
uv run mypy .
```

---

## OSS vs Paid

**Open source (free forever):**
- SDK — OpenAI, LangChain, LangGraph
- Collector + event pipeline
- Metering + pricing engine + analytics API
- Run Explorer + DAG viewer (Phase 5)
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

## Documentation

| Doc | Description |
|-----|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | 5-minute getting-started guide |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | Full 6-month technical implementation plan |
| [roadmap.md](./roadmap.md) | Product roadmap with feature areas and status |

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).

The core SDK and collector are open source. The paid tier (multi-tenancy, enforcement, ledger, enterprise integrations) is offered as a hosted service and under a commercial license.
