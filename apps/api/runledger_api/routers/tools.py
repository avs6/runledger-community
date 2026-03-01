"""
Tool registry and security events endpoints.

Prefix: /tools
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET    /tools/registry                   List tool registry entries
POST   /tools/registry                   Upsert a tool entry
PATCH  /tools/registry/{tool_name}       Update policy/description
DELETE /tools/registry/{tool_name}       Remove a tool entry
GET    /tools/security-events            List security events (limit 100)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.ledger import SecurityEvent, ToolRegistry
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.tools import (
    SecurityEventList,
    SecurityEventResponse,
    ToolRegistryCreate,
    ToolRegistryList,
    ToolRegistryResponse,
    ToolRegistryUpdate,
)

router = APIRouter(prefix="/tools", tags=["tools"])
log = structlog.get_logger()


def _tool_to_response(tool: ToolRegistry) -> ToolRegistryResponse:
    return ToolRegistryResponse(
        id=str(tool.id),
        workspace_id=str(tool.workspace_id),
        tool_name=tool.tool_name,
        policy=tool.policy,
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
) -> ToolRegistryResponse:
    # Check if already exists
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
                description=body.description,
                updated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        await db.refresh(existing)
        return _tool_to_response(existing)

    tool = ToolRegistry(
        workspace_id=workspace.id,
        tool_name=body.tool_name,
        policy=body.policy,
        description=body.description,
    )
    db.add(tool)
    await db.flush()
    await db.commit()
    await db.refresh(tool)
    return _tool_to_response(tool)


# ── PATCH /tools/registry/{tool_name} ────────────────────────────────────────


@router.patch("/registry/{tool_name}", response_model=ToolRegistryResponse)
async def update_tool_registry(
    tool_name: str,
    body: ToolRegistryUpdate,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
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

    await db.execute(update(ToolRegistry).where(ToolRegistry.id == tool.id).values(**values))
    await db.commit()
    await db.refresh(tool)
    return _tool_to_response(tool)


# ── DELETE /tools/registry/{tool_name} ───────────────────────────────────────


@router.delete("/registry/{tool_name}", status_code=204)
async def delete_tool_registry(
    tool_name: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
