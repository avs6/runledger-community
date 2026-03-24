# RunLedger — Implementation Roadmap

6-month plan for a solo founder building a production-grade Agent FinOps Control Plane.

---

## Guiding Principles

- **Async instrumentation first** — lowest friction. Optional inline gateway later.
- **Billing-grade correctness over pretty dashboards** — accuracy is the product.
- **Privacy-first by default** — payload logging is always opt-in, never default.
- **End-user analytics is first-class** — not an afterthought on a per-tenant view.
- **Auditability built into the architecture** — tamper-evidence, provenance, and policies from day one.
- **Finance moat over feature breadth** — reconciliation, chargeback, budget enforcement, routing, and outcome visibility are defensible; generic observability is not.
- **OTLP as an adoption path, not a replacement** — normalize into the RunLedger domain model; keep the SDK as the richer, finance-native path.

---

## Current Build Status

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
| 15 | Anthropic SDK | ✅ Complete | 8 |
| 16 | Production Hardening + UI Polish | ✅ Complete | 13 |
| 17 | Evaluations & Scores | ✅ Complete | 13 |
| 17B | Evaluator Framework (LLM judge, rule-based, batch eval, drift) | ✅ Complete | 17 |
| 18 | Prompt Management | ✅ Complete | 12 |
| 19 | Sessions UI + Payload Viewer | ✅ Complete | 8 |
| 20 | TypeScript / Node.js SDK | ✅ Complete | 9 |
| 21A | Advanced Alerting | ✅ Complete | 9 |
| 21B | Model Gateway | ✅ Complete | 14 |
| 21C | Runs Enhancements (model/cost filters, CSV export, Ollama fix, API key UX) | ✅ Complete | — |
| 21D | Unified Policy Checks (budgets + tools + gateway + eval gate) | ✅ Complete | 6 |
| 21E | Gateway Provider Expansion — Azure OpenAI, AWS Bedrock, Vertex AI | ✅ Complete | 17 |
| 22 | SaaS Foundation (signup, Stripe billing, quota enforcement, RBAC) | ✅ Complete | — |
| 23 | Provider Invoice Reconciliation | ✅ Complete | 28 |
| 24 | Outcome & ROI Ledger | ✅ Complete | 20 |
| 25 | Approvals & Policy Workflows | ✅ Complete | 19 |
| 26 | Email Notification System (alerts, budget breach, billing close, dispute, weekly report) | ✅ Complete | 13 |
| 27 | Data Retention & Deletion Policy APIs | ✅ Complete | 21 |
| 28 | Warehouse Export — S3/GCS/R2 daily exports (JSONL + Parquet) | ✅ Complete | 22 |
| OTEL-0 | OTLP Ingestion — Schema Foundation + Receiver | ✅ Complete | 37 |
| OTEL-1 | OTLP — Run-context Extraction + Payload Capture + Management API + Settings UI | ✅ Complete | 13 |
| OTEL-2 | OTLP — OTel GenAI Support + Retrieval Metadata + Convention Tracking | ✅ Complete | — |
| OTEL-3 | OTLP — Trace Finalization + Source-Provenance Propagation | ✅ Complete | 8 |
| OTEL-4 | OTLP — Reconciliation-grade Enrichment (provider_request_id, reported_cost_usd, token details) | ✅ Complete | 23 |

**Total tests shipped:** 520 API tests · 61 Python SDK tests · 9 TypeScript SDK tests

**Audit snapshot (2026-03-23):**
- API suite: `520/520` passing
- Python SDK suite: `61/61` passing
- TypeScript SDK suite: `9/9` passing (vitest)
- Web lint: clean (`next lint`)
- Repo lint: clean (`ruff check .` + `ruff format --check .`)
- Core API typing: clean (`mypy apps/api/runledger_api packages/sdk/runledger_sdk`)

---

## Recommended Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.13 | Async-native; LangChain/LangGraph ecosystem |
| API framework | FastAPI | Async, OpenAPI auto-docs, fastest iteration velocity |
| Primary database | PostgreSQL 16 | Transactional + analytics via partitioned tables + materialized views |
| Queue / cache | Redis 7 (Streams) | Budget enforcement hot path, event buffering, idempotency keys |
| Async workers | Celery + Redis broker | Event pipeline, aggregation rollups, reconciliation jobs |
| SDK (Python) | `runledger-sdk` (PyPI) | OpenAI + Anthropic + LangChain + LangGraph wrappers |
| SDK (TypeScript) | `@runledger/sdk` | OpenAI + Gemini + Mistral + Cohere; AsyncLocalStorage context |
| Frontend | Next.js 14 (App Router, TypeScript) | shadcn/ui components, Recharts for dashboards |
| UI auth | NextAuth.js v4 (credentials + API key) | Session auth for dashboard, JWT for API |
| DB migrations | Alembic | Standard for FastAPI/SQLAlchemy projects |
| Package manager | uv (workspaces) | Fastest Python tooling |
| Deploy (prod) | Railway (Postgres + Redis + containers) | Managed ops, solo-friendly |
| Deploy (local) | Docker Compose | Single `docker compose up` for full stack |

**Why PostgreSQL only (no ClickHouse, no TimescaleDB):**
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
│   │   │   ├── routers/        # FastAPI routers
│   │   │   ├── services/       # Business logic (metering, pricing, chargeback, guardrails, OTLP)
│   │   │   ├── workers/        # Celery tasks (pipeline, rollups, reconciliation, OTLP finalize)
│   │   │   └── main.py         # FastAPI app entrypoint
│   │   ├── alembic/            # Alembic migrations (001 – 027)
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── web/                    # Next.js 14 frontend
│       ├── app/                # App Router pages
│       ├── components/         # Shared UI components
│       ├── lib/                # API client, auth config, utils
│       └── package.json
├── packages/
│   ├── sdk/                    # runledger-sdk (Python, published to PyPI)
│   │   └── runledger_sdk/
│   │       ├── client.py       # RunLedger client + instrument()
│   │       ├── context.py      # contextvars-based context propagation
│   │       ├── openai.py       # OpenAI wrapper
│   │       ├── anthropic.py    # Anthropic Claude wrapper
│   │       ├── langchain.py    # LangChain CallbackHandler
│   │       ├── langgraph.py    # LangGraph node hooks
│   │       ├── gemini.py       # Google Gemini wrapper
│   │       ├── mistral.py      # Mistral wrapper
│   │       ├── cohere.py       # Cohere wrapper
│   │       ├── mcp.py          # MCP tool hooks
│   │       ├── tool_check.py   # Tool registry policy check
│   │       ├── transport.py    # Async HTTP client (batching + retry)
│   │       └── cli.py          # runledger CLI
│   └── ts-sdk/                 # @runledger/sdk (TypeScript)
│       └── src/
│           ├── client.ts       # RunLedger class
│           ├── openai.ts       # OpenAI instrumentation
│           ├── gemini.ts       # Gemini instrumentation
│           ├── mistral.ts      # Mistral instrumentation
│           ├── cohere.ts       # Cohere instrumentation
│           ├── context.ts      # AsyncLocalStorage context
│           ├── transport.ts    # Batch + retry transport
│           └── types.ts        # Shared type definitions
├── examples/                   # 22 runnable example scripts (Python + TypeScript)
├── docs/                       # otlp.md, openinference.md, collector.md, deployment.md
├── infra/
│   ├── docker-compose.yml      # Full local stack (+ otel profile)
│   └── otel-collector-config.yaml  # OTel Collector config forwarding to RunLedger
├── pyproject.toml              # uv workspace root
├── CLAUDE.md
├── IMPLEMENTATION.md           # This file
└── README.md
```

---

## Database Schema

### Tenant & Auth

```sql
tenants          (id, slug, name, plan ENUM, owner_user_id UUID, is_default BOOL, created_at)
workspaces       (id, tenant_id, name, created_at)
applications     (id, workspace_id, name, environment ENUM[dev|staging|prod])
api_keys         (id, workspace_id, key_hash, key_prefix, scopes[], last_used_at, expires_at,
                  is_session BOOL, created_by UUID)
users            (id, email, email_hash, full_name, is_active BOOL, is_platform_admin BOOL,
                  last_login_at, created_at)
tenant_users     (id, tenant_id, user_id, role ENUM[owner|admin|member|viewer], created_at)
workspace_users  (id, workspace_id, user_id, role ENUM[admin|billing_admin|member|viewer])
```

### Instrumentation Events

```sql
agent_runs       (id UUID, workspace_id, application_id, end_user_id, session_id,
                  feature_tag, status ENUM, started_at, ended_at,
                  total_cost_usd NUMERIC, total_input_tokens BIGINT,
                  total_output_tokens BIGINT, deployment_version, metadata JSONB,
                  -- OTLP source provenance:
                  source_type TEXT,           -- 'runledger_sdk' | 'otlp' | 'openinference'
                  external_trace_id TEXT,
                  external_trace_state TEXT,
                  resource_attributes JSONB)

spans            (id UUID, run_id, parent_span_id, span_type ENUM[chain|llm|tool|agent|retrieval],
                  name, started_at, ended_at, status ENUM, cost_usd NUMERIC, metadata JSONB,
                  -- OTLP source provenance:
                  external_span_id TEXT,
                  external_parent_span_id TEXT,
                  trace_flags TEXT,
                  instrumentation_scope_name TEXT,
                  instrumentation_scope_version TEXT,
                  source_span_kind TEXT,
                  source_attributes JSONB)

provider_calls   (id UUID, span_id, run_id, workspace_id, end_user_id,
                  provider, model, input_tokens INT, output_tokens INT,
                  cached_input_tokens INT, latency_ms INT, cost_usd NUMERIC,
                  status ENUM, error_type, created_at,
                  -- Reconciliation-grade fields:
                  provider_request_id TEXT,   -- from response header/body; used for invoice matching
                  reported_cost_usd NUMERIC,  -- cost as emitted by upstream (OpenInference llm.cost.total)
                  cost_source TEXT,           -- 'reported' | 'pricing_engine' | 'invoice_reconciled'
                  model_provider TEXT,        -- hosting provider if different (e.g. Azure-hosted OpenAI)
                  input_tokens_details JSONB, -- cached/audio/reasoning token breakdown
                  output_tokens_details JSONB)
                  -- PARTITIONED BY RANGE (created_at) — monthly partitions

tool_calls       (id UUID, span_id, run_id, workspace_id,
                  tool_name, tool_type ENUM[read|write|privileged],
                  risk_score SMALLINT, duration_ms INT, status ENUM, created_at,
                  external_span_id TEXT,
                  tool_arguments JSONB,
                  tool_result_summary JSONB)

outcome_events   (id UUID, run_id, event_type, success BOOL,
                  labels JSONB, created_at)
```

### Metering

```sql
provider_pricing (id, provider, model, input_cost_per_1m NUMERIC,
                  output_cost_per_1m NUMERIC, cached_input_cost_per_1m NUMERIC,
                  effective_from TIMESTAMPTZ, effective_to TIMESTAMPTZ,
                  workspace_id UUID NULL)   -- NULL = global; non-null = workspace override

usage_hourly     (workspace_id, application_id, end_user_id, model, feature_tag,
                  hour TIMESTAMPTZ, input_tokens BIGINT, output_tokens BIGINT,
                  cost_usd NUMERIC, run_count INT, call_count INT)

usage_daily      (same columns, day DATE)

data_quality_issues (id, provider_call_id, workspace_id, issue_type, detail, created_at)
```

### Budgets & Guardrails

```sql
budgets          (id, workspace_id, scope_type ENUM[workspace|app|end_user|feature_tag],
                  scope_id TEXT, period_type ENUM[daily|monthly|total],
                  limit_usd NUMERIC, action ENUM[notify|throttle|block|downgrade],
                  downgrade_to_model TEXT, is_active BOOL, created_at)

budget_breaches  (id, budget_id, occurred_at, spend_at_breach_usd, action_taken, notified_at)

budget_notifications (id, workspace_id, channel ENUM[webhook|slack],
                      destination_url, events[], is_active, created_at)
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

### Analytics & Annotations

```sql
annotations      (id UUID, workspace_id UUID, note TEXT, annotation_date DATE,
                  version TEXT NULL, created_at TIMESTAMPTZ)
```

### Replay (Phase 10)

```sql
user_anomalies   (id UUID, workspace_id UUID, end_user_id TEXT, detected_at DATE,
                  daily_spend NUMERIC, mean_spend NUMERIC, zscore NUMERIC,
                  reason TEXT, created_at TIMESTAMPTZ)

replay_datasets  (id UUID, workspace_id UUID, name TEXT, source TEXT,
                  run_ids JSONB, created_at TIMESTAMPTZ)

replay_experiments (id UUID, workspace_id UUID, dataset_id UUID, name TEXT,
                    configs JSONB, status TEXT, results JSONB NULL,
                    estimated_cost_usd NUMERIC NULL, created_at TIMESTAMPTZ)
```

### Ledger & Security & Privacy (Phase 11)

```sql
ledger_keys      (id UUID, workspace_id UUID, key_value TEXT, active BOOL,
                  expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ)

ledger_snapshots (id UUID, workspace_id UUID, snapshot_date DATE,
                  total_cost_usd NUMERIC, model_breakdown JSONB, call_count INT,
                  hash TEXT, key_id UUID, created_at TIMESTAMPTZ)

tool_registry    (id UUID, workspace_id UUID, tool_name TEXT,
                  policy TEXT DEFAULT 'audit',  -- 'allow' | 'audit' | 'block'
                  description TEXT NULL, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)

security_events  (id UUID, workspace_id UUID, event_type TEXT, tool_name TEXT NULL,
                  end_user_id TEXT NULL, run_id UUID NULL, details JSONB,
                  detected_at TIMESTAMPTZ, created_at TIMESTAMPTZ)

capture_policies (id UUID, workspace_id UUID UNIQUE, privacy_mode TEXT DEFAULT 'METADATA_ONLY',
                  sampled_rate NUMERIC NULL, updated_at TIMESTAMPTZ, created_at TIMESTAMPTZ)
```

### Evaluations & Scores (Phase 17)

```sql
score_events     (id UUID, workspace_id UUID, run_id UUID NULL, span_id UUID NULL,
                  session_id TEXT NULL, end_user_id TEXT NULL,
                  name TEXT, value NUMERIC(8,4), label TEXT NULL,
                  source TEXT DEFAULT 'human',  -- 'human' | 'llm' | 'rule' | 'telemetry'
                  confidence NUMERIC(4,3) NULL, evidence JSONB NULL, created_at TIMESTAMPTZ)

score_rollups_daily (workspace_id UUID, day DATE, score_name TEXT, feature_tag TEXT,
                     model TEXT, deployment_version TEXT,
                     avg_value NUMERIC, p50 NUMERIC, p90 NUMERIC, sample_count INT,
                     PRIMARY KEY (workspace_id, day, score_name, feature_tag, model, deployment_version))

evaluators       (id UUID, workspace_id UUID, name TEXT, type TEXT,
                  config JSONB, created_at TIMESTAMPTZ)  -- Phase 17B
```

### Prompt Management (Phase 18)

```sql
prompts          (id UUID, workspace_id UUID, name TEXT UNIQUE per workspace,
                  description TEXT NULL, default_environment TEXT DEFAULT 'production',
                  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)

prompt_versions  (id UUID, prompt_id UUID, version INT,
                  content TEXT, variables JSONB DEFAULT '[]',
                  commit_message TEXT NULL, environment TEXT DEFAULT 'production',
                  model_hint TEXT NULL, created_at TIMESTAMPTZ)
```

### Sessions (Phase 19 — no new tables)

Session-level analytics are virtual aggregations (`GROUP BY session_id`). The `session_id` column already exists on `agent_runs`. Index added: `(workspace_id, session_id, started_at) WHERE session_id IS NOT NULL`.

### Model Gateway (Phase 21B)

```sql
gateway_routes   (id UUID, workspace_id UUID, name TEXT, provider TEXT, model TEXT,
                  fallback_model TEXT NULL, priority INT DEFAULT 0,
                  weight NUMERIC DEFAULT 1.0, is_active BOOL, created_at TIMESTAMPTZ)

gateway_requests (id UUID, workspace_id UUID, route_id UUID NULL, run_id UUID NULL,
                  provider TEXT, model TEXT, fallback_used BOOL, cache_hit BOOL,
                  latency_ms INT, cost_usd NUMERIC, status TEXT,
                  decision_reason TEXT NULL, created_at TIMESTAMPTZ)
                  -- PARTITIONED BY RANGE (created_at)

prompt_cache     (id UUID, workspace_id UUID, cache_key TEXT UNIQUE per workspace,
                  response JSONB, input_tokens INT, output_tokens INT,
                  model TEXT, provider TEXT, hit_count INT DEFAULT 0,
                  expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ)

routing_policies (id UUID, workspace_id UUID, name TEXT, strategy TEXT,
                  config JSONB DEFAULT '{}', is_active BOOL, created_at TIMESTAMPTZ)
```

### SaaS Foundation (Phase 22)

```sql
plans            (id UUID, name TEXT UNIQUE,  -- 'free' | 'starter' | 'growth' | 'enterprise'
                  monthly_price_usd NUMERIC, event_quota_monthly BIGINT NULL,
                  seat_quota INT, features JSONB DEFAULT '{}', created_at TIMESTAMPTZ)

subscriptions    (id UUID, tenant_id UUID, plan_id UUID,
                  stripe_subscription_id TEXT NULL, stripe_customer_id TEXT NULL,
                  status TEXT DEFAULT 'active', current_period_start DATE,
                  current_period_end DATE, cancel_at DATE NULL,
                  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)

usage_quotas     (id UUID, workspace_id UUID, period_start DATE, period_end DATE,
                  events_used BIGINT DEFAULT 0, seats_used INT DEFAULT 0, updated_at TIMESTAMPTZ)
```

### Provider Invoice Reconciliation (Phase 23)

```sql
provider_invoices (id UUID, workspace_id UUID, provider TEXT,
                   period_start DATE, period_end DATE, currency TEXT DEFAULT 'USD',
                   total_amount NUMERIC(14,4), status TEXT DEFAULT 'imported',
                   created_at TIMESTAMPTZ)

provider_invoice_lines (id UUID, invoice_id UUID, provider_request_id TEXT NULL,
                        model TEXT NULL, input_tokens BIGINT NULL,
                        output_tokens BIGINT NULL, amount NUMERIC(14,6),
                        occurred_at TIMESTAMPTZ NULL, raw JSONB DEFAULT '{}')
```

### Outcomes & ROI (Phase 24)

```sql
outcomes         (id UUID, workspace_id UUID, run_id UUID NULL, session_id TEXT NULL,
                  end_user_id TEXT NULL, feature_tag TEXT NULL,
                  outcome_type TEXT, success BOOL, value_usd NUMERIC NULL,
                  labels JSONB DEFAULT '{}', created_at TIMESTAMPTZ)

outcome_rollups_daily (workspace_id UUID, day DATE, feature_tag TEXT,
                       outcome_type TEXT, total_outcomes INT, successful_outcomes INT,
                       total_value_usd NUMERIC, total_cost_usd NUMERIC,
                       avg_cost_per_outcome NUMERIC, PRIMARY KEY (workspace_id, day, feature_tag, outcome_type))
```

### Approvals (Phase 25)

```sql
approvals        (id UUID, workspace_id UUID, requested_by UUID NULL,
                  action_type TEXT,  -- 'prompt_promote' | 'budget_increase' | etc.
                  subject_id TEXT, subject_type TEXT,
                  status TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'denied' | 'cancelled'
                  approver_id UUID NULL, decided_at TIMESTAMPTZ NULL,
                  notes TEXT NULL, created_at TIMESTAMPTZ)
```

### OTLP Staging (OTEL-0)

```sql
otlp_ingest_batches (id UUID, workspace_id UUID, received_at TIMESTAMPTZ,
                      content_type TEXT, encoding TEXT, trace_count INT, span_count INT,
                      status TEXT, error TEXT NULL, raw_payload BYTEA NULL)

otlp_spans_raw   (id UUID, workspace_id UUID, batch_id UUID,
                  external_trace_id TEXT, external_span_id TEXT,
                  external_parent_span_id TEXT NULL, span_name TEXT,
                  start_time TIMESTAMPTZ, end_time TIMESTAMPTZ NULL,
                  status_code TEXT NULL, resource_attributes JSONB,
                  scope_attributes JSONB, span_attributes JSONB,
                  events JSONB, links JSONB, normalized BOOL DEFAULT FALSE)
```

---

## API Routes

### Auth & Workspace

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/workspaces` | Create workspace |
| POST | `/auth/api-keys` | Create API key |
| GET | `/auth/api-keys` | List API keys |
| DELETE | `/auth/api-keys/{id}` | Revoke API key |
| POST | `/auth/login` | Login (returns JWT + session API key) |
| POST | `/auth/signup` | Self-service signup (SaaS) |

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest/v1/events` | Ingest single event |
| POST | `/ingest/v1/batch` | Ingest event batch |

### OTLP

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/traces` | OTLP/HTTP trace ingestion |
| POST | `/otlp/v1/traces` | Alias for collectors that prefix `/otlp` |
| GET | `/v1/traces/stats` | OTLP ingestion stats (24h, 7d) |
| GET | `/v1/traces/batches` | List ingestion batches |
| GET | `/v1/traces/batches/{id}` | Single batch details |

### Runs & Spans

| Method | Path | Description |
|--------|------|-------------|
| GET | `/runs` | List runs (filters: status, model, cost range, time, feature, user) |
| GET | `/runs/{id}` | Run detail (includes payload when captured) |
| GET | `/runs/{id}/graph` | DAG structure (nodes + edges) |
| GET | `/runs/export` | CSV export |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics/summary` | Total cost/tokens/runs + period delta |
| GET | `/analytics/spend-over-time` | Time-series (hourly/daily) |
| GET | `/analytics/spend-by-model` | Cost breakdown by model |
| GET | `/analytics/spend-by-user` | Top spenders |
| GET | `/analytics/spend-by-feature` | Cost by feature_tag |
| GET | `/analytics/users/{id}` | User spend profile |
| GET | `/analytics/users/cohorts` | Spend-tier cohorts |
| GET | `/analytics/users/anomalies` | Anomalous users |
| GET | `/analytics/economics/{run_id}` | Unit economics for a run |
| GET | `/analytics/workflows/top` | Top workflows by cost |
| GET | `/analytics/compare` | Before/after version comparison |
| GET | `/analytics/regressions` | Cost regressions (>20% increase) |
| GET | `/analytics/annotations` | List annotations |
| POST | `/analytics/annotations` | Create annotation |
| GET | `/analytics/scores/summary` | Score averages + period delta |
| GET | `/analytics/scores/regressions` | Score regressions |
| GET | `/analytics/export` | Bulk CSV/JSON export of usage_daily |

### Budgets

| Method | Path | Description |
|--------|------|-------------|
| POST | `/budgets` | Create budget |
| GET | `/budgets` | List budgets (with live Redis spend) |
| GET | `/budgets/check` | Hot-path check (<5ms p99) |
| GET | `/budgets/{id}/breaches` | Breach history |
| DELETE | `/budgets/{id}` | Soft-delete budget |
| POST | `/budgets/notifications` | Create notification channel |
| GET | `/budgets/notifications` | List notification channels |

### Billing & Chargeback

| Method | Path | Description |
|--------|------|-------------|
| POST | `/billing/periods` | Create billing period |
| GET | `/billing/periods` | List periods |
| GET | `/billing/periods/{id}` | Period detail |
| POST | `/billing/periods/{id}/close` | Close + sign snapshot |
| GET | `/billing/periods/{id}/reconciliation` | Internal reconciliation |
| GET | `/billing/periods/{id}/breakdown` | Chargeback breakdown |
| GET | `/billing/periods/{id}/export` | CSV or signed JSON export |
| POST | `/billing/chargeback-rules` | Create chargeback rule |
| GET | `/billing/chargeback-rules` | List rules |
| GET | `/billing/subscription` | Current plan + usage (SaaS) |
| POST | `/billing/checkout` | Stripe checkout session |
| POST | `/billing/portal` | Stripe customer portal |
| POST | `/webhooks/stripe` | Stripe webhook handler |

### Provider Invoice Reconciliation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/invoices` | Import provider invoice |
| GET | `/invoices` | List invoices |
| GET | `/invoices/{id}` | Invoice detail |
| POST | `/invoices/{id}/reconcile` | Run reconciliation |
| GET | `/invoices/{id}/reconciliation` | Reconciliation report |

### Evaluations & Scores

| Method | Path | Description |
|--------|------|-------------|
| POST | `/evaluations/scores` | Submit quality score |
| GET | `/evaluations/scores` | List scores |

### Prompts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/prompts` | Create prompt |
| GET | `/prompts` | List prompts |
| GET | `/prompts/{name}` | Get prompt |
| DELETE | `/prompts/{name}` | Delete prompt |
| POST | `/prompts/{name}/versions` | Commit new version |
| GET | `/prompts/{name}/versions` | List versions |
| GET | `/prompts/{name}/latest` | Latest version (SDK pull endpoint) |
| GET | `/prompts/{name}/versions/{v}` | Specific version |
| POST | `/prompts/{name}/promote` | Promote staging → production (requires approval) |
| GET | `/prompts/{name}/metrics` | Per-version cost + score metrics |

### Approvals

| Method | Path | Description |
|--------|------|-------------|
| POST | `/approvals` | Create approval request |
| GET | `/approvals` | List approval requests |
| GET | `/approvals/summary` | Status counts |
| GET | `/approvals/{id}` | Single approval |
| PUT | `/approvals/{id}/approve` | Approve |
| PUT | `/approvals/{id}/deny` | Deny |
| DELETE | `/approvals/{id}` | Cancel |

### Outcomes & ROI

| Method | Path | Description |
|--------|------|-------------|
| POST | `/outcomes` | Record an outcome |
| GET | `/outcomes` | List outcomes |
| GET | `/outcomes/summary` | Summary KPIs |
| GET | `/outcomes/trend` | Daily trend |
| GET | `/outcomes/workflows` | Workflow ROI table |
| GET | `/outcomes/quality-correlation` | Score-to-outcome correlation |

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions` | List sessions |
| GET | `/sessions/{id}` | Session detail + run timeline |
| GET | `/sessions/{id}/cost-over-turns` | Cost per turn number |

### Ledger & Privacy & Tools

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ledger/snapshots` | List ledger snapshots |
| POST | `/ledger/snapshots/generate` | Generate signed snapshot |
| GET | `/ledger/verify/{date}` | Verify snapshot integrity |
| GET | `/tools/registry` | List tool registry |
| POST | `/tools/registry` | Register tool policy |
| PUT | `/tools/registry/{id}` | Update tool policy |
| DELETE | `/tools/registry/{id}` | Remove tool entry |
| GET | `/tools/security-events` | List security events |
| GET | `/privacy/capture-policy` | Get workspace capture policy |
| PUT | `/privacy/capture-policy` | Set workspace capture policy |

### Model Gateway

| Method | Path | Description |
|--------|------|-------------|
| POST | `/gateway/chat/completions` | OpenAI-compatible completions (streaming supported) |
| POST | `/gateway/routes` | Create route |
| GET | `/gateway/routes` | List routes |
| PUT | `/gateway/routes/{id}` | Update route |
| DELETE | `/gateway/routes/{id}` | Delete route |
| GET | `/gateway/stats` | Cache hit rates + cost saved |
| GET | `/gateway/requests` | Request routing log |
| POST | `/gateway/policies` | Create routing policy |
| GET | `/gateway/policies` | List routing policies |
| PUT | `/gateway/policies/{id}` | Update routing policy |
| DELETE | `/gateway/policies/{id}` | Delete routing policy |

### Replay

| Method | Path | Description |
|--------|------|-------------|
| POST | `/replay/datasets` | Create dataset |
| GET | `/replay/datasets` | List datasets |
| GET | `/replay/datasets/{id}` | Dataset detail |
| POST | `/replay/experiments` | Create experiment |
| GET | `/replay/experiments` | List experiments |
| POST | `/replay/experiments/{id}/run` | Run experiment (Celery) |
| GET | `/replay/experiments/{id}/results` | Results + Δ% projections |

### Settings & Providers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/settings/api-keys` | List API keys |
| POST | `/settings/api-keys` | Create API key |
| DELETE | `/settings/api-keys/{id}` | Revoke API key |
| GET | `/providers/pricing` | List provider pricing |
| POST | `/providers/pricing` | Create pricing override |
| DELETE | `/providers/pricing/{id}` | Delete pricing override |
| POST | `/providers/reprice` | Reset and re-enrich costs |

### Integrations & Alerts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/integrations/slack/test` | Send Slack test message |
| POST | `/alerts/rules` | Create alert rule |
| GET | `/alerts/rules` | List alert rules |
| PUT | `/alerts/rules/{id}` | Update/toggle rule |
| DELETE | `/alerts/rules/{id}` | Delete rule |
| GET | `/alerts/history` | Firing history |

### Org & Platform Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/org/profile` | Tenant profile |
| PUT | `/org/profile` | Update tenant profile |
| GET | `/org/workspaces` | List workspaces |
| POST | `/org/workspaces` | Create workspace |
| DELETE | `/org/workspaces/{id}` | Delete workspace |
| GET | `/org/members` | List org members |
| POST | `/org/members/invite` | Invite member |
| PUT | `/org/members/{id}/role` | Update member role |
| DELETE | `/org/members/{id}/role` | Remove member |
| GET | `/users/me` | Current user profile |
| PUT | `/users/me` | Update user profile |
| GET | `/platform/stats` | Platform-wide stats (admin only) |
| GET | `/platform/tenants` | List tenants (admin only) |
| POST | `/platform/tenants` | Create tenant (admin only) |
| GET | `/platform/users` | List all users (admin only) |
| POST | `/admin/bootstrap` | One-time admin + default tenant setup |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Combined health (DB + Redis status) |
| GET | `/health/live` | Liveness probe — always 200 |
| GET | `/health/ready` | Readiness probe — 503 if DB or Redis down |

---

## OTLP / OpenTelemetry Architecture

RunLedger supports three adoption modes:

1. **RunLedger SDK** → `/ingest/v1/events` — richest path; finance-native context, budget enforcement, MCP hooks
2. **OTel SDK / OpenInference** → OTel Collector → `/v1/traces` — collector handles batching, retry, auth
3. **OTel SDK / OpenInference** → `/v1/traces` directly — low-friction evaluation

### Design Principles

- OTLP is an external ingest format, not the internal storage model. Every OTLP trace is normalized into RunLedger canonical events (`run_start / span_start / provider_call / tool_call / span_end / run_end`) and fed through the existing Celery pipeline.
- Workspace identity comes from API key auth — never from OTLP resource attributes.
- Privacy modes (`METADATA_ONLY / ERRORS_ONLY / SAMPLED / FULL`) apply equally to SDK and OTLP-ingested payloads.
- Raw OTLP payloads are staged (`otlp_ingest_batches`, `otlp_spans_raw`) for replay and parser-evolution safety.

### Normalization Priority

1. OpenInference (`openinference.span.kind`, `llm.model_name`, `llm.token_count.*`)
2. OTel GenAI semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`)
3. Generic span name / kind heuristics

### Span Kind Mapping

| OpenInference kind | RunLedger span type |
|--------------------|---------------------|
| AGENT | agent |
| CHAIN | chain |
| LLM | llm → synthesizes `provider_call` |
| TOOL | tool → synthesizes `tool_call` |
| RETRIEVER | retrieval |
| PROMPT / EVALUATOR / GUARDRAIL | chain (with metadata) |
| EMBEDDING | retrieval |

### ID Strategy

- `run_id` = `uuid5(NAMESPACE_URL, "otlp-trace:<workspace_id>:<trace_id_hex>")` — deterministic, idempotent
- `span_id` = `uuid5(NAMESPACE_URL, "otlp-span:<workspace_id>:<trace_id_hex>:<span_id_hex>")`
- External IDs preserved in `external_trace_id` / `external_span_id` columns for auditability

### RunLedger-Specific Span Attributes

Attach to the root span to enrich context without touching tenancy:

| Attribute | Aliases | Description |
|-----------|---------|-------------|
| `runledger.session_id` | `session.id`, `openinference.session_id` | User session |
| `runledger.end_user_id` | `user.id`, `openinference.user_id`, `enduser.id` | End-user ID |
| `runledger.feature_tag` | `tag.feature`, `feature_tag` | Product feature label |
| `runledger.deployment_version` | `service.version` (resource) | Deployment label |

### Reconciliation-grade Cost Model

| Field | Source | Meaning |
|-------|--------|---------|
| `reported_cost_usd` | Upstream instrumentor | Cost as emitted by client (e.g. `llm.cost.total`) |
| `cost_usd` | RunLedger pricing engine | Authoritative current cost used in analytics |
| `cost_source` | Set at write time | `reported` / `pricing_engine` / `invoice_reconciled` |

### Trace Finalization

Incomplete OTLP traces (partial batches, lost run_end spans) are handled by `workers/otlp_finalize.py` — a Celery beat task running every 3 minutes that closes `agent_runs` where `source_type='otlp'`, `status='running'`, and `started_at < now() - 5 minutes`.

### OTel Collector

The repo ships a reference `infra/otel-collector-config.yaml`. Start with:

```bash
docker compose --profile otel up otel-collector
```

The collector listens on 4317 (gRPC) and 4318 (HTTP), batches spans, and forwards to `http://api:8000` with Bearer auth via `${RUNLEDGER_API_KEY}`.

---

## Phase Build Details

### Phase 0 — Monorepo + Infrastructure Foundation ✅

**Goal:** `docker compose up` runs Postgres + Redis + a health-check API.

- `core/config.py`, `core/db.py`, `core/redis.py`, `core/logging.py`, `core/celery_app.py`
- `routers/health.py` — `GET /health`
- `infra/docker-compose.yml` — postgres:16-alpine, redis:7-alpine, api, worker, web services
- `.github/workflows/ci.yml` — ruff + mypy + pytest on push
- **3 tests** (health ok, db degraded, redis degraded)

---

### Phase 1 — Ingestion API + Multi-tenancy + Auth ✅

**Goal:** A real event can be sent via HTTP with an API key, stored in Postgres, and queried back.

- Migration `001_initial_schema.py` — all Tenant & Auth + Instrumentation Events tables; `provider_calls` with 12 monthly partitions
- `routers/auth.py` — workspace + API key CRUD
- `routers/ingest.py` — `POST /ingest/v1/events` + `/batch`; API key auth; idempotency via Redis SETNX; events → Redis Stream
- `workers/pipeline.py` — Celery `process_event_batch`: drains Redis Stream → validates → upserts all event types
- `scripts/seed.py` — default tenant + workspace + API key + pricing data
- **17 tests** (auth: 11, ingest: 6)

---

### Phase 2 — SDK: OpenAI Wrapper + Context Propagation ✅

**Goal:** `rl.instrument()` wraps the OpenAI client. One line of code captures model, tokens, latency, and cost.

- `runledger_sdk/client.py` — `RunLedger` client with `instrument()`, `context()`, `shutdown()`
- `runledger_sdk/context.py` — `contextvars`-based context; cross-service propagation headers
- `runledger_sdk/openai.py` — wraps `chat.completions.create` + async; captures tokens, latency, status
- `runledger_sdk/transport.py` — async httpx, in-memory buffer (max 500), flush every 2s or 100 events, exponential backoff retry
- **28 tests** (openai: 10, context: 10, transport: 8)

---

### Phase 3 — SDK: LangChain + LangGraph + CLI ✅

**Goal:** Any LangChain chain or LangGraph graph is fully instrumented with one callback.

- `runledger_sdk/langchain.py` — `RunLedgerCallbackHandler` for chain/llm/tool/agent events
- `runledger_sdk/langgraph.py` — `instrument_graph()` via `graph.with_config({"callbacks": [handler]})`
- `runledger_sdk/cli.py` — `runledger validate / status / runs / check-regression`
- **33 tests** (langchain: 13, langgraph: 9, cli: 11)

---

### Phase 4 — Billing-grade Metering Core ✅

**Goal:** Every provider call has a cost in USD attached within 30 seconds.

- Migration `002_metering_tables.py` — `provider_pricing`, `usage_hourly`, `usage_daily`, `data_quality_issues`
- `services/pricing.py` — `calculate_cost()`: effective-dated lookup, workspace override, cached input discount
- `workers/metering.py` — 5 Celery tasks: cost_enrichment (60s), rollup_hourly (30m), rollup_daily (daily), data_quality (1h), replay_backfill
- `routers/analytics.py` — 5 analytics endpoints (summary, spend-over-time, spend-by-model, spend-by-user, spend-by-feature)
- **22 tests** (pricing: 9, analytics: 13)

---

### Phase 5 — Run Explorer + DAG Viewer UI ✅

**Goal:** Log into the dashboard, search for a run, click into it, see the full DAG with cost per node.

- Next.js 14 App Router frontend with TypeScript, Tailwind, shadcn/ui
- `@xyflow/react` DAG with auto-layout via dagre; colored nodes by span type
- `routers/runs.py` — `GET /runs` (cursor pagination, filters), `GET /runs/{id}`, `GET /runs/{id}/graph`
- NextAuth.js credentials provider; session API key in JWT

---

### Phase 6 — Metering Dashboard ✅

**Goal:** A finance person opens the dashboard and immediately understands spend, who's driving it, and where it's going.

- Recharts charts: LineChart (spend-over-time), BarChart (by-model), PieChart (by-feature)
- `AnalyticsSummary` with `prev_cost_usd` + `cost_delta_pct` (prior period comparison)
- User spend profile page (`/analytics/users/[end_user_id]`)
- **+3 tests** (delta computed, delta None on zero prior, user spend detail)

---

### Phase 7 — Budgets + Spend Guardrails ✅

**Goal:** Set a budget for an end-user. Run a chatbot that exceeds it. The next call is blocked automatically.

- Migration `004_budgets.py` — `budgets`, `budget_breaches`, `budget_notifications`
- `services/budgets.py` — Redis INCR hot path, workspace cache (TTL 300s), breach firing
- `workers/budgets.py` — `runaway_protection` (every 5 min), `budget_spend_sync` (daily)
- SDK: `RunLedgerBudgetExceededError`; pre-call budget check in `openai.py`
- **19 tests**

---

### Phase 8 — Chargeback Engine + Reconciliation ✅

**Goal:** Close the month, generate a usage statement, drill from any line item back to the exact run.

- Migration `005_billing.py` — `billing_periods`, `chargeback_rules`, `usage_snapshots`
- `services/billing.py` — `sign_snapshot()` HMAC-SHA256, `close_billing_period()`, `run_reconciliation()`, `apply_chargeback_rules()`
- CSV + signed JSON export
- **15 tests**

---

### Phase 9 — Unit Economics Graph + Change Impact ✅

**Goal:** "What did this run cost per step?" and "What changed between v1 and v2?"

- Migration `006_annotations.py` — `annotations` table
- 6 new analytics endpoints: `/economics/{run_id}`, `/workflows/top`, `/compare`, `/regressions`, `/annotations` GET+POST
- **12 tests**

---

### Phase 10 — End-user Analytics + Replay Harness ✅

**Goal:** Identify top spenders and anomalous users. Create a replay dataset and project cost across model configs.

- Migration `007_replay.py` — `user_anomalies`, `replay_datasets`, `replay_experiments`
- Cohort segmentation (P0/P1/P2/P3 tiers), Z-score anomaly detection (nightly Celery)
- `routers/replay.py` — dataset CRUD + experiment CRUD + cost-projection worker
- **15 tests**

---

### Phase 11 — Tamper-evident Ledger + Security + Privacy ✅

**Goal:** Cryptographically verifiable daily spend snapshots, tool policies, suspicious-sequence detection, and a privacy capture policy API.

- Migration `008_ledger.py` — `ledger_keys`, `ledger_snapshots`, `tool_registry`, `security_events`, `capture_policies`
- `services/ledger.py` — HMAC-signed snapshots, key rotation (30d TTL), verify endpoint
- `workers/ledger.py` — `daily_snapshots` (01:00 UTC), `suspicious_sequences` (every 60s, 5-min dedup)
- `core/feature_gate.py` — `require_cloud()` raises HTTP 402 in OSS mode
- **15 tests** (ledger: 8, tools + privacy: 7)

---

### Phase 12 — Settings Console + Dark Mode + Provider Profiles ✅

**Goal:** Manage API keys, configure model pricing overrides, and switch themes — all from a single Settings page.

- `routers/settings.py` — API key CRUD (raw key shown once)
- `routers/providers.py` — workspace pricing override CRUD
- Dark mode via `next-themes` `ThemeProvider`
- **13 tests**

---

### Phase 14 — Integrations: Slack Alerts + GitHub CI Gate ✅

**Goal:** Budget breach and anomaly alerts fire in Slack automatically. CI pipelines can gate on cost regressions.

- `services/notifications.py` — Slack Block Kit builder + `send_slack_message()`
- `routers/integrations.py` — `POST /integrations/slack/test`
- `GET /analytics/export` — bulk CSV/JSON export of usage_daily
- `runledger check-regression` CLI — exits 1 if regressions found (GitHub Actions gate)
- **8 tests**

---

### Phase 15 — Anthropic SDK ✅

**Goal:** Instrument Anthropic API calls with the same zero-config pattern as the OpenAI wrapper.

- `runledger_sdk/anthropic.py` — `instrument_anthropic()` monkey-patches `anthropic.Anthropic` + `AsyncAnthropic`
- Captures `input_tokens` / `output_tokens` / `latency_ms` / `status`; streaming + async supported
- `provider_request_id` captured from `result.id`; `cache_creation_input_tokens` in details
- **8 SDK tests**

---

### Phase 16 — Production Hardening + UI Polish ✅

**Goal:** Rate limiting, PII scrubbing, richer health checks, complete deployment guide, consistent UI.

- `core/ratelimit.py` — Redis sliding-window: 600 req/min (ingest), 120 (analytics), 60 (management)
- `services/scrubbing.py` — PII regex scrubber applied before ORM write
- `GET /health/live` + `GET /health/ready` probes
- Sonner toasts on all pages; Sidebar active state via `usePathname()`
- `docs/deployment.md` — Railway deployment guide
- **13 tests**

---

### Phase 17 — Evaluations & Scores ✅

**Goal:** Attach quality scores to any run from human feedback, rule-based evaluators, or telemetry.

- Migration `010_scores.py` — `score_events`, `score_rollups_daily`
- `routers/evaluations.py` — `POST /evaluations/scores`, `GET /evaluations/scores`
- `routers/analytics.py` — `GET /analytics/scores/summary`, `GET /analytics/scores/regressions`
- `workers/score_rollup.py` — nightly PERCENTILE_CONT rollup
- SDK `rl.score()` method — fail-silent, auto-fills run_id from context
- **13 tests**

---

### Phase 17B — Evaluator Framework ✅

**Goal:** LLM-as-judge, rule-based evaluators, batch evaluation, drift detection.

- `models/evaluators.py` — `Evaluator` ORM model (migration `022_evaluators.py`)
- `services/evaluators.py` — LLM judge + rule-based evaluator runners
- `workers/evaluators.py` — batch eval Celery task; drift detection comparing score windows
- **17 tests**

---

### Phase 18 — Prompt Management ✅

**Goal:** Version-controlled prompt registry with variable templating, environment promotion, and per-version cost + quality metrics.

- Migration `011_prompts.py` — `prompts`, `prompt_versions`
- `routers/prompts.py` — 10 endpoints including promote (gated by approvals in Phase 25)
- SDK `rl.get_prompt()` — 60s in-memory cache, `{{variable}}` substitution
- Diff viewer in UI between any two versions
- **12 tests**

---

### Phase 19 — Sessions UI + Payload Viewer ✅

**Goal:** Surface session-level analytics (multi-turn conversations) and display captured payloads inline.

- `routers/sessions.py` — list sessions, session detail + cost-over-turns chart
- `routers/runs.py` extended — `input_payload` / `output_payload` / `span_payloads` in run detail
- `PayloadViewer.tsx` — role-colored message display
- **8 tests**

---

### Phase 20 — TypeScript / Node.js SDK ✅

**Goal:** First-class instrumentation for JS/TS applications.

- `packages/ts-sdk/src/` — `RunLedger` class, OpenAI/Gemini/Mistral/Cohere instrumentation
- `AsyncLocalStorage` context propagation; batch + retry transport
- Multi-provider auto-detection from baseURL
- TypeScript examples: `ts/01_openai_basic.ts`, `ts/02_multi_turn.ts`, `ts/03_vercel_ai.ts`
- **9 vitest tests**

---

### Phase 21A — Advanced Alerting ✅

**Goal:** Rule-based alerts on error rate, p95 latency, avg score, and spend velocity.

- Migration `012_alerts.py` — `alert_rules`, `alert_firings`
- `routers/alerts.py` — rule CRUD + history
- `workers/alerts.py` — Celery beat (every 5 min): evaluate rules, dedup, Slack dispatch
- **9 tests**

---

### Phase 21B — Model Gateway ✅

**Goal:** OpenAI-compatible proxy with prompt caching, provider fallback, routing policies, and full request logging.

- Migration `013_gateway.py` — `gateway_routes`, `gateway_requests`, `prompt_cache`
- Migration `015_routing_policies.py` — `routing_policies` table + `decision_reason` on `gateway_requests`
- `services/gateway.py` — cache check, route and forward, SSE streaming, `_build_payload()` pass-through
- `services/routing.py` — 8 strategies: manual, cost_optimized, latency_optimized, quality_optimized, weighted, canary, budget_aware, complexity_based
- **12 + policy tests**

---

### Phase 21C — Runs Enhancements ✅

- Model filter (ilike subquery on `ProviderCall`) + min/max cost filters
- `GET /runs/export` CSV endpoint + `RunsExportButton` client component
- Ollama cost = $0 fix in `metering.py`
- API key UX: hide `is_session=True` keys; show `created_at` with time

---

### Phase 21D — Unified Policy Checks ✅

- `services/policies.py` — `check_policies()` combining budgets + tool registry + gateway rules + eval gates
- `routers/policies.py` — `POST /policies/check` decision endpoint
- `examples/19_policy_check.py`
- **6 tests**

---

### Phase 21E — Gateway Provider Expansion ✅

**Goal:** Extend the Model Gateway to support Azure OpenAI, AWS Bedrock, and Google Vertex AI in addition to OpenAI-compatible endpoints.

- `services/gateway_providers.py` — abstract `BaseAdapter` + `OpenAIAdapter`, `AzureAdapter`, `BedrockAdapter`, `VertexAdapter`
- `AzureAdapter` — deployment-based URL construction (`/openai/deployments/{model}/chat/completions`), `api-key` header, configurable `api_version`, removes `model` from payload
- `BedrockAdapter` — boto3 `bedrock-runtime` client; `_messages_to_bedrock()` format conversion; `_normalize_bedrock_response()` to OpenAI-compatible output; streaming via `converse_stream` → SSE chunks; `asyncio.to_thread` for sync boto3 calls
- `VertexAdapter` — Google auth via `google-auth` (`service_account.Credentials.from_service_account_info()` or ADC); token refresh via `asyncio.to_thread`; Gemini content format conversion; `_normalize_vertex_response()` to OpenAI-compatible output
- `get_adapter(provider)` registry function — routes to correct adapter by provider string
- Migration `033_gateway_config.py` — adds `config JSONB` column to `gateway_routes` for provider-specific options (deployment_name, api_version, region, project_id, location)
- `schemas/gateway.py` extended — `GatewayRouteCreate` / `GatewayRouteResponse` include `config` field; provider enum extended to `azure | bedrock | vertex`
- Frontend Settings page — route create form shows Azure/Bedrock/Vertex options in provider dropdown; `config` rendered as JSON textarea
- **17 tests** (OpenAI adapter forward+stream, Azure URL construction+custom version+stream, Bedrock format conversion+forward+stream, Vertex format conversion+forward, adapter registry, route CRUD with config)

---

### Phase 26 — Email Notification System ✅

**Goal:** Automated email delivery for all finance-critical events — alerts, budget breaches, billing closures, dispute flags, and weekly analytics reports.

- Migration `031_email_prefs.py` — `email_preferences` table (workspace-scoped): `alerts_enabled`, `budget_enabled`, `billing_enabled`, `report_frequency ENUM[daily|weekly|monthly|never]`; `email_log` table for delivery audit trail
- Migration `032_email_system.py` — adds `email_notifications_enabled` to `users`; `unsubscribe_tokens` table for one-click unsubscribe
- `models/email_prefs.py` — `EmailPreference` + `EmailLog` + `UnsubscribeToken` ORM models
- `services/email.py` — `send_email()` via SMTP (Brevo/SendGrid/SES); `send_alert_fired_email()`, `send_budget_breach_email()`, `send_billing_closed_email()`, `send_dispute_flagged_email()`, `send_analytics_report_email()`; HTML templates with unsubscribe footer
- `services/email_utils.py` — `get_workspace_admin_users()` queries `WorkspaceUser` join; `get_email_preference()` lazy-loads `EmailPreference`
- `routers/settings.py` extended — `GET/PUT /settings/email/preferences`, `POST /settings/email/test`, `GET /settings/email/log`; `GET /settings/email/unsubscribe?token=…` one-click unsubscribe (unauthenticated)
- `workers/alerts.py` updated — `evaluate_alert_rules` dispatches `send_alert_fired_email()` when `email_enabled=True` on rule
- `workers/budgets.py` updated — `runaway_protection` dispatches `send_budget_breach_email()` to workspace admins
- `routers/billing.py` updated — `close_period` fires `send_billing_closed_email()` as background task
- `routers/invoices.py` updated — `dispute_line` fires `send_dispute_flagged_email()` as background task
- `workers/email_reports.py` — `send_weekly_analytics_reports` Celery beat task (Monday 08:00 UTC): queries `UsageDaily`, respects `report_frequency` preference, delivers formatted HTML to all workspace admins
- **13 tests** covering: preferences CRUD, test endpoint, email log, unsubscribe token validation, alert worker email dispatch, budget breach email, billing close email, dispute email, weekly report scheduling

---

### Phase 27 — Data Retention & Deletion Policy APIs ✅

**Goal:** GDPR/CCPA-ready data lifecycle management — configurable retention policies, right-to-erasure, scrub-not-delete.

- Migration `029_retention_policies.py` — `retention_policies` table with workspace/end_user scope
- `models/retention.py` — `RetentionPolicy` ORM model
- `schemas/retention.py` — Pydantic schemas with `@model_validator` enforcing scope+action constraints
- `services/retention.py` — `purge_resource()`: delete/scrub per resource type; dry-run COUNT mode; JSONB payload scrub via `-` operator; Span workspace join via run_id subquery
- `routers/retention.py` — CRUD + `POST /retention/purge` (policy_id or inline params) + audit events emitted on every purge
- `workers/retention.py` — nightly Celery beat (86400s): runs all active policies automatically
- `RetentionTab.tsx` — policy table with toggle/dry-run/purge/delete + create form in Settings
- **21 tests**

---

### Phase 28 — Warehouse Export — S3/GCS/R2 ✅

**Goal:** Daily automated exports to object storage in analyst-ready formats for Snowflake, BigQuery, and Athena.

- Migration `030_warehouse_exports.py` — `warehouse_destinations` + `warehouse_export_jobs` tables
- Dependencies: `boto3`, `pyarrow`
- `services/warehouse.py` — `export_workspace_data()` for JSONL/Parquet; `test_destination_connection()` validates credentials before save
- `routers/warehouse.py` — destination CRUD + `/test` + job trigger/list/get
- `workers/warehouse.py` — `warehouse.run_scheduled_exports` daily beat + `warehouse.run_single_export` per-job task
- `WarehouseTab.tsx` — collapsible destination cards + job history in Settings
- File paths: `{prefix}/{resource}/date={YYYY-MM-DD}/data.{ext}` — Hive-style partition layout for Snowflake external stages and BigQuery external tables
- Supported resources: `agent_runs`, `provider_calls`, `usage_daily`, `score_events`, `outcomes`
- **22 tests**

---

### Phase 22 — SaaS Foundation ✅

**Goal:** Self-service signup, Stripe subscription management, usage quota enforcement, and full RBAC.

- Migration `014_rbac.py` — `users`, `tenant_users`, `workspace_users` with role enums
- Migration `018_tenancy_spec.py` — tenancy model refinements
- Migration `019_saas.py` — `plans`, `subscriptions`, `usage_quotas`
- `routers/saas.py` — signup, Stripe checkout, portal, webhook handler
- `routers/org.py` — org profile, workspaces, members management
- `routers/users.py` — user profile CRUD
- `routers/platform.py` — platform admin: stats, tenants, users
- `core/deps.py` — `require_user / require_platform_admin / require_org_admin / require_workspace_admin / require_member`
- `POST /admin/bootstrap` — one-time admin + default tenant setup
- Frontend: `/signup`, `/admin/*` pages, OrgTab component, platform admin sidebar section
- JWT extended with `full_name / user_id / tenant_id / is_platform_admin / tenant_role / workspace_role / workspace_ids`

---

### Phase 23 — Provider Invoice Reconciliation ✅

**Goal:** Reconcile RunLedger internal usage against provider billing exports. Explain deltas. Export dispute packages.

- Migration `023_provider_invoices.py` — `provider_invoices`, `provider_invoice_lines`
- `services/invoices.py` — import parser, request-ID matching, fuzzy matching (timestamp window + token ranges), confidence scores, dispute trail
- `routers/invoices.py` — invoice import, list, detail, reconcile, report
- Frontend: `/invoices` page — import form, reconciliation summary, drilldown, dispute export
- **28 tests**

---

### Phase 24 — Outcome & ROI Ledger ✅

**Goal:** Tie spend to business outcomes. Cost-per-success, ROI by workflow, outcome trend.

- Migration `024_outcomes.py` — `outcomes`, `outcome_rollups_daily`
- `routers/outcomes.py` — 6 endpoints: record, list, summary, trend, workflow ROI, quality correlation
- `workers/outcomes.py` — `rollup_outcomes_daily` + `check_outcome_alerts` Celery tasks
- SDK `rl.outcome()` method
- Frontend: `/outcomes` page with KPI cards, trend chart, workflow ROI table, quality correlation table
- **20 tests**

---

### Phase 25 — Approvals & Policy Workflows ✅

**Goal:** Require approval for sensitive actions (prompt production promotion, budget increases).

- Migration `025_approvals.py` — `approvals` table
- `routers/approvals.py` — 7 endpoints (create, list, summary, get, approve, deny, cancel)
- `validate_approved()` helper — used as gate on `POST /prompts/{name}/promote` for `target=production`
- Frontend: `/approvals` page — summary strip, table with approve/deny/cancel, create modal
- Sidebar "Governance" section
- **19 tests**

---

### OTEL-0 — OTLP Ingestion: Schema Foundation + Receiver ✅

**Goal:** Accept native OTLP traces — no RunLedger SDK required.

- Migrations `026_otlp_source_fields` + `027_otlp_staging` — source-provenance columns on `agent_runs`, `spans`, `provider_calls`, `tool_calls`; `otlp_ingest_batches` and `otlp_spans_raw` staging tables
- `services/otlp_parse.py` — base64/hex ID decoding, attribute flattening, span classification, deterministic UUID5 IDs, `synthesize_canonical_events()`
- `routers/otlp.py` — `POST /v1/traces` + alias; gzip decompression; 401/413/415/422 error codes; `{"partialSuccess": {}}` response
- `infra/otel-collector-config.yaml` + Docker Compose `otel` profile
- **37 tests**

---

### OTEL-1 — Run-context Extraction + Payload Capture + Management API ✅

**Goal:** Make OTLP traces first-class citizens: enrich with session/user context, forward payloads through privacy pipeline, provide management surfaces.

- `_extract_run_context()` — reads `runledger.*` attributes with priority over generic OTel/OpenInference names; spreads `session_id`, `end_user_id`, `feature_tag`, `deployment_version` onto `run_start` events
- `_extract_message_payloads()` — extracts `llm.input_messages.*` / `llm.output_messages.*` / `input.value` / `output.value`; attached to `span_end["metadata"]` for privacy pipeline processing
- `GET /v1/traces/stats`, `GET /v1/traces/batches`, `GET /v1/traces/batches/{id}` management endpoints
- Settings UI: OTLP stats section with endpoint display, collector example, privacy mode notes
- **13 tests**

---

### OTEL-2 — OTel GenAI Support + Retrieval Metadata ✅

**Goal:** Support OTel GenAI semantic conventions as a second normalization priority.

- `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens/output_tokens` mapping
- Convention version tracking (`telemetry.sdk.name` / `gen_ai.semantic_conventions.version`)
- Retrieval metadata extraction (`retrieval.documents`, `document.id/content/score`)
- Generic span fallback rules for non-AI spans

---

### OTEL-3 — Trace Finalization + Source-Provenance Propagation ✅

**Goal:** Reliably close incomplete OTLP traces; persist source-provenance columns through the pipeline.

- `workers/otlp_finalize.py` — Celery beat (every 3 min): closes stale OTLP runs (`started_at < now() - 5min`) by setting spans to `failed`, runs to `cancelled`
- `workers/pipeline.py` updated — `_handle_run_start` + `_handle_span_start` persist all OTLP source-provenance columns (`source_type`, `external_trace_id`, `external_span_id`, scope fields)
- **8 tests**

---

### OTEL-4 — Reconciliation-grade Enrichment ✅

**Goal:** Every OTLP-ingested provider call is usable in future invoice reconciliation workflows.

- `_extract_llm_fields()` extended — provider request ID priority chain, `reported_cost_usd`, `model_provider`, token details breakdown (cached/reasoning/audio)
- `cost_source` set to `"reported"` when upstream emits cost; `"pricing_engine"` otherwise
- `workers/pipeline.py` — `_handle_provider_call` INSERT persists all reconciliation columns
- Python SDK: `result.id` → `provider_request_id` for OpenAI + Anthropic; `prompt_tokens_details` / `completion_tokens_details` captured
- **23 API tests + 7 SDK tests**

---

## Testing Strategy

### Unit tests (pytest)

- Pricing engine: cost calculation, effective-date lookups, cached token discounts
- Budget enforcement: Redis counter logic, action resolution, scope matching
- Chargeback allocation: weight-based splits, edge cases
- HMAC signing: generation + verification, key rotation
- OTLP: ID decoding, span classification, attribute mapping, UUID5 determinism
- SDK: wrapper captures correct metadata; context vars propagate; budget check pre-call

### Integration tests (pytest + mocked dependencies)

- Ingestion pipeline: event → Celery worker → Postgres
- Rollup jobs: idempotency (run twice → same result)
- Budget check: Redis hot path correctness
- API auth: 401 for missing/wrong/expired API keys
- OTLP: full trace → canonical events → run visibility

### Load tests (Locust — run before each phase milestone)

- Ingestion API: 1000 events/sec for 60s — target p99 < 50ms
- Budget check endpoint: 500 req/sec — target p99 < 10ms
- OTLP ingest: burst from Collector — verify backpressure and idempotency

---

## Deployment (Railway)

```
Railway Project: runledger-prod
├── Service: api          (Docker image, 1-3 replicas)
├── Service: worker       (Docker image, Celery worker + beat, 1-2 replicas)
├── Service: web          (Next.js, 1 replica)
├── Plugin: PostgreSQL    (Railway managed Postgres 16)
└── Plugin: Redis         (Railway managed Redis 7)
```

**Key environment variables:**
```
DATABASE_URL          = postgresql+asyncpg://...
REDIS_URL             = redis://...
SECRET_KEY            = <32-byte hex>
ADMIN_SECRET          = <admin bootstrap secret>
ENVIRONMENT           = production
RUNLEDGER_MODE        = paid   # 'oss' for self-hosted
STRIPE_SECRET_KEY     = sk_live_...
STRIPE_WEBHOOK_SECRET = whsec_...
NEXT_PUBLIC_API_URL   = https://api.runledger.io
NEXTAUTH_URL          = https://app.runledger.io
NEXTAUTH_SECRET       = <32-char secret>
```

See `docs/deployment.md` for the complete Railway deployment guide.

---

## Strategic Positioning

RunLedger's defensible moat is not observability — it is the **finance and control plane**:

1. **System of record for AI spend** — provider invoice reconciliation + HMAC-signed snapshots finance teams can trust
2. **Chargeback and allocation** — trace-linked: billing line → AgentRun → Span → ProviderCall
3. **Budget-aware runtime control** — budgets, routing policies, gateway enforcement
4. **Outcome and ROI visibility** — cost-per-success, not just cost-per-token
5. **Enterprise credibility** — SSO-ready RBAC, approval workflows, audit trail, data retention policies

Non-goals: competing with LangSmith on eval depth, Langfuse on OSS mindshare, or LiteLLM on provider breadth. The SDK is the richest path; OTLP is the zero-friction adoption path.

The external positioning statement at launch should be:

> *RunLedger is the AI spend system of record and runtime control plane for production AI products. It reconciles provider invoices, powers internal chargeback, enforces budgets and routing policy, and ties cost to outcomes and ROI.*

---

## Forward Roadmap

The core finance and control plane is complete. The existing build covers instrumentation, metering, chargeback, gateway, alerting, outcomes, approvals, OTLP ingestion, email notifications, data retention, and warehouse export. The next strategic layer concentrates on **enterprise readiness** (SSO, SCIM, audit), **gateway runtime controls** (cost caps, PII redaction), and **finance system integration** (billing webhooks, accounting exports).

### Current Status vs. Six Original Workstreams

| Workstream | Status |
|-----------|--------|
| Provider Invoice Reconciliation | ✅ Complete (Phase 23) |
| Outcome & ROI Ledger | ✅ Complete (Phase 24) |
| Packaging and Editions (SaaS foundation) | ✅ Complete (Phase 22) |
| Enterprise Controls — Data Retention | ✅ Complete (Phase 27) |
| Enterprise Controls — SSO / SCIM | 🔲 Next |
| Gateway Expansion (Azure/Bedrock/Vertex) | ✅ Complete (Phase 21E) |
| Warehouse Export (S3/GCS/R2) | ✅ Complete (Phase 28) |
| Gateway Runtime Controls (cost caps, PII) | 🔲 Next |
| Finance System Integrations (webhooks, accounting) | 🔲 Next |

### Next Phases

---

#### Phase 29 — SSO / OIDC + SCIM

**Goal:** Enterprise sales blocker cleared. Any org using Google Workspace, Okta, or Azure AD can log in on day one without manual user provisioning.

**Scope:**
- OIDC SSO via `authlib` — Google Workspace, Okta, Azure AD; JIT user creation on first login mapped to existing `users` table
- Workspace-level IdP configuration (issuer URL, client ID/secret, attribute mapping) stored in a new `sso_configs` table
- `POST /auth/oidc/callback` — token exchange + session creation; maps OIDC `sub` → user; creates `TenantUser` if first login for that tenant
- SCIM 2.0 server at `/scim/v2/Users` + `/scim/v2/Groups` — create/update/deactivate users; group → workspace mapping; bearer token auth per tenant
- Migration `034_sso.py` — `sso_configs(id, tenant_id, provider, issuer_url, client_id, client_secret_enc, attribute_mapping JSONB, is_active)`
- Frontend: SSO Configuration tab in Org settings; SCIM token display; login page shows "Sign in with SSO" button when SSO is configured for the domain
- Dependencies: `authlib`, `cryptography` (for client secret encryption at rest)

---

#### Phase 30 — Gateway Runtime Controls

**Goal:** The gateway enforces spend boundaries and privacy at the request level — not just routing decisions.

**Scope:**
- **Per-route cost caps** — `daily_cost_limit_usd` and `monthly_cost_limit_usd` on `gateway_routes`; checked against `gateway_requests` aggregate before forwarding; returns 429 with `X-Cost-Cap-Reason` header on breach; automatic failover to next-priority route
- **Route health monitoring** — Celery beat (every 5 min): disables routes with >5% error rate over a 10-min window; re-enables when error rate drops; emits `alert_firing` for visibility
- **Gateway-level PII redaction** — `services/gateway_redact.py`: regex-based redaction (email, phone, SSN, credit card) applied to request messages before forwarding; configurable per route (off by default); redaction log stored on `gateway_requests` JSONB field
- **Per-end-user rate limiting** — `X-RunLedger-End-User-Id` header on gateway requests; Redis sliding window per `(workspace_id, end_user_id, route_id)`; 429 with `Retry-After` on breach
- Migration `035_gateway_runtime.py` — adds `daily_cost_limit_usd`, `monthly_cost_limit_usd`, `pii_redaction_enabled`, `per_user_rpm_limit` to `gateway_routes`
- Frontend: extended route edit form with cost cap + PII toggle + per-user rate limit fields; cost cap usage bar shown per route in gateway stats strip
- **~15 tests**

---

#### Phase 31 — Finance System Integrations

**Goal:** Close-period events automatically flow into finance systems. Cost data lands in accounting tools with zero manual export steps.

**Scope:**
- **Signed billing-close webhook** — `POST /billing/periods/{id}/close` triggers an HMAC-signed webhook to a configured endpoint; payload includes `period_start`, `period_end`, `total_cost_usd`, `chargeback_breakdown[]`, `snapshot_signature`; finance teams can verify the signature and auto-import into GL
- **Webhook config** — `billing_webhook_configs` table; workspace-scoped; `POST/GET/DELETE /billing/webhooks`; stored with secret; delivery log with retry (3 attempts, exponential backoff)
- **QuickBooks CSV export** — `GET /billing/periods/{id}/export?format=quickbooks` — maps chargeback rules to QB chart of accounts; generates double-entry journal lines: debit cost center, credit AI spend clearing account
- **NetSuite CSV export** — `GET /billing/periods/{id}/export?format=netsuite` — journal entry format with subsidiary + department dimensions
- Migration `036_billing_webhooks.py` — `billing_webhook_configs` + `billing_webhook_deliveries`
- Frontend: Billing page "Close Period" modal adds webhook destination field; export dropdown gains QuickBooks/NetSuite options
- **~12 tests**

---

#### Phase 32 — Developer Experience + Public API

**Goal:** Any engineer can evaluate RunLedger in < 30 minutes and integrate it in < 2 hours.

**Scope:**
- **Published OpenAPI spec** — `GET /openapi.json` versioned; served at `api.runledger.io/openapi.json`; Redoc UI at `/docs`; Scalar UI at `/reference` (richer DX than Swagger)
- **`runledger init` CLI command** — interactive: asks for API URL + admin secret; calls `POST /admin/bootstrap`; writes `.env` with `RUNLEDGER_API_KEY`; creates default workspace + prints quickstart curl commands
- **SDK changelog** — `CHANGELOG.md` in `packages/sdk/` and `packages/ts-sdk/`; semantic versioning; breaking changes annotated
- **`runledger doctor` CLI** — checks connectivity, auth, Redis, worker health (`/health/ready`); prints pass/fail for each; exit 1 if any critical check fails
- **Examples refresh** — expand to 30 examples covering gateway, OTLP, outcomes, sessions, approvals, evaluators, warehouse; each with inline cost annotation showing expected spend
- **No new migrations required**

---

### Non-Goals (unchanged)

- Competing with LangSmith on generic prompt/eval workflow depth
- Competing with Langfuse on broad OSS observability mindshare
- Competing with LiteLLM or Portkey on maximum provider breadth
- Building a full application deployment platform
- Shipping speculative AI assistant features inside the product

### Target Capabilities at Completion

1. System of record for AI spend across providers — with external invoice reconciliation
2. Internal chargeback with trace-linked evidence
3. Cost tied to business outcomes and ROI
4. Runtime behavior controlled through budgets, routing, gateway cost caps, and PII redaction
5. Enterprise buyer onboarding via SSO, SCIM, approvals, and warehouse exports
6. Finance system integration via signed webhooks and accounting-format exports
7. Clear OSS / SaaS / Enterprise packaging boundaries enforced in product behavior

---

## OTLP Design Rationale

The OTLP ingestion path was built to lower adoption friction without compromising the finance-native SDK path.

**Core decisions:**

- OTLP is an external ingest format, not the internal storage model. Every trace is normalized into RunLedger canonical events and fed through the existing Celery pipeline. This preserves architecture consistency and avoids a parallel data path.
- Normalization priority: OpenInference first (best AI-native concepts), OTel GenAI conventions second (still evolving), generic span heuristics third. This order ensures finance-critical fields (model identity, token counts, cost) are extracted with maximum fidelity from AI-specific frameworks.
- Workspace identity always comes from API key auth — never from OTLP resource attributes. This is a security boundary, not a convenience choice.
- Deterministic UUID5 IDs (`uuid5(NAMESPACE_URL, "otlp-trace:<ws_id>:<trace_hex>")`) make ingest idempotent across retries and partial batches.
- Raw staging tables (`otlp_ingest_batches`, `otlp_spans_raw`) are kept for parser-evolution safety and replay. If the normalizer is updated, historical traces can be re-normalized without re-ingestion.
- The finalizer worker (`workers/otlp_finalize.py`) handles the reality that OTLP batches arrive out of order and root spans may never arrive. Traces open for > 5 minutes are closed automatically.
- Cost provenance fields (`reported_cost_usd`, `cost_source`) ensure OTLP-ingested data participates in invoice reconciliation workflows with the same fidelity as SDK-instrumented data.

**The SDK remains the premium path** because it adds: pre-call budget enforcement, MCP tool hooks, `rl.score()` inline scoring, `rl.outcome()` recording, structured context propagation, and finance-native request ID capture. OTLP gives compatibility; the SDK gives control.
