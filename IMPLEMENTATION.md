# RunLedger — Implementation Roadmap

6-month plan for a solo founder building a production-grade Agent FinOps Control Plane.

---

## Guiding Principles

- **Async instrumentation first** — lowest friction. Optional inline gateway later.
- **Billing-grade correctness over pretty dashboards** — accuracy is the product.
- **Privacy-first by default** — payload logging is always opt-in, never default.
- **End-user analytics is first-class** — not an afterthought on a per-tenant view.
- **Auditability built into the architecture** — tamper-evidence, provenance, and policies from day one, even if compliance features ship later.

---

## Phase Status

| Phase | Title | Status | Tests |
|-------|-------|--------|-------|
| 0 | Monorepo + Infrastructure Foundation | ✅ Complete | 3 |
| 1 | Ingestion API + Multi-tenancy + Auth | ✅ Complete | 17 |
| 2 | SDK — OpenAI Wrapper + Context Propagation | ✅ Complete | 28 |
| 3 | SDK — LangChain + LangGraph + CLI | ✅ Complete | 33 |
| 4 | Billing-grade Metering Core | ✅ Complete | 22 |
| 5 | Run Explorer + DAG Viewer UI | ✅ Complete | — |
| 6 | Metering Dashboard | ✅ Complete | +3 |
| 7 | Budgets + Spend Guardrails | ✅ Complete | 19 |
| 8 | Chargeback Engine + Reconciliation | ✅ Complete | 15 |
| 9 | Unit Economics Graph + Change Impact | ✅ Complete | 12 |
| 10 | End-user Analytics + Replay Harness | ✅ Complete | 15 |
| 11 | Tamper-evident Ledger + Security + Privacy | ✅ Complete | 15 |
| 12 | Settings Console + Dark Mode + Provider Profiles | ✅ Complete | 13 |
| 14 | Integrations: Slack Alerts + GitHub CI Gate | ✅ Complete | 8 |
| 15 | Anthropic SDK | 🔲 Planned | — |
| 16 | Production Hardening + UI Polish | ✅ Complete | 13 |
| 17 | Evaluations & Scores | ✅ Complete | 13 |
| 18 | Prompt Management | ✅ Complete | 12 |
| 19 | Sessions UI + Payload Viewer | ✅ Complete | 8 |
| 20 | TypeScript / Node.js SDK | 🔲 Planned | — |
| 21A | Advanced Alerting | ✅ Complete | 9 |
| 21B | Model Gateway | ✅ Complete | 14 |
| 21C | Runs enhancements — model/cost filters · CSV export · Ollama cost fix · API key UX | ✅ Complete | — |
| 21D | Unified policy checks — budgets + tools + gateway + eval gate | ✅ Complete | 6 |
| 22 | SaaS Foundation | 🔲 Planned | — |

**Total tests shipped (Phases 0–21D):** 233 API tests + 61 SDK tests

**Audit snapshot (2026-03-15):**
- API suite: `233/233` passing
- SDK suite: `61/61` passing
- Web lint: clean (`next lint`)
- Repo lint: clean (`ruff check .`)
- Core API typing: clean (`mypy apps/api/runledger_api`)
- Web UI polish: refined dashboard shell + login experience; lint remains clean

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
├── runledger-samples/          # Runnable example agents (separate repo)
│   ├── 01_openai_basic.py
│   ├── 02_openai_multi_turn.py
│   ├── 03_langchain_chain.py
│   ├── 04_langgraph_agent.py
│   ├── 05_fastapi_service.py
│   ├── 06_ollama_local.py / 06_ollama_local.ipynb
│   ├── 07_analytics_query.py
│   ├── 08_budget_enforcement.py
│   ├── 09_economics_query.py
│   ├── 10_replay_experiment.py
│   ├── 11_ledger_verify.py
│   ├── 12_settings.py
│   ├── 13_integrations.py
│   ├── 14_evaluations.py
│   ├── 15_prompts.py
│   ├── .env.example            # All env vars documented
│   └── README.md
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

### Annotations (Phase 9)

```sql
annotations      (id UUID, workspace_id UUID FK workspaces.id,
                  note TEXT NOT NULL, annotation_date DATE NOT NULL,
                  version TEXT NULL,   -- deployment_version anchor (optional)
                  created_at TIMESTAMPTZ)
                  -- INDEX ix_annotations_workspace_date on (workspace_id, annotation_date)
```

### Replay (Phase 10)

```sql
user_anomalies   (id UUID, workspace_id UUID FK workspaces.id,
                  end_user_id TEXT, detected_at DATE,
                  daily_spend NUMERIC, mean_spend NUMERIC, zscore NUMERIC,
                  reason TEXT, created_at TIMESTAMPTZ)
                  -- INDEX ix_user_anomalies_workspace_date on (workspace_id, detected_at)

replay_datasets  (id UUID, workspace_id UUID FK workspaces.id,
                  name TEXT, source TEXT, run_ids JSONB, created_at TIMESTAMPTZ)
                  -- INDEX ix_replay_datasets_workspace on (workspace_id, created_at)

replay_experiments (id UUID, workspace_id UUID FK workspaces.id,
                    dataset_id UUID FK replay_datasets.id,
                    name TEXT, configs JSONB, status TEXT,
                    results JSONB NULL, estimated_cost_usd NUMERIC NULL,
                    created_at TIMESTAMPTZ)
                    -- INDEX ix_replay_experiments_workspace on (workspace_id, created_at)
```

### Ledger & Security & Privacy (Phase 11)

```sql
ledger_keys      (id UUID PK, workspace_id UUID FK workspaces.id,
                  key_value TEXT NOT NULL,   -- 32-byte hex, never returned in API
                  active BOOL DEFAULT TRUE,
                  expires_at TIMESTAMPTZ NOT NULL,  -- 30-day TTL
                  created_at TIMESTAMPTZ)
                  -- INDEX ix_ledger_keys_workspace on (workspace_id, active, expires_at)

ledger_snapshots (id UUID PK, workspace_id UUID FK workspaces.id,
                  snapshot_date DATE NOT NULL,
                  total_cost_usd NUMERIC(14,8),
                  model_breakdown JSONB DEFAULT '{}',
                  call_count INT DEFAULT 0,
                  hash TEXT NOT NULL,        -- HMAC-SHA256 hex
                  key_id UUID FK ledger_keys.id,
                  created_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_ledger_snapshots_workspace_date on (workspace_id, snapshot_date)

tool_registry    (id UUID PK, workspace_id UUID FK workspaces.id,
                  tool_name TEXT NOT NULL,
                  policy TEXT DEFAULT 'audit',  -- 'allow' | 'audit' | 'block'
                  description TEXT NULL,
                  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_tool_registry_workspace_name on (workspace_id, tool_name)

security_events  (id UUID PK, workspace_id UUID FK workspaces.id,
                  event_type TEXT NOT NULL,   -- 'suspicious_sequence' | 'policy_violation'
                  tool_name TEXT NULL, end_user_id TEXT NULL, run_id UUID NULL,
                  details JSONB DEFAULT '{}',
                  detected_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ)
                  -- INDEX ix_security_events_workspace_detected on (workspace_id, detected_at)

capture_policies (id UUID PK, workspace_id UUID FK workspaces.id UNIQUE,
                  privacy_mode TEXT DEFAULT 'METADATA_ONLY',
                  sampled_rate NUMERIC(5,4) NULL,
                  updated_at TIMESTAMPTZ, created_at TIMESTAMPTZ)
```

### Evaluations & Scores (Phase 17)

```sql
score_events     (id UUID PK, workspace_id UUID NOT NULL,
                  run_id UUID NULL,             -- soft reference; no FK (scores outlive runs for audit)
                  span_id UUID NULL,
                  session_id TEXT NULL,
                  end_user_id TEXT NULL,
                  name TEXT NOT NULL,           -- e.g. "relevance", "accuracy", "helpfulness"
                  value NUMERIC(8,4) NOT NULL,  -- 0–100 scale
                  label TEXT NULL,              -- "good" | "bad" | "pass" | "fail" | ...
                  source TEXT DEFAULT 'human',  -- 'human' | 'llm' | 'rule' | 'telemetry'
                  confidence NUMERIC(4,3) NULL, -- 0–1
                  evidence JSONB NULL,
                  created_at TIMESTAMPTZ)
                  -- INDEX ix_score_events_workspace on (workspace_id, created_at)
                  -- INDEX ix_score_events_run on (run_id)
                  -- INDEX ix_score_events_name on (workspace_id, name)

score_rollups_daily (workspace_id UUID NOT NULL, day DATE NOT NULL,
                  score_name TEXT NOT NULL, feature_tag TEXT NOT NULL DEFAULT '',
                  model TEXT NOT NULL DEFAULT '', deployment_version TEXT NOT NULL DEFAULT '',
                  avg_value NUMERIC(8,4) NOT NULL,
                  p50 NUMERIC(8,4) NOT NULL, p90 NUMERIC(8,4) NOT NULL,
                  sample_count INT NOT NULL)
                  -- PRIMARY KEY (workspace_id, day, score_name, feature_tag, model, deployment_version)
                  -- Populated nightly by score_rollup.run Celery task (idempotent DELETE + INSERT)
```

Note: V1 ships without the `evaluators` table (LLM-as-judge framework deferred to Phase 17B). The `evaluators` table remains in the schema plan for Phase 17B.

### Prompt Management (Phase 18)

```sql
prompts          (id UUID PK, workspace_id UUID FK workspaces.id,
                  name TEXT NOT NULL,           -- slug-style unique name, e.g. "support-agent-v2"
                  description TEXT NULL,
                  default_environment TEXT DEFAULT 'production',  -- 'production' | 'staging' | 'dev'
                  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_prompts_workspace_name on (workspace_id, name)

prompt_versions  (id UUID PK, prompt_id UUID FK prompts.id,
                  version INT NOT NULL,         -- auto-increment per prompt
                  content TEXT NOT NULL,        -- template with {{variable}} placeholders
                  variables JSONB DEFAULT '[]', -- [{name, type, description}]
                  commit_message TEXT NULL,
                  environment TEXT NOT NULL DEFAULT 'production',
                  model_hint TEXT NULL,         -- suggested model for this version
                  created_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_prompt_versions_prompt_version on (prompt_id, version)
                  -- INDEX ix_prompt_versions_prompt_env on (prompt_id, environment)
```

### Sessions (Phase 19 — no new tables)

```sql
-- session_id already exists on agent_runs.
-- Sessions are virtual aggregations — a GROUP BY session_id query.
-- No new table needed. New index:
-- INDEX ix_agent_runs_workspace_session on (workspace_id, session_id, started_at)
-- where session_id IS NOT NULL
```

### Model Gateway (Phase 21)

```sql
gateway_routes   (id UUID PK, workspace_id UUID FK workspaces.id,
                  name TEXT NOT NULL,
                  provider TEXT NOT NULL,           -- 'openai' | 'anthropic' | 'google' | 'cohere'
                  model TEXT NOT NULL,
                  fallback_model TEXT NULL,
                  priority INT DEFAULT 0,           -- lower = try first
                  weight NUMERIC(4,3) DEFAULT 1.0,  -- for load-balanced routes
                  is_active BOOL DEFAULT TRUE,
                  created_at TIMESTAMPTZ)

gateway_requests (id UUID PK, workspace_id UUID FK workspaces.id,
                  route_id UUID FK gateway_routes.id NULL,
                  run_id UUID FK agent_runs.id NULL,
                  provider TEXT, model TEXT,
                  fallback_used BOOL DEFAULT FALSE,
                  cache_hit BOOL DEFAULT FALSE,
                  latency_ms INT, cost_usd NUMERIC(14,8),
                  status TEXT, created_at TIMESTAMPTZ)
                  -- PARTITIONED BY RANGE (created_at) — monthly partitions

prompt_cache     (id UUID PK, workspace_id UUID FK workspaces.id,
                  cache_key TEXT NOT NULL,   -- sha256 of (model + normalized_prompt)
                  response JSONB NOT NULL,
                  input_tokens INT, output_tokens INT,
                  model TEXT, provider TEXT,
                  hit_count INT DEFAULT 0,
                  expires_at TIMESTAMPTZ NOT NULL,
                  created_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_prompt_cache_workspace_key on (workspace_id, cache_key)
```

### SaaS Foundation (Phase 22)

```sql
plans            (id UUID PK, name TEXT UNIQUE,   -- 'free' | 'starter' | 'growth' | 'enterprise'
                  monthly_price_usd NUMERIC(8,2),
                  event_quota_monthly BIGINT,       -- max events/month; NULL = unlimited
                  seat_quota INT,                   -- max workspace users
                  features JSONB DEFAULT '{}',      -- feature flags per plan
                  created_at TIMESTAMPTZ)

subscriptions    (id UUID PK, tenant_id UUID FK tenants.id,
                  plan_id UUID FK plans.id,
                  stripe_subscription_id TEXT NULL,
                  stripe_customer_id TEXT NULL,
                  status TEXT DEFAULT 'active',     -- 'active' | 'past_due' | 'cancelled'
                  current_period_start DATE,
                  current_period_end DATE,
                  cancel_at DATE NULL,
                  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_subscriptions_tenant on (tenant_id)

usage_quotas     (id UUID PK, workspace_id UUID FK workspaces.id,
                  period_start DATE, period_end DATE,
                  events_used BIGINT DEFAULT 0,
                  seats_used INT DEFAULT 0,
                  updated_at TIMESTAMPTZ)
                  -- UNIQUE INDEX ix_usage_quotas_workspace_period on (workspace_id, period_start)
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

- `packages/sdk/runledger_sdk/client.py` — `RunLedger(api_key, base_url, privacy_mode, local, budget_check)` client; `instrument()` monkey-patches `openai.OpenAI` and `openai.AsyncOpenAI`; `context()` context manager; `shutdown()` / `flush()` / `aflush()`; all constructor params fall back to env vars (`RUNLEDGER_API_KEY`, `RUNLEDGER_BASE_URL`, `RUNLEDGER_LOCAL`)
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

### Phase 8 — Weeks 17–18: Chargeback Engine + Reconciliation + Dispute Trail ✅
**Roadmap areas:** 12 (Chargeback + Billing Periods)

**Goal:** Close the month, generate a usage statement, and drill from any line item back to the exact run that caused it.

**What was built:**

Database migration (`apps/api/alembic/versions/005_billing.py`):
- `billing_periods` — `(id, workspace_id, period_start, period_end, status, total_cost_usd, snapshot_hash, closed_at)` + two indexes (status, dates)
- `chargeback_rules` — `(id, workspace_id, allocation_type, dimension, weight NUMERIC(6,4))`
- `usage_snapshots` — `(id, billing_period_id, snapshot_data JSONB, signature TEXT, signing_key_id, created_at)`

ORM models (`apps/api/runledger_api/models/billing.py`):
- `BillingPeriod`, `ChargebackRule`, `UsageSnapshot`

Pydantic schemas (`apps/api/runledger_api/schemas/billing.py`):
- `BillingPeriodCreate`, `BillingPeriodResponse`, `ChargebackRuleCreate`, `ChargebackRuleResponse`
- `UsageSnapshotResponse`, `ReconciliationResult`, `PeriodBreakdown`, `BreakdownApp`, `BreakdownUser`

Service layer (`apps/api/runledger_api/services/billing.py`):
- `sign_snapshot(data, key)` — `json.dumps(sort_keys=True, default=str)` → `hmac.new(sha256).hexdigest()`
- `close_billing_period(db, period_id)` — status='closing' → compute total from `SUM(provider_calls.cost_usd)` → build snapshot_data → sign → create UsageSnapshot → set status='closed' + `snapshot_hash=sig[:16]`
- `run_reconciliation(db, period_id)` → `ReconciliationResult` — compares `SUM(provider_calls.cost_usd)` vs `SUM(usage_daily.cost_usd)` for date range; flags orphaned + duplicate calls
- `apply_chargeback_rules(db, period_id)` → `dict[dimension, cost]` — weight-based allocation from `chargeback_rules` table
- `export_csv(db, period_id)` → CSV string
- `export_signed_json(db, period_id, signing_key)` → signed JSON dict

Router (`apps/api/runledger_api/routers/billing.py`), prefix `/billing`:
- `POST /billing/periods` → 201 with `BillingPeriodResponse`
- `GET /billing/periods` — list workspace periods
- `GET /billing/periods/{id}` — single period
- `POST /billing/periods/{id}/close` → `UsageSnapshotResponse`; 409 if already closed
- `GET /billing/periods/{id}/reconciliation` → `ReconciliationResult`
- `GET /billing/periods/{id}/breakdown` → `PeriodBreakdown`
- `GET /billing/periods/{id}/export?format=csv|signed_json` → CSV (`text/csv`) or JSON
- `POST /billing/chargeback-rules` → 201; `GET /billing/chargeback-rules`

Celery worker (`apps/api/runledger_api/workers/billing.py`):
- `nightly_reconciliation` — processes all closed periods nightly, logs any reconciliation failures

Main app (`apps/api/runledger_api/main.py`):
- `app.include_router(billing.router)`

Frontend (`apps/web/`):
- `types/api.ts` — `BillingPeriod`, `BillingPeriodList`, `ChargebackRule`, `ReconciliationResult`, `PeriodBreakdown`, `UsageSnapshot`
- `lib/api.ts` — `getBillingPeriods`, `createBillingPeriod`, `closeBillingPeriod`, `getReconciliation`, `getPeriodBreakdown`, `exportPeriodCsv`, `exportPeriodSignedJson`
- `components/layout/Sidebar.tsx` — `Receipt` Billing nav item
- `components/billing/` — `BillingPeriodList`, `ClosePeriodButton`, `ReconciliationPanel`, `BreakdownTable`, `ExportButton`
- `app/(dashboard)/billing/page.tsx` — periods list with status badges, close/export controls
- `app/(dashboard)/billing/[period_id]/page.tsx` — detail: summary cards, chargeback breakdown, reconciliation panel

Example (`examples/08_budget_enforcement.py` was Phase 7; billing has no standalone example — use the dashboard or Swagger UI)

Tests (`apps/api/tests/test_billing.py`) — **15 tests:**
- `test_sign_snapshot`, `test_export_signed_json_verifiable`
- `test_create_billing_period`, `test_list_billing_periods`, `test_get_billing_period`
- `test_close_billing_period`, `test_close_already_closed_409`
- `test_reconciliation_pass`, `test_reconciliation_fail_delta`, `test_reconciliation_orphaned`
- `test_export_csv_columns`, `test_create_chargeback_rule`
- `test_apply_chargeback_rules`, `test_nightly_reconciliation_worker`
- `test_billing_requires_auth`

**Definition of done:** ✅ Close a billing period. Export the signed JSON. Verify the HMAC offline with the known signing key. Click a line item in the breakdown and arrive at the exact run in the run explorer.

---

### Phase 9 — Weeks 19–20: Unit Economics Graph + Change Impact ✅
**Roadmap areas:** 13 (Unit Economics + Change Impact)

**Goal:** Ship a new prompt version, tag it in the SDK, and see a side-by-side cost breakdown vs the previous version.

**What was built:**

Database migration (`apps/api/alembic/versions/006_annotations.py`):
- `annotations` — `(id UUID, workspace_id UUID FK workspaces.id NOT NULL, note TEXT, annotation_date DATE, version TEXT NULL, created_at TIMESTAMPTZ)` + `ix_annotations_workspace_date`

ORM model (`apps/api/runledger_api/models/annotations.py`):
- `Annotation` — mapped columns matching migration; registered in `models/__init__.py`

Pydantic schemas (`apps/api/runledger_api/schemas/economics.py`):
- `SpanTypeCost`, `ModelCost`, `RunEconomics`
- `WorkflowSummary`, `WorkflowTopList`
- `SpanTypeDelta`, `VersionSummary`, `VersionCompareResult`
- `RegressionItem`, `RegressionList`
- `AnnotationCreate`, `AnnotationResponse`, `AnnotationList`

New endpoints added to `apps/api/runledger_api/routers/analytics.py`:

**`GET /analytics/economics/{run_id}`** — 4 execute calls:
1. Run lookup (workspace scope check → 404 if not found)
2. Span-type costs — `SELECT span_type, SUM(cost_usd) FROM spans WHERE run_id=? GROUP BY span_type`
3. Model costs — `SELECT model, provider, SUM(cost_usd), COUNT(*) FROM provider_calls WHERE run_id=? GROUP BY model, provider`
4. Retry cost — `SUM(spans.cost_usd) WHERE parent_span_id IS NOT NULL AND span_type='llm'`
Total from Python sum of model cost rows (authoritative source = provider_calls).

**`GET /analytics/workflows/top`** — 2 execute calls (avoids join fan-out on AVG/p95):
1. From `agent_runs` only: `COUNT`, `AVG(total_cost_usd)`, `percentile_cont(0.95).within_group(total_cost_usd)`, `SUM`, ordered by avg cost or latency, `LIMIT N`
2. From `provider_calls JOIN agent_runs`: `COUNT(provider_calls.id)` per (feature_tag, application_id) — merged in Python

**`GET /analytics/compare`** — 4 execute calls:
1. Baseline version `AgentRun` stats: `COUNT, AVG(cost), AVG(input_tokens), AVG(output_tokens), AVG(extract(epoch from ended_at-started_at)*1000)`
2. Comparison version `AgentRun` stats (same shape)
3. Baseline span costs by type: `Span JOIN AgentRun WHERE deployment_version=baseline GROUP BY span_type`
4. Comparison span costs by type
Delta pct: `(cmp - base) / base * 100`; None if baseline=0

**`GET /analytics/regressions`** — 2 execute calls:
1. Current window (default last 7d): `GROUP BY feature_tag` → `AVG(total_cost_usd)`, `COUNT(*)`
2. Prior window (7d before that): same shape
Python: for each feature_tag present in both windows, flag if `(current - prior) / prior > 0.20` AND `current_run_count >= 3`

**`POST /analytics/annotations`** → 201 — create `Annotation` row, commit, refresh, return

**`GET /analytics/annotations`** — optional `from`, `to`, `version` filters; `ORDER BY annotation_date DESC`

Frontend (`apps/web/`):
- `types/api.ts` — 10 new interfaces: `SpanTypeCost`, `ModelCost`, `RunEconomics`, `WorkflowSummary`, `WorkflowTopList`, `SpanTypeDelta`, `VersionSummary`, `VersionCompareResult`, `RegressionItem`, `RegressionList`, `Annotation`, `AnnotationList`
- `lib/api.ts` — 6 fetch helpers: `getRunEconomics`, `getTopWorkflows`, `getVersionCompare`, `getRegressions`, `createAnnotation`, `getAnnotations`
- `components/layout/Sidebar.tsx` — `TrendingUp` Economics nav item (after Analytics)
- `components/economics/EconomicsBreakdown.tsx` — `'use client'`; Recharts `BarChart` with `Cell` per span type; model cost table below
- `components/economics/ChangeImpactPanel.tsx` — `'use client'`; baseline + comparison text inputs + Compare button; 3 delta cards (red/green) + span-type breakdown table
- `components/economics/RegressionTable.tsx` — server-renderable table; change % column bold red >20%, green otherwise; empty state text
- `components/economics/AnnotationForm.tsx` — `'use client'`; date + version + textarea + submit; calls `createAnnotation`; `onCreated` callback
- `app/(dashboard)/analytics/economics/page.tsx` — `'use client'`; `useSession` for API key; 4 independently-loading sections each with `animate-pulse` skeleton

Example (`examples/09_economics_query.py`):
- Queries all 6 new endpoints; prints per-run breakdown, workflow table, version compare table, regression list, annotations; handles empty-state gracefully

Tests (`apps/api/tests/test_economics.py`) — **12 tests:**
- `test_run_economics_by_span_type`, `test_run_economics_by_model`, `test_run_economics_404`
- `test_top_workflows_returns_list`, `test_top_workflows_limit`
- `test_version_compare_delta_pct`, `test_version_compare_missing_baseline`
- `test_regressions_detected`, `test_regressions_below_threshold`
- `test_create_annotation`, `test_list_annotations`
- `test_economics_requires_auth`

**Definition of done:** ✅ Tag runs with `deployment_version=v1` and `v2`. Compare endpoint returns correct per-span-type cost deltas. Regressions endpoint flags workflows with >20% cost increase. Annotations can be created and listed via API and UI.

---

### Phase 10 — Weeks 21–22: End-user Analytics + Replay Harness ✅
**Roadmap areas:** 9 (Replay), 10 (End-user Analytics)

**Goal:** Identify your top spenders and anomalous users. Create a replay dataset and project cost across model configs.

**What was built:**

Database migration (`apps/api/alembic/versions/007_replay.py`):
- `user_anomalies` — `(workspace_id, end_user_id, detected_at DATE, daily_spend, mean_spend, zscore, reason)`
- `replay_datasets` — `(workspace_id, name, source, run_ids JSONB)`
- `replay_experiments` — `(workspace_id, dataset_id, name, configs JSONB, status, results JSONB, estimated_cost_usd)`

End-user analytics (new endpoints in `routers/analytics.py`):
- `GET /analytics/users/cohorts` — groups by spend tier (P0/P1/P2/P3) using SQLAlchemy `case()` on subquery; returns `user_count`, `avg_cost_usd`, `total_cost_usd`
- `GET /analytics/users/anomalies` — reads `user_anomalies` table ordered by detected_at DESC

Nightly analytics Celery task (`workers/replay.py` — `nightly_analytics_worker`):
- Runs at 02:00 UTC; computes 30d mean spend per active end_user; Z-score flags users with Z > 3 into `user_anomalies`

Replay router (`routers/replay.py`, prefix `/replay`):
- `POST /replay/datasets` → 201; `GET /replay/datasets` → list with `run_count`
- `GET /replay/datasets/{id}` → single dataset or 404
- `POST /replay/experiments` → 201; `GET /replay/experiments` → list
- `POST /replay/experiments/{id}/run` → 202; triggers `run_experiment_worker` Celery task
- `GET /replay/experiments/{id}/results` → per-config projected cost + token totals + Δ% deltas

Replay Celery worker (`workers/replay.py` — `run_experiment_worker`):
- Projects cost per config by reading `provider_pricing` table; no real LLM calls
- Writes `results` JSONB + `estimated_cost_usd` back to experiment row; sets status='completed'

Frontend (`apps/web/`):
- `types/api.ts` — `CohortSummary/List`, `AnomalyItem/List`, `DatasetResponse/List`, `ExperimentResponse/List`, `ConfigResult`, `ConfigDelta`, `ExperimentResults`
- `lib/api.ts` — `getUserCohorts`, `getUserAnomalies`, `createDataset`, `listDatasets`, `createExperiment`, `listExperiments`, `runExperiment`, `getExperimentResults`
- `/analytics/users` page — cohort badges + anomaly tabs + segmentation
- `/replay` page — dataset list + create form + experiment list + create modal
- `/replay/[experiment_id]` — side-by-side config results with Δ% badges

Tests (`apps/api/tests/test_replay.py`) — **15 tests:**
- `test_create_dataset`, `test_list_datasets`, `test_get_dataset_404`
- `test_create_experiment`, `test_create_experiment_invalid_dataset`, `test_list_experiments`
- `test_run_experiment`, `test_get_results_pending`, `test_get_results_completed`
- `test_replay_requires_auth` + 5 worker/analytics tests

**Definition of done:** ✅ Create a dataset of run IDs. Define an experiment comparing two model configs. Run it. See projected cost delta in the results page.

---

### Phase 11 — Weeks 23–24: Tamper-evident Ledger + Security Boundaries + Privacy Governance ✅
**Roadmap areas:** 11 (Security), 12 (Ledger), 13 (Privacy), 15 (OSS/Paid Packaging)

**Goal:** Cryptographically verifiable daily spend snapshots, per-workspace tool policies, suspicious-sequence detection, and a privacy capture policy API.

**What was built:**

Database migration (`apps/api/alembic/versions/008_ledger.py`):
- `ledger_keys` — workspace-scoped 30-day HMAC signing keys (auto-rotated on expiry)
- `ledger_snapshots` — HMAC-signed daily spend records; unique index on `(workspace_id, snapshot_date)`
- `tool_registry` — per-workspace tool → policy (allow|audit|block) mapping; unique on `(workspace_id, tool_name)`
- `security_events` — flagged suspicious sequences and policy violations
- `capture_policies` — one-row-per-workspace privacy mode override

ORM models (`apps/api/runledger_api/models/ledger.py`):
- `LedgerKey`, `LedgerSnapshot`, `ToolRegistry`, `SecurityEvent`, `CapturePolicy`
- All registered in `models/__init__.py`

Pydantic schemas:
- `schemas/ledger.py` — `LedgerSnapshotResponse`, `LedgerSnapshotList`, `LedgerVerifyResult`
- `schemas/tools.py` — `ToolRegistryCreate/Update/Response/List`, `SecurityEventResponse/List`
- `schemas/privacy.py` — `CapturePolicyUpsert`, `CapturePolicyResponse`

Service layer (`apps/api/runledger_api/services/ledger.py`):
- `get_or_create_active_key(db, workspace_id)` — returns active key or creates 32-byte hex key with 30d TTL
- `build_daily_snapshot(db, workspace_id, date)` — queries `provider_calls` for total cost, call count, and per-model breakdown
- `compute_snapshot_hash(data, key_value)` — calls `sign_snapshot()` from `services/billing.py` (reuse)
- `verify_snapshot(db, workspace_id, date)` — fetches snapshot + key, rebuilds data, re-computes hash, returns `LedgerVerifyResult`

Routers:
- `routers/ledger.py` (prefix `/ledger`) — `GET /snapshots`, `POST /snapshots/generate` (201), `GET /verify/{date}`
- `routers/tools.py` (prefix `/tools`) — full CRUD on `/registry` + `GET /security-events`
- `routers/privacy.py` (prefix `/privacy`) — `GET /capture-policy` (404 if not set), `PUT /capture-policy`

Celery workers (`workers/ledger.py`):
- `ledger.daily_snapshots` (daily at 01:00 UTC) — finds workspaces active yesterday → build + sign + upsert snapshot per workspace
- `ledger.suspicious_sequences` (every 60s) — `HAVING COUNT(*) > 5` over last 60s per (workspace, tool_name, end_user_id); 5-minute dedup window; inserts `SecurityEvent` rows

Core updates:
- `core/config.py` — `runledger_mode: str = "oss"` field (RUNLEDGER_MODE env var)
- `core/feature_gate.py` — `require_cloud(feature_name)` raises HTTP 402 when mode != "cloud"
- `core/celery_app.py` — added `workers.ledger` to include + 2 beat entries
- `main.py` — registered `ledger.router`, `tools.router`, `privacy.router`

Frontend (`apps/web/`):
- `types/api.ts` — 8 new interfaces: `LedgerSnapshotResponse/List`, `LedgerVerifyResult`, `ToolRegistryResponse/List`, `SecurityEventResponse/List`, `CapturePolicyResponse`
- `lib/api.ts` — 9 new helpers: `listLedgerSnapshots`, `generateLedgerSnapshot`, `verifyLedgerSnapshot`, `listToolRegistry`, `upsertToolRegistry`, `deleteToolRegistry`, `getSecurityEvents`, `getCapturePolicy`, `upsertCapturePolicy`
- `components/layout/Sidebar.tsx` — `ShieldCheck` Ledger nav item
- `app/(dashboard)/ledger/page.tsx` — `'use client'` page; 4 sections: snapshots table + verify buttons, tool registry CRUD, security events read-only, capture policy form

Example (`examples/11_ledger_verify.py`):
- CLI script demonstrating all 7 Phase 11 endpoints with formatted table output

Tests:
- `tests/test_ledger.py` — **8 tests:** list_snapshots_empty, generate_snapshot, verify_ok, verify_not_found, verify_tampered, ledger_requires_auth, tool_registry_crud, security_events_list
- `tests/test_tools_privacy.py` — **7 tests:** create_tool, upsert_tool, list_tools, delete_tool, get_policy_404, upsert_policy, tools_requires_auth

**Definition of done:** ✅ Generate a daily snapshot. Call `/ledger/verify/{date}` → `status=ok`. Mutate the stored hash → `status=tampered`. Register a tool with `policy=block`. Suspicious sequences are detected every 60s. Set workspace privacy mode via PUT. 121/121 tests pass.

---

### Phase 12 — Weeks 25–26: Settings Console + Dark Mode + Provider Profiles ✅

**Goal:** Workspace administrators can manage API keys, configure model pricing overrides, and switch between light/dark themes — all from a single Settings page.

**What was built:**

Settings router (`apps/api/runledger_api/routers/settings.py`, prefix `/settings`):
- `GET /settings/api-keys` — list active (non-revoked) workspace API keys
- `POST /settings/api-keys` → 201 — generate a new key (raw key returned once; stored as SHA-256 hash in DB)
- `DELETE /settings/api-keys/{id}` → 204 — revoke a key (sets `revoked_at=now()`)

Providers router (`apps/api/runledger_api/routers/providers.py`, prefix `/providers`):
- `GET /providers/pricing` — list workspace pricing overrides + global rows
- `POST /providers/pricing` → 201 — create workspace-scoped pricing override
- `DELETE /providers/pricing/{id}` → 204 — delete workspace pricing override (global rows protected)

Pydantic schemas (`apps/api/runledger_api/schemas/providers.py`):
- `ProviderPricingCreate`, `ProviderPricingResponse`, `ProviderPricingList`

Frontend (`apps/web/`):
- `npm install next-themes` — dark mode support
- `components/providers/ThemeProvider.tsx` — wraps `next-themes` ThemeProvider
- Dashboard layout wraps children in `ThemeProvider`
- `TopBar` — sun/moon icon toggle button calling `setTheme()`
- `components/layout/Sidebar.tsx` — Settings nav item
- `app/(dashboard)/settings/page.tsx` — `'use client'` page; 3 sections:
  - **API Keys** — create form (name + env), one-time raw key banner (copy + dismiss), keys table with revoke button
  - **Provider Profiles** — add pricing form (provider, model, input/output/cached costs), pricing table with delete for workspace-scoped rows
  - **Appearance** — theme selector (Light / Dark / System) via `useTheme()`
- `types/api.ts` — `ApiKeyResponse`, `ApiKeyCreateResponse`, `ProviderPricingResponse`, `ProviderPricingList`
- `lib/api.ts` — `listApiKeys`, `createApiKey`, `revokeApiKey`, `listProviderPricing`, `createProviderPricing`, `deleteProviderPricing`

Tests (`apps/api/tests/test_settings.py`) — **8 tests:**
- `test_list_api_keys_empty`, `test_create_api_key`, `test_create_api_key_raw_key_not_stored`, `test_revoke_api_key`, `test_revoke_wrong_workspace`, `test_settings_requires_auth`, `test_list_pricing_includes_global`, `test_create_and_delete_pricing`

Tests (`apps/api/tests/test_providers.py`) — **5 tests** (pricing CRUD).

**Total new tests: 13 (134 cumulative)**

**Definition of done:** ✅ Create an API key, copy the raw value (shown once), revoke it. Add a workspace pricing override for a model, verify it appears in the pricing list. Toggle dark mode — persists on reload. 134/134 tests pass.

---

### Phase 14 — Weeks 27–28: Integrations: Slack Alerts + GitHub CI Gate ✅

**Goal:** Budget breach and anomaly alerts fire in Slack automatically. CI pipelines can gate on cost regressions.

**Product areas covered:** Integrations ecosystem (Slack/Teams alerts, CI gate, bulk data export)

**What was built:**

No new DB migration needed — `BudgetNotification` (`channel`, `destination_url`, `events`) already stores Slack webhook URLs from Phase 7.

Slack Block Kit notifications service (`apps/api/runledger_api/services/notifications.py`):
- `build_budget_breach_blocks(budget_id, scope_type, scope_id, spend_usd, limit_usd, action)` → Block Kit list
- `build_anomaly_blocks(user_id, daily_spend, mean_spend, zscore, reason)` → Block Kit list
- `build_test_blocks()` → Block Kit connectivity test message
- `send_slack_message(webhook_url, blocks, fallback_text)` → async httpx POST to Slack webhook

Budget service update (`apps/api/runledger_api/services/budgets.py`):
- `send_notification()` now branches on `channel == "slack"`: calls `send_slack_message()` with Block Kit; otherwise uses existing HMAC-signed generic webhook POST

Analytics worker update (`apps/api/runledger_api/workers/analytics.py`):
- After anomaly detection commit: queries `BudgetNotification` rows with `channel="slack"` and `"anomaly.detected" in events` per workspace; dispatches Slack message per anomaly per notification

Integrations router (`apps/api/runledger_api/routers/integrations.py`, prefix `/integrations`):
- `POST /integrations/slack/test` — send a test Block Kit message to a webhook URL; returns `{"ok": true}` or `{"ok": false, "error": "..."}`

Analytics router update (`apps/api/runledger_api/routers/analytics.py`):
- `GET /analytics/export?format=csv|json&from=...&to=...` — bulk export of `usage_daily` rows for the date range; CSV returns `StreamingResponse` with `text/csv`; JSON returns `{"items": [...]}`

Main app update (`apps/api/runledger_api/main.py`):
- `app.include_router(integrations_router.router)`

SDK CLI update (`packages/sdk/runledger_sdk/cli.py`):
- `runledger check-regression --threshold 20.0` — calls `GET /analytics/regressions`, prints a rich table of regressions exceeding the threshold, exits 1 if any found; designed as a GitHub Actions CI gate

Frontend (`apps/web/`):
- `types/api.ts` — `ExportRow`, `AnalyticsExport`, `SlackTestResponse`
- `lib/api.ts` — `exportAnalytics(apiKey, format, from?, to?)`, `testSlackWebhook(apiKey, webhookUrl)`
- `app/(dashboard)/settings/page.tsx` — added **Integrations** section below Appearance:
  - Info banner linking to `POST /budgets/{id}/notifications` API
  - Slack webhook URL input + "Test" button
  - Inline success/error feedback after test send

Example (`examples/13_integrations.py`):
- Demonstrates: Slack test, analytics JSON export, analytics CSV export (saved to `export.csv`), regression list

Tests (`apps/api/tests/test_integrations.py`) — **8 tests:**
- `test_slack_test_ok`, `test_slack_test_error`, `test_integrations_requires_auth`
- `test_analytics_export_json`, `test_analytics_export_csv`, `test_analytics_export_date_filter`, `test_analytics_export_requires_auth`
- `test_slack_blocks_budget_breach` (unit test — Block Kit structure validation)

**Total new tests: 8 (142 cumulative)**

**Definition of done:** ✅ `POST /integrations/slack/test` with a real Slack webhook → message appears in Slack. `GET /analytics/export?format=csv` → valid CSV with date/provider/model/cost columns. `runledger check-regression --threshold 20` exits 0 (no regressions) or exits 1 with table (regressions found). Settings page Integrations section renders with test button.

---

### Phase 15 — Anthropic SDK 🔲

**Goal:** Instrument Anthropic API calls (Claude) with the same zero-config pattern as the existing OpenAI wrapper.

**What to build:**

SDK — `packages/sdk/runledger_sdk/anthropic.py`:
- `AnthropicCallbackHandler` or instrument function wrapping `anthropic.Anthropic` and `anthropic.AsyncAnthropic`
- Mirror of `openai.py`: captures model, input/output tokens (from `usage.input_tokens` / `usage.output_tokens`), latency_ms, status, error_type
- Handles streaming responses by accumulating token counts from stream events
- Works with `rl.context(...)` — same context propagation

SDK — `runledger_sdk/__init__.py`:
- Export `AnthropicCallbackHandler`; bump version to v0.5.0

Example (`examples/12_anthropic_basic.py`):
- Minimal Anthropic instrumentation with `rl.instrument()` for Anthropic client

Pricing seeds (`apps/api/scripts/seed.py`):
- Add Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Opus pricing rows (already partially seeded as `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5`)

Tests (`packages/sdk/tests/test_anthropic.py`) — ~8 tests:
- `test_instrument_captures_tokens`, `test_instrument_captures_latency`
- `test_async_instrument`, `test_streaming_token_count`
- `test_error_captures_error_type`, `test_context_propagated`

**Definition of done:** 🔲 Two-line instrumentation captures all Anthropic Claude calls with correct token and cost attribution.

---

### Phase 16 — Production Hardening + UI Polish ✅

**Goal:** The API is rate-limited, PII is scrubbed before storage, health checks are richer, the deployment guide is complete, and the frontend has consistent dark mode, toast notifications, and loading states across all pages.

**What was built:**

Rate limiting (`apps/api/runledger_api/core/ratelimit.py` — new, no new library):
- Custom Redis INCR + EXPIRE sliding-window limiter; key: `rl:ratelimit:{tier}:{token[:16]}:{epoch_minute}`
- Three tiers: `ingest_rate_limit` (600 req/min), `analytics_rate_limit` (120 req/min), `management_rate_limit` (60 req/min)
- Returns HTTP 429 with `Retry-After: 60` header when exceeded
- Fail-open on any Redis exception — rate limiting never blocks ingest
- Applied as router-level dependency (`router = APIRouter(dependencies=[Depends(...)])`) on: `ingest.py`, `analytics.py`, `budgets.py`, `billing.py`, `settings.py`, `providers.py`, `replay.py`, `integrations.py`

PII scrubbing (`apps/api/runledger_api/services/scrubbing.py` — new):
- `scrub_value(s: str) → str` — regex replace for email, SSN, credit card, phone → `[REDACTED]`
- `scrub_dict(d: dict | None) → dict | None` — recursive scrubber for nested metadata dicts
- Applied in `workers/pipeline.py` to `run_metadata` (in `_handle_run_start`) and `span_metadata` (in `_handle_span_end`) before ORM write

Health probes (`apps/api/runledger_api/routers/health.py` — updated):
- `GET /health/live` — always returns HTTP 200 `{"status": "ok"}`; used as Railway/container restart probe
- `GET /health/ready` — tests DB (`SELECT 1`) and Redis (`ping`); returns HTTP 200 on success, HTTP 503 with `{"status": "degraded", "db": "...", "redis": "..."}` on failure
- Existing `GET /health` endpoint unchanged (backward compat)

Admin secret configuration (`apps/api/runledger_api/core/config.py` — updated):
- New `admin_secret: str = ""` field loaded from `ADMIN_SECRET` env var
- `effective_admin_secret` property: returns `admin_secret` if set, otherwise falls back to `secret_key`
- `require_admin` dependency in `core/deps.py` updated to use `effective_admin_secret`
- `ADMIN_SECRET=runledger-admin` added to `infra/docker-compose.yml`
- `NEXT_PUBLIC_ADMIN_SECRET` in `apps/web/.env.local` pre-fills the Settings page admin field

Frontend — sonner toasts (`apps/web/`):
- `npm install sonner` — Sonner toast library
- `<Toaster position="top-right" richColors />` mounted in `app/(dashboard)/layout.tsx`
- `toast.success()` / `toast.error()` added to: `budgets/page.tsx`, `billing/page.tsx`, `ledger/page.tsx`, `replay/page.tsx`, `settings/page.tsx`

Frontend — Sidebar active state (`apps/web/components/layout/Sidebar.tsx` — rewrite):
- Converted to `'use client'` component using `usePathname()` from `next/navigation`
- Active detection: `pathname.startsWith(item.href)`
- Active style: `bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300`
- Idle style: `text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800`
- Container + logo: full dark mode class variants

Frontend — dark mode fixes (all pages):
- `budgets/page.tsx`, `components/budgets/BudgetList.tsx` — table, progress bar, badge dark variants
- `billing/page.tsx`, `components/billing/BillingPeriodTable.tsx` — table, status badge dark variants
- `ledger/page.tsx` — skeleton loading rows + toast feedback + dark mode table
- `replay/page.tsx` — skeleton rows (replaces "Loading…" text), empty state message per section, toasts
- `settings/page.tsx` — toast feedback + dark mode card borders
- `analytics/users/page.tsx` — table and badge dark variants
- Dashboard layout `main`: `bg-gray-50 dark:bg-gray-950`

Frontend — loading states + empty states:
- `ledger/page.tsx` — 5-row `animate-pulse` skeleton while loading; empty state text for snapshot list
- `replay/page.tsx` — 3-row skeleton; "No datasets yet" and "No experiments yet" empty states with icons

SDK — env-var config (`packages/sdk/runledger_sdk/client.py` — updated):
- `RUNLEDGER_BASE_URL` env var overrides `base_url` parameter
- `RUNLEDGER_API_KEY` env var used when `api_key` not passed explicitly
- `RUNLEDGER_LOCAL=true/1/yes` enables local/print mode without code changes
- `ValueError` raised early if `local=False` and no API key (replaces silent fallback)

Railway deployment guide (`docs/deployment.md` — new):
- Provision managed Postgres + Redis on Railway
- Environment variable reference table
- Deploy API + Celery worker as separate Railway services
- Run migrations: `railway run alembic upgrade head`
- Health check configuration: `/health/live` for TCP probe, `/health/ready` for readiness gate

Tests (`apps/api/tests/test_hardening.py` — new, **13 tests**):
- `test_ingest_rate_limit_allows_under_limit`, `test_ingest_rate_limit_blocks_over_limit`
- `test_analytics_rate_limit_blocks`, `test_management_rate_limit_blocks`
- `test_rate_limit_fail_open` — Redis down → request passes (no 429)
- `test_scrub_value_email`, `test_scrub_value_ssn`, `test_scrub_value_credit_card`
- `test_scrub_dict_recursive`, `test_scrub_dict_none`
- `test_health_live`, `test_health_ready_ok`, `test_health_ready_degraded`

**Total new tests: 13 (155 cumulative)**

**Definition of done:** ✅ Ingestion endpoint returns 429 after 600 req/min exceeded. Metadata with `email@example.com` stored as `[REDACTED]`. `/health/live` always 200; `/health/ready` returns 503 when Redis mocked down. Sidebar highlights active route. Dark mode renders correctly on all pages. Toast appears on budget create/delete. Ledger and replay pages show skeleton while loading. Admin secret pre-filled in Settings from `NEXT_PUBLIC_ADMIN_SECRET`. 155/155 tests pass.

---

### Phase 17 — Evaluations & Scores ✅

**Goal:** Attach quality scores to any run or span — from human feedback, rule-based evaluators, or telemetry. Cost without quality is half the picture. This closes the loop: *how much did it cost, and was it worth it?*

**Why now:** LangSmith and Langfuse are primarily known as eval platforms. This is the most impactful gap vs both. Every subsequent feature (prompt management, smart routing, alerting) becomes significantly more powerful with a quality signal.

**V1 scope:** Score CRUD + analytics (summary + regressions) + nightly rollup worker + `/evaluations` frontend page + `rl.score()` SDK method. LLM-as-judge evaluator framework (batch evaluation, judge drift) deferred to Phase 17B.

**What was built:**

Backend (`apps/api/`):
- `alembic/versions/010_scores.py` — `score_events` + `score_rollups_daily` tables (no FK constraints on run_id/span_id — scores outlive runs for audit)
- `models/scores.py` — `ScoreEvent`, `ScoreRollupDaily` ORM models; both registered in `models/__init__.py` for Alembic autogenerate
- `schemas/scores.py` — `ScoreCreate`, `ScoreResponse`, `ScoreList`, `ScoreSummaryItem`, `ScoreSummary`, `ScoreRegressionItem`
- `routers/evaluations.py` — prefix `/evaluations`, `management_rate_limit`:
  - `POST /evaluations/scores` → HTTP 201 with `ScoreResponse`; fields: name, value (0–100), label, source (human|llm|rule|telemetry), confidence (0–1), evidence JSONB, run_id, span_id, session_id, end_user_id
  - `GET /evaluations/scores` — filterable by run_id, name, source, from/to, limit (≤200); returns `ScoreList`
- `routers/analytics.py` — two new endpoints appended:
  - `GET /analytics/scores/summary` — two-execute pattern (current + prior window), GROUP BY name, AVG + COUNT; `ScoreSummary` with `change_pct` (None when no prior data)
  - `GET /analytics/scores/regressions` — same two-execute pattern; threshold >20% drop in avg_value with sample_count ≥ 3; returns `list[ScoreRegressionItem]`
- `workers/score_rollup.py` — `score_rollup_worker(day_str=None)` Celery task (NullPool + asyncio.run pattern); idempotent DELETE + raw SQL INSERT using PERCENTILE_CONT(0.5/0.9); LEFT JOINs `agent_runs` + `provider_calls` for feature_tag/model/deployment_version enrichment; fails gracefully (log + no raise)

SDK (`packages/sdk/`):
- `client.py` — `rl.score(name, value, *, run_id, span_id, label, source, confidence, evidence)` method: direct `httpx.post()` to `/evaluations/scores`, fail-silent (log warning), auto-fills run_id from current context via `get_context_snapshot()`; `local=True` → log to stdout, no HTTP

Frontend (`apps/web/`):
- `types/api.ts` — `ScoreEvent`, `ScoreList`, `ScoreSummaryItem`, `ScoreSummary`, `ScoreRegressionItem` interfaces
- `lib/api.ts` — `submitScore()`, `listScores()`, `getScoreSummary()` functions (same `apiFetch` pattern)
- `app/(dashboard)/evaluations/page.tsx` — `'use client'` page with two-column layout: left = score submit form (run_id, name, value, label select, source select, confidence), right = per-score summary cards with `ChangeBadge` (↑/↓ %, green/red); bottom = recent scores table (7 columns, skeleton + empty state with Star icon); toast on submit success/error
- `components/layout/Sidebar.tsx` — Evaluations entry with `Star` icon, inserted after Replay

**New API routes:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/evaluations/scores` | Submit a quality score (HTTP 201) |
| `GET` | `/evaluations/scores` | List scores (filterable by run_id, name, source, from, to) |
| `GET` | `/analytics/scores/summary` | Avg score per name + period-over-period delta |
| `GET` | `/analytics/scores/regressions` | Names where avg dropped >20% vs prior period |

**Tests:** `tests/test_evaluations.py` — **13 tests**:
- `test_create_score_success` — POST 201, response has id/name/value/source
- `test_create_score_requires_auth` — unauthenticated → 401
- `test_create_score_with_run_id` — run_id stored and returned
- `test_create_score_value_out_of_range` — value=150 → 422
- `test_create_score_invalid_source` — source="robot" → 422
- `test_create_score_confidence_validation` — confidence=1.5 → 422
- `test_list_scores_empty` — GET → `{"items": []}`
- `test_list_scores_returns_items` — mock 2 rows → items len 2
- `test_score_summary_empty` — no rows → `{"items": []}`
- `test_score_summary_returns_aggregates` — mocked row → avg/count in response
- `test_score_summary_delta_pct` — prior data → change_pct = 12.5%
- `test_score_regressions_none` — no drop → empty list
- `test_score_regressions_detected` — current 0.5, prior 0.8 → −37.5% flagged

**Total new tests: 13 (183 cumulative)**

**Definition of done:** ✅ `POST /evaluations/scores {"name":"relevance","value":0.9}` → 201. `GET /analytics/scores/summary` → `{"items": [...]}`. `GET /analytics/scores/regressions` → `[]` when no regressions. `/evaluations` page renders form, submits score → toast, table refreshes. Sidebar shows "Evaluations" with Star icon; active link highlights on navigate. `rl.score("relevance", 0.9, run_id="<uuid>")` posts to `/evaluations/scores`. 183/183 tests pass.

---

### Phase 18 — Prompt Management ✅ Complete (12 tests, 195 total)

**What was built:**

Backend:
- `models/prompts.py` — `Prompt` ORM model (workspace-scoped, UNIQUE on workspace_id+name) + `PromptVersion` ORM model (auto-increment version per prompt, UNIQUE on prompt_id+version, INDEX on prompt_id+environment)
- `alembic/versions/011_prompts.py` — migration (revision "011", down_revision "010"); creates `prompts` + `prompt_versions` tables with FK cascade delete
- `schemas/prompts.py` — `PromptCreate`, `PromptResponse`, `PromptList`, `VersionCreate`, `VersionResponse`, `VersionList`, `PromptRender`, `PromoteRequest`, `VersionMetrics`, `PromptMetrics`
- `routers/prompts.py` — prefix `/prompts`, 10 endpoints: `POST /prompts` (201), `GET /prompts`, `GET /prompts/{name}`, `DELETE /prompts/{name}` (204), `POST /prompts/{name}/versions` (201, auto-increment version), `GET /prompts/{name}/versions`, `GET /prompts/{name}/latest` (SDK pull, query param `environment`), `GET /prompts/{name}/versions/{v}`, `POST /prompts/{name}/promote` (copies latest from source env → new version in target env), `GET /prompts/{name}/metrics` (per-version run_count+avg_cost+avg_score, joins agent_runs on `deployment_version="{name}:{version}"`)
- `main.py` updated — includes prompts router
- `models/__init__.py` updated — registers Prompt + PromptVersion for Alembic autogenerate

SDK:
- `packages/sdk/runledger_sdk/client.py` — `rl.get_prompt(name, environment, variables)` with 60s in-memory cache (threading.Lock), `{{variable}}` regex substitution, fails loudly (re-raises httpx errors), local=True mode returns placeholder

Frontend:
- `types/api.ts` — `PromptResponse`, `PromptList`, `PromptVersion`, `VersionList`, `VersionMetrics`, `PromptMetrics`
- `lib/api.ts` — `listPrompts`, `createPrompt`, `getPrompt`, `deletePrompt`, `createVersion`, `listVersions`, `getLatestVersion`, `promoteVersion`, `getPromptMetrics`
- `app/(dashboard)/prompts/page.tsx` — list page with create form (toggle) + table (name, description, env badge, created, delete button) + click → detail
- `app/(dashboard)/prompts/[name]/page.tsx` — detail page: version history list with env badges + metrics (run count, avg cost, avg score per version) + commit form + side-by-side line-level diff viewer (select any two versions as before/after) + promote staging→production button
- `Sidebar.tsx` — added `BookText` icon + Prompts nav entry between Evaluations and Ledger

**Deployment_version convention:** `"{prompt_name}:{version_number}"` (e.g. `"support-agent:3"`) — set this in `rl.context(deployment_version=f"{name}:{version}")` to link runs to prompt versions in metrics.

**Original goal:** Version-controlled prompt registry with variable templating, environment promotion (staging → production), and per-version cost + quality metrics. Closes the gap between "cost regression detected on v2" and "here is exactly what changed in the prompt."

**Why now:** RunLedger already tracks `deployment_version` on every run. Without prompt management, that field is just a string label — users can't see what changed. With it, every regression report links directly to a prompt diff.

**What to build:**

Backend (`apps/api/`):
- `alembic/versions/010_prompts.py` — `prompts` + `prompt_versions` tables
- `models/prompts.py` — `Prompt`, `PromptVersion` ORM models
- `schemas/prompts.py` — request/response schemas; `PromptRender` schema for variable substitution
- `routers/prompts.py` — prefix `/prompts`:
  - `POST /prompts` — create prompt (name, description, default_environment)
  - `GET /prompts` — list prompts for workspace
  - `GET /prompts/{name}` — get prompt metadata
  - `DELETE /prompts/{name}` — delete prompt + all versions
  - `POST /prompts/{name}/versions` — commit a new version (content, variables, commit_message, environment)
  - `GET /prompts/{name}/versions` — list all versions (desc)
  - `GET /prompts/{name}/latest` — latest version for an environment (SDK pull endpoint)
  - `GET /prompts/{name}/versions/{version}` — get specific version
  - `POST /prompts/{name}/promote` — copy latest staging version → production
  - `GET /prompts/{name}/metrics` — per-version cost + avg score + run count

SDK (`packages/sdk/`):
- `runledger_sdk/transport.py` — `get_prompt(name, environment="production", variables={})` method
  - Fetches `/prompts/{name}/latest` with caching (60s TTL in-memory)
  - Renders `{{variable}}` placeholders with provided values
  - Returns rendered string + version metadata
- `runledger_sdk/transport.py` — `async aget_prompt(...)` async variant

Frontend (`apps/web/`):
- `/app/(dashboard)/prompts/page.tsx` — Prompts list: name, latest version, environment, run count, avg cost, avg score badge
- `/app/(dashboard)/prompts/[name]/page.tsx` — Prompt detail:
  - Version history list with commit messages + dates
  - Side-by-side diff viewer between any two versions (highlight added/removed tokens)
  - Variable schema editor (name, type, description)
  - Promote-to-production button
  - Cost + score chart per version (line chart, version on X axis)
- Sidebar: add "Prompts" nav entry between Replay and Ledger

**New API routes:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/prompts` | Create prompt |
| GET | `/prompts` | List prompts |
| GET | `/prompts/{name}` | Get prompt |
| DELETE | `/prompts/{name}` | Delete prompt |
| POST | `/prompts/{name}/versions` | Commit new version |
| GET | `/prompts/{name}/versions` | List versions |
| GET | `/prompts/{name}/latest` | Latest version for environment (SDK pull) |
| GET | `/prompts/{name}/versions/{v}` | Get specific version |
| POST | `/prompts/{name}/promote` | Promote staging → production |
| GET | `/prompts/{name}/metrics` | Per-version cost + score metrics |

**Tests:** `tests/test_prompts.py` — 12 tests:
- Prompt CRUD (create, list, delete)
- Version commit and retrieval (latest by environment, specific version)
- Variable rendering (`{{name}}` substitution)
- Promotion: staging version becomes production latest
- Per-version metrics query (join with agent_runs on deployment_version)
- Workspace scoping (no cross-workspace leakage)

**Definition of done:** 🔲 Create a prompt "support-agent" with 2 versions. Promote v1 to production. `transport.get_prompt("support-agent", variables={"user_name": "Alice"})` returns rendered string. Per-version cost visible in UI. Diff between v1 and v2 shown correctly.

---

### Phase 19 — Sessions UI + Payload Viewer ✅
**Goal:** Surface session-level analytics (multi-turn conversations) and display captured payloads inline in the trace viewer. Both features use data that is already collected — this phase is purely about making it visible.

**Why now:** `session_id` exists on every `AgentRun`. Multi-turn conversations are the primary LLM use case in production. Without session grouping, a 12-turn customer support conversation appears as 12 disconnected runs. Payload viewing is the difference between "span took 800ms" and "span took 800ms because the context window was 90k tokens."

**What to build:**

Backend (`apps/api/`):
- `routers/sessions.py` — prefix `/sessions`:
  - `GET /sessions` — list sessions (GROUP BY session_id, filterable by end_user_id, date range)
    - Returns: session_id, end_user_id, run_count, total_cost_usd, started_at, ended_at, avg_score
  - `GET /sessions/{session_id}` — ordered runs in session + cumulative cost timeline
  - `GET /sessions/{session_id}/cost-over-turns` — cost per turn number (for charting)
- `routers/runs.py` — extend `GET /runs/{run_id}` response to include:
  - `input_payload`: request content (only present when captured — SAMPLED or FULL mode)
  - `output_payload`: response content (same condition)
  - `span_payloads`: per-span input/output map

Frontend (`apps/web/`):
- `/app/(dashboard)/sessions/page.tsx` — Sessions list:
  - Table: session_id (truncated), end_user_id, run count, turns, total cost, duration, avg score badge
  - Filter by end_user_id and date range
  - Click → session detail
- `/app/(dashboard)/sessions/[session_id]/page.tsx` — Session detail:
  - Ordered run timeline (horizontal timeline chart showing cost per turn)
  - Each run card: feature_tag, cost, latency, score badges
  - Cumulative cost chart (cost accumulates across turns)
- `/components/runs/PayloadViewer.tsx` — In run detail sidebar, new "Payload" tab:
  - Shown only when `input_payload` / `output_payload` are present in API response
  - Input: rendered prompt (with system message, user turn, assistant turn clearly labelled)
  - Output: completion text
  - Token count annotation inline with the text
  - Privacy mode indicator ("captured because: FULL mode")
- Sidebar: add "Sessions" nav entry

**Tests:** `tests/test_sessions.py` — 8 tests:
- Sessions list: groups correctly by session_id, correct run count + cost aggregation
- Sessions list: filterable by end_user_id
- Session detail: runs returned in chronological order
- Cost-over-turns endpoint: correct per-turn breakdown
- Payload passthrough: run detail includes payloads when captured, omits when not
- Privacy gate: run in METADATA_ONLY mode returns no payload fields

**Definition of done:** 🔲 Create 3 runs with same session_id. Sessions list shows 1 session with run_count=3 and correct total cost. Session detail shows all 3 runs in order with cumulative cost chart. Run with FULL privacy mode shows input/output in payload tab.

---

### Phase 20 — TypeScript / Node.js SDK 🔲
**Goal:** First-class TypeScript SDK published to npm as `@runledger/sdk`. Instruments OpenAI Node.js client, Vercel AI SDK, and raw `fetch` calls. Opens the entire JS/TS ecosystem to RunLedger.

**Why now:** The Python SDK works for Python-native agents. The majority of production LLM applications (Next.js apps, Node.js backends, Vercel AI SDK) are TypeScript. Langfuse and LangSmith both have native TypeScript SDKs. This is a market access blocker.

**What to build:**

New package `packages/sdk-ts/` (TypeScript, npm):
- `src/client.ts` — `RunLedger` class: `new RunLedger({ apiKey, baseUrl, privacyMode })`
- `src/context.ts` — `AsyncLocalStorage`-based context (Node.js equivalent of Python's contextvars)
  - `withRun(fn, { runId, endUserId, sessionId, featureTag })` — async context wrapper
  - `getContext()` — read current context from AsyncLocalStorage
- `src/openai.ts` — `instrumentOpenAI(client, transport)` — wraps `openai` npm package
  - Patches `client.chat.completions.create` (streaming + non-streaming)
  - Pre-call: budget check (optional)
  - Post-call: capture model, tokens, latency, cost → emit event
- `src/vercel-ai.ts` — `createRunLedgerMiddleware()` — Vercel AI SDK middleware
  - Wraps `streamText`, `generateText`, `streamObject`
  - Compatible with `useChat` / `useCompletion` React hooks
- `src/fetch.ts` — `instrumentFetch(transport)` — global `fetch` wrapper for arbitrary HTTP calls to AI providers
- `src/transport.ts` — `Transport` class: batching (50 events / 2s flush), retry (3x exponential backoff), async `score()` method
- `src/types.ts` — full TypeScript types mirroring Python SDK event schemas
- `src/index.ts` — public exports

Tests (`packages/sdk-ts/tests/`, Jest):
- OpenAI wrapper: correct event shape, token counts, latency recorded
- Context propagation: `withRun` correctly scopes nested calls
- Batch flushing: events buffered then sent in correct shape
- `score()` method: sends correct payload to `/evaluations/scores`
- Vercel AI middleware: wraps `streamText`, emits event on completion

**Definition of done:** 🔲 `npm install @runledger/sdk` in a Next.js app. Add `instrumentOpenAI(openai)` in one line. Make 5 chat completions. Runs appear in the RunLedger UI with correct token counts. `score(runId, "relevance", 0.9)` from TypeScript creates a score.

---

### Phase 21 — Advanced Alerting + Model Gateway ✅
**Goal:** Two related features that each add significant value independently but are strongest together: (1) alerting rules beyond budget breaches, and (2) an intelligent model gateway that can route requests to the cheapest model meeting quality requirements.

**Why now:** The alerting infrastructure (Slack, webhooks, notification channels) already exists from Phase 14. Error rate and quality alerts are the next-most-requested monitoring feature. The gateway is RunLedger's biggest architectural differentiator vs Langfuse/LangSmith — they are observability-only. A gateway makes RunLedger active infrastructure, not just passive monitoring.

**Part A — Advanced Alerting:**

Backend:
- `models/alerts.py` — `AlertRule` (id, workspace_id, name, metric, operator, threshold, window_minutes, action, channel_id, is_active, created_at)
- `routers/alerts.py` — prefix `/alerts`:
  - `POST /alerts/rules` — create rule (metric: error_rate | p95_latency | avg_score | spend_velocity; operator: gt/lt; threshold; window_minutes; notification channel)
  - `GET /alerts/rules` — list rules
  - `PUT /alerts/rules/{id}` — update / toggle rule
  - `DELETE /alerts/rules/{id}` — delete rule
  - `GET /alerts/history` — recent alert firings
- `workers/alerts.py` — `alert_evaluation_worker()` Celery beat task (every 5 min):
  - For each active rule: compute metric for window → compare → fire notification if threshold crossed
  - Deduplication: don't re-fire if already fired in last window
- Frontend: Alert Rules section in Settings page — create/list/toggle rules

**Part B — Model Gateway:**

Backend:
- `models/gateway.py` — `GatewayRoute`, `GatewayRequest`, `PromptCache` ORM models
- `routers/gateway.py` — prefix `/gateway`:
  - `POST /gateway/chat/completions` — OpenAI-compatible proxy endpoint
    - Authenticate via Bearer API key (same as ingest)
    - Match request to configured routes by model requested
    - Apply load balancing / priority / cost-aware routing
    - On provider error: retry next route in priority order
    - Check `PromptCache` before forwarding (cache hit → return cached, record zero-cost hit)
    - Stream response back to client
    - Async: emit `ProviderCall` event for cost tracking (same pipeline as SDK)
  - `POST /gateway/routes` — create route (provider, model, priority, fallback_model)
  - `GET /gateway/routes` — list routes
  - `GET /gateway/stats` — cache hit rate, error rate, cost saved via caching
- `services/gateway.py` — `route_request()`, `check_cache()`, `store_cache()`, `select_cheapest_route()`
- Frontend: Gateway section in Settings — configure routes, view stats, toggle cache

**Key Gateway differentiation:**
- Uses existing `ProviderPricing` table for cost-per-route calculation
- Cache key = SHA256(model + normalized messages) — identical prompts share cache
- Fallback chain: if primary route 429s or 5xxs, retry next route automatically
- All gateway requests visible in Run Explorer as normal `AgentRun` records
- No SDK changes needed — just point `base_url` at the RunLedger gateway

**Tests:** `tests/test_alerts.py` (8 tests) + `tests/test_gateway.py` (10 tests):
- Alert rule CRUD
- Alert evaluation: error rate threshold triggers notification
- Alert deduplication: no double-fire within window
- Gateway: routes request to configured provider
- Gateway: fallback on 429
- Gateway: cache hit returns cached response, records zero tokens
- Gateway: all requests appear as ProviderCall records

**Definition of done:** 🔲 Create error-rate alert rule (threshold: 5%). Trigger 6 errors in 10 min. Slack notification fires. Configure a gateway route for `gpt-4o`. Point `OPENAI_BASE_URL` at RunLedger gateway. Make 10 completions — all appear in Run Explorer. Make same prompt twice — second is cache hit, cost is $0.

---

### Phase 22 — SaaS Foundation 🔲
**Goal:** Self-service signup, Stripe subscription management, and usage quota enforcement. Transforms RunLedger from a self-hosted tool into a deployable SaaS product.

**Why now:** After Phase 21 the core product is complete. Commercialization infrastructure is the last major unlock. Without it, every user must self-host, limiting distribution.

**What to build:**

Backend:
- `alembic/versions/013_saas.py` — `plans`, `subscriptions`, `usage_quotas` tables
- `models/saas.py` — `Plan`, `Subscription`, `UsageQuota` ORM models
- `routers/saas.py`:
  - `POST /auth/signup` — create tenant + workspace + user in one transaction; auto-assign free plan
  - `GET /billing/subscription` — current plan + usage for the tenant
  - `POST /billing/checkout` — create Stripe checkout session (upgrade flow)
  - `POST /billing/portal` — Stripe customer portal link (manage subscription)
  - `POST /webhooks/stripe` — handle `invoice.paid`, `customer.subscription.deleted`, `customer.subscription.updated`
- `services/quotas.py` — `check_quota(workspace_id, event_type)` — enforced in ingest router (return 402 when exceeded)
- `workers/quotas.py` — `quota_reset_worker()` — monthly reset of `usage_quotas.events_used`
- `core/feature_gate.py` — extend existing feature gate with plan-based checks

Frontend:
- `/app/signup/page.tsx` — self-service signup form (email, password, org name → POST /auth/signup)
- `/app/(dashboard)/billing/subscription/page.tsx` — current plan card, usage meter (events used / quota), upgrade button → Stripe checkout
- Upgrade modal: plan comparison table (Free vs Starter vs Growth vs Enterprise)
- Quota exceeded banner: inline notification when >90% of monthly events used

**Definition of done:** 🔲 Sign up via `/signup` with no admin intervention. Receive API key. Send 100 events. See usage meter at 100/10000. Click upgrade → Stripe checkout loads. Complete Stripe test payment → plan upgrades to Starter. Quota increases.

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

---

## Feature-to-Phase Mapping

| Feature Area | Phase(s) | Status |
|---|---|---|
| Architecture baseline (multi-tenant, ingestion, auth) | 0, 1 | ✅ |
| SDKs: OpenAI wrapper, LangChain, LangGraph, CLI | 2, 3 | ✅ |
| Billing-grade metering core | 4 | ✅ |
| Run Explorer + DAG Viewer UI | 5 | ✅ |
| Metering Dashboard (analytics pages + Recharts charts) | 6 | ✅ |
| Budgets + spend guardrails (Redis hot path) | 7 | ✅ |
| Chargeback engine + reconciliation + dispute trail | 8 | ✅ |
| Unit economics graph + change impact + annotations | 9 | ✅ |
| End-user analytics (cohorts, anomaly detection) + replay harness | 10 | ✅ |
| Tamper-evident ledger + tool registry + privacy governance | 11 | ✅ |
| Settings console: API keys, provider profiles, dark mode | 12 | ✅ |
| Integrations: Slack Block Kit alerts + CI gate + analytics export | 14 | ✅ |
| Anthropic SDK (Claude wrapper) | 15 | 🔲 |
| Production hardening (rate limiting, PII scrubbing, deployment) | 16 | ✅ |
| **Evaluations & Scores** — LLM-as-judge, human feedback, score analytics | **17** | ✅ |
| **Prompt Management** — versioned registry, variables, diff, per-version metrics | **18** | ✅ |
| **Sessions UI + Payload Viewer** — multi-turn grouping, inline prompt/completion display | **19** | ✅ |
| **TypeScript / Node.js SDK** — npm `@runledger/sdk`, OpenAI Node + Vercel AI SDK | **20** | 🔲 |
| **Advanced Alerting** — error rate / latency / quality threshold rules | **21A** | ✅ |
| **Model Gateway** — OpenAI-compatible proxy, smart routing, prompt caching | **21B** | ✅ |
| **Runs enhancements** — model/cost filters, CSV export, Ollama cost fix, API key UX | **21C** | ✅ |
| **SaaS Foundation** — self-service signup, Stripe subscriptions, quota enforcement | **22** | 🔲 |



# RunLedger — Roadmap Enhancements (Phases 17–22+)
**Keep Phases 0–16 as-is (already shipped).** This document enhances Phases **17–22** and adds **new phases** that strengthen long-term defensibility (3–5 years) and strategic-acquisition fit.

---

## Guiding Goal for Phases 17–22+
RunLedger becomes the **billing-grade System of Record + Enforcement Plane** for agent spend and quality across providers, models, tools, and business outcomes.

**North-star outcomes**
- **Invoice-grade correctness:** reconcile RunLedger ledger totals to provider invoices/exports.
- **Cost ↔ Quality ↔ Outcome loop:** optimize *cost per outcome* with quality gates.
- **Control plane:** budgets + policies + routing + caching enforce in the hot path.
- **Enterprise-grade governance:** retention, audit logs, approvals, RBAC, export.

---

## Phase 17 — Evaluations, Scores & Quality Signals (Enhanced)
### Goal
Turn “traces + spend” into “spend + quality + confidence”, enabling optimization and safe automation.

### What to ship
#### A) Scores v1 (you already planned) — make it “scores-as-a-first-class currency”
- Score types:
  - **Scalar**: 0–1 or 0–100 (relevance, faithfulness, correctness)
  - **Categorical**: {good, neutral, bad} or {-1,0,1}
  - **Boolean**: pass/fail (policy compliance, safety)
- Score scope:
  - Per **run**, per **span**, per **session**, and optionally per **end-user/day** rollups
- Score provenance:
  - `source`: human | llm_judge | rule | telemetry
  - `evidence`: optional references to spans/messages/chunks used to compute score
  - `confidence`: 0–1 or low/med/high
- Score governance:
  - soft-delete, immutable audit trail for score edits (see Audit Events in Phase 22+)

#### B) Evaluator framework v1 — extensible “judge runner”
- Evaluator types:
  - **LLM Judge**: calls a provider/model (cost tracked as ProviderCall)
  - **Rule-based**: regex, schema validation, JSON validity, tool-policy checks
  - **Python**: user-supplied sandboxed function (OSS only or paid feature)
- Judging modes:
  - **Single-run** evaluation
  - **Batch** evaluation (time window, feature_tag, deployment_version)
  - **Canary** evaluation (evaluate only 1% of runs)
- Judge prompt templates:
  - standardized judge envelopes (system prompt + rubric + scoring schema)
  - robust parsing with schema (JSON schema) + fallback heuristics
- Anti-gaming:
  - “judge drift detection”: monitor judge score distribution changes week-to-week
  - “judge reliability”: correlation between human & judge for sampled items

#### C) Score analytics surfaces
- Cost vs score (scatter, quartiles)
- Score trend over time (by model, version, feature)
- “Best bang for buck” ranking: highest score per $ or per 1k tokens
- “Score regressions” similar to your cost regressions:
  - flags if avg score drops > X% and run_count ≥ N

#### D) New tables (adds)
```sql
score_events (
  id UUID PK,
  workspace_id UUID,
  run_id UUID NULL,
  span_id UUID NULL,
  session_id TEXT NULL,
  end_user_id TEXT NULL,
  name TEXT NOT NULL,
  value NUMERIC(8,4) NOT NULL,
  label TEXT NULL,
  source TEXT NOT NULL,           -- human|llm|rule|telemetry
  evaluator_id UUID NULL,
  confidence NUMERIC(4,3) NULL,
  evidence JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ
);

score_rollups_daily (
  workspace_id UUID,
  day DATE,
  feature_tag TEXT NULL,
  model TEXT NULL,
  deployment_version TEXT NULL,
  score_name TEXT,
  avg_value NUMERIC(8,4),
  p50 NUMERIC(8,4),
  p90 NUMERIC(8,4),
  sample_count INT,
  PRIMARY KEY (workspace_id, day, score_name, feature_tag, model, deployment_version)
);
```

#### E) New API routes
- `POST /evaluations/scores` (run/span/session)
- `GET /evaluations/scores` (filters)
- `POST /evaluations/evaluators`
- `POST /evaluations/evaluators/{id}/run` (batch support)
- `GET /analytics/scores/summary`
- `GET /analytics/scores/regressions`

#### F) SDK additions (Python)
- `rl.score(run_id, name, value, label=None, comment=None, confidence=None, evidence=None)`
- `rl.evaluate(run_id, evaluator="relevance_v1")` (optional helper; calls API)
- LangChain/LangGraph hook: optional **auto-score** on chain completion

#### G) Tests
- Score CRUD, filters, scoping
- Judge task creates ProviderCall cost entry + Score entry
- Score regressions detection correctness
- Rollup idempotency

**Definition of done**
- Create evaluator → run batch → scores appear in Run Detail + Analytics overlays → score regressions alertable.

---

## Phase 18 — Prompt Management & Experimentation (Enhanced)
### Goal
Make `deployment_version` meaningful: connect versions to **prompt diffs**, **cost**, **quality**, and **outcomes**.

### What to ship
#### A) Prompt registry with environment promotion (planned) — make it “release-grade”
- Prompt objects:
  - `name`, `description`, `owner`, `tags`, `default_environment`
- Prompt versions:
  - version integer auto-increment
  - `content` template with variables
  - `schema` for variables (type, required, constraints)
  - `commit_message`, `author`
  - `created_at`
- Promotion pipeline:
  - staging → production with **approval workflow** (optional)
  - lock production edits (must go through staging promotion)
- Prompt rendering:
  - safe templating (no arbitrary code)
  - variable validation against schema
- Prompt diff viewer:
  - token diff + semantic diff option (LLM-generated summary of changes)
- Prompt “usage references”:
  - where used (feature_tag, app_id)
  - last used, run_count

#### B) Prompt-to-run linkage (critical)
- Add `prompt_ref` to events:
  - `prompt_name`, `prompt_version`, `environment`
- SDK support:
  - `transport.get_prompt(name, env, vars)` returns `(rendered, prompt_version)`
  - automatically sets `deployment_version` or separate `prompt_version` fields

#### C) Experimentation layer v1 (adds)
- Prompt experiments:
  - A/B test by end_user_id hash
  - Multi-variant allocation weights
  - Guardrails: max spend per variant, min score threshold
- Metrics:
  - cost/run, score, latency, tool-risk events, outcomes
- Rollout:
  - ramp from 1% → 10% → 50% → 100% (manual control)

#### D) New tables (adds)
```sql
prompt_experiments (
  id UUID PK,
  workspace_id UUID,
  name TEXT,
  prompt_name TEXT,
  environment TEXT,              -- production/staging/dev
  variants JSONB NOT NULL,       -- [{version, weight}]
  ramp_pct NUMERIC(5,2) DEFAULT 0,
  score_guardrail JSONB DEFAULT '{}',  -- {score_name, min_value}
  budget_guardrail_usd NUMERIC(12,4) NULL,
  status TEXT DEFAULT 'draft',   -- draft|running|paused|completed
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

#### E) API routes (add)
- Prompt CRUD + versions (planned)
- `POST /prompts/{name}/render` (server-side render with validation)
- `POST /prompts/experiments`
- `PUT /prompts/experiments/{id}` (ramp, pause, stop)
- `GET /prompts/experiments/{id}/metrics`

#### F) UI
- Prompt list + version history + diff + promote
- Experiment creation wizard:
  - variants selection
  - ramp control
  - guardrails control
  - metrics dashboard

#### G) Tests
- Promotion correctness
- Rendering validation
- Experiment allocation determinism (hash-based)
- Guardrails enforcement

**Definition of done**
- Prompt v1 → v2 diff visible; v2 promoted; A/B test running with score + spend guardrails.

---

## Phase 19 — Sessions, Payload Viewer & Data Governance (Enhanced)
### Goal
Sessions become first-class, and payload capture becomes governance-grade with retention, sampling, and access control.

### What to ship
#### A) Session model as a product surface
- Session list: cost, turns, duration, avg score, anomalies
- Session timeline: cost per turn, score per turn, tool risk per turn
- Session “state” panels:
  - summary of models used
  - retries/errors
  - caching hits (Phase 21/23)
- Session replay viewer (UI) using captured payloads if allowed

#### B) Payload viewer v1 (planned) — make it safe + controlled
- Payload tabs:
  - prompt/messages (system/user/assistant)
  - tool inputs/outputs
  - provider raw response (optional)
- Redaction:
  - apply existing scrubber
  - add structured redaction rules (regex library + allowlist keys)
- Access control:
  - payload view requires role `security_admin` or explicit permission
- Export:
  - export a single run/session as JSON with signatures (Phase 22+)

#### C) Data retention & deletion (adds)
- Workspace-level retention policies:
  - metadata retention: 90d/180d/365d
  - payload retention: 0d/7d/30d/90d
- “Right to delete”:
  - delete end_user_id data within a window
  - creates audit record + tombstone
- Storage:
  - keep payloads in Postgres JSONB initially
  - optional S3 blob store for payloads later (Phase 22+ or 23+)

#### D) New tables (adds)
```sql
retention_policies (
  workspace_id UUID PK,
  metadata_days INT DEFAULT 180,
  payload_days INT DEFAULT 0,
  updated_at TIMESTAMPTZ
);

deletion_requests (
  id UUID PK,
  workspace_id UUID,
  end_user_id TEXT,
  requested_by UUID NULL,
  status TEXT DEFAULT 'pending',   -- pending|running|completed|failed
  created_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ NULL,
  details JSONB DEFAULT '{}'
);
```

#### E) Workers
- `retention_sweeper` daily: purge expired payloads, then metadata if configured
- `deletion_worker`: hard delete payloads + soft delete metadata with tombstones

**Definition of done**
- Sessions UI ships; payload viewer respects privacy + RBAC; retention sweeps run daily.

---

## Phase 20 — TypeScript / Node SDK + Ecosystem Hooks (Enhanced)
### Goal
Win distribution via JS/TS ecosystems where most production LLM apps live.

### What to ship
#### A) SDK core (planned)
- `AsyncLocalStorage` context propagation
- OpenAI client instrumentation + streaming support
- Transport batching + retries + backpressure

#### B) Ecosystem hooks (adds)
- Vercel AI SDK middleware (planned)
- LangChain.js callbacks (add)
- Next.js route handler helpers:
  - `withRunLedger(req, handler)` auto-injects context from headers
- OpenTelemetry/OpenInference bridge:
  - accept spans from OTel exporters and translate into RunLedger spans/events
  - enables non-SDK adoption (critical for enterprise)

#### C) DX features
- `runledger init` (CLI): sets env vars, creates API key, prints sample code
- `runledger verify` parity in TS
- Typesafe event schemas mirrored from backend OpenAPI

#### D) Tests
- Streaming token aggregation tests
- ALS nesting behavior tests
- OTel bridge test: ingests synthetic span tree and produces run DAG

**Definition of done**
- `npm i @runledger/sdk` + one-line instrumentation + events appear with correct DAG and tokens.

---

## Phase 21 — Advanced Alerting + Model Gateway (Enhanced to “Control Plane”)
### Goal
Move from observability to **active enforcement**: routing, caching, fallbacks, quality gates, and cost guarantees.

### Part A: Advanced Alerting (enhanced)
#### Alert rule types
- Spend velocity (USD/min, USD/hour)
- Error rate, retry storms (already have runaway detection—formalize it)
- p95 latency
- Avg score drop (requires Phase 17)
- Cost per outcome spike (Phase 23)
- Tool-policy violations (Phase 11 tool registry)

#### Alert delivery
- Slack (done)
- Webhooks (done)
- Email (optional later)
- PagerDuty/Opsgenie (Phase 22+ integrations)

#### Dedup & suppression
- per-rule cooldown windows
- “maintenance windows” (mute alerts temporarily)
- “alert grouping” by feature_tag or app_id

---

### Part B: Model Gateway v1 (make it meaningfully better than generic proxies)
#### Gateway capabilities
1) **Routing policies**
- route by: requested model, feature_tag, tenant plan, environment
- priority + weighted load balancing
- fallback chains on 429/5xx/timeouts
- allowlist/denylist models per workspace

2) **Cost-aware + Quality-aware routing**
- choose cheapest route that meets:
  - min score threshold (Phase 17)
  - max latency target
  - tool-policy constraints
- “quality floor” per feature_tag: enforce baseline quality

3) **Caching**
- Exact-match prompt cache (planned)
- Normalized-message cache:
  - whitespace normalization
  - tool result stripping in cache key (optional)
- Cache governance:
  - per-workspace TTL
  - disable cache for sensitive routes
  - cache hit reporting + cost saved

4) **Shadow traffic / mirroring**
- Send 1% traffic to candidate model/prompt for evaluation only
- Store shadow results with cost estimate + score (Phase 17)
- No user-visible impact

5) **Budget enforcement in gateway**
- Hard block or downgrade before forwarding
- Guarantees: “never exceed $X/day for this feature”
- Logs enforcement decisions as security/audit events

#### New tables (adds)
```sql
gateway_policies (
  id UUID PK,
  workspace_id UUID,
  feature_tag TEXT NULL,
  environment TEXT DEFAULT 'production',
  min_score JSONB DEFAULT '{}',     -- {score_name: min_value}
  max_latency_ms INT NULL,
  max_cost_per_run_usd NUMERIC(12,4) NULL,
  allow_models JSONB DEFAULT '[]',
  deny_models JSONB DEFAULT '[]',
  updated_at TIMESTAMPTZ
);

gateway_shadow_runs (
  id UUID PK,
  workspace_id UUID,
  run_id UUID,
  candidate JSONB NOT NULL,         -- {provider, model, prompt_version?}
  status TEXT,
  estimated_cost_usd NUMERIC(12,4),
  scores JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ
);
```

#### API
- OpenAI-compatible endpoints (`/gateway/*`)
- Policy CRUD:
  - `GET/PUT /gateway/policies`
- Shadow controls:
  - `POST /gateway/shadow` (set sampling, candidates)
  - `GET /gateway/shadow/results`

#### Tests
- routing selection correctness
- fallback correctness
- cache hit behavior and cost saved accounting
- quality-aware routing chooses alternative when score floor violated
- shadow run creation + result storage

**Definition of done**
- RunLedger gateway enforces budgets + policies and demonstrates measurable cost savings via caching/routing.

---

## Phase 22 — SaaS Foundation (Enhanced to Enterprise-Ready SaaS)
### Goal
Self-serve SaaS that can sell to serious teams: subscription + quotas + RBAC + audit + exports.

### What to ship
#### A) Plans & quotas (planned) — add enforcement surfaces
- event ingestion quota (events/month)
- retention policy constraints by plan
- gateway features by plan (cache/shadow/quality routing)
- score/evaluator limits by plan (judge runs/day)

#### B) RBAC and permissions (adds, critical)
Roles:
- `owner`
- `admin`
- `billing_admin`
- `security_admin`
- `developer`
- `viewer`

Permission groups:
- view traces
- view payloads (restricted)
- manage budgets
- manage billing/chargeback
- manage evaluators/prompts
- manage gateway policies

Add:
```sql
roles (id, name UNIQUE, permissions JSONB);
workspace_user_roles (workspace_id, user_id, role_id);
```

#### C) Audit log / compliance-grade eventing (adds)
Every sensitive action emits an audit record:
- API key created/revoked
- pricing override changed
- budget created/changed/deleted
- prompt promoted
- retention policy changed
- payload viewed/exported
- deletion request executed
- gateway policy changes

```sql
audit_events (
  id UUID PK,
  workspace_id UUID,
  actor_user_id UUID NULL,
  actor_api_key_prefix TEXT NULL,
  action TEXT NOT NULL,
  target_type TEXT NULL,
  target_id TEXT NULL,
  before JSONB DEFAULT '{}',
  after JSONB DEFAULT '{}',
  ip_hash TEXT NULL,
  user_agent_hash TEXT NULL,
  created_at TIMESTAMPTZ
);
```

#### D) Billing integrations
- Stripe checkout + portal (planned)
- Invoice exports:
  - CSV (done)
  - Signed JSON (done)
  - **QuickBooks / Netsuite export format** (adds, optional)

#### E) Data export + warehouse connectors (adds, high stickiness)
- Scheduled export to S3 (daily usage snapshots)
- BigQuery/Snowflake via external stage (later)
- Webhook “usage.closed” event after billing period closes

#### F) Security hardening packaging
- SSO (SAML/OIDC) as enterprise plan feature
- SCIM provisioning (later)
- IP allowlisting for admin endpoints

**Definition of done**
- Customer can sign up, set roles, enforce quotas, export finance-ready statements, and show an audit trail.

---

# New Phases (Defensibility Boosters)

## Phase 23 — Provider Invoice Reconciliation (Flagship Moat)
### Goal
Make RunLedger “invoice-grade”: reconcile against provider usage exports and explain deltas.

### What to ship
#### A) Import pipelines
- Upload provider usage CSV/JSON exports (OpenAI, Anthropic, Google)
- Parse into normalized `provider_invoice_lines`

```sql
provider_invoices (
  id UUID PK,
  workspace_id UUID,
  provider TEXT,
  period_start DATE,
  period_end DATE,
  currency TEXT DEFAULT 'USD',
  total_amount NUMERIC(14,4),
  status TEXT DEFAULT 'imported', -- imported|reconciled|flagged
  created_at TIMESTAMPTZ
);

provider_invoice_lines (
  id UUID PK,
  invoice_id UUID,
  provider_request_id TEXT NULL,
  model TEXT NULL,
  input_tokens BIGINT NULL,
  output_tokens BIGINT NULL,
  amount NUMERIC(14,6) NOT NULL,
  occurred_at TIMESTAMPTZ NULL,
  raw JSONB DEFAULT '{}'
);
```

#### B) Reconciliation engine
- Match invoice lines to RunLedger `provider_calls`:
  - exact match via provider request id where available
  - fuzzy match on timestamp/model/token ranges when not
- Output:
  - matched %, unmatched totals, rounding deltas, token mismatch buckets
- “Dispute trail”:
  - mark invoice lines as disputed
  - attach notes + evidence links to runs/spans

#### C) UI
- Invoice list + reconciliation summary
- Drill-down into unmatched lines and why
- “Export dispute package” (signed JSON) for finance

**Definition of done**
- Import invoice export → RunLedger reconciles ≥ X% and explains remainder with drilldown.

---

## Phase 24 — Outcome & ROI Ledger (Cost Per Outcome)
### Goal
Move beyond tokens: measure and optimize **cost per business outcome**.

### What to ship
#### A) Outcome taxonomy
- Outcomes emitted via SDK or API:
  - `ticket_resolved`, `lead_qualified`, `bug_fixed`, `refund_issued`, etc.
- Outcome value:
  - optional revenue impact or business value score
- Link outcomes to run_id/session_id/end_user_id

```sql
outcomes (
  id UUID PK,
  workspace_id UUID,
  run_id UUID NULL,
  session_id TEXT NULL,
  end_user_id TEXT NULL,
  outcome_type TEXT,
  success BOOL,
  value_usd NUMERIC(14,4) NULL,
  labels JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ
);

outcome_rollups_daily (
  workspace_id UUID,
  day DATE,
  outcome_type TEXT,
  success_rate NUMERIC(6,4),
  count INT,
  total_cost_usd NUMERIC(14,6),
  cost_per_success_usd NUMERIC(14,6),
  total_value_usd NUMERIC(14,4) NULL,
  roi NUMERIC(10,4) NULL
);
```

#### B) Analytics
- Cost per outcome over time
- ROI trend and “most profitable workflows”
- Quality ↔ outcome correlation

#### C) Alerts
- “Cost per success” spike alerts
- “Success rate drop” alerts

**Definition of done**
- Customer can instrument outcomes and see cost/success/ROI per workflow.

---

## Phase 25 — Approvals & Policy Workflows (Enterprise Stickiness)
### Goal
Bring governance into control plane: approvals for sensitive actions and tool access.

### What to ship
- Approval-required actions:
  - raise budget limits
  - promote prompt to production
  - allow privileged tool
  - enable FULL payload capture
  - enable shadow routing to external provider
- Workflow:
  - request → approve/deny → audit record
  - Slack approvals (interactive buttons later)

```sql
approvals (
  id UUID PK,
  workspace_id UUID,
  request_type TEXT,
  request JSONB,
  status TEXT DEFAULT 'pending',
  requested_by UUID,
  decided_by UUID NULL,
  decided_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ
);
```

**Definition of done**
- Sensitive changes require approvals; audit trail is complete.

---

# Phase Sequencing Recommendation (Founder-Friendly)
1) **17 (Enhanced)** scores + judge runner + score analytics  
2) **18 (Enhanced)** prompt registry + promotion + experiments  
3) **21 (Enhanced)** gateway with quality-aware routing + caching + shadow  
4) **23** invoice reconciliation (moat + finance buyer)  
5) **22 (Enhanced)** SaaS + RBAC + audit + exports (commercial readiness)  
6) **24** outcomes & ROI (exec relevance)  
7) **25** approvals workflows (enterprise stickiness)

---

## Defensibility Checklist (What this buys you)
- **System of record:** signed ledger snapshots + invoice reconciliation
- **Control plane:** budgets + gateway enforcement + policy engine
- **Optimization loop:** scores + prompts + experiments + shadow routing
- **Business relevance:** outcomes + ROI, not just traces
- **Enterprise readiness:** RBAC + audit logs + retention + approvals + exports

---

## “Definition of Winning” (3–5 year north-star)
RunLedger is the default:
- for **finance**: internal chargeback + reconciled invoices + audit trails  
- for **platform**: centralized gateway + policy enforcement + safe routing  
- for **AI teams**: prompt + eval + cost/quality/outcome optimization loop


