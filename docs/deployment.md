# Railway Deployment Guide

This guide covers deploying RunLedger to [Railway](https://railway.app) using managed Postgres + Redis.

## Prerequisites

- Railway account and the `railway` CLI installed (`npm install -g @railway/cli`)
- Docker installed locally (for local testing)
- A RunLedger repository cloned locally

---

## 1. Provision Infrastructure

### Create a new Railway project

```bash
railway login
railway init
```

### Add managed Postgres

In the Railway dashboard: **New** → **Database** → **PostgreSQL**

Copy the `DATABASE_URL` from the Variables tab.

### Add managed Redis

In the Railway dashboard: **New** → **Database** → **Redis**

Copy the `REDIS_URL` from the Variables tab.

---

## 2. Set Environment Variables

Set these variables in your Railway project (dashboard → Variables, or via CLI):

```bash
railway variables set DATABASE_URL="postgresql+asyncpg://..."
railway variables set REDIS_URL="redis://..."
railway variables set API_KEY_SECRET="<random-32-char-secret>"
railway variables set HMAC_SECRET="<random-32-char-secret>"
railway variables set SECRET_KEY="<random-32-char-secret>"
```

Generate secrets with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Frontend variables (apps/web)

```bash
NEXTAUTH_URL="https://your-frontend.railway.app"
NEXTAUTH_SECRET="<random-32-char-secret>"
NEXT_PUBLIC_API_URL="https://your-api.railway.app"
```

---

## 3. Run Database Migrations

After provisioning Postgres, run Alembic migrations via Railway:

```bash
cd apps/api
railway run uv run alembic upgrade head
```

This applies all migrations up to the latest revision (`008_ledger`).

---

## 4. Deploy the API

```bash
cd apps/api
railway up
```

Railway will use the `Dockerfile` (or auto-detect the Python app) and deploy the FastAPI service.

The API is served by `uvicorn` on the port Railway assigns (`$PORT`).

---

## 5. Deploy the Frontend

```bash
cd apps/web
railway up
```

Railway will detect Next.js and run `npm run build && npm run start`.

---

## 6. Health Check URLs

Configure Railway TCP health probes to use:

| Probe | URL | Expected |
|-------|-----|----------|
| Liveness | `GET /health/live` | Always `200 OK` |
| Readiness | `GET /health/ready` | `200 OK` when DB + Redis reachable; `503` when degraded |

In Railway → Service → Settings → **Health Check Path**: set to `/health/live`.

The `/health/ready` endpoint returns `503` with `{"status": "degraded", "db": "...", "redis": "..."}` if either dependency is unreachable — useful for canary deployments and rollback triggers.

---

## 7. Run a Celery Worker

For background tasks (metering, rollups, replay experiments):

```bash
cd apps/api
railway run uv run celery -A runledger_api.core.celery worker --loglevel=info --pool=solo
```

Or add a second Railway service with this as the start command.

---

## 8. Local Full Stack (Docker Compose)

To run everything locally before deploying:

```bash
docker compose up
```

Services started:
- `api` — FastAPI on port 8000
- `worker` — Celery worker
- `web` — Next.js on port 3000
- `db` — PostgreSQL on port 5432
- `redis` — Redis on port 6379

Run migrations in local dev:
```bash
cd apps/api && uv run alembic upgrade head
```

---

## Rate Limits

The API enforces per-API-key rate limits via Redis sliding window:

| Tier | Endpoints | Limit |
|------|-----------|-------|
| Ingest | `POST /ingest/v1/*` | 600 req/min |
| Analytics | `GET /analytics/*` | 120 req/min |
| Management | All CRUD endpoints | 60 req/min |

Rate limiting fails open — if Redis is unreachable, requests pass through without a limit check.
