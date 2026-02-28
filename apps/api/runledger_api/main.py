from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from runledger_api.core.config import settings
from runledger_api.core.db import engine
from runledger_api.core.logging import configure_logging
from runledger_api.core.redis import redis_client
from runledger_api.routers import analytics, auth, billing, budgets, health, ingest, login, replay, runs

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

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(runs.router)
app.include_router(login.router)
app.include_router(budgets.router)
app.include_router(billing.router)
app.include_router(replay.router)
