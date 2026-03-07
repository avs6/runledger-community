from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runledger_api.core.config import settings
from runledger_api.core.db import AsyncSessionLocal, engine
from runledger_api.core.logging import configure_logging
from runledger_api.core.redis import redis_client
from runledger_api.services.pricing_sync import load_pricing_yaml, sync_pricing
from runledger_api.routers import (
    analytics,
    auth,
    billing,
    budgets,
    health,
    ingest,
    ledger,
    login,
    privacy,
    replay,
    runs,
    tools,
)
from runledger_api.routers import evaluations as evaluations_router
from runledger_api.routers import integrations as integrations_router
from runledger_api.routers import prompts as prompts_router
from runledger_api.routers import providers as providers_router
from runledger_api.routers import settings as settings_router

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    log.info("startup", environment=settings.environment)

    # Sync provider pricing from YAML file on every startup
    try:
        entries = load_pricing_yaml(settings.pricing_file)
        if entries:
            async with AsyncSessionLocal() as session:
                result = await sync_pricing(session, entries)
                log.info("pricing_startup_sync", **result)
    except Exception:
        log.exception("pricing_startup_sync_failed")  # non-fatal

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
app.include_router(evaluations_router.router)
app.include_router(prompts_router.router)
