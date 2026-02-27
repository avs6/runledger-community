# RunLedger — Product Roadmap

Agent FinOps Control Plane: billing-grade usage accounting, cost attribution, budgets, and chargeback for LLM agents.

---

## Guiding Principles

- **Async instrumentation first** — lowest friction. Optional inline gateway later.
- **Billing-grade correctness over pretty dashboards** — accuracy is the product.
- **Privacy-first by default** — payload logging is always opt-in, never default.
- **End-user analytics is first-class** — not an afterthought on a per-tenant view.
- **Auditability built into the architecture** — tamper-evidence, provenance, and policies from day one, even if compliance features ship later.

---

## Status

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🔲 | Planned |

---

## Product Areas

---

### 0 — Product Architecture Baseline ✅
**Implementation:** Phase 0 (infra) + Phase 1 (ingestion + auth)

**Core domain objects:**
- Tenant / Workspace
- Application / Environment (dev / staging / prod)
- End-user (`end_user_id`)
- Agent Run (`run_id`)
- Span (`span_id`, `parent_span_id`, `span_type`)
- Provider Call (model invocation — tokens, latency, cost)
- Tool Call (`tool_name`, `tool_type`, `risk_score`)
- Outcome Event (success / fail + optional business labels)

**Event ingestion & storage:**
- Ingestion API — single event (`POST /ingest/v1/events`) and batch (`POST /ingest/v1/batch`)
- Redis Stream queue — events buffered before pipeline writes to Postgres
- Celery pipeline worker — drains stream, validates, upserts all event types to Postgres
- Idempotency via `ON CONFLICT DO NOTHING` on all upserts
- Backfill / replay pipeline via `replay_backfill` Celery task (added in Phase 4)

**Privacy modes (groundwork):**
- `METADATA_ONLY` — default: tokens, model, latency only
- `ERRORS_ONLY` — metadata + payload on errors
- `SAMPLED` — metadata + payload on N% of calls
- `FULL` — capture everything (explicit opt-in)

**Multi-tenancy & auth:**
- Workspace-scoped API keys (`rl_live_` / `rl_test_` prefixes)
- Bearer token authentication on all API endpoints
- Admin secret for workspace/key management (`X-Admin-Secret`)
- RBAC skeleton: admin, billing_admin, viewer roles

**Deployment:**
- Docker Compose stack: Postgres 16 + Redis 7 + FastAPI API + Celery worker + Next.js web
- Dev overrides with hot reload
- Makefile targets: `make dev`, `make migrate`, `make test`, `make lint`

**Definition of done:** ✅ Events ingested reliably, deduped, replayable, and queryable with correct workspace attribution.

---

### 1 — OSS Adoption Layer: SDKs + Drop-in Instrumentation ✅
**Implementation:** Phase 2 (OpenAI + context) + Phase 3 (LangChain + LangGraph + CLI)

**OpenAI instrumentation:**
- `rl.instrument()` — monkey-patches `openai.OpenAI` and `openai.AsyncOpenAI`
- Captures model, input/output tokens, cached input tokens, latency, status, error type
- Works from both sync and async call sites via background-thread transport

**Context propagation:**
- `rl.context(end_user_id, session_id, feature_tag, deployment_version)` — context manager
- Thread-safe and async-safe via `contextvars.ContextVar`
- Nested contexts inherit and selectively override parent values
- `rl.propagation_headers()` — serialises context to HTTP headers for cross-service propagation
- `RunLedger.from_headers(headers)` — restores context from inbound request headers

**LangChain integration:**
- `RunLedgerCallbackHandler` — implements `BaseCallbackHandler`
- Fires `run_start` / `run_end` at chain boundaries, `span_start` / `span_end` per node
- Uses LangChain's `run_id` / `parent_run_id` as `span_id` / `parent_span_id` for exact DAG reconstruction
- Captures token usage from `LLMResult` (handles OpenAI and Anthropic usage formats)

**LangGraph integration:**
- `instrument_graph(graph, transport)` — attaches handler via `graph.with_config({"callbacks": [...]})` — zero intrusion
- `RunLedgerNodeWrapper` — manual per-node wrapper for custom executors (sync + async)

**Developer experience:**
- 1-line enablement: `rl.instrument()` + `rl.context(...)`
- `local=True` mode — events logged to stdout as structured JSON, no API key needed
- `runledger validate` — sends a synthetic test event and confirms acceptance
- `runledger runs` — lists recent agent runs as a rich table
- `runledger status` — checks API + DB + Redis health
- 5 runnable example agents in `examples/`
- `QUICKSTART.md` — end-to-end getting-started guide

**Definition of done:** ✅ Team instruments an agent in minutes and sees runs, spans, tokens, latency, and tool calls.

---

### 2 — Observability UI: Run Explorer + DAG Viewer 🔲
**Implementation:** Phase 5

**Run Explorer (`/runs`):**
- Search by `run_id` prefix, `end_user_id`, `feature_tag`, model, status, time window
- `RunsTable`: truncated run_id, end_user_id, primary model, total cost, status badge, duration, started_at
- Cursor-based pagination (not page numbers)
- Filters: status, model, end_user_id, feature_tag, time window (1h / 6h / 24h / 7d / custom)

**Run Detail (`/runs/[run_id]`):**
- `RunGraph` (react-flow) — nodes for each span type (CHAIN, LLM, TOOL, AGENT), edges for parent-child links
  - Node colours: LLM=blue, TOOL=orange, CHAIN=gray, error=red
  - Node badge: cost in USD + token count for LLM nodes
  - Click node → `SpanDetailPanel` slides in from right
- `SpanDetailPanel` — span type, duration, model, tokens, cost, error details, metadata JSONB viewer
- `RunSummaryBar` — total cost, total tokens, duration, status, end_user_id, feature_tag
- Payload status badge: "No payload captured" / "Payload available (request access)"

**Next.js foundation:**
- NextAuth.js credentials provider (email + password, bcrypt, JWT session)
- Typed API client (`lib/api.ts`) — reads `NEXT_PUBLIC_API_URL`, attaches session token
- Layout: sidebar nav, workspace switcher, top bar

**API routes added in this phase:**
- `GET /runs` — cursor-paginated list with filters
- `GET /runs/{run_id}` — run + all spans + provider_calls + tool_calls
- `GET /runs/{run_id}/graph` — DAG nodes + edges for react-flow

**Definition of done:** 🔲 Find a run, see every LLM + tool call in the DAG, click a node and see cost + token counts. DAG renders for 50+ nodes.

---

### 3 — Billing-grade Metering Core ✅
**Implementation:** Phase 4

**Pricing engine:**
- `provider_pricing` table — effective-dated pricing, workspace-specific overrides
- `calculate_cost(provider, model, input_tokens, output_tokens, cached_tokens, at_time)` → `Decimal | None`
  - Workspace override checked first, falls back to global pricing
  - Cached input discount: uses `cached_input_cost_per_1m` if set, defaults to 50% of input rate
  - Returns `None` if no pricing row exists (flagged by data quality worker)
- Seeded pricing for 11 models: OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1, o3-mini), Anthropic (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5), Google (gemini-1.5-pro, gemini-1.5-flash)
- Add new models via database row — no code change required

**Celery workers (all idempotent):**
- `cost_enrichment_worker` — runs every 60s; computes `cost_usd` for uncost provider_calls; rolls up to `span.cost_usd` and `agent_run.total_cost_usd`
- `rollup_hourly_worker` — every 30 min; full DELETE + INSERT for a 2-hour window into `usage_hourly`
- `rollup_daily_worker` — daily at 00:05 UTC; aggregates `usage_hourly` → `usage_daily` for previous day
- `data_quality_worker` — every hour; flags calls with missing tokens or missing cost in `data_quality_issues`
- `replay_backfill` — one-shot task; clears costs for a time range and re-enriches (used after pricing corrections)

**Analytics API:**
- `GET /analytics/summary` — total cost, tokens, run count, call count for a time window
- `GET /analytics/spend-over-time?granularity=hourly|daily` — time-series array
- `GET /analytics/spend-by-model` — breakdown by provider + model, ordered by cost
- `GET /analytics/spend-by-user?limit=N` — top N end-users by spend
- `GET /analytics/spend-by-feature` — breakdown by `feature_tag`

**Definition of done:** ✅ Replaying the same events twice produces identical cost totals. Effective-dated pricing returns different values before/after a price change date.

---

### 4 — Reconciliation + Dispute Trail 🔲
**Implementation:** Phase 8

**Invoice period close:**
- Freeze a `usage_daily` snapshot for the period
- Generate signed `usage_statement` JSON artifact
- Late events flagged in `agent_runs.late_event = true`

**Reconciliation checks (nightly Celery):**
- Sum of `provider_calls.cost_usd` = sum via `usage_daily` within 0.01% tolerance
- Flag orphaned provider_calls (no parent agent_run)
- Flag duplicate provider_calls (same run_id + model + timestamp within 1s)
- Report: `GET /billing/periods/{id}/reconciliation`

**Dispute trail:**
- `GET /billing/periods/{id}/breakdown` — hierarchical: period → app → end_user → model → runs → spans + calls
- `GET /billing/periods/{id}/export?format=csv` — columns: date, end_user_id, model, input_tokens, output_tokens, cost_usd, run_id
- `GET /billing/periods/{id}/export?format=signed_json` — JSON + HMAC signature (verifiable offline)

**Definition of done:** 🔲 Finance team asks "why is this bill high?" and can prove it with trace-linked evidence exportable as a signed artifact.

---

### 5 — Chargeback Engine + Billing Packaging 🔲
**Implementation:** Phase 8 (chargeback rules) + later phases (packaging)

**Chargeback rules:**
- Allocate spend by team / cost center, tenant / customer, end-user, environment (prod vs dev)
- Weight-based splits and explicit dimension assignments via `chargeback_rules` table

**Billing packaging:**
- Credits wallets and prepaid bundles
- Overage policies
- Per-seat + usage hybrids
- Billing portal for end-customers: usage dashboard + invoice download

**Revenue analytics:**
- Gross margin estimator (if reselling model usage)
- Cost of goods per tenant / plan

**Definition of done:** 🔲 Customer can launch or improve their AI product monetisation with minimal custom work.

---

### 6 — Budgets + Spend Guardrails 🔲
**Implementation:** Phase 7

**Budget objects:**
- Scoped by: workspace, end-user, application / environment, feature_tag
- Period types: daily, monthly, total
- Actions: notify, throttle, block, downgrade (switch to cheaper model)

**Hot-path enforcement (<5ms p99):**
- Redis counter per budget scope: `rl:budget:{budget_id}:spend:{period_key}`
- SDK pre-call check: `GET /budgets/check` → `{allowed, action, model}` — Redis only, no Postgres
- SDK: `downgrade` action silently substitutes model; `block` raises `RunLedgerBudgetExceededError`

**Runaway protection (Celery, every 5 min):**
- Retry storm: >20 provider_calls for a single run_id in last 2 min
- Tool loop: same `tool_name` called >N times consecutively
- Token spike: single provider_call input_tokens >100k (configurable)

**Notifications:**
- Webhook: POST to destination URL with HMAC-signed payload
- Slack: POST to webhook URL with formatted message

**Budget API:**
- `POST /budgets` — create budget
- `GET /budgets` — list with current spend from Redis counters
- `GET /budgets/{id}/breaches` — breach history with action_taken log
- `DELETE /budgets/{id}` — deactivate

**Definition of done:** 🔲 Create a $0.10 daily budget, exceed it, 6th call is blocked, webhook fires, breach appears in UI.

---

### 7 — Budget-aware Routing & Optimisation 🔲
**Implementation:** Future phase (post month 6)

**Async recommendations (no proxy required):**
- "Should have used a cheaper model" post-hoc suggestions
- Policy simulator: "if we cap at $X, what would have changed?"

**Optional enforcement plane:**
- Lightweight OpenAI-compatible proxy (Docker container)
- Inline enforcement of routing and budget actions

**Routing policies:**
- Failover rules
- Cheapest model that meets quality / SLO target
- Workload tiers: support agent vs sales agent

**Optimisation features:**
- Caching hints
- Prompt / version targeting
- Provider throttling handling

**Definition of done:** 🔲 Customers see measurable savings tied directly to routing policies and budgets.

---

### 8 — Unit Economics Graph + Change Impact 🔲
**Implementation:** Phase 9

**True cost attribution per run:**
- Cost by span type: `{llm, tool, retrieval, retry, approval}`
- Cost by model within a run
- Retry cost separated from first-attempt cost

**Deployment versioning:**
- SDK `rl.context(deployment_version="v2.1.0")` — stored in `agent_runs.deployment_version`

**Change impact API:**
- `GET /analytics/compare?baseline_version=&comparison_version=` — cost delta, token delta, latency delta per span type
- `GET /analytics/regressions` — workflows where cost >120% of same-period prior week average
- `POST /analytics/annotations` — team notes attached to a date or version

**UI — `/analytics/economics`:**
- Stacked cost bar per run or feature_tag, split by LLM / tool / retrieval / retry
- Version comparison: side-by-side delta cards
- Regression table with % increase and volume context
- Annotation markers on spend timeline

**Definition of done:** 🔲 Tag 50 runs with v1 and 50 with v2. Compare endpoint returns correct per-node-type cost deltas.

---

### 9 — Replay Harness + Experiment System 🔲
**Implementation:** Phase 10

**Replay datasets:**
- Save a set of live run inputs as a named dataset (respects privacy mode)
- Synthetic dataset support

**Experiment runner:**
- Run same dataset tasks across: two prompts, two models, two routing policies
- Cost estimate shown before firing (requires explicit confirmation)

**Outcome scoring:**
- Simple labels from `outcome_events`
- Hooks for plugging in external eval scores

**Results:**
- Per-config: avg cost, p50 / p95 latency, success rate
- Delta table: config A vs config B — cost delta, latency delta, success rate delta

**Definition of done:** 🔲 Run 10 tasks against gpt-4o vs gpt-4o-mini, see cost delta and latency comparison.

---

### 10 — End-user Analytics (Product-grade) 🔲
**Implementation:** Phase 6 (dashboard) + Phase 10 (cohorts + anomaly detection)

**End-user drilldowns:**
- Cost per end-user, tokens per end-user, outcomes per end-user
- User profile: spend over time (30d), models used, feature tags, run count, avg cost/run

**Cohort analysis:**
- Spend tiers: P0 (<$1/mo), P1 ($1–10), P2 ($10–100), P3 ($100+)
- Retention vs cost by first-seen week

**Segmentation:**
- By feature_tag, plan / tier, geography (if provided)

**Anomaly detection (nightly Celery):**
- Z-score of today's spend vs 30d mean per active user
- Flag users with Z >3 in `user_anomalies` table
- `GET /analytics/users/anomalies` — flagged users with anomaly reason

**Definition of done:** 🔲 Product + customer success teams can identify top spenders, churn risk, and suspicious usage patterns.

---

### 11 — Security Boundaries + Tool Risk Scoring 🔲
**Implementation:** Phase 11

**Tool registry:**
- Classify tools: read / write / privileged
- Attach risk scores (0–10)
- `rl.register_tool(name, risk_level)` SDK method — sends metadata on first call

**Policy rules:**
- Require human approval for privileged actions
- Restrict certain tools to certain workspaces / environments
- Detect suspicious sequences (same tool called >5 times in <60s)

**Action governance:**
- Approval workflow + audit history
- Break-glass access patterns
- Security events table for flagged sequences

**Definition of done:** 🔲 Teams can safely enable agents that can "do things," not just "say things."

---

### 12 — Tamper-evident Usage Ledger 🔲
**Implementation:** Phase 11

**Signed snapshots:**
- Nightly Celery job: daily summary per workspace signed with HMAC-SHA256 using rotating keys
- `GET /ledger/snapshots` — list of daily signed snapshots
- `GET /ledger/snapshots/{date}/verify` — re-compute and verify signature offline

**Immutable evidence packs:**
- `GET /ledger/export/{billing_period_id}` — ZIP: `totals.json` + `run_index.json` + `integrity.json`
- Key rotation: monthly, old keys retained for verification

**Retention policy:**
- Configurable retention for raw events vs summaries
- Immutable summaries outlast raw logs (privacy-friendly)

**Definition of done:** 🔲 Usage accounting trusted even when payload logging is off and raw logs are pruned. Signature verifiable offline.

---

### 13 — Privacy-first Governance + Controls 🔲
**Implementation:** Phase 11

**Capture policies:**
- Per workspace / environment / tool / error type
- Configurable sampling and allowlists
- `POST /privacy/policies` — create a scoped capture policy

**Redaction pipeline:**
- Configurable PII patterns
- Customer-provided redaction functions

**Access controls:**
- Payload access approval workflow: `POST /privacy/access-requests/{span_id}`
- Audit log for every payload view in `payload_access_log`

**Definition of done:** 🔲 Deploy broadly across customers with minimal legal / security friction.

---

### 14 — Integrations Ecosystem 🔲
**Implementation:** Future phase (post month 6)

**Billing systems:**
- Stripe: invoices, credits, plan tiers (or adapter interface)

**Data / BI:**
- Export to warehouse (Snowflake / BigQuery / Redshift) via connectors or scheduled dumps

**Incident & communications:**
- Slack / Teams alerts (budget breaches, anomalies, regressions)
- Webhook to incident tools (PagerDuty-style)

**Developer workflows:**
- GitHub PR comment: "this change increases cost by X%"
- CI gate: block rollout if cost regression exceeds threshold

**Definition of done:** 🔲 RunLedger sits in existing customer workflows — hard to replace.

---

### 15 — Packaging: OSS + Paid Split 🔲
**Implementation:** Phase 11

**Open source (drives adoption):**
- Python SDK: LangGraph / LangChain / OpenAI integrations
- Collector + local viewer
- Basic metering + dashboards (single tenant)
- Local replay harness

**Paid (creates stickiness):**
- Multi-tenant analytics + end-user billing portal
- Reconciliation + dispute tooling
- Budgets with enforcement actions
- Routing policies + optional gateway
- Tamper-evident ledger + evidence packs
- Advanced integrations + RBAC / SSO (enterprise)

**Feature gating:**
- `FeatureGate` middleware reads `workspace.plan`
- `RUNLEDGER_MODE=oss` env var disables all paid gates for self-hosted users

**Definition of done:** 🔲 OSS is useful standalone; production-grade financial control requires the paid layer.

---

## Feature-to-Phase Mapping

| Product area | Phase(s) | Status |
|---|---|---|
| 0 — Architecture baseline | 0, 1 | ✅ |
| 1 — SDKs + instrumentation | 2, 3 | ✅ |
| 2 — Observability UI | 5 | 🔲 |
| 3 — Metering core | 4 | ✅ |
| 4 — Reconciliation + dispute | 8 | 🔲 |
| 5 — Chargeback engine | 8 | 🔲 |
| 6 — Budgets + guardrails | 7 | 🔲 |
| 7 — Budget-aware routing | Future | 🔲 |
| 8 — Unit economics + change impact | 9 | 🔲 |
| 9 — Replay harness | 10 | 🔲 |
| 10 — End-user analytics | 6, 10 | 🔲 |
| 11 — Security + tool risk | 11 | 🔲 |
| 12 — Tamper-evident ledger | 11 | 🔲 |
| 13 — Privacy governance | 11 | 🔲 |
| 14 — Integrations | Future | 🔲 |
| 15 — OSS / paid packaging | 11 | 🔲 |
