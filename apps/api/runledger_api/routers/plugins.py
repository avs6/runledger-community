"""
Custom Plugin System API.

Prefix: /plugins
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /plugins                    Install/create plugin
GET    /plugins                    List plugins
GET    /plugins/{id}               Get plugin detail
PUT    /plugins/{id}               Update plugin
DELETE /plugins/{id}               Uninstall (deactivate) plugin
GET    /plugins/{id}/executions    Plugin execution log
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.plugins import Plugin, PluginExecution
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.plugins import (
    PluginCreate,
    PluginExecutionList,
    PluginExecutionResponse,
    PluginList,
    PluginResponse,
    PluginUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/plugins", tags=["plugins"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _to_response(p: Plugin) -> PluginResponse:
    return PluginResponse(
        id=p.id,
        workspace_id=p.workspace_id,
        name=p.name,
        description=p.description,
        plugin_type=p.plugin_type,
        hooks=p.hooks or [],
        config=p.config or {},
        priority=p.priority,
        is_active=p.is_active,
        version=p.version,
        author=p.author,
        install_count=p.install_count,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.post(
    "",
    response_model=PluginResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def create_plugin(body: PluginCreate, ws: WorkspaceDep, db: DbDep) -> PluginResponse:
    p = Plugin(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        plugin_type=body.plugin_type,
        hooks=body.hooks,
        config=body.config,
        priority=body.priority,
        version=body.version,
        author=body.author,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _to_response(p)


@router.get("", response_model=PluginList, dependencies=[Depends(analytics_rate_limit)])
async def list_plugins(
    ws: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = False,
) -> PluginList:
    q = select(Plugin).where(Plugin.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(Plugin.is_active.is_(True))
    q = q.order_by(Plugin.priority, Plugin.name)
    rows = (await db.execute(q)).scalars().all()
    return PluginList(items=[_to_response(p) for p in rows])


@router.get(
    "/{plugin_id}", response_model=PluginResponse, dependencies=[Depends(analytics_rate_limit)]
)
async def get_plugin(plugin_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> PluginResponse:
    p = (
        await db.execute(select(Plugin).where(Plugin.id == plugin_id, Plugin.workspace_id == ws.id))
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plugin not found")
    return _to_response(p)


@router.put(
    "/{plugin_id}",
    response_model=PluginResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_plugin(
    plugin_id: uuid.UUID, body: PluginUpdate, ws: WorkspaceDep, db: DbDep
) -> PluginResponse:
    p = (
        await db.execute(select(Plugin).where(Plugin.id == plugin_id, Plugin.workspace_id == ws.id))
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plugin not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(p)
    return _to_response(p)


@router.delete(
    "/{plugin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def uninstall_plugin(plugin_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    await db.execute(
        update(Plugin)
        .where(Plugin.id == plugin_id, Plugin.workspace_id == ws.id)
        .values(is_active=False, updated_at=datetime.now(UTC))
    )
    await db.commit()


@router.get(
    "/{plugin_id}/executions",
    response_model=PluginExecutionList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_executions(
    plugin_id: uuid.UUID,
    ws: WorkspaceDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
) -> PluginExecutionList:
    rows = (
        (
            await db.execute(
                select(PluginExecution)
                .where(
                    PluginExecution.plugin_id == plugin_id, PluginExecution.workspace_id == ws.id
                )
                .order_by(PluginExecution.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return PluginExecutionList(
        items=[
            PluginExecutionResponse(
                id=e.id,
                plugin_id=e.plugin_id,
                hook=e.hook,
                latency_ms=e.latency_ms,
                status=e.status,
                error=e.error,
                created_at=e.created_at,
            )
            for e in rows
        ]
    )


DEFAULT_PREINTEGRATED_PLUGINS = [
    {
        "name": "PII & Secret Redactor Plugin",
        "description": "Pre-gateway sanitizer that automatically redacts SSNs, API tokens, passwords, and credit card numbers before LLM processing.",
        "plugin_type": "transformer",
        "hooks": ["pre_ingest", "pre_gateway"],
        "priority": 10,
        "author": "RunLedger Security",
        "version": "1.2.0",
    },
    {
        "name": "LangSmith Trace Bridge",
        "description": "Post-gateway telemetry enricher exporting spans, tool call traces, and token latencies directly to LangSmith & OpenInference collectors.",
        "plugin_type": "enricher",
        "hooks": ["post_ingest", "post_gateway"],
        "priority": 20,
        "author": "RunLedger Integrations",
        "version": "2.0.1",
    },
    {
        "name": "PagerDuty / Slack Emergency Dispatcher",
        "description": "Instant notification webhook fired when a workspace project breaches cost budget limits or triggers high-severity guardrail alerts.",
        "plugin_type": "webhook",
        "hooks": ["on_budget_exceeded", "on_guardrail_violation"],
        "priority": 5,
        "author": "RunLedger Ops",
        "version": "1.0.0",
    },
    {
        "name": "Prompt Injection Firewall",
        "description": "Pre-gateway validator inspecting incoming prompt payloads for jailbreaks, system prompt overrides, and adversarial instructions.",
        "plugin_type": "validator",
        "hooks": ["pre_gateway"],
        "priority": 1,
        "author": "RunLedger AI Safety",
        "version": "3.1.0",
    },
    {
        "name": "Kafka Realtime Event Mirror",
        "description": "Streams completed LLM proxy transactions, tool execution logs, and usage telemetry directly to Kafka/Redpanda topic buffers.",
        "plugin_type": "transformer",
        "hooks": ["post_gateway"],
        "priority": 50,
        "author": "RunLedger Streaming",
        "version": "1.4.0",
    },
    {
        "name": "Cost Attribution Header Injector",
        "description": "Injects Project ID, Access Group ID, and Workspace Metadata headers into upstream model provider calls for FinOps tracking.",
        "plugin_type": "enricher",
        "hooks": ["pre_gateway"],
        "priority": 15,
        "author": "RunLedger FinOps",
        "version": "1.1.0",
    },
]


@router.post(
    "/seed-defaults",
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def seed_default_plugins(ws: WorkspaceDep, db: DbDep) -> dict:
    added = 0
    for p_def in DEFAULT_PREINTEGRATED_PLUGINS:
        existing = (
            await db.execute(
                select(Plugin).where(Plugin.workspace_id == ws.id, Plugin.name == p_def["name"])
            )
        ).scalar_one_or_none()
        if not existing:
            p = Plugin(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                name=p_def["name"],
                description=p_def["description"],
                plugin_type=p_def["plugin_type"],
                hooks=p_def["hooks"],
                priority=p_def["priority"],
                version=p_def["version"],
                author=p_def["author"],
                is_active=True,
            )
            db.add(p)
            added += 1
    await db.commit()
    return {"status": "seeded", "plugins_added": added, "total": len(DEFAULT_PREINTEGRATED_PLUGINS)}
