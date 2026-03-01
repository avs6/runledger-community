.PHONY: install dev dev-infra dev-api dev-worker dev-web \
        migrate migrate-new migrate-down seed \
        test test-sdk test-all test-watch \
        lint lint-fix typecheck \
        health check-regression \
        samples-setup samples-env \
        build down down-volumes

# ── Setup ──────────────────────────────────────────────────────────────────────

## Install all backend + frontend dependencies
install:
	uv sync --all-packages
	cd apps/web && npm install

# ── Local development ──────────────────────────────────────────────────────────

## Full stack via Docker Compose (Postgres + Redis + API + Worker + Web)
## On first start the API prints the generated API key — save it.
dev:
	docker compose -f infra/docker-compose.yml up

## Detached mode (runs in background)
dev-d:
	docker compose -f infra/docker-compose.yml up -d

## Run only Postgres + Redis — use alongside dev-api / dev-worker / dev-web
dev-infra:
	docker compose -f infra/docker-compose.yml up postgres redis

## API with hot-reload (requires Postgres + Redis running)
dev-api:
	cd apps/api && uv run fastapi dev runledger_api/main.py

## Celery worker (requires Redis running)
dev-worker:
	cd apps/api && uv run celery -A runledger_api.core.celery_app worker --loglevel=info --pool=solo

## Celery beat scheduler (requires Redis running)
dev-beat:
	cd apps/api && uv run celery -A runledger_api.core.celery_app beat --loglevel=info

## Next.js frontend (http://localhost:3000)
dev-web:
	cd apps/web && npm run dev

# ── Database ───────────────────────────────────────────────────────────────────

## Apply all pending migrations
migrate:
	cd apps/api && uv run alembic upgrade head

## Create a new migration (usage: make migrate-new name="add users table")
migrate-new:
	cd apps/api && uv run alembic revision --autogenerate -m "$(name)"

## Roll back one migration
migrate-down:
	cd apps/api && uv run alembic downgrade -1

## Seed default tenant, workspace, and API key (idempotent)
seed:
	cd apps/api && uv run python -m runledger_api.scripts.seed

# ── Health ─────────────────────────────────────────────────────────────────────

## Check all health endpoints (requires API running on :8000)
health:
	@echo "── /health (legacy) ──────────────────────────────────"
	@curl -s http://localhost:8000/health | python -m json.tool
	@echo ""
	@echo "── /health/live (liveness probe) ────────────────────"
	@curl -s http://localhost:8000/health/live | python -m json.tool
	@echo ""
	@echo "── /health/ready (readiness probe) ──────────────────"
	@curl -s http://localhost:8000/health/ready | python -m json.tool

# ── Quality ────────────────────────────────────────────────────────────────────

## Run API tests
test:
	uv run pytest apps/api/tests -v

## Run SDK tests
test-sdk:
	uv run pytest packages/sdk/tests -v

## Run all tests (API + SDK)
test-all:
	uv run pytest apps/api/tests packages/sdk/tests -v

## Run API tests, stop on first failure
test-watch:
	uv run pytest apps/api/tests -v --tb=short -x

## Check lint + format
lint:
	uv run ruff check apps/api packages/sdk
	uv run ruff format --check apps/api packages/sdk

## Auto-fix lint + format issues
lint-fix:
	uv run ruff check --fix apps/api packages/sdk
	uv run ruff format apps/api packages/sdk

## Type check backend + frontend
typecheck:
	uv run mypy apps/api/runledger_api packages/sdk/runledger_sdk
	cd apps/web && npm run typecheck

## Check for cost regressions (exits 1 if any feature_tag has >20% cost increase)
## Requires: RUNLEDGER_API_KEY and RUNLEDGER_BASE_URL set in environment
check-regression:
	uv run runledger check-regression --threshold 20.0

# ── Samples ────────────────────────────────────────────────────────────────────
# The examples/ directory in this repo is the canonical source.
# runledger-samples is a standalone repo for users who just want the examples.
#
# Usage (from repo root):
#   make samples-env          # create examples/.env from .env.example
#   make samples-setup        # create venv + install deps inside examples/
#   cd examples && source .venv/bin/activate && python 01_openai_basic.py

## Copy examples/.env.example → examples/.env (skip if already exists)
samples-env:
	@if [ -f examples/.env ]; then \
		echo "examples/.env already exists — skipping. Edit it directly."; \
	else \
		cp examples/.env.example examples/.env; \
		echo "Created examples/.env — fill in RUNLEDGER_API_KEY and OPENAI_API_KEY."; \
	fi

## Create a Python venv in examples/ and install all sample dependencies
## SDK examples (01-06) also need the runledger-sdk installed from this repo.
samples-setup: samples-env
	python -m venv examples/.venv
	examples/.venv/bin/pip install --upgrade pip
	examples/.venv/bin/pip install httpx python-dotenv openai langchain langchain-openai langgraph
	examples/.venv/bin/pip install -e "packages/sdk[all]"
	@echo ""
	@echo "Venv ready. Activate with:"
	@echo "  source examples/.venv/bin/activate   (macOS/Linux)"
	@echo "  examples\\.venv\\Scripts\\activate      (Windows)"
	@echo ""
	@echo "Then run any example:"
	@echo "  cd examples && python 01_openai_basic.py"

# ── Docker ─────────────────────────────────────────────────────────────────────

## Build Docker images
build:
	docker compose -f infra/docker-compose.yml build

## Stop all containers
down:
	docker compose -f infra/docker-compose.yml down

## Stop all containers and delete volumes (wipes database)
down-volumes:
	docker compose -f infra/docker-compose.yml down -v

## Show running container status
ps:
	docker compose -f infra/docker-compose.yml ps

## Tail all container logs
logs:
	docker compose -f infra/docker-compose.yml logs -f

## Tail API logs only (shows the generated API key on first start)
logs-api:
	docker compose -f infra/docker-compose.yml logs -f api
