.PHONY: install dev dev-api dev-worker dev-web migrate migrate-new seed test test-sdk lint typecheck

# ── Setup ──────────────────────────────────────────────────────────────────────

install:
	uv sync --all-packages
	cd apps/web && npm install

# ── Local development ──────────────────────────────────────────────────────────

# Full stack via Docker Compose (Postgres + Redis + API + Worker + Web)
dev:
	docker compose -f infra/docker-compose.yml up

# Run only infrastructure (Postgres + Redis) — use with dev-api / dev-web
dev-infra:
	docker compose -f infra/docker-compose.yml up postgres redis

# API with hot-reload (requires Postgres + Redis running)
dev-api:
	cd apps/api && uv run fastapi dev runledger_api/main.py

# Celery worker (requires Redis running)
dev-worker:
	cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo

# Next.js frontend
dev-web:
	cd apps/web && npm run dev

# ── Database ───────────────────────────────────────────────────────────────────

migrate:
	cd apps/api && uv run alembic upgrade head

# Usage: make migrate-new name="add users table"
migrate-new:
	cd apps/api && uv run alembic revision --autogenerate -m "$(name)"

migrate-down:
	cd apps/api && uv run alembic downgrade -1

seed:
	cd apps/api && uv run python scripts/seed.py

# ── Quality ────────────────────────────────────────────────────────────────────

test:
	cd apps/api && uv run pytest -v

test-sdk:
	cd packages/sdk && uv run pytest -v

test-all:
	cd apps/api && uv run pytest -v
	cd packages/sdk && uv run pytest -v

test-watch:
	cd apps/api && uv run pytest -v --tb=short -x

lint:
	uv run ruff check apps/api packages/sdk
	uv run ruff format --check apps/api packages/sdk

lint-fix:
	uv run ruff check --fix apps/api packages/sdk
	uv run ruff format apps/api packages/sdk

typecheck:
	uv run mypy apps/api/runledger_api packages/sdk/runledger_sdk
	cd apps/web && npm run typecheck

# ── Docker ─────────────────────────────────────────────────────────────────────

build:
	docker compose -f infra/docker-compose.yml build

down:
	docker compose -f infra/docker-compose.yml down

down-volumes:
	docker compose -f infra/docker-compose.yml down -v
