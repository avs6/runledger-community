# RunLedger — Implementation Roadmap

6-month plan for a solo founder building a production-grade Agent FinOps Control Plane.

---

## Phase Status

| Phase | Title | Status | Roadmap Areas | Tests |
|-------|-------|--------|---------------|-------|
| 0 | Monorepo + Infrastructure Foundation | ✅ Complete | Area 0 | 3 |
| 1 | Ingestion API + Multi-tenancy + Auth | ✅ Complete | Areas 1, 2 | 17 |
| 2 | SDK — OpenAI Wrapper + Context Propagation | ✅ Complete | Area 3 | 28 |
| 3 | SDK — LangChain + LangGraph + CLI | ✅ Complete | Areas 4, 5, 6 | 33 |
| 4 | Billing-grade Metering Core | ✅ Complete | Area 7 | 22 |
| 5 | Run Explorer + DAG Viewer UI | ✅ Complete | Area 8 | — |
| 6 | Metering Dashboard | ✅ Complete | Area 9 | +3 |
| 7 | Budgets + Spend Guardrails | ✅ Complete | Areas 10, 11 | 19 |
| 8 | Chargeback Engine + Reconciliation | 🔲 Pending | Area 12 | — |
| 9 | Unit Economics Graph + Change Impact | 🔲 Pending | Area 13 | — |
| 10 | End-user Analytics + Replay Harness | 🔲 Pending | Area 14 | — |
| 11 | Tamper-evident Ledger + OSS Launch | 🔲 Pending | Area 15 | — |

**Total tests shipped (Phases 0–7):** 125

---

## Recommended Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.13 | Already chosen; async-native; LangChain/LangGraph ecosystem |
| API framework | FastAPI | Async, OpenAPI auto-docs, fastest iteration velocity |
| Primary database | PostgreSQL 16 | Transactional + analytics via partitioned tables + materialized views |
| Queue / cache | Redis 7 (Streams) | Budget enforcement hot path, event buffering, idempotency keys |
| Async workers | Celery + Redis broker | Event pipeline, aggregation rollups, reconciliation jobs |
| SDK | Python 3.13 (PyPI: `runledger-sdk`) | LangChain callbacks + LangGraph hooks + OpenAI wrapper |
| Frontend | Next.js 14 (App Router, TypeScript) | shadcn/ui components, Recharts for dashboards |
| UI auth | NextAuth.js (credentials + API key) | Session auth for dashboard, JWT for API |
| DB migrations | Alembic | Standard for FastAPI/SQLAlchemy projects |
| Package manager | uv (workspaces) | Already chosen; fastest Python tooling |
| Deploy (prod) | Railway (Postgres + Redis + containers) | Managed ops, solo-friendly |
| Deploy (local) | Docker Compose | Single `docker compose up` for full stack |

**Why PostgreSQL only (no ClickHouse, no TimescaleDB extension):**
Partitioned tables + materialized views handle V1 metering scale with zero extra ops. TimescaleDB requires an extension not available on Railway's managed Postgres. ClickHouse adds a second database to operate. Migrate to ClickHouse if you outgrow Postgres — the data model is designed for it.

---

## Monorepo Structure

```
runledger/
├── apps/
│   ├── api/                    # FastAPI backend (collector + business API)
│   │   ├── runledger_api/
│   │   │   ├── core/           # Config, DB session, Redis client, Celery app
│   │   │   ├── models/         # SQLAlchemy ORM models
│   │   │   ├── schemas/        # Pydantic request/response schemas
│   │   │   ├── routers/        # FastAPI routers (ingest, runs, analytics, budgets, billing)
│   │   │   ├── services/       # Business logic (metering, pricing, chargeback, guardrails)
│   │   │   ├── workers/        # Celery tasks (pipeline, rollups, reconciliation)
│   │   │   └── main.py         # FastAPI app entrypoint
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── web/                    # Next.js frontend
│       ├── app/                # App Router pages
│       ├── components/         # Shared UI components
│       ├── lib/                # API client, auth config, utils
│       └── package.json
├── packages/
│   └── sdk/                    # runledger-sdk (published to PyPI)
│       ├── runledger_sdk/
│       │   ├── client.py       # RunLedger client + instrument()
│       │   ├── context.py      # contextvars-based context propagation
│       │   ├── openai.py       # OpenAI wrapper
│       │   ├── langchain.py    # LangChain CallbackHandler
│       │   ├── langgraph.py    # LangGraph node hooks
│       │   ├── transport.py    # Async HTTP client (batching + retry)
│       │   └── cli.py          # runledger CLI (validate/status/runs)
│       ├── pyproject.toml
│       └── README.md
├── examples/                   # Runnable example agents
│   ├── 01_openai_basic.py
│   ├── 02_openai_multi_turn.py
│   ├── 03_langchain_chain.py
│   ├── 04_langgraph_agent.py
│   ├── 05_fastapi_service.py
│   ├── 06_ollama_local.py
│   └── 07_analytics_query.py
├── db/
│   └── migrations/             # Alembic migration files
├── infra/
│   ├── docker-compose.yml      # Full local stack
│   └── docker-compose.dev.yml  # Dev overrides (hot reload)
├── docs/
│   ├── quickstart.md
│   ├── sdk-reference.md
│   └── deployment.md
├── QUICKSTART.md               # Getting started guide (5-minute onboarding)
├── pyproject.toml              # uv workspace root
├── CLAUDE.md
├── IMPLEMENTATION.md           # This file
└── README.md
```

---

## Database Schema

### Tenant & Auth

```sql
tenants          (id, slug, name, plan ENUM, created_at)
workspaces       (id, tenant_id, name, created_at)
applications     (id, workspace_id, name, environment ENUM[dev|staging|prod])
api_keys         (id, workspace_id, key_hash, key_prefix, scopes[], last_used_at, expires_at)
workspace_users  (id, workspace_id, user_id, role ENUM[admin|billing_admin|viewer])
users            (id, email_hash, created_at)
```

### Instrumentation Events

```sql
agent_runs       (id UUID, workspace_id, application_id, end_user_id, session_id,
                  feature_tag, status ENUM, started_at, ended_at,
                  total_cost_usd NUMERIC, total_input_tokens BIGINT,
                  total_output_tokens BIGINT, deployment_version, metadata JSONB)

spans            (id UUID, run_id, parent_span_id, span_type ENUM[chain|llm|tool|agent|retrieval],
                  name, started_at, ended_at, status ENUM, cost_usd NUMERIC, metadata JSONB)

provider_calls   (id UUID, span_id, run_id, workspace_id, end_user_id,
                  provider, model, input_tokens INT, output_tokens INT,
                  cached_input_tokens INT, latency_ms INT, cost_usd NUMERIC,
                  status ENUM, error_type, created_at)
                  -- PARTITIONED BY RANGE (created_at) — monthly partitions

tool_calls       (id UUID, span_id, run_id, workspace_id,
                  tool_name, tool_type ENUM[read|write|privileged],
                  risk_score SMALLINT, duration_ms INT, status ENUM, created_at)

outcome_events   (id UUID, run_id, event_type, success BOOL,
                  labels JSONB, created_at)
```

### Metering

```sql
provider_pricing (id, provider, model, input_cost_per_1m NUMERIC,
                  output_cost_per_1m NUMERIC, cached_input_cost_per_1m NUMERIC,
                  effective_from TIMESTAMPTZ, effective_to TIMESTAMPTZ,
                  workspace_id UUID NULL)   -- NULL = global; non-null = workspace override

-- Materialized rollup tables (Celery jobs maintain these)
usage_hourly     (workspace_id, application_id, end_user_id, model, feature_tag,
                  hour TIMESTAMPTZ, input_tokens BIGINT, output_tokens BIGINT,
                  cost_usd NUMERIC, run_count INT, call_count INT)
                  -- INDEX on (workspace_id, hour) and (end_user_id, hour)

usage_daily      (same columns, day DATE)

data_quality_issues (id, provider_call_id, workspace_id, issue_type, detail, created_at)
```

### Budgets & Guardrails

```sql
budgets          (id, workspace_id, scope_type ENUM[workspace|app|end_user|feature_tag],
                  scope_id TEXT, period_type ENUM[daily|monthly|total],
                  limit_usd NUMERIC, action ENUM[notify|throttle|block|downgrade],
                  downgrade_to_model TEXT, created_at)

budget_breaches  (id, budget_id, occurred_at, spend_at_breach_usd,
                  action_taken ENUM, notified_at)

budget_notifications (id, workspace_id, channel ENUM[webhook|slack],
                      destination_url, events[])
```

### Billing & Chargeback

```sql
billing_periods  (id, workspace_id, period_start DATE, period_end DATE,
                  status ENUM[open|closing|closed], total_cost_usd NUMERIC,
                  snapshot_hash TEXT, closed_at)

chargeback_rules (id, workspace_id, allocation_type ENUM[cost_center|team|env],
                  dimension TEXT, weight NUMERIC)

usage_snapshots  (id, billing_period_id, snapshot_data JSONB,
                  signature TEXT, signing_key_id, created_at)
```

### Ledger & Privacy

```sql
ledger_keys      (id, workspace_id, key_hash, active BOOL,
                  created_at, rotated_at)

capture_policies (id, workspace_id, scope JSONB, mode ENUM[metadata|errors|sampled|full],
                  sample_rate NUMERIC, redaction_rules JSONB)

payload_access_log (id, workspace_id, accessor_user_id, run_id, span_id,
                    accessed_at, reason)
```

---

## 6-Month Implementation Plan

### Phase 0 — Weeks 1–2: Monorepo + Infrastructure Foundation ✅
**Roadmap areas:** 0 (Product Architecture Baseline)

**Goal:** `docker compose up` runs Postgres + Redis + a health-check API. The skeleton is in place for every subsequent phase to build on.

**What was built:**

- `apps/api/runledger_api/core/config.py` — pydantic-settings config (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ENVIRONMENT`, `LOG_LEVEL`)
- `apps/api/runledger_api/core/db.py` — SQLAlchemy async engine + session factory (asyncpg driver)
- `apps/api/runledger_api/core/redis.py` — async Redis client
- `apps/api/runledger_api/core/logging.py` — structlog structured logging setup
- `apps/api/runledger_api/core/celery_app.py` — Celery app wired to Redis broker
- `apps/api/runledger_api/routers/health.py` — `GET /health` → `{"status":"ok","db":"ok","redis":"ok"}`
- `apps/api/runledger_api/main.py` — FastAPI app entrypoint, health router registered
- `apps/api/alembic/` — Alembic init, `alembic.ini`, `env.py` using async engine
- `infra/docker-compose.yml` — `postgres:16-alpine`, `redis:7-alpine`, `api`, `worker` services
- `infra/docker-compose.dev.yml` — hot-reload override (watchfiles)
- `.github/workflows/ci.yml` — ruff + mypy + pytest + typecheck on push

Tests: `tests/test_health.py` — **3 tests** (health ok, db degraded, redis degraded)

**Definition of done:** ✅ `docker compose up` starts all services; `GET /health` returns `{"status": "ok", "db": "ok", "redis": "ok"}`

---

### Phase 1 — Weeks 3–4: Ingestion API + Multi-tenancy + Auth ✅
**Roadmap areas:** 1 (Event Ingestion Pipeline), 2 (Multi-tenancy + Auth)

**Goal:** A real event can be sent via HTTP with an API key, stored in Postgres, and queried back.

**What was built:**

- `apps/api/alembic/versions/001_initial_schema.py` — migration for all Tenant & Auth + Instrumentation Events tables; `provider_calls` with 12 monthly range partitions
- `apps/api/runledger_api/models/tenant.py` — ORM: `Tenant`, `Workspace`, `Application`, `ApiKey`, `WorkspaceUser`, `User`
- `apps/api/runledger_api/models/events.py` — ORM: `AgentRun`, `Span`, `ProviderCall`, `ToolCall`, `OutcomeEvent`
- `apps/api/runledger_api/schemas/auth.py` — Pydantic schemas for workspace + API key CRUD
- `apps/api/runledger_api/schemas/events.py` — discriminated union event schema for batch ingestion
- `apps/api/runledger_api/routers/auth.py` — `POST /auth/workspaces`, `POST /auth/api-keys`, `GET /auth/api-keys`, `DELETE /auth/api-keys/{id}`
- `apps/api/runledger_api/routers/ingest.py` — `POST /ingest/v1/events`, `POST /ingest/v1/batch`; API key auth middleware; idempotency via Redis SETNX; events → Redis Stream `runledger:events:{workspace_id}`
- `apps/api/runledger_api/services/auth.py` — API key hashing, prefix generation (`rl_live_` / `rl_test_`), scope check
- `apps/api/runledger_api/core/deps.py` — FastAPI dependency: extract + validate Bearer token → `Workspace`
- `apps/api/runledger_api/workers/pipeline.py` — Celery `process_event_batch`: drains Redis Stream → validates → upserts all event types → acks stream
- `apps/api/scripts/seed.py` — seeds default tenant + workspace + API key; later extended with pricing data

Tests: `tests/test_auth.py` (**11 tests**), `tests/test_ingest.py` (**6 tests**) — **17 tests total**

**Definition of done:** ✅ Send 1000 events via batch endpoint, confirm they're all queryable with correct workspace scoping. No events cross tenant boundaries.

---

### Phase 2 — Weeks 5–6: SDK — OpenAI Wrapper + Context Propagation ✅
**Roadmap areas:** 3 (SDK — OpenAI + Context)

**Goal:** `rl.instrument()` wraps the OpenAI client. One line of code captures model, tokens, latency, and cost for every call.

**What was built:**

- `packages/sdk/runledger_sdk/client.py` — `RunLedger(api_key, base_url, privacy_mode, local)` client; `instrument()` monkey-patches `openai.OpenAI` and `openai.AsyncOpenAI`; `context()` context manager; `shutdown()` / `flush()` / `aflush()`
- `packages/sdk/runledger_sdk/context.py` — `contextvars.ContextVar`-based context; nested context inheritance; `propagation_headers()` / `from_headers()` for cross-service propagation; thread-safe + async-safe
- `packages/sdk/runledger_sdk/openai.py` — wraps `chat.completions.create` + async variant; captures `run_id`, `model`, `started_at`, tokens (`input_tokens`, `output_tokens`, `cached_input_tokens`), `latency_ms`, `status`, `error_type`
- `packages/sdk/runledger_sdk/transport.py` — async httpx transport; in-memory buffer (max 500 events); flush every 2s or 100 events; exponential backoff retry (3 attempts); background thread for sync usage; `local=True` mode logs structured JSON to stdout
- `packages/sdk/runledger_sdk/__init__.py` — public exports: `RunLedger`, `PrivacyMode`

Privacy modes:
```python
class PrivacyMode(Enum):
    METADATA_ONLY = "metadata_only"   # default
    ERRORS_ONLY   = "errors_only"
    SAMPLED       = "sampled"
    FULL          = "full"
```

Tests: `tests/test_openai.py` (**10 tests**), `tests/test_context.py` (**10 tests**), `tests/test_transport.py` (**8 tests**) — **28 tests total**

**Definition of done:** ✅ A bare `openai` script with two lines of RunLedger setup shows up in the ingestion pipeline with correct token counts.

---

### Phase 3 — Weeks 7–8: SDK — LangChain + LangGraph + CLI ✅
**Roadmap areas:** 4 (LangChain Callbacks), 5 (LangGraph Instrumentation), 6 (CLI)

**Goal:** Any LangChain chain or LangGraph graph is fully instrumented with one callback. The CLI validates instrumentation.

**What was built:**

- `packages/sdk/runledger_sdk/langchain.py` — `RunLedgerCallbackHandler(BaseCallbackHandler)`:
  - `on_chain_start/end/error` → CHAIN spans
  - `on_llm_start/end` → LLM spans + `ProviderCall` event with token counts extracted from `LLMResult`
  - `on_tool_start/end/error` → TOOL spans
  - `on_agent_action/finish` → AGENT spans + outcome event
  - `track_llm_cost=False` flag to prevent double-counting when used alongside `rl.instrument()`
  - Span parent-child stack maintained per `run_id` in contextvars

- `packages/sdk/runledger_sdk/langgraph.py` — `instrument_graph(graph, transport)`:
  - Uses `graph.with_config({"callbacks": [handler]})` — zero intrusion on the original graph object
  - Every node fires `span_start` / `span_end` via LangChain callbacks
  - Returns a new configured view; original graph unchanged

- `packages/sdk/runledger_sdk/cli.py` — `runledger` CLI (typer):
  - `runledger validate` — sends synthetic test event, confirms receipt
  - `runledger status` — checks API + DB + Redis health
  - `runledger runs [--limit N]` — lists recent runs as a table (run_id, model, cost, status, age)

- `examples/01_openai_basic.py` — minimal OpenAI instrumentation (2 lines of setup)
- `examples/02_openai_multi_turn.py` — multi-turn chat with `session_id` tracking
- `examples/03_langchain_chain.py` — `prompt | llm | StrOutputParser()` chain with callback handler
- `examples/04_langgraph_agent.py` — ReAct agent (search + calculator tools) with `instrument_graph()`
- `examples/05_fastapi_service.py` — FastAPI service with per-request `async with rl.context(...)`
- `examples/06_ollama_local.py` — local Ollama via OpenAI-compatible endpoint; `--local` flag for stdout mode (added in Phase 3)
- `QUICKSTART.md` — 11-section getting-started guide (install → API key → verify → OpenAI → LangChain → LangGraph → async → FastAPI → cross-service → analytics → examples)

Tests: `tests/test_langchain.py` (**13 tests**), `tests/test_langgraph.py` (**9 tests**), `tests/test_cli.py` (**11 tests**) — **33 tests total**

**Definition of done:** ✅ A LangGraph agent with `instrument_graph()` shows the full DAG structure (nodes as spans with parent-child links) in the API after a run.

---

### Phase 4 — Weeks 9–10: Billing-grade Metering Core ✅
**Roadmap areas:** 7 (Billing-grade Metering Core)

**Goal:** Every provider call has a cost in USD attached within 30 seconds. Aggregations by tenant/user/model/feature are queryable and stay correct after replay.

**What was built:**

- `apps/api/alembic/versions/002_metering_tables.py` — migration adding `provider_pricing`, `usage_hourly`, `usage_daily`, `data_quality_issues`
- `apps/api/runledger_api/models/metering.py` — ORM: `ProviderPricing`, `UsageHourly`, `UsageDaily`, `DataQualityIssue`
- `apps/api/runledger_api/services/pricing.py` — `calculate_cost()` async function:
  - Effective-dated price lookup (`at_time` parameter handles retroactive corrections)
  - Workspace override priority: workspace-specific row checked before global row
  - Cached input discount: uses `cached_input_cost_per_1m` if set; defaults to 50% of input rate
  - Formula: `tokens / 1_000_000 * rate_per_1m` (Decimal arithmetic, ROUND_HALF_UP, 8 decimal places)
  - Returns `None` if no pricing row found (surfaced as data quality issue)
- `apps/api/runledger_api/workers/metering.py` — 5 Celery tasks (all use `asyncio.run()` + `NullPool`):
  - `cost_enrichment_worker` (60s schedule): enriches `provider_calls` where `cost_usd IS NULL`; cascades to parent span + agent run
  - `rollup_hourly_worker` (30m schedule): full DELETE + INSERT for last 2h window in `usage_hourly`
  - `rollup_daily_worker` (daily 00:05 UTC): aggregates into `usage_daily` for previous day
  - `data_quality_worker` (1h schedule): flags calls with missing tokens/cost into `data_quality_issues`
  - `replay_backfill` (manual trigger): clears `cost_usd` for a time window, re-enriches, re-rolls hourly + daily
- `apps/api/runledger_api/schemas/analytics.py` — Pydantic: `AnalyticsSummary`, `SpendOverTime`, `SpendByModel`, `SpendByUser`, `SpendByFeature`, `SpendPoint`, `ModelSpend`, `UserSpend`, `FeatureSpend`
- `apps/api/runledger_api/routers/analytics.py` — 5 endpoints (all workspace-scoped via Bearer auth, query `provider_calls` directly):
  - `GET /analytics/summary` — total cost, tokens, run count for a time range
  - `GET /analytics/spend-over-time?granularity=hourly|daily` — time-series array
  - `GET /analytics/spend-by-model` — breakdown by model
  - `GET /analytics/spend-by-user?limit=N` — top spenders
  - `GET /analytics/spend-by-feature` — breakdown by feature_tag
- `apps/api/runledger_api/core/celery_app.py` (updated) — added `metering` worker to includes + Beat schedule
- `apps/api/scripts/seed.py` (updated) — `_seed_pricing()` inserts 11 model pricing rows:
  - OpenAI: gpt-4o ($2.50/$10.00), gpt-4o-mini ($0.15/$0.60), gpt-4-turbo ($10/$30), gpt-3.5-turbo ($0.50/$1.50), o1 ($15/$60), o3-mini ($1.10/$4.40)
  - Anthropic: claude-opus-4-6 ($15/$75), claude-sonnet-4-6 ($3/$15), claude-haiku-4-5 ($0.25/$1.25)
  - Google: gemini-1.5-pro ($1.25/$5.00), gemini-1.5-flash ($0.075/$0.30)
  - All effective from 2025-01-01 UTC

Tests: `tests/test_pricing.py` (**9 tests**), `tests/test_analytics.py` (**13 tests**, expanded to 16 in Phase 6) — **22 tests total**

**Definition of done:** ✅ Replaying the same set of events twice produces identical cost totals. Cost for `gpt-4o` at a date before and after OpenAI's pricing change returns different values.

---

### Phase 5 — Weeks 11–12: Run Explorer + DAG Viewer UI ✅
**Roadmap areas:** 8 (Run Explorer + DAG Viewer)

**Goal:** Log into the dashboard, search for a run, click into it, see the full DAG with cost per node.

**What was built:**

- `apps/web/` — Next.js 14 App Router frontend (TypeScript, Tailwind, shadcn/ui)
- `apps/web/lib/auth.ts` — NextAuth.js credentials provider; session API key generated on login and stored in JWT
- `apps/web/lib/api.ts` — typed fetch wrapper (`apiFetch`) reading `NEXT_PUBLIC_API_URL` + session Bearer token
- `apps/web/components/layout/` — `Sidebar`, `TopBar`, `SessionProvider` wrapper
- `apps/web/app/(dashboard)/runs/page.tsx` — Run Explorer: `RunsTable` (run_id, end_user_id, primary model, total cost, status badge, duration), `RunFilters` (status / feature_tag / end_user_id / search / time window), cursor-based pagination
- `apps/web/app/(dashboard)/runs/[run_id]/page.tsx` — Run Detail: `RunSummaryBar` (cost, tokens, duration, status, user, feature), `RunGraph` (react-flow DAG with colored nodes by span type, cost badge per LLM node, click-to-panel)
- `apps/web/components/dag/RunGraph.tsx` — `@xyflow/react` graph; auto-layout via dagre; node colors: LLM=indigo, TOOL=amber, CHAIN/AGENT=gray, error=red
- `apps/web/components/dag/SpanDetailPanel.tsx` — slide-in panel with span metadata, model, tokens, cost, error type
- `apps/web/types/api.ts` — `RunListItem`, `RunDetailResponse`, `SpanDetail`, `ProviderCallDetail`, `GraphNode`, `GraphEdge`
- `apps/api/runledger_api/routers/runs.py` — `GET /runs` (cursor pagination, filters), `GET /runs/{id}`, `GET /runs/{id}/graph`

**Definition of done:** ✅ Can find a run, see every LLM call and tool call in the DAG, click a node and see token counts and cost. DAG renders correctly for graphs with 50+ nodes.

---

### Phase 6 — Weeks 13–14: Metering Dashboard ✅
**Roadmap areas:** 9 (Metering Dashboard)

**Goal:** A finance person or engineering lead opens the dashboard and immediately understands spend, who's driving it, and where it's going.

**What was built:**

Backend schema additions (`apps/api/runledger_api/schemas/analytics.py`):
- `AnalyticsSummary`: added `prev_cost_usd` + `cost_delta_pct: Decimal | None` (prior period of equal duration; `None` when prior cost is zero)
- `UserSpend`: added `avg_cost_per_run` (computed Python-side) + `last_active` (SQL `MAX(created_at)`)
- `UserSpendDetail`: new schema with `spend_over_time[]`, `models_used[]`, `features_used[]`

Backend endpoint additions (`apps/api/runledger_api/routers/analytics.py`):
- `GET /analytics/summary` — now runs two DB queries (current + prior period), computes `cost_delta_pct`
- `GET /analytics/spend-by-user` — adds `MAX(created_at)` for `last_active`; `avg_cost_per_run` computed in Python
- `GET /analytics/users/{end_user_id}` — 4 sub-queries: summary, daily spend trend, models used, features used

Frontend (`apps/web/`):
- `npm install recharts` — Recharts charting library
- `apps/web/types/api.ts` — 8 new analytics TypeScript types
- `apps/web/lib/api.ts` — 6 fetch helpers: `getAnalyticsSummary`, `getSpendOverTime`, `getSpendByModel`, `getSpendByFeature`, `getSpendByUser`, `getUserSpend`
- `apps/web/components/analytics/SummaryCards.tsx` — 4 stat cards (total spend, runs, avg cost/run, tokens) with delta % badge (TrendingUp/Down icons)
- `apps/web/components/analytics/SpendOverTimeChart.tsx` — Recharts `LineChart` (client component)
- `apps/web/components/analytics/SpendByModelChart.tsx` — Recharts horizontal `BarChart` with input/output stacking
- `apps/web/components/analytics/SpendByFeatureChart.tsx` — Recharts `PieChart` (donut)
- `apps/web/components/analytics/TimeWindowPicker.tsx` — 24h / 7d / 30d preset buttons; updates URL search params via `useRouter`
- `apps/web/components/analytics/TopSpendersTable.tsx` — table with user links to `/analytics/users/[id]`
- `apps/web/app/(dashboard)/analytics/page.tsx` — server component; fetches 4 endpoints in parallel with `Promise.all`; passes data to client chart components
- `apps/web/app/(dashboard)/analytics/users/page.tsx` — top spenders table with time window picker
- `apps/web/app/(dashboard)/analytics/users/[end_user_id]/page.tsx` — user profile: spend trend + models + features
- `apps/web/components/layout/Sidebar.tsx` — removed `soon: true` badge from Analytics nav item
- `examples/07_analytics_query.py` — runnable example querying all analytics endpoints

Tests added to `apps/api/tests/test_analytics.py`:
- `test_summary_delta_computed` — verifies `cost_delta_pct = 100` when current = 2× prior
- `test_summary_delta_none_when_prev_zero` — verifies `cost_delta_pct = None` on zero prior cost
- `test_user_spend_detail` — verifies user profile endpoint returns correct summary + models

**Total analytics tests: 16 (13 existing + 3 new)**

**Definition of done:** ✅ Dashboard loads with summary cards (including period delta), spend charts, and top-spenders table. Clicking a user navigates to their spend profile. All 16 analytics tests pass.

---

### Phase 7 — Weeks 15–16: Budgets + Spend Guardrails ✅
**Roadmap areas:** 10 (Budget Guardrails), 11 (Runaway Protection)

**Goal:** Set a budget for an end-user. Run a chatbot that exceeds it. The next call is blocked — automatically, no code change.

**What was built:**

Database migration (`apps/api/alembic/versions/004_budgets.py`):
- `budgets` — `(id, workspace_id, scope_type, scope_id, period_type, limit_usd, action, downgrade_to_model, is_active, created_at)` + `ix_budgets_workspace` on `(workspace_id, is_active)`
- `budget_breaches` — `(id, budget_id, occurred_at, spend_at_breach_usd, action_taken, notified_at)` + `ix_budget_breaches_budget` on `(budget_id, occurred_at)`
- `budget_notifications` — `(id, workspace_id, channel, destination_url, events TEXT[], is_active, created_at)` + `ix_budget_notifications_workspace`

ORM models (`apps/api/runledger_api/models/budgets.py`):
- `Budget`, `BudgetBreach`, `BudgetNotification` with `ScopeTypeEnum`, `PeriodTypeEnum`, `ActionEnum`, `ChannelEnum`

Pydantic schemas (`apps/api/runledger_api/schemas/budgets.py`):
- `BudgetCreate`, `BudgetResponse` (includes `current_spend_usd` + `pct_used` from Redis)
- `BudgetCheckResponse` — `{allowed, action, budget_id, downgrade_model}`
- `BreachResponse`, `NotificationCreate`, `NotificationResponse`

Service layer (`apps/api/runledger_api/services/budgets.py`):
- `_period_key(period_type, dt)` — formats `"2026-02-27"` / `"2026-02"` / `"total"`
- `incr_budget_spend(redis, budget_id, period_type, cost_usd)` — `INCRBYFLOAT` + TTL
- `get_budget_spend(redis, budget_id, period_type)` → `Decimal`
- `get_workspace_budgets_cached(redis, db, workspace_id)` — Redis JSON cache (TTL 300s), Postgres fallback
- `invalidate_workspace_budgets_cache(redis, workspace_id)` — called on create/delete
- `_matching_budgets(budgets, end_user_id, feature_tag)` — scope matching (workspace always matches; end_user/feature_tag check scope_id)
- `check_budgets(redis, db, workspace_id, end_user_id, feature_tag)` → `BudgetCheckResponse` — hot path, Redis only
- `fire_breach(db, redis, budget_dict, spend, action_taken)` — writes `BudgetBreach`, fetches notifications, calls `send_notification()`
- `send_notification(notification, payload)` — HTTP POST with `X-RunLedger-Signature: sha256=<hmac>` header

Router (`apps/api/runledger_api/routers/budgets.py`), prefix `/budgets`:
- `POST /budgets` → 201 with `BudgetResponse`; invalidates workspace cache
- `GET /budgets` — list with live Redis spend + `pct_used`
- `GET /budgets/check` — hot-path, Redis only, target <5ms p99
- `GET /budgets/{id}/breaches` — breach history (most recent first)
- `DELETE /budgets/{id}` → 204, soft-deletes (is_active=False), invalidates cache
- `POST /budgets/notifications` → 201; `GET /budgets/notifications`

Celery workers (`apps/api/runledger_api/workers/budgets.py`):
- `runaway_protection` (every 5 min): queries `agent_runs` with `status='running'` for ≥2 min; detects retry storm (>20 calls in last 2 min) or token spike (>100k input tokens); cancels run, fires `runaway.detected` notifications
- `budget_spend_sync` (every 24h): re-computes spend from `provider_calls` and writes back to Redis — recovery from Redis eviction

Metering worker update (`apps/api/runledger_api/workers/metering.py`):
- After each `cost_usd` is computed, calls `incr_budget_spend` for every matching budget
- If spend ≥ limit and action ≠ `notify`: calls `fire_breach()`

Celery app update (`apps/api/runledger_api/core/celery_app.py`):
- Added `"runledger_api.workers.budgets"` to `include`
- Added `runaway-protection-5m` (300s) and `budget-spend-sync-daily` (86400s) to Beat schedule

Main app update (`apps/api/runledger_api/main.py`):
- `app.include_router(budgets.router)`

SDK — exceptions (`packages/sdk/runledger_sdk/exceptions.py`):
- `RunLedgerBudgetExceededError(budget_id, message)` — raised on `action=block`

SDK — client (`packages/sdk/runledger_sdk/client.py`):
- `budget_check: bool = False` parameter on `RunLedger.__init__`; stored and forwarded to `SyncTransport`

SDK — transport (`packages/sdk/runledger_sdk/transport.py`):
- `SyncTransport.budget_check` attribute passed through from client

SDK — OpenAI wrapper (`packages/sdk/runledger_sdk/openai.py`):
- `_sync_budget_check(transport, ctx, kwargs)` called before both sync and async OpenAI create; raises `RunLedgerBudgetExceededError` on block; mutates `kwargs['model']` on downgrade; fails open on any network/timeout error

SDK — `__init__.py`:
- Exports `RunLedgerBudgetExceededError`; bumped to v0.4.0

Frontend (`apps/web/`):
- `types/api.ts` — `Budget`, `BudgetList`, `BudgetCheckResponse`, `Breach`, `BreachList` interfaces
- `lib/api.ts` — `getBudgets`, `createBudget`, `deleteBudget`, `getBudgetBreaches`
- `components/layout/Sidebar.tsx` — `ShieldAlert` Budgets nav item
- `components/budgets/BudgetList.tsx` — table with spend progress bar (green/yellow/red), action badge, delete button
- `components/budgets/CreateBudgetModal.tsx` — modal: scope type/id, period, limit, action, downgrade model
- `components/budgets/BreachHistoryTable.tsx` — occurred_at, spend, action taken, notified_at
- `app/(dashboard)/budgets/page.tsx` — client page with live budget list + "New Budget" modal trigger
- `app/(dashboard)/budgets/[id]/page.tsx` — server page with breach history

Example (`examples/08_budget_enforcement.py`):
- Creates a daily budget via API, runs LLM calls until blocked, catches `RunLedgerBudgetExceededError`

Tests (`apps/api/tests/test_budgets.py`) — **19 tests:**
- `test_period_key_daily`, `test_period_key_monthly`, `test_period_key_total`
- `test_matching_budgets_workspace_scope`, `test_matching_budgets_end_user_scope`, `test_matching_budgets_feature_tag_scope`
- `test_incr_budget_spend`, `test_get_budget_spend_returns_zero_when_missing`, `test_get_budget_spend_returns_value`
- `test_create_budget`, `test_list_budgets_includes_spend`
- `test_budget_check_allowed`, `test_budget_check_blocked`, `test_budget_check_downgrade`
- `test_delete_budget_deactivates`, `test_breach_history_empty`
- `test_runaway_protection_retry_storm`, `test_send_notification_webhook`, `test_budgets_requires_auth`

**Definition of done:** ✅ Create a daily $0.10 budget for a test user. Run 5 LLM calls that exceed it. The 6th call is blocked. A webhook fires with the breach payload. The breach shows up in the UI.

---

### Phase 8 — Weeks 17–18: Chargeback Engine + Reconciliation + Dispute Trail
**Roadmap areas:** 12 (Chargeback + Billing Periods)

**Goal:** Close the month, generate a usage statement, and drill from any line item back to the exact run that caused it.

**Period close workflow:**
- `POST /billing/periods/{id}/close` → background job:
  1. Freeze: snapshot `usage_daily` totals for the period into `usage_snapshots.snapshot_data`
  2. Apply chargeback rules: distribute cost across allocation dimensions
  3. Compute HMAC-SHA256 signature of snapshot JSON → store in `usage_snapshots.signature`
  4. Set `billing_periods.status = 'closed'`, record `closed_at`
  5. Generate `usage_statement` JSON artifact (downloadable)
- Late events: events arriving after period close are flagged in `agent_runs.late_event = true` — reconciliation report flags them

**Chargeback rules engine:**
- Simple allocation: split workspace cost by dimension (env: prod gets 90% / dev 10%, or by explicit cost_center tags)
- `chargeback_rules` support weight-based splits and explicit dimension assignments

**Reconciliation:**
- Internal consistency check (scheduled, runs nightly):
  - Sum of `provider_calls.cost_usd` = sum via `usage_daily` for same period (within 0.01% tolerance)
  - Flag any orphaned `provider_calls` (no parent `agent_run`)
  - Flag duplicate `provider_calls` (same `run_id` + same `model` + same timestamp within 1s)
- Report: `GET /billing/periods/{id}/reconciliation` → consistency status, flagged issues

**Dispute trail:**
- `GET /billing/periods/{id}/breakdown` → hierarchical JSON:
  ```
  period total
  └─ by application
     └─ by end_user_id
        └─ by model
           └─ agent_runs (sorted by cost desc)
              └─ spans + provider_calls
  ```
- `GET /billing/periods/{id}/export?format=csv` → CSV with columns: date, end_user_id, model, input_tokens, output_tokens, cost_usd, run_id
- `GET /billing/periods/{id}/export?format=signed_json` → JSON bundle + HMAC signature (verifiable offline)

**UI — `/billing`:**
- Billing periods list: period dates, total cost, status badge, actions (close, export)
- `/billing/[period_id]`: summary cards, chargeback breakdown table, reconciliation status panel
- Drill-down: click a row in breakdown → filters down to that dimension → click a run_id → navigates to `/runs/[run_id]`
- Evidence export button: downloads CSV + signed JSON

**Definition of done:** Close a billing period. Export the signed JSON. Verify the HMAC offline with the known signing key. Click a line item in the breakdown and arrive at the exact run in the run explorer.

---

### Phase 9 — Weeks 19–20: Unit Economics Graph + Change Impact
**Roadmap areas:** 13 (Unit Economics + Change Impact)

**Goal:** Ship a new prompt version, tag it in the SDK, and see a side-by-side cost breakdown vs the previous version.

**Cost attribution:**
- `GET /analytics/economics/{run_id}` → cost profile:
  - cost_by_span_type: `{llm: $0.032, tool: $0.001, retrieval: $0.005}`
  - cost_by_model: `{gpt-4o: $0.030, gpt-4o-mini: $0.002}`
  - retry_cost: cost of all re-runs within the run
  - human_approval_cost: spans of type APPROVAL
- Top N workflows: `GET /analytics/workflows/top?metric=cost&limit=10&from=&to=`
  - Groups by `feature_tag` + `application_id`, returns avg cost, p95 cost, call volume

**Deployment versioning:**
- SDK context gains `deployment_version` field: `rl.context(deployment_version="v2.1.0")`
- Stored in `agent_runs.deployment_version`

**Change impact:**
- `GET /analytics/compare?baseline_version=v2.0.0&comparison_version=v2.1.0&from=&to=`
  - Returns: cost delta (%), token delta (%), latency delta (%), run count for each
  - Breakdown by span type: which node type drove the change
- `GET /analytics/regressions?from=&to=` → workflows where cost > 120% of same-period prior week average
- `POST /analytics/annotations` → team can attach notes to a date/version ("rolled back gpt-4o, switched to gpt-4o-mini")

**UI — `/analytics/economics`:**
- `EconomicsBreakdown` component: stacked bar per run_id or feature_tag, split by LLM/tool/retrieval/retry
- `ChangeImpactPanel`: version selector (baseline vs comparison), side-by-side delta cards
- `RegressionTable`: workflows with cost regression flag, % increase, volume context
- Annotations: inline markers on the spend timeline

**Definition of done:** Tag 50 runs with `deployment_version=v1` and 50 with `v2`. The compare endpoint returns correct per-node-type cost deltas.

---

### Phase 10 — Weeks 21–22: End-user Analytics + Replay Harness
**Roadmap areas:** 14 (End-user Analytics + Replay Harness)

**Goal:** Identify your top spenders and anomalous users. Run the same 20 agent tasks against two models and compare cost + outcome.

**End-user analytics (deepening Phase 6):**
- `GET /analytics/users/{id}` now includes:
  - Cost trend (30d), models used, feature tags used, run count, avg cost/run
  - Cohort: which spend tier (P0: <$1/mo, P1: $1-10, P2: $10-100, P3: $100+)
- Cohort analysis: `GET /analytics/users/cohorts` → retention vs cost by first-seen week
- Anomaly detection (Z-score, computed by nightly Celery job):
  - For each active end_user, compute Z-score of today's spend vs their 30d mean
  - Flag users with Z > 3 (configurable) in `user_anomalies` table
  - `GET /analytics/users/anomalies` → flagged users with anomaly reason

**UI — `/analytics/users`:**
- Segmentation tabs: All / Heavy users (P3) / Anomalous / New this week
- User rows include cohort badge and anomaly flag icon

**Replay harness:**
- `replay_datasets` table: `(id, workspace_id, name, source ENUM[live_runs|synthetic], run_ids[], created_at)`
- `POST /replay/datasets` → save a set of run_ids as a dataset (captures input metadata, respects privacy mode)
- `replay_experiments` table: `(id, dataset_id, name, configs JSONB[{model, prompt_version, routing_policy}], status, created_at)`
- `POST /replay/experiments` → define experiment: dataset + list of configs to compare
- Celery `run_experiment_worker`: for each config, re-run each dataset item via the SDK (fires real LLM calls — note this incurs cost)
- `GET /replay/experiments/{id}/results` →
  - Per config: avg cost, p50/p95 latency, outcome labels (success/fail from outcome_events)
  - Delta table: config A vs config B — cost delta, latency delta, success rate delta
- **Safety check**: experiment must be explicitly confirmed before firing (cost estimate shown first)

**UI — `/replay`:**
- Dataset list + create dataset modal (pick runs from Run Explorer)
- Experiment list + create experiment wizard: pick dataset → pick configs (model A / model B)
- `/replay/[experiment_id]`: side-by-side results table, cost delta chart, latency percentile comparison

**Definition of done:** Create a dataset of 10 runs. Define an experiment comparing gpt-4o vs gpt-4o-mini. Run it. See the cost delta and latency comparison in the UI.

---

### Phase 11 — Weeks 23–24: Tamper-evident Ledger + Production Polish + OSS Launch
**Roadmap areas:** 15 (Tamper-evident Ledger + OSS Launch)

**Goal:** Ship a production-grade release. Docker image on Docker Hub. SDK on PyPI. Comprehensive docs.

**Tamper-evident ledger:**
- Nightly Celery job (`ledger_snapshot_worker`): for each workspace, compute daily summary (total cost, run count, model breakdown), sign with HMAC-SHA256 using `ledger_keys.key_hash`, store in `ledger_snapshots`
- Key rotation: new key created monthly, old keys retained for verification
- `GET /ledger/snapshots?from=&to=` → list of daily signed snapshots
- `GET /ledger/snapshots/{date}/verify` → re-compute hash and verify against stored signature
- `GET /ledger/export/{billing_period_id}` → evidence pack: ZIP containing `totals.json` + `run_index.json` + `integrity.json` (all hashes + signing key fingerprint)

**Security boundaries (basic):**
- `tool_registry` table: `(tool_name, workspace_id, risk_level ENUM[read|write|privileged], risk_score 0-10)`
- SDK: `rl.register_tool(name, risk_level)` — sends tool metadata on first call
- `GET /tools` → list registered tools with risk levels
- Policy: log + flag privileged tool calls in `tool_calls.flagged = true`
- Suspicious sequence detection (Celery): same tool called >5 times in <60s → flag in `security_events`

**Privacy governance:**
- `capture_policies` table operationalized: Celery pipeline reads policy for workspace before capturing span metadata
- `POST /privacy/policies` → create policy (scope: env/tool, mode, sample_rate, redaction_rules)
- Payload access workflow: `POST /privacy/access-requests/{span_id}` → creates access request, logs to `payload_access_log` on approval

**Production hardening:**
- Prometheus metrics endpoint (`/metrics`): request latency, event queue depth, worker lag, active budget checks/sec
- Sentry integration: `SENTRY_DSN` env var, captures unhandled exceptions in API + workers
- Connection pooling: asyncpg pool (min 2, max 20), Redis connection pool
- DB query timeouts: 5s default on all queries
- Rate limiting: per API key (100 req/s default, configurable per workspace)
- Health check deepened: `GET /health` checks Celery worker heartbeat + queue depth

**OSS / paid feature gating:**
- `FeatureGate` middleware: reads `workspace.plan`, gates paid features (multi-tenancy, enforcement, ledger, replay)
- `RUNLEDGER_MODE=oss` env var: disables all paid gates for self-hosted OSS users

**Docker release:**
- Multi-stage `Dockerfile` for `apps/api`: builder stage (uv install) + runtime stage (slim Python)
- Single-container mode: API + Celery worker in one container via `supervisord` (OSS tier default)
- Split-container mode: separate `api` and `worker` services (paid/production)
- `docker-compose.yml` for full stack (Postgres + Redis + api + worker + web)
- Docker image published to Docker Hub: `runledger/runledger:0.1.0`

**SDK PyPI release:**
- `runledger-sdk` 0.1.0 on PyPI
- CI job: publish on git tag push
- SDK README with full quickstart, all integrations, privacy mode docs

**Documentation (`docs/`):**
- `quickstart.md`: from zero to first run in 5 minutes
- `sdk-reference.md`: all SDK classes, methods, context vars
- `deployment.md`: Docker Compose, Railway, Render, Fly.io guides
- `data-model.md`: event schema reference
- `privacy.md`: privacy modes + redaction guide

**Definition of done:** A new user follows `quickstart.md` and has their first instrumented run visible in a self-hosted RunLedger instance in under 10 minutes. The signed daily ledger snapshot for the previous day is verifiable offline.

---

## Testing Strategy

### Unit tests (pytest)
- Pricing engine: cost calculation correctness, effective-date lookups, cached token discounts
- Budget enforcement: Redis counter logic, action resolution
- Chargeback allocation: weight-based splits, edge cases (zero cost, missing dimension)
- HMAC signing: signature generation + verification, key rotation
- SDK: OpenAI wrapper captures correct metadata; context vars propagate correctly

### Integration tests (pytest + testcontainers)
- Ingestion pipeline: event → Redis → Celery worker → Postgres (round-trip test)
- Rollup jobs: idempotency (run twice → same result)
- Budget check: hot path latency assertion (<10ms in test environment)
- API auth: correct 401/403 for missing/wrong/expired API keys

### E2E tests (Playwright)
- Run Explorer: search for a run, click through to DAG, verify node count
- Budget guardrail: create budget → exceed it via API calls → verify block response
- Billing: close a period → verify snapshot is downloadable and signature verifies

### Load test (Locust, run before each phase milestone)
- Ingestion API: 1000 events/sec sustained for 60s — measure p99 latency
- Budget check endpoint: 500 req/sec — measure p99 latency (target: <10ms)
- Analytics queries: 50 concurrent dashboard users — measure p95 page load time

---

## Deployment Architecture (Railway)

```
Railway Project: runledger-prod
├── Service: api          (Docker image, replicas: 1-3 auto-scale)
├── Service: worker       (Docker image, Celery worker, replicas: 1-2)
├── Service: web          (Docker image or Next.js static, replicas: 1)
├── Plugin: PostgreSQL    (Railway managed Postgres 16)
└── Plugin: Redis         (Railway managed Redis 7)
```

**Environment variables (Railway):**
```
DATABASE_URL         = postgresql+asyncpg://...
REDIS_URL            = redis://...
SECRET_KEY           = (random 32 bytes, hex)
ENVIRONMENT          = production
RUNLEDGER_MODE       = paid   # or "oss" for self-hosted
SENTRY_DSN           = (optional)
NEXT_PUBLIC_API_URL  = https://api.runledger.io
```

**Staging environment:** Identical Railway project with `ENVIRONMENT=staging`, separate Postgres + Redis plugins, seeded with synthetic data.
