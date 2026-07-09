# RunLedger Community

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/avs6/runledger-community)

**Self-hosted AI cost observability and budget control for production agents.**

RunLedger Community is an open-source FinOps control plane for AI agents. It turns OpenAI, Anthropic, Gemini, Mistral, Cohere, LangChain, LangGraph, and any OpenTelemetry-instrumented agent into trace-linked usage accounting, budget enforcement, cost analytics, and outcome-to-cost visibility -- with payload logging optional by default.

Tracing tools tell you *what happened*. RunLedger tells you *what it cost, who pays, whether you're over budget, and what the ROI was.*

---

## The Problem

Every team shipping AI agents in production hits the same wall:

- **Spend explodes** -- a retry loop or runaway agent silently burns through API budget overnight
- **Attribution is guesswork** -- you can't attribute cost to a tenant, user, or feature without custom instrumentation
- **Routing isn't tied to economics** -- model selection is based on capability, not cost-per-outcome
- **No audit trail** -- no link between internal metering and the exact agent run that generated the spend

---

## What's Included

- **Provider-aware metering** -- input vs output tokens (plus cached input) mapped to provider pricing tables
- **Spend guardrails** -- budgets with automatic actions (throttle / block / downgrade model) for runaway loops and retry storms
- **End-user analytics** -- cost per user/tenant/feature, cohorts, top spenders, anomaly detection
- **Unit economics graph** -- cost breakdown across steps, tools, retrieval, retries; "what changed?" diffs after prompt or model updates
- **Tamper-evident usage ledger** -- HMAC-signed snapshots for billing integrity
- **Model gateway** -- OpenAI-compatible proxy with prompt caching, provider fallback, and cost-aware routing
- **Outcome & ROI ledger** -- tie spend to business outcomes: cost-per-success, ROI by workflow, success rate trends
- **Approvals & governance** -- require approval for prompt production promotions and sensitive policy changes
- **OTLP / OpenTelemetry ingestion** -- accept traces from any OTel or OpenInference instrumented application, no SDK required
- **Evaluations & experiments** -- submit quality scores, run prompt x model x dataset evaluations, track regressions
- **Prompt registry** -- version-controlled prompts with diff viewer, promote-to-production workflow, variable substitution
- **Multi-tenant RBAC** -- workspace-scoped isolation with org admin, workspace admin, member, and viewer roles
- **Privacy-first** -- payload logging off by default; errors-only / sampled / full are explicit opt-ins
- **MCP server** -- connect Claude Desktop or Claude Code directly to your RunLedger instance

---

## Architecture

<img width="1408" height="768" alt="RunLedger Architecture" src="https://github.com/user-attachments/assets/f57882fb-c531-4e02-80d4-6c6e9b512a76" />

**Ingestion paths:**

| Path | When to use |
|------|-------------|
| **RunLedger SDK** | Best path -- budget enforcement, `rl.score()`, prompt fetch, propagation headers |
| **OTLP direct** | Already emit OTel / OpenInference; zero instrumentation change |
| **OTLP via Collector** | Production -- batching, retry, attribute enrichment |
| **Model Gateway** | OpenAI base_url swap -- works for any OpenAI-compatible client |

All paths normalise into the same domain model: `AgentRun -> Span -> ProviderCall / ToolCall`.

---

## Quickstart

**Docker Compose (recommended):**

```bash
git clone https://github.com/avs6/runledger-community
cd runledger-community
cp infra/.env.example infra/.env   # set SECRET_KEY
docker compose -f infra/docker-compose.yml up -d
```

Then bootstrap the admin:

```bash
curl -s -X POST http://localhost:8000/admin/bootstrap \
  -H "X-Admin-Secret: runledger-admin" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin123!","full_name":"Admin","org_name":"My Org"}'
```

| URL | What it is |
|-----|------------|
| `http://localhost:3000` | Dashboard |
| `http://localhost:8000/reference` | Interactive API reference (Scalar) |
| `http://localhost:4318` | OTLP/HTTP receiver (via OTel Collector) |

---

## Instrument Your Code

### Python -- 2 lines

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

rl.shutdown()
```

Also supports Anthropic, LangChain, LangGraph, async, and cross-service propagation.

### TypeScript -- 2 lines

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

---

## Model Gateway

Point any OpenAI client at RunLedger's proxy -- change only `base_url`:

```python
import openai

client = openai.OpenAI(
    api_key="rl_...",
    base_url="http://localhost:8000/gateway",
)
resp = client.chat.completions.create(model="gpt-4o-mini", messages=[...])
# First call -> forwarded to provider. Identical second call -> cache hit (<5ms).
```

---

## Dashboard Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/dashboard` | Spend summary, key metrics |
| Run Explorer | `/runs` | Filter + paginate runs; DAG viewer; CSV export |
| Sessions | `/sessions` | Multi-turn conversations; cost-over-turns chart |
| Analytics | `/analytics` | Spend charts, top spenders, economics |
| Budgets | `/budgets` | Create budgets, live spend progress, breach history |
| Outcomes & ROI | `/outcomes` | Cost-per-outcome, workflow ROI, success rate trends |
| Evaluations | `/evaluations` | Submit + view quality scores, regressions |
| Experiments | `/experiments` | Run prompt x model x dataset evaluations |
| Prompts | `/prompts` | Version-controlled registry, diff viewer, promote |
| Gateway | `/gateway` | Routes, routing log, runtime controls |
| Approvals | `/approvals` | Governance queue for sensitive actions |
| Monitoring | `/monitoring` | Alert rules, metric thresholds |
| Settings | `/settings` | API keys, MCP setup, alerts, integrations, retention |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.13 |
| API framework | FastAPI (async) |
| Database | PostgreSQL 16 (partitioned tables + materialized views) |
| Queue / cache | Redis 7 (Streams + budget hot-path) |
| Workers | Celery + Redis broker |
| SDKs | Python (`runledger-sdk`) + TypeScript (`@runledger/sdk`) |
| Frontend | Next.js 14, App Router, TypeScript, Tailwind, shadcn/ui, Recharts |
| Migrations | Alembic |
| Package manager | uv (workspaces) |
| Deploy | Docker Compose (local), Railway (managed) |

---

## Supported Providers

| Provider | SDK |
|----------|-----|
| OpenAI (gpt-4o, gpt-4o-mini, o1, o3-mini, ...) | Python + TypeScript |
| Anthropic (Claude Opus, Sonnet, Haiku, ...) | Python + TypeScript |
| Google Gemini | Python + TypeScript |
| Mistral | Python + TypeScript |
| Cohere | Python + TypeScript |
| Any OpenAI-compatible (Ollama, vLLM, Groq, Azure, Bedrock, Vertex) | Python + TypeScript |

Add a new model by inserting a row into `provider_pricing` -- no code change required.

---

## Development

```bash
# Install all workspace dependencies
uv sync --all-packages

# API (dev server)
cd apps/api && uv run fastapi dev runledger_api/main.py

# Celery worker + beat
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

## Community vs Enterprise

| Feature | Community | Enterprise |
|---------|:---------:|:----------:|
| SDK instrumentation (Python + TypeScript) | Y | Y |
| OTLP / OpenTelemetry ingestion | Y | Y |
| Core metering + pricing engine | Y | Y |
| Budgets + spend guardrails | Y | Y |
| Analytics + dashboards | Y | Y |
| Model gateway + prompt caching | Y | Y |
| Evaluations + experiments | Y | Y |
| Prompt registry | Y | Y |
| Outcomes & ROI | Y | Y |
| Approvals & governance | Y | Y |
| Multi-tenant RBAC | Y | Y |
| Alert rules | Y | Y |
| Data retention policies | Y | Y |
| Provider invoice reconciliation | | Y |
| Chargeback engine + cost centers | | Y |
| SSO / OIDC + SCIM provisioning | | Y |
| Warehouse export (S3/GCS/R2) | | Y |
| BYOK / KMS encryption | | Y |
| Advanced routing policies | | Y |
| Finance system exports (QuickBooks, NetSuite) | | Y |
| Kafka event streaming | | Y |
| Pricing contracts + credits | | Y |

Enterprise features are available separately -- [contact for details](mailto:abijith13@gmail.com).

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR process.

---

## License

[Apache License 2.0](LICENSE)
