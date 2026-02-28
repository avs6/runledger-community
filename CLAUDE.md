# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RunLedger is a **FinOps Control Plane for AI agents** — billing-grade usage accounting, budgets/chargeback, and economics-aware routing for LangGraph/LangChain + OpenAI. It is Docker-deployable and async-instrumentation-first. See `about.md` for the full product description and `IMPLEMENTATION.md` for the complete build plan (phases, schema, API routes, and specs).

This repo is the **OSS core** (`runledger`). Planned components: `runledger-sdk`, `runledger-collector`, `runledger-api`, `runledger-ui`, `runledger-gateway`, `runledger-replay`.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.13 |
| API framework | FastAPI (async) |
| Database | PostgreSQL 16 — partitioned tables + materialized views for metering |
| Queue / cache | Redis 7 (Streams for event buffering, hot path for budget enforcement) |
| Async workers | Celery + Redis broker |
| SDK | `runledger-sdk` Python package (PyPI) |
| Frontend | Next.js 14, App Router, TypeScript, Tailwind, shadcn/ui, Recharts |
| UI auth | NextAuth.js |
| DB migrations | Alembic |
| Package manager | uv (workspaces) |
| Deploy (prod) | Railway (managed Postgres + Redis + containers) |
| Deploy (local) | Docker Compose |

**No TimescaleDB, no ClickHouse.** Pure PostgreSQL with partitioning + materialized views is sufficient for V1 and keeps deployment anywhere (Railway's managed Postgres has no TimescaleDB extension).

## Commands

```bash
# Install all workspace dependencies (must use --all-packages for workspace)
uv sync --all-packages

# Run the API (dev)
cd apps/api && uv run fastapi dev runledger_api/main.py

# Run Celery worker
cd apps/api && uv run celery -A runledger_api.core.celery worker --loglevel=info

# Run frontend (dev)
cd apps/web && npm run dev

# Run database migrations
cd apps/api && uv run alembic upgrade head

# Full local stack
docker compose up

# Run tests
cd apps/api && uv run pytest

# Lint + typecheck
uv run ruff check . && uv run mypy apps/api

# Add a backend dependency
cd apps/api && uv add <package>

# Add an SDK dependency
cd packages/sdk && uv add <package>
```

## Monorepo Structure

```
runledger/
├── apps/api/               # FastAPI backend — collector + business API + Celery workers
│   └── runledger_api/
│       ├── core/           # Config, DB session, Redis client, Celery app
│       ├── models/         # SQLAlchemy ORM models
│       ├── schemas/        # Pydantic request/response schemas
│       ├── routers/        # FastAPI route handlers
│       ├── services/       # Business logic (metering, pricing, chargeback, guardrails)
│       └── workers/        # Celery tasks
├── apps/web/               # Next.js 14 frontend
├── packages/sdk/           # runledger-sdk (PyPI) — OpenAI wrapper + LangChain/LangGraph callbacks
├── db/migrations/          # Alembic migrations
└── infra/                  # Docker Compose files
```

## Architecture

**Event flow:** SDK (async, non-blocking) → Ingestion API → Redis Streams → Celery pipeline → PostgreSQL

**Budget enforcement hot path:** SDK pre-call → `GET /budgets/check` → Redis counters only → <5ms p99

**Metering:** Celery cost-enrichment worker calculates USD cost per `provider_call`. Celery rollup workers maintain `usage_hourly` and `usage_daily` materialized tables. All rollups are idempotent (safe to re-run).

**Key domain objects:** Tenant → Workspace → Application/Environment → AgentRun → Span (parent/child tree) → ProviderCall / ToolCall / OutcomeEvent

**Privacy model:** `METADATA_ONLY` by default (tokens, model, latency — no payload). `ERRORS_ONLY`, `SAMPLED`, `FULL` are explicit opt-ins. Privacy mode is enforced in the Celery pipeline before writing to Postgres.

**Billing periods:** Closed periods produce a signed JSON snapshot (HMAC-SHA256). All evidence is trace-linked: billing line → AgentRun → Span → ProviderCall.

See `IMPLEMENTATION.md` for the full 6-month phase plan and complete database schema.
