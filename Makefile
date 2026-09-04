.PHONY: install dev dev-d dev-infra dev-api dev-worker dev-beat dev-web \
        migrate migrate-new migrate-down \
        simulate simulate-hard clean-data reset \
        test test-sdk test-all test-watch \
        lint lint-fix typecheck \
        health check-regression \
        samples-setup samples-env \
        build down down-volumes ps logs logs-api

# API base URL used by the `health` target. Defaults to the Docker Compose stack
# (host port 8201). Override for a local hot-reload API: make health API_URL=http://localhost:8000
API_URL ?= http://localhost:8201

# ── Setup ──────────────────────────────────────────────────────────────────────

## Install all backend + frontend dependencies
install:
	uv sync --all-packages
	cd apps/web && npm install

# ── Local development ──────────────────────────────────────────────────────────

## Full stack via Docker Compose (Postgres + Redis + API + Worker + Web)
## On first start the API prints the generated API key — save it.
dev:
	docker compose up

## Detached mode (runs in background)
dev-d:
	docker compose up -d

## Run only Postgres + Redis — use alongside dev-api / dev-worker / dev-web
dev-infra:
	docker compose up runledger-postgres runledger-redis

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

# ── Simulation / demo data ─────────────────────────────────────────────────────
# Populate the whole cluster from the API by running every scenario in
# scripts/scenarios/. `simulate` resets (truncate) first; `simulate-hard` wipes
# every volume first. See docs/deployment/docker-compose.mdx.

## Reset + populate the cluster with all scenarios (via the API)
simulate:
	uv run python scripts/full_simulate.py

## Wipe every volume, then populate the cluster with all scenarios
simulate-hard:
	uv run python scripts/full_simulate.py --hard-clean

## Truncate all data tables + flush Redis (keeps schema; stack stays up)
clean-data:
	uv run python scripts/cleanup.py

## Full reset — docker compose down -v + up (wipes every volume)
reset:
	uv run python scripts/cleanup.py --hard

# ── Health ─────────────────────────────────────────────────────────────────────

## Check all health endpoints (uses API_URL, default http://localhost:8201)
health:
	@echo "── /health (legacy) ──────────────────────────────────"
	@curl -s $(API_URL)/health | python -m json.tool
	@echo ""
	@echo "── /health/live (liveness probe) ────────────────────"
	@curl -s $(API_URL)/health/live | python -m json.tool
	@echo ""
	@echo "── /health/ready (readiness probe) ──────────────────"
	@curl -s $(API_URL)/health/ready | python -m json.tool

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
	docker compose build

## Stop all containers
down:
	docker compose down

## Stop all containers and delete volumes (wipes database)
down-volumes:
	docker compose down -v

## Show running container status
ps:
	docker compose ps

## Tail all container logs
logs:
	docker compose logs -f

## Tail API logs only (shows the generated API key on first start)
logs-api:
	docker compose logs -f runledger-api

# ── Image Build, Tag, Push & Deploy ───────────────────────────────────────────
# Usage:
#   make build-images TAG=v2          # build all 15 images as abijith13/runledger-*:v2
#   make push-images TAG=v2           # push all 15 images to Docker Hub
#   make deploy TAG=v2                # recreate running containers with v2 images
#   make deploy TAG=v1alpha1          # deploy the current published alpha tag
#   make deploy TAG=v1                # revert to v1 (no rebuild, just swap)
#   make build-push TAG=v2            # build + push in one step
#   make build-push-deploy TAG=v2     # build + push + deploy in one step
#
# The docker-compose.yml defaults to v1alpha1 via the image: tags. These Makefile
# targets let you build, test, and deploy a new tag without editing compose.
# To revert after a bad deploy: make deploy TAG=v1

REGISTRY ?= abijith13
TAG ?= v1alpha1

## Build all 15 RunLedger images with TAG
build-images:
	@echo "═══ Building all RunLedger images as $(REGISTRY)/runledger-*:$(TAG) ═══"
	docker build -t $(REGISTRY)/runledger-api:$(TAG)    -f apps/api/Dockerfile .
	docker tag $(REGISTRY)/runledger-api:$(TAG) $(REGISTRY)/runledger-worker:$(TAG)
	docker tag $(REGISTRY)/runledger-api:$(TAG) $(REGISTRY)/runledger-beat:$(TAG)
	docker build -t $(REGISTRY)/runledger-web:$(TAG)    ./apps/web
	docker build -t $(REGISTRY)/runledger-embedding-svc:$(TAG)       ./apps/embedding-svc
	docker build -t $(REGISTRY)/runledger-semantic-cache-svc:$(TAG)  ./apps/semantic-cache-svc
	docker build -t $(REGISTRY)/runledger-context-compiler:$(TAG)    ./apps/context-compiler-svc
	docker build -t $(REGISTRY)/runledger-reranker:$(TAG)            ./apps/reranker-svc
	docker build -t $(REGISTRY)/runledger-compression:$(TAG)         ./apps/compression-svc
	# runledger-router sidecar deprecated — absorbed into runledger-gateway-rs
	# docker build -t $(REGISTRY)/runledger-router:$(TAG)              ./apps/router-svc
	docker build -t $(REGISTRY)/runledger-mcp-gateway:$(TAG)         ./apps/mcp-gateway
	docker build -t $(REGISTRY)/runledger-memory-svc:$(TAG)          ./apps/memory-svc
	docker build -t $(REGISTRY)/runledger-kg-svc:$(TAG)              ./apps/kg-svc
	docker build -t $(REGISTRY)/runledger-skill-registry:$(TAG)      ./apps/skill-registry
	docker build -t $(REGISTRY)/runledger-flywheel:$(TAG)            ./apps/flywheel-svc
	@echo ""
	@echo "✓ All 15 images built as $(REGISTRY)/runledger-*:$(TAG)"

## Push all 15 RunLedger images to Docker Hub
push-images:
	@echo "═══ Pushing $(REGISTRY)/runledger-*:$(TAG) ═══"
	@for svc in api worker beat web \
		embedding-svc semantic-cache-svc context-compiler reranker compression \
		router mcp-gateway memory-svc kg-svc skill-registry flywheel; do \
		echo "  → $(REGISTRY)/runledger-$$svc:$(TAG)"; \
		docker push $(REGISTRY)/runledger-$$svc:$(TAG); \
	done
	@echo ""
	@echo "✓ All 15 images pushed"

## Build + push all images
build-push: build-images push-images

## Deploy: recreate all RunLedger containers using the tagged images.
## Infrastructure (postgres, redis, qdrant, letta, memory-db, otel-collector) is untouched.
deploy:
	@echo "═══ Deploying RunLedger with $(REGISTRY)/runledger-*:$(TAG) ═══"
	@echo ""
	@echo "── Stopping app containers ──"
	@for svc in api worker beat web \
		embedding-svc semantic-cache-svc context-compiler reranker compression \
		router mcp-gateway memory-svc kg-svc skill-registry flywheel; do \
		docker stop runledger-$$svc 2>/dev/null || true; \
		docker rm   runledger-$$svc 2>/dev/null || true; \
	done
	@echo ""
	@echo "── Starting containers from $(TAG) images ──"
	RUNLEDGER_TAG=$(TAG) docker compose up -d --no-build
	@echo ""
	@echo "✓ Stack deployed with tag $(TAG)"
	@echo "  Dashboard: http://localhost:3201"
	@echo "  API:       http://localhost:8201"
	@echo "  Revert:    make deploy TAG=v1"

## Build, push, and deploy in one step
build-push-deploy: build-images push-images deploy

## List all RunLedger images with their tags
list-images:
	@echo "RunLedger images:"
	@docker images --format "  {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}" | grep "$(REGISTRY)/runledger" | sort
