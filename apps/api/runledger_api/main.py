from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from runledger_api.core.config import settings
from runledger_api.core.db import engine
from runledger_api.core.logging import configure_logging
from runledger_api.core.redis import redis_client
from runledger_api.mcp_server import mcp as _mcp_server
from runledger_api.routers import agents as agents_router
from runledger_api.routers import alerts as alerts_router
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
from runledger_api.routers import approvals as approvals_router
from runledger_api.routers import audit as audit_router
from runledger_api.routers import budget_tiers as budget_tiers_router
from runledger_api.routers import eval_experiments as eval_experiments_router
from runledger_api.routers import evaluations as evaluations_router
from runledger_api.routers import flywheel as flywheel_router
from runledger_api.routers import gateway as gateway_router
from runledger_api.routers import guardrails as guardrails_router
from runledger_api.routers import governance as governance_router
from runledger_api.routers import integrations as integrations_router
from runledger_api.routers import intelligence as intelligence_router
from runledger_api.routers import model_budgets as model_budgets_router
from runledger_api.routers import org as org_router
from runledger_api.routers import otlp as otlp_router
from runledger_api.routers import outcomes as outcomes_router
from runledger_api.routers import playground as playground_router
from runledger_api.routers import policies as policies_router
from runledger_api.routers import prompts as prompts_router
from runledger_api.routers import providers as providers_router
from runledger_api.routers import retention as retention_router
from runledger_api.routers import sessions as sessions_router
from runledger_api.routers import security as security_router
from runledger_api.routers import settings as settings_router
from runledger_api.routers import users as users_router
from runledger_api.routers import vector_stores as vector_stores_router
from runledger_api.routers import workflows as workflows_router
from runledger_api.routers import mcp_registry as mcp_registry_router
from runledger_api.routers import plugins as plugins_router
from runledger_api.routers import hub as hub_router
from runledger_api.routers import workspace_controls as workspace_controls_router

configure_logging()
log = structlog.get_logger()
_mcp_http_app = _mcp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    log.info("startup", environment=settings.environment)
    async with _mcp_server.session_manager.run():
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Workspace-ID"],
)

from runledger_api.core.ratelimit_middleware import RateLimitHeaderMiddleware  # noqa: E402

app.add_middleware(RateLimitHeaderMiddleware)

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
app.include_router(security_router.router)
app.include_router(providers_router.router)
app.include_router(integrations_router.router)
app.include_router(alerts_router.router)
app.include_router(gateway_router.router)
app.include_router(flywheel_router.router)
app.include_router(evaluations_router.router)
app.include_router(prompts_router.router)
app.include_router(sessions_router.router)
app.include_router(policies_router.router)
app.include_router(users_router.router)
app.include_router(org_router.router)
app.include_router(outcomes_router.router)
app.include_router(approvals_router.router)
app.include_router(audit_router.router)
app.include_router(retention_router.router)
app.include_router(otlp_router.router)
app.include_router(eval_experiments_router.router)
app.include_router(guardrails_router.router)
app.include_router(governance_router.router)
app.include_router(intelligence_router.router)
app.include_router(budget_tiers_router.router)
app.include_router(model_budgets_router.router)
app.include_router(agents_router.router)
app.include_router(workflows_router.router)
app.include_router(vector_stores_router.router)
app.include_router(playground_router.router)
app.include_router(workspace_controls_router.tags_router)
app.include_router(workspace_controls_router.search_tools_router)
app.include_router(workspace_controls_router.tool_policies_router)
app.include_router(workspace_controls_router.access_groups_router)
app.include_router(workspace_controls_router.response_cache_router)
app.include_router(mcp_registry_router.router)
app.include_router(plugins_router.router)
app.include_router(hub_router.router)

# ── MCP server — mounted at /mcp (streamable-HTTP transport) ─────────────────
# Connect Claude Desktop / Claude Code:
#   claude mcp add --transport http runledger http://localhost:8000/mcp
# Or in claude_desktop_config.json:
#   { "mcpServers": { "runledger": { "url": "http://localhost:8000/mcp" } } }
app.mount("/mcp", _mcp_http_app)

# ── API Reference UI — Scalar (richer DX than Swagger UI) ────────────────────


@app.get("/reference", include_in_schema=False)
async def scalar_reference() -> Any:
    from fastapi.responses import HTMLResponse  # noqa: PLC0415

    return HTMLResponse(
        """<!DOCTYPE html>
<html>
<head>
  <title>RunLedger API Reference</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
</head>
<body>
  <script
    id="api-reference"
    data-url="/openapi.json"
    data-configuration='{"theme":"purple","layout":"modern","defaultHttpClient":{"targetKey":"python","clientKey":"requests"}}'
  ></script>
  <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body>
</html>"""
    )
