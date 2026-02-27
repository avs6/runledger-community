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

**Spend guardrails that change behavior** — budgets with automatic actions (throttle / block / downgrade model) for runaway loops and retry storms.

**Provider-aware metering** — input vs output tokens (plus cached input where available) mapped to provider pricing so your internal numbers match the invoice.

**Reconciliation + dispute trail** — prove every invoice line item back to the exact agent run and steps, even with payload logging off.

**End-user analytics** — cost per user/tenant/feature, cost-per-outcome, cohorts, top spenders, anomaly users — built for customer-facing agents.

**Agent unit economics graph** — cost breakdown across steps, tools, retrieval, retries, and human approvals, plus "what changed?" diffs after prompt or model updates.

**Budget-aware router** — route by cost/quality SLO: fallbacks, cheapest-model-that-meets-target, and caching-aware economics.

**Tamper-evident usage ledger** — cryptographic integrity for usage summaries so finance teams can trust chargeback and invoices.

**Privacy-first modes** — payload logging off / errors-only / sampled / full. Deploy safely from day one.

---

## Quick Start

> **Phase 1 is live.** The ingestion API, multi-tenancy, and API-key auth are fully operational. SDK instrumentation (OpenAI + LangChain/LangGraph) ships in Phase 2/3.

**Run locally:**
```bash
git clone https://github.com/yourorg/runledger
cd runledger
make install        # uv sync --all-packages + npm install
make dev-infra      # start Postgres + Redis via Docker Compose
make migrate        # apply initial schema (9 tables, 6 enum types)
make seed           # create default tenant + workspace + API key
make dev-api        # FastAPI with hot-reload at http://localhost:8000
```

**Ingest your first event:**
```bash
# Use the API key printed by `make seed`
curl -X POST http://localhost:8000/ingest/v1/events \
  -H "Authorization: Bearer rl_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "run_start",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "started_at": "2026-02-26T10:00:00Z",
    "feature_tag": "support-chat"
  }'
# → {"accepted": 1}
```

**Batch ingest (typical SDK flow):**
```bash
curl -X POST http://localhost:8000/ingest/v1/batch \
  -H "Authorization: Bearer rl_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"event_type": "run_start", "run_id": "...", "started_at": "..."},
      {"event_type": "provider_call", "run_id": "...", "provider": "openai",
       "model": "gpt-4o", "input_tokens": 512, "output_tokens": 128,
       "cost_usd": "0.00384", "status": "success"},
      {"event_type": "run_end", "run_id": "...", "status": "succeeded",
       "ended_at": "...", "total_cost_usd": "0.00384"}
    ]
  }'
# → {"accepted": 3}
```

**SDK (coming in Phase 2/3):**
```python
from runledger_sdk import RunLedger

rl = RunLedger(api_key="rl_live_...")
rl.instrument()  # patches OpenAI + LangChain/LangGraph automatically

with rl.context(end_user_id="user_123", feature_tag="support-chat"):
    response = openai_client.chat.completions.create(...)
```

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
│                    RunLedger Platform                        │
│                                                             │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │  Collector API │──▶│  Redis Streams (event buffer)    │  │
│  │  (FastAPI)     │   └──────────────┬───────────────────┘  │
│  └────────────────┘                  │                      │
│                             ┌────────▼────────┐            │
│  ┌────────────────┐         │  Celery Workers  │            │
│  │  Business API  │         │  - metering      │            │
│  │  (FastAPI)     │◀────────│  - aggregations  │            │
│  └───────┬────────┘         │  - guardrails    │            │
│          │                  └────────┬─────────┘            │
│  ┌───────▼────────────────────────────────────┐             │
│  │              PostgreSQL                     │             │
│  │  events · spans · metering · budgets        │             │
│  │  billing periods · ledger · policies        │             │
│  └─────────────────────────────────────────────┘            │
│                                                             │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │  Redis (cache) │   │  Budget Enforcement (hot path)   │  │
│  │  idempotency   │   │  <5ms p99 spend check            │  │
│  └────────────────┘   └──────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┬─┘
                                                            │
                            ┌───────────────────────────────▼─┐
                            │        RunLedger UI              │
                            │        (Next.js 14)              │
                            │                                  │
                            │  Run Explorer · DAG Viewer       │
                            │  Metering · Budgets · Chargeback │
                            │  Unit Economics · Analytics      │
                            └──────────────────────────────────┘
```

---

## API Reference (Phase 1)

All ingest endpoints require `Authorization: Bearer <api_key>`.
Admin endpoints require `X-Admin-Secret: <secret_key>`.

### Ingest

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/v1/events` | Ingest a single event (202, async) |
| `POST` | `/ingest/v1/batch` | Ingest a batch of events (202, async) |
| `GET`  | `/ingest/v1/runs` | List agent runs for the workspace |

**Event types:** `run_start` · `run_end` · `span_start` · `span_end` · `provider_call` · `tool_call` · `outcome`

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/tenants` | Create tenant |
| `GET`  | `/admin/tenants` | List tenants |
| `POST` | `/admin/workspaces` | Create workspace |
| `GET`  | `/admin/tenants/{id}/workspaces` | List workspaces for tenant |
| `POST` | `/admin/applications` | Create application |
| `POST` | `/admin/workspaces/{id}/api-keys` | Create API key (returns raw key once) |
| `GET`  | `/admin/workspaces/{id}/api-keys` | List active API keys |
| `DELETE` | `/admin/api-keys/{id}` | Revoke API key |

Interactive docs: `http://localhost:8000/docs`

---

## OSS vs Paid

**Open source (free forever):**
- SDK — LangChain, LangGraph, OpenAI
- Collector + event pipeline
- Run explorer + DAG viewer
- Basic metering + spend dashboard (single tenant)
- Local replay harness

**Paid (production FinOps):**
- Multi-tenant analytics + end-user billing portal
- Reconciliation + dispute tooling
- Budget enforcement with automatic actions
- Routing policies + optional enforcement gateway
- Tamper-evident ledger + evidence packs
- Advanced integrations (Stripe, data warehouse, CI gates)
- RBAC + SSO (enterprise)

---

## Roadmap

See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) for the full 6-month technical implementation plan.

| Phase | What ships | Status |
|-------|------------|--------|
| 0 | Monorepo + infrastructure foundation | ✅ Done |
| 1 | Ingestion API + multi-tenancy + auth | ✅ Done |
| 2 | SDK — OpenAI wrapper + context propagation | Planned |
| 3 | SDK — LangChain + LangGraph + CLI | Planned |
| 4 | Billing-grade metering core + pricing engine | Planned |
| 5 | Run Explorer + DAG viewer UI | Planned |
| 6 | Metering dashboard (spend by model/user/feature) | Planned |
| 7 | Budgets + spend guardrails with automatic actions | Planned |
| 8 | Chargeback engine + reconciliation + dispute trail | Planned |
| 9 | Unit economics graph + change impact diffs | Planned |
| 10 | End-user analytics + replay harness | Planned |
| 11 | Tamper-evident ledger + production polish + OSS release | Planned |

---

## Deployment

**Local / self-hosted:**
```bash
git clone https://github.com/yourorg/runledger
cd runledger
make install && make dev-infra && make migrate && make seed
make dev-api    # API at http://localhost:8000
make dev-web    # UI  at http://localhost:3000  (Phase 5)
```

**Full stack via Docker Compose:**
```bash
make dev        # starts Postgres + Redis + API + Worker + Web
```

**Cloud (Railway / Render / Fly.io):** deployment guide coming in Phase 4.

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).

The core SDK and collector are open source. The paid tier (multi-tenancy, enforcement, ledger, enterprise integrations) is offered as a hosted service and under a commercial license.
