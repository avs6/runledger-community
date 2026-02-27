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

```python
pip install runledger-sdk
```

```python
from runledger_sdk import RunLedger

# One line to instrument your entire app
rl = RunLedger(api_key="rl_live_...")
rl.instrument()  # patches OpenAI + LangChain/LangGraph automatically

# Optionally attach user context
with rl.context(end_user_id="user_123", feature_tag="support-chat"):
    response = openai_client.chat.completions.create(...)
```

That's it. Your runs, steps, tokens, latency, and cost are now flowing into RunLedger.

**LangChain / LangGraph:**
```python
from runledger_sdk.langchain import RunLedgerCallbackHandler

handler = RunLedgerCallbackHandler(api_key="rl_live_...")

# Attach to any chain or graph
chain.invoke(input, config={"callbacks": [handler]})
```

**Validate your instrumentation:**
```bash
runledger validate --api-key rl_live_...
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
| 0 | Monorepo + infrastructure foundation | Planned |
| 1 | Ingestion API + multi-tenancy + auth | Planned |
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
docker compose up
```

Open `http://localhost:3000`.

**Cloud (Railway / Render / Fly.io):**
See the [deployment guide](./docs/deployment.md).

---

## License

Apache 2.0 — see [LICENSE](./LICENSE).

The core SDK and collector are open source. The paid tier (multi-tenancy, enforcement, ledger, enterprise integrations) is offered as a hosted service and under a commercial license.
