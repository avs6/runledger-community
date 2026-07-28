# Contributing to RunLedger

Thank you for your interest in contributing. This document covers how to get a local dev environment running, the coding standards we use, and the PR process.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local development setup](#local-development-setup)
- [Project structure](#project-structure)
- [Running tests](#running-tests)
- [Lint, format, and type-check](#lint-format-and-type-check)
- [Database migrations](#database-migrations)
- [Submitting a pull request](#submitting-a-pull-request)
- [Coding standards](#coding-standards)
- [Commit messages](#commit-messages)

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | [python.org](https://www.python.org/) |
| uv | Latest | `curl -Ls https://astral.sh/uv/install.sh \| sh` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Docker + Compose | Latest | [docker.com](https://www.docker.com/) |
| PostgreSQL 16 | 16+ | via Docker (recommended) |
| Redis 7 | 7+ | via Docker (recommended) |

---

## Local development setup

**1. Clone and install Python dependencies**

```bash
git clone https://github.com/avs6/runledger
cd runledger
uv sync --all-packages
```

**2. Start Postgres + Redis via Docker**

```bash
docker compose up -d runledger-postgres runledger-redis
```

Or run the full stack:

```bash
docker compose up -d
```

**3. Configure environment**

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local
```

The defaults in `.env.example` point to the Docker services and work out of the box.

**4. Run migrations**

```bash
cd apps/api && uv run alembic upgrade head
```

**5. Start the API**

```bash
cd apps/api && uv run fastapi dev runledger_api/main.py
```

**6. Start the Celery worker** (separate terminal)

```bash
cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo
```

**7. Start the frontend** (separate terminal)

```bash
cd apps/web && npm install && npm run dev
```

The dashboard is at `http://localhost:3000`. The API is at `http://localhost:8000`.

---

## Project structure

```
runledger/
├── apps/api/               # FastAPI backend
│   ├── runledger_api/
│   │   ├── core/           # Config, DB session, Redis, Celery
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── routers/        # FastAPI route handlers
│   │   ├── services/       # Business logic
│   │   └── workers/        # Celery tasks
│   ├── alembic/            # Database migrations
│   └── tests/              # Pytest test suite
├── apps/web/               # Next.js 14 frontend
├── packages/sdk/           # runledger-sdk (Python)
│   ├── runledger_sdk/
│   └── tests/
├── packages/ts-sdk/        # @runledger/sdk (TypeScript)
│   ├── src/
│   └── tests/
├── examples/               # Runnable example scripts
├── docs/                   # Integration guides
└── infra/                  # Docker Compose + OTel Collector config
```

---

## Running tests

**API tests** (pytest):

```bash
cd apps/api && uv run pytest
```

Run a single test file:

```bash
cd apps/api && uv run pytest tests/test_analytics.py -v
```

Run with coverage:

```bash
cd apps/api && uv run pytest --cov=runledger_api --cov-report=term-missing
```

**Python SDK tests**:

```bash
cd packages/sdk && uv run pytest
```

**TypeScript SDK tests** (vitest):

```bash
cd packages/ts-sdk && npm test
```

**Frontend type-check**:

```bash
cd apps/web && npm run typecheck
```

Tests do **not** require a running database or Redis. All external dependencies are mocked in the test fixtures (`conftest.py`).

---

## Lint, format, and type-check

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [mypy](https://mypy.readthedocs.io/) for type checking.

```bash
# Lint
uv run ruff check apps/api packages/sdk

# Auto-fix lint issues
uv run ruff check --fix apps/api packages/sdk

# Format
uv run ruff format apps/api packages/sdk

# Check formatting without writing
uv run ruff format --check apps/api packages/sdk

# Type check
uv run mypy apps/api/runledger_api packages/sdk/runledger_sdk
```

The CI pipeline runs all three as required checks. PRs must pass before merging.

---

## Database migrations

Migrations live in `apps/api/alembic/versions/`. Each migration file is named `NNN_description.py` where `NNN` is a zero-padded three-digit sequence number.

**Create a new migration** (after modifying SQLAlchemy models):

```bash
cd apps/api && uv run alembic revision --autogenerate -m "describe your change"
```

Review the generated file before committing — autogenerate is a starting point, not a final answer. Rename the file to follow the `NNN_` naming convention and update `down_revision` to match the previous migration.

**Apply migrations**:

```bash
cd apps/api && uv run alembic upgrade head
```

**Rollback one step**:

```bash
cd apps/api && uv run alembic downgrade -1
```

All migrations must be reversible (implement `downgrade()`).

---

## Submitting a pull request

1. **Fork** the repo and create a branch from `master`.
2. Make your change. Keep PRs focused — one logical change per PR.
3. Add or update tests. The test suite must pass and coverage should not drop.
4. Run lint + format + type-check locally before pushing.
5. Open a PR with a clear title and description. Reference any related issues.
6. CI must be green before the PR can be merged.

For significant new features or architectural changes, open an issue first to discuss the approach before writing code.

---

## Coding standards

**Python (backend + SDK)**

- Python 3.13+. Use modern syntax — `X | Y` unions, `match` statements, `type` aliases.
- All public functions and methods must have type annotations.
- Async-first: FastAPI route handlers and service functions are `async def`.
- Celery tasks use `NullPool` + `asyncio.run()` — safe with `--pool=solo`.
- Enums: use `StrEnum`, not `(str, enum.Enum)`.
- ORM dict columns: annotate as `dict[str, Any] | None`.
- Do not leave `# type: ignore` comments unless unavoidable; prefer real fixes.
- No `print()` in application code — use `logging` or `structlog`.

**TypeScript (frontend + TS SDK)**

- TypeScript strict mode. No `any` unless genuinely unavoidable.
- React Server Components by default; add `'use client'` only when needed.
- Recharts components require `'use client'`.
- NextAuth v4 (`next-auth` without version pin).
- `next-themes` for dark mode — wrap with `ThemeProvider` from `components/providers/ThemeProvider.tsx`.

**Tests**

- Use `SimpleNamespace` for mock ORM objects (not `Model.__new__`).
- Set all required fields in mock `db.refresh` side effects, including fields with `server_default`.
- Mock external HTTP calls — tests must not make real network requests.
- Every new router endpoint needs at least one test covering the happy path.

---

## Commit messages

Follow the pattern used in this repo:

```
Type: Short description (imperative, ≤72 chars)

Optional body explaining why, not what.
```

Types: `Feat`, `Fix`, `Docs`, `Style`, `Refactor`, `Test`, `Chore`.

Examples:

```
Feat: add budget enforcement pre-call hook to OpenAI wrapper
Fix: correct token sum for cached input in metering worker
Docs: add OTLP integration guide
```
