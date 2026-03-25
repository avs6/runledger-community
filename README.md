# RunLedger

[![CI](https://github.com/avs6/runledger/actions/workflows/ci.yml/badge.svg)](https://github.com/avs6/runledger/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/avs6/runledger)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/avs6/runledger)

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

- **Provider-aware metering** — input vs output tokens (plus cached input) mapped to provider pricing so internal numbers match the invoice
- **Spend guardrails** — budgets with automatic actions (throttle / block / downgrade model) for runaway loops and retry storms
- **Provider invoice reconciliation** — import billing exports from OpenAI, Anthropic, Google; match against internal calls by request ID; export signed dispute packages
- **End-user analytics** — cost per user/tenant/feature, cohorts, top spenders, anomaly detection
- **Unit economics graph** — cost breakdown across steps, tools, retrieval, retries, and human approvals; "what changed?" diffs after prompt or model updates
- **Tamper-evident usage ledger** — cryptographic integrity for usage summaries so finance teams can trust chargeback and invoices
- **Model gateway** — OpenAI-compatible proxy with prompt caching, provider fallback, cost-aware routing policies, outcome-optimized routing, and full request logging
- **Outcome & ROI ledger** — tie spend to business outcomes: cost-per-success, ROI by workflow, success rate trends
- **Approvals & governance** — require approval for prompt production promotions, budget increases, and sensitive policy changes
- **OTLP / OpenTelemetry ingestion** — accept traces from any OTel or OpenInference instrumented application, no SDK required
- **SSO / SCIM** — OIDC single sign-on and SCIM 2.0 user provisioning for enterprise deployments
- **Warehouse export** — daily Parquet/JSONL exports to S3, GCS, or R2 for BI and data warehouse
- **Privacy-first** — payload logging off by default; errors-only / sampled / full are explicit opt-ins

---

## Architecture

<img width="1408" height="768" alt="image" src="https://github.com/user-attachments/assets/f57882fb-c531-4e02-80d4-6c6e9b512a76" />

---

**Ingestion paths:**

| Path | When to use |
|------|-------------|
| **RunLedger SDK** | Best path — budget enforcement, `rl.score()`, prompt fetch, propagation headers |
| **OTLP direct** | Already emit OTel / OpenInference; zero instrumentation change |
| **OTLP via Collector** | Production — batching, retry, attribute enrichment |
| **Model Gateway** | OpenAI base_url swap — works for any OpenAI-compatible client |

All paths normalise into the same domain model: `AgentRun → Span → ProviderCall / ToolCall`.

---

## Quickstart

**Docker Compose (recommended):**

```bash
git clone https://github.com/avs6/runledger
cd runledger
cp infra/.env.example infra/.env   # set SECRET_KEY
docker compose -f infra/docker-compose.yml up -d
```

Then bootstrap the platform admin:

```bash
curl -s -X POST http://localhost:8000/admin/bootstrap \
  -H "X-Admin-Secret: runledger-admin" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!","full_name":"Platform Admin","org_name":"My Org"}'
```

| URL | What it is |
|-----|------------|
| `http://localhost:3000` | Dashboard |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/reference` | Scalar API reference |
| `http://localhost:4318` | OTLP/HTTP receiver (via OTel Collector) |

→ **Full setup guide, Codespaces, Railway deploy, pip install:** [docs/quickstart.mdx](docs/quickstart.mdx)

---

## Instrument Your Code

### Python — 2 lines

```python
from runledger_sdk import RunLedger
import openai

rl = RunLedger(api_key="rl_...")   # or RUNLEDGER_API_KEY env var
rl.instrument()                     # wraps openai.OpenAI + AsyncOpenAI

client = openai.OpenAI()

with rl.context(end_user_id="u_123", feature_tag="support-chat") as run_id:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )

rl.shutdown()  # flush before process exits
```

**Anthropic, LangChain, LangGraph, async, FastAPI, cross-service propagation:** [docs/quickstart.mdx](docs/quickstart.mdx)

### TypeScript — 2 lines

```typescript
import OpenAI from 'openai'
import { RunLedger } from '@runledger/sdk'

const rl = new RunLedger({ apiKey: process.env.RUNLEDGER_API_KEY })
const openai = new OpenAI()
rl.instrument(openai)

const result = await rl.withContext(
  { endUserId: 'u_123', featureTag: 'support-chat' },
  async () => openai.chat.completions.create({ model: 'gpt-4o-mini', messages: [{ role: 'user', content: 'Hello!' }] }),
)
await rl.flush()
```

Also supports Gemini, Mistral, Cohere.

### Install

```bash
# Python
pip install "runledger-sdk[openai] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"
# or: pip install "runledger-sdk[all]"   # openai + anthropic + langchain + langgraph + otel + cli

# TypeScript
npm install ./packages/ts-sdk
```

---

## Model Gateway

Point any OpenAI client at RunLedger's proxy — change only `base_url`:

```python
import openai

client = openai.OpenAI(
    api_key="rl_...",
    base_url="http://localhost:8000/gateway",
)
resp = client.chat.completions.create(model="gpt-4o-mini", messages=[...])
# First call → forwarded to provider. Identical second call → cache hit (<5ms).
```

Routes support priority fallback, canary splits, cost-optimized selection, and **outcome-optimized routing** (picks the model with the best cost-per-success based on recorded outcomes).

---

## Dashboard

| Page | Path | Description |
|------|------|-------------|
| Run Explorer | `/runs` | Filter + paginate runs; DAG viewer; CSV export |
| Analytics | `/analytics` | Spend summary, charts, top spenders |
| User Profiles | `/analytics/users` | Cohorts, anomaly detection, per-user spend |
| Economics | `/analytics/economics` | Unit economics, version comparison, regressions |
| Budgets | `/budgets` | Create budgets, live spend progress, breach history |
| Billing | `/billing` | Billing periods, chargeback breakdown, signed export |
| Invoices | `/invoices` | Provider invoice import, reconciliation, dispute trail |
| Outcomes & ROI | `/outcomes` | Cost-per-outcome, workflow ROI, success rate trends |
| Sessions | `/sessions` | Multi-turn conversations; cost-over-turns chart |
| Evaluations | `/evaluations` | Submit + view quality scores, regressions |
| Prompts | `/prompts` | Version-controlled prompt registry, diff viewer, promote |
| Approvals | `/approvals` | Governance queue for sensitive actions |
| Replay | `/replay` | Cost-projection experiments across model configs |
| Ledger | `/ledger` | HMAC-signed snapshots, tool registry, privacy policy |
| Gateway | `/gateway` | Routes, routing log, outcome-aware insights, runtime controls |
| Settings | `/settings` | API keys, SSO/SCIM, alerts, integrations, warehouse, retention |
| Admin | `/admin` | Platform stats, tenant + user management (platform admin only) |

---

## Coming from LangSmith / Langfuse / Helicone?

RunLedger can run **alongside** your existing observability tool — or replace it. The migration is typically 1–3 lines.

| From | What changes | Guide |
|------|-------------|-------|
| **LangSmith** | Add `rl.callback_handler()` to the same `callbacks` list | [docs/migration/from-langsmith.mdx](docs/migration/from-langsmith.mdx) |
| **Langfuse** | Add `rl.instrument()` after `from langfuse.openai import openai` | [docs/migration/from-langfuse.mdx](docs/migration/from-langfuse.mdx) |
| **Helicone** | Change `base_url` from `oai.helicone.ai/v1` to `your-runledger/gateway` | [docs/migration/from-helicone.mdx](docs/migration/from-helicone.mdx) |

The key difference: the other tools focus on trace visibility and evals. RunLedger adds **finance-grade cost accounting** — invoice reconciliation, budget enforcement, chargeback, and tamper-evident billing snapshots.

---

## Documentation

| Doc | Contents |
|-----|----------|
| [Quickstart](docs/quickstart.mdx) | Full setup guide, all SDK providers, gateway, analytics API, troubleshooting |
| [Introduction](docs/introduction.mdx) | Product overview, ingestion paths, navigation |
| [OTLP integration](docs/otlp.md) | Route reference, attribute priority, error codes |
| [OpenInference mapping](docs/openinference.md) | Full attribute mapping tables |
| [OTel Collector config](docs/collector.md) | Reference configs, processor examples |
| [Railway deployment](docs/deployment.md) | Full production deployment guide |
| [Migration from LangSmith](docs/migration/from-langsmith.mdx) | Add RunLedger alongside or replace LangSmith |
| [Migration from Langfuse](docs/migration/from-langfuse.mdx) | Callback swap or wrapper replacement |
| [Migration from Helicone](docs/migration/from-helicone.mdx) | One `base_url` change |

---

## Supported Providers

| Provider | SDK |
|----------|-----|
| OpenAI (gpt-4o, gpt-4o-mini, o1, o3-mini, …) | Python + TypeScript |
| Anthropic (claude-opus-4-6, claude-sonnet-4-6, …) | Python + TypeScript |
| Google Gemini | Python + TypeScript |
| Mistral | Python + TypeScript |
| Cohere | Python + TypeScript |
| Any OpenAI-compatible (Ollama, vLLM, Groq, Azure, Bedrock, Vertex) | Python + TypeScript |

Add a new model by inserting a row into `provider_pricing` — no code change required.

---

## Development Commands

```bash
# Install all workspace dependencies
uv sync --all-packages

# API (dev server)
cd apps/api && uv run fastapi dev runledger_api/main.py

# Celery worker + beat (separate terminals)
cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
cd apps/api && uv run celery -A runledger_api.core.celery_app beat --loglevel=info

# Frontend
cd apps/web && npm run dev

# Migrations
cd apps/api && uv run alembic upgrade head

# Full local stack
docker compose -f infra/docker-compose.yml up

# Tests
cd apps/api && uv run pytest

# Lint + typecheck
uv run ruff check . && uv run mypy apps/api/runledger_api
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and the PR process.

---

## License

[MIT](LICENSE)
