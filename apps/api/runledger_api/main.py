from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runledger_api.core.config import settings
from runledger_api.core.db import engine
from runledger_api.core.logging import configure_logging
from runledger_api.core.redis import redis_client
from runledger_api.routers import analytics, auth, billing, budgets, health, ingest, integrations as integrations_router, ledger, login, privacy, providers as providers_router, replay, runs, settings as settings_router, tools

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    log.info("startup", environment=settings.environment)
    yield
    log.info("shutdown")
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="RunLedger API",
    version="0.1.0",
    description="Agent FinOps Control Plane — billing-grade observability for AI agents.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(runs.router)
app.include_router(login.router)
app.include_router(budgets.router)
app.include_router(billing.router)
app.include_router(replay.router)
app.include_router(ledger.router)
app.include_router(tools.router)
app.include_router(privacy.router)
app.include_router(settings_router.router)
app.include_router(providers_router.router)
app.include_router(integrations_router.router)
