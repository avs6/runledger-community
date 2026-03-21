"""
Tool registry, runtime enforcement, and security events endpoints.

Prefix: /tools
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET    /tools/check/{tool_name}       Runtime policy check (SDK hot path, Redis-cached)
GET    /tools/registry                List tool registry entries
POST   /tools/registry                Upsert a tool entry
PATCH  /tools/registry/{tool_name}    Update policy/description/enforcement
DELETE /tools/registry/{tool_name}    Remove a tool entry
GET    /tools/security-events         List security events (limit 100)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.redis import get_redis
from runledger_api.models.ledger import SecurityEvent, ToolRegistry
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.tools import (
    SecurityEventList,
    SecurityEventResponse,
    ToolCheckResponse,
    ToolRegistryCreate,
    ToolRegistryList,
    ToolRegistryResponse,
    ToolRegistryUpdate,
)

router = APIRouter(prefix="/tools", tags=["tools"])
log = structlog.get_logger()

_CACHE_TTL = 60  # seconds


def _cache_key(workspace_id: Any, tool_name: str) -> str:
    return f"rl:tools:{workspace_id}:{tool_name}"


def _tool_to_response(tool: ToolRegistry) -> ToolRegistryResponse:
    return ToolRegistryResponse(
        id=str(tool.id),
        workspace_id=str(tool.workspace_id),
        tool_name=tool.tool_name,
        policy=tool.policy,
        runtime_enforcement=tool.runtime_enforcement,
        description=tool.description,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


def _event_to_response(event: SecurityEvent) -> SecurityEventResponse:
    return SecurityEventResponse(
        id=str(event.id),
        workspace_id=str(event.workspace_id),
        event_type=event.event_type,
        tool_name=event.tool_name,
        end_user_id=event.end_user_id,
        run_id=str(event.run_id) if event.run_id else None,
        details=event.details or {},
        detected_at=event.detected_at,
    )


# ── GET /tools/check/{tool_name} ──────────────────────────────────────────────


@router.get("/check/{tool_name}", response_model=ToolCheckResponse)
async def check_tool(
    tool_name: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Any, Depends(get_redis)],
) -> ToolCheckResponse:
    """
    Runtime tool policy check — called by the SDK before executing a tool.

    Response time target: <5 ms via Redis cache.
    Falls back to DB on cache miss. Fail-open on Redis errors.

    Returns 403 if policy=block and runtime_enforcement=True, which causes
    the SDK to raise ToolBlockedError before the tool executes.
    """
    key = _cache_key(workspace.id, tool_name)
    policy = "allow"
    runtime_enforcement = False
    cache_hit = False

    # 1. Try Redis cache (fast path)
    try:
        raw = await redis.get(key)
        if raw:
            data = json.loads(raw)
            policy = data["policy"]
            runtime_enforcement = data["runtime_enforcement"]
            cache_hit = True
    except Exception:
        pass  # Redis down — fall through to DB

    # 2. DB lookup on cache miss
    if not cache_hit:
        result = await db.execute(
            select(ToolRegistry).where(
                ToolRegistry.workspace_id == workspace.id,
                ToolRegistry.tool_name == tool_name,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is not None:
            policy = entry.policy
            runtime_enforcement = entry.runtime_enforcement

        # Populate cache for next hit
        try:
            await redis.setex(
                key,
                _CACHE_TTL,
                json.dumps({"policy": policy, "runtime_enforcement": runtime_enforcement}),
            )
        except Exception:
            pass

    # 3. Enforce block — write security event and return 403
    if policy == "block" and runtime_enforcement:
        db.add(
            SecurityEvent(
                workspace_id=workspace.id,
                event_type="tool_runtime_blocked",
                tool_name=tool_name,
                details={"enforcement": "runtime", "cache_hit": cache_hit},
            )
        )
        await db.commit()
        log.warning("tool_runtime_blocked", tool_name=tool_name, workspace_id=str(workspace.id))
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' is blocked by workspace policy",
        )

    return ToolCheckResponse(
        tool_name=tool_name,
        policy=policy,
        runtime_enforcement=runtime_enforcement,
        allowed=True,
    )


# ── GET /tools/registry ───────────────────────────────────────────────────────


@router.get("/registry", response_model=ToolRegistryList)
async def list_tool_registry(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ToolRegistryList:
    result = await db.execute(
        select(ToolRegistry)
        .where(ToolRegistry.workspace_id == workspace.id)
        .order_by(ToolRegistry.tool_name)
    )
    tools = result.scalars().all()
    return ToolRegistryList(items=[_tool_to_response(t) for t in tools])


# ── POST /tools/registry ──────────────────────────────────────────────────────


@router.post("/registry", response_model=ToolRegistryResponse, status_code=201)
async def upsert_tool_registry(
    body: ToolRegistryCreate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Any, Depends(get_redis)],
) -> ToolRegistryResponse:
    existing_result = await db.execute(
        select(ToolRegistry).where(
            ToolRegistry.workspace_id == workspace.id,
            ToolRegistry.tool_name == body.tool_name,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        await db.execute(
            update(ToolRegistry)
            .where(ToolRegistry.id == existing.id)
            .values(
                policy=body.policy,
                runtime_enforcement=body.runtime_enforcement,
                description=body.description,
                updated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        await db.refresh(existing)
        # Invalidate Redis cache
        try:
            await redis.delete(_cache_key(workspace.id, body.tool_name))
        except Exception:
            pass
        return _tool_to_response(existing)

    tool = ToolRegistry(
        workspace_id=workspace.id,
        tool_name=body.tool_name,
        policy=body.policy,
        runtime_enforcement=body.runtime_enforcement,
        description=body.description,
    )
    db.add(tool)
    await db.flush()
    await db.commit()
    await db.refresh(tool)
    # Invalidate Redis cache (in case a "allow" entry was cached for an unknown tool)
    try:
        await redis.delete(_cache_key(workspace.id, body.tool_name))
    except Exception:
        pass
    return _tool_to_response(tool)


# ── PATCH /tools/registry/{tool_name} ────────────────────────────────────────


@router.patch("/registry/{tool_name}", response_model=ToolRegistryResponse)
async def update_tool_registry(
    tool_name: str,
    body: ToolRegistryUpdate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Any, Depends(get_redis)],
) -> ToolRegistryResponse:
    result = await db.execute(
        select(ToolRegistry).where(
            ToolRegistry.workspace_id == workspace.id,
            ToolRegistry.tool_name == tool_name,
        )
    )
    tool = result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    values: dict[str, Any] = {"updated_at": datetime.now(UTC)}
    if body.policy is not None:
        values["policy"] = body.policy
    if body.description is not None:
        values["description"] = body.description
    if body.runtime_enforcement is not None:
        values["runtime_enforcement"] = body.runtime_enforcement

    await db.execute(update(ToolRegistry).where(ToolRegistry.id == tool.id).values(**values))
    await db.commit()
    await db.refresh(tool)

    # Invalidate Redis cache
    try:
        await redis.delete(_cache_key(workspace.id, tool_name))
    except Exception:
        pass

    return _tool_to_response(tool)


# ── DELETE /tools/registry/{tool_name} ───────────────────────────────────────


@router.delete("/registry/{tool_name}", status_code=204)
async def delete_tool_registry(
    tool_name: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Any, Depends(get_redis)],
) -> Response:
    result = await db.execute(
        select(ToolRegistry).where(
            ToolRegistry.workspace_id == workspace.id,
            ToolRegistry.tool_name == tool_name,
        )
    )
    tool = result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    await db.execute(delete(ToolRegistry).where(ToolRegistry.id == tool.id))
    await db.commit()

    # Invalidate Redis cache
    try:
        await redis.delete(_cache_key(workspace.id, tool_name))
    except Exception:
        pass

    return Response(status_code=204)


# ── GET /tools/security-events ────────────────────────────────────────────────


@router.get("/security-events", response_model=SecurityEventList)
async def list_security_events(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SecurityEventList:
    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == workspace.id)
        .order_by(SecurityEvent.detected_at.desc())
        .limit(100)
    )
    events = result.scalars().all()
    return SecurityEventList(items=[_event_to_response(e) for e in events])
