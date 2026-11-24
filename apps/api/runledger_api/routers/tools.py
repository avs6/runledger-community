"""
Tool catalog, runtime tool check, and security events.

Prefix: /tools
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
GET    /tools/check/{tool_name}       Runtime decision for the SDK (shared evaluator)
GET    /tools/registry                List catalog entries (with their effective decision)
POST   /tools/registry                Upsert a catalog entry (+ its managed policy)
PATCH  /tools/registry/{tool_name}    Update description / policy
DELETE /tools/registry/{tool_name}    Remove the entry and its managed policy
GET    /tools/security-events         Paginated security events (event_type, tool_name filters)

The registry is a catalog. Its ``policy`` is stored as the managed ToolPolicy row
``registry:<tool>`` (priority 50), so there is one tool-control system (review S-07)
and one evaluator for this check, /policies/check, the dry run, MCP and the gateway
(S-06, S-08).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_writer
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.models.ledger import SecurityEvent, ToolRegistry
from runledger_api.models.tenant import Workspace
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.schemas.tools import (
    SecurityEventList,
    SecurityEventResponse,
    ToolCheckResponse,
    ToolRegistryCreate,
    ToolRegistryList,
    ToolRegistryResponse,
    ToolRegistryUpdate,
)
from runledger_api.services import plugin_runner as governance
from runledger_api.services import tool_policy_engine as engine
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.sessions import resolve_principal_user_id

router = APIRouter(prefix="/tools", tags=["tools"])
log = structlog.get_logger()

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _managed_name(tool_name: str) -> str:
    return f"{engine.REGISTRY_POLICY_PREFIX}{tool_name}"[:200]


async def _managed_policy(db: AsyncSession, ws_id: uuid.UUID, tool_name: str) -> ToolPolicy | None:
    return (
        await db.execute(
            select(ToolPolicy).where(
                ToolPolicy.workspace_id == ws_id,
                ToolPolicy.name == _managed_name(tool_name),
                ToolPolicy.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def _set_managed_policy(
    db: AsyncSession, ws_id: uuid.UUID, tool_name: str, action: str
) -> ToolPolicy:
    policy = await _managed_policy(db, ws_id, tool_name)
    if policy is None:
        policy = ToolPolicy(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            name=_managed_name(tool_name),
            description="Managed by the tool registry",
            tool_name=tool_name,
            action=action,
            condition_type="all",
            scope_type="workspace",
            priority=engine.REGISTRY_POLICY_PRIORITY,
            is_active=True,
        )
        db.add(policy)
    else:
        policy.action = action
        policy.updated_at = datetime.now(UTC)
    engine.invalidate(ws_id)
    return policy


def _tool_to_response(
    tool: ToolRegistry,
    managed: ToolPolicy | None,
    rules: list[engine.PolicyRule],
) -> ToolRegistryResponse:
    decision = engine.evaluate(rules, engine.ToolCallContext(tool_name=tool.tool_name))
    return ToolRegistryResponse(
        id=str(tool.id),
        workspace_id=str(tool.workspace_id),
        tool_name=tool.tool_name,
        policy=engine.normalize_action(managed.action) if managed is not None else "allow",
        runtime_enforcement=True,
        description=tool.description,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        effective_action=decision.action,
        effective_policy_name=decision.policy_name,
        policy_id=str(managed.id) if managed is not None else None,
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
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
    end_user_id: Annotated[str | None, Query(max_length=255)] = None,
    feature_tag: Annotated[str | None, Query(max_length=255)] = None,
    risk_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    approval_id: uuid.UUID | None = None,
) -> ToolCheckResponse:
    """Runtime decision, called by the SDK before it executes a tool.

    ``block`` → 403. ``require_approval`` → 403 with ``X-RunLedger-Approval-Id``
    (a real pending Approval); repeat with ``?approval_id=`` once it is approved.
    Identity comes from the authenticated key.
    """
    api_key = getattr(request.state, "api_key", None)
    principal = await resolve_principal_user_id(
        db, api_key=api_key, end_user_id=end_user_id, workspace=workspace
    )
    ctx = await governance.build_context(
        db,
        workspace.id,
        tool_name,
        api_key=api_key,
        principal_user_id=principal,
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        risk_score=risk_score,
    )
    try:
        decision = await governance.govern_tool_call(
            db,
            workspace.id,
            ctx,
            source="tools_check",
            approval_id=approval_id,
            hold_type=governance.GATEWAY_HOLD_TYPE,
            requested_by=str(principal) if principal else None,
        )
    except governance.ToolCallBlocked as exc:
        await db.commit()
        log.warning("tool_runtime_blocked", tool_name=tool_name, workspace_id=str(workspace.id))
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' is blocked by workspace policy: {exc.decision.reason}",
        ) from exc
    except governance.ToolCallHeld as exc:
        await db.commit()
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' requires approval {exc.approval_id}",
            headers={"X-RunLedger-Approval-Id": str(exc.approval_id)},
        ) from exc
    await db.commit()
    return ToolCheckResponse(
        tool_name=tool_name,
        policy=decision.action,
        runtime_enforcement=True,
        allowed=True,
        policy_name=decision.policy_name,
        reason=decision.reason,
    )


# ── Registry (catalog) ────────────────────────────────────────────────────────


async def _registry_entry(db: AsyncSession, ws_id: uuid.UUID, tool_name: str) -> ToolRegistry:
    tool = (
        await db.execute(
            select(ToolRegistry).where(
                ToolRegistry.workspace_id == ws_id, ToolRegistry.tool_name == tool_name
            )
        )
    ).scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


async def _managed_by_tool(db: AsyncSession, ws_id: uuid.UUID) -> dict[str, ToolPolicy]:
    rows = (
        (
            await db.execute(
                select(ToolPolicy).where(
                    ToolPolicy.workspace_id == ws_id,
                    ToolPolicy.is_active.is_(True),
                    ToolPolicy.name.like(f"{engine.REGISTRY_POLICY_PREFIX}%"),
                )
            )
        )
        .scalars()
        .all()
    )
    return {p.tool_name: p for p in rows}


@router.get("/registry", response_model=ToolRegistryList)
async def list_tool_registry(workspace: WorkspaceDep, db: DbDep) -> ToolRegistryList:
    tools = (
        (
            await db.execute(
                select(ToolRegistry)
                .where(ToolRegistry.workspace_id == workspace.id)
                .order_by(ToolRegistry.tool_name)
            )
        )
        .scalars()
        .all()
    )
    managed = await _managed_by_tool(db, workspace.id)
    rules = await engine.load_rules(db, workspace.id)
    return ToolRegistryList(
        items=[_tool_to_response(t, managed.get(t.tool_name), rules) for t in tools]
    )


@router.post(
    "/registry",
    response_model=ToolRegistryResponse,
    status_code=201,
    dependencies=[Depends(require_workspace_writer)],
)
async def upsert_tool_registry(
    body: ToolRegistryCreate, workspace: WorkspaceDep, db: DbDep
) -> ToolRegistryResponse:
    tool = (
        await db.execute(
            select(ToolRegistry).where(
                ToolRegistry.workspace_id == workspace.id,
                ToolRegistry.tool_name == body.tool_name,
            )
        )
    ).scalar_one_or_none()
    if tool is None:
        tool = ToolRegistry(
            workspace_id=workspace.id, tool_name=body.tool_name, description=body.description
        )
        db.add(tool)
    else:
        tool.description = body.description
        tool.updated_at = datetime.now(UTC)
    managed = await _set_managed_policy(db, workspace.id, body.tool_name, body.policy)
    await db.flush()
    await emit_audit_event(
        db,
        workspace.id,
        "tool_registry.upserted",
        target_type="tool",
        target_id=body.tool_name,
        after={"policy": body.policy, "description": body.description},
    )
    await db.commit()
    await db.refresh(tool)
    rules = await engine.load_rules(db, workspace.id, use_cache=False)
    return _tool_to_response(tool, managed, rules)


@router.patch(
    "/registry/{tool_name}",
    response_model=ToolRegistryResponse,
    dependencies=[Depends(require_workspace_writer)],
)
async def update_tool_registry(
    tool_name: str, body: ToolRegistryUpdate, workspace: WorkspaceDep, db: DbDep
) -> ToolRegistryResponse:
    tool = await _registry_entry(db, workspace.id, tool_name)
    values: dict[str, object] = {"updated_at": datetime.now(UTC)}
    if body.description is not None:
        values["description"] = body.description
    await db.execute(update(ToolRegistry).where(ToolRegistry.id == tool.id).values(**values))
    managed = await _managed_policy(db, workspace.id, tool_name)
    if body.policy is not None:
        managed = await _set_managed_policy(db, workspace.id, tool_name, body.policy)
    await emit_audit_event(
        db,
        workspace.id,
        "tool_registry.updated",
        target_type="tool",
        target_id=tool_name,
        after=body.model_dump(exclude_unset=True, exclude={"runtime_enforcement"}),
    )
    await db.commit()
    await db.refresh(tool)
    rules = await engine.load_rules(db, workspace.id, use_cache=False)
    return _tool_to_response(tool, managed, rules)


@router.delete(
    "/registry/{tool_name}", status_code=204, dependencies=[Depends(require_workspace_writer)]
)
async def delete_tool_registry(tool_name: str, workspace: WorkspaceDep, db: DbDep) -> Response:
    tool = await _registry_entry(db, workspace.id, tool_name)
    await db.execute(delete(ToolRegistry).where(ToolRegistry.id == tool.id))
    managed = await _managed_policy(db, workspace.id, tool_name)
    if managed is not None:
        managed.is_active = False
        managed.updated_at = datetime.now(UTC)
    engine.invalidate(workspace.id)
    await emit_audit_event(
        db, workspace.id, "tool_registry.deleted", target_type="tool", target_id=tool_name
    )
    await db.commit()
    return Response(status_code=204)


# ── GET /tools/security-events ────────────────────────────────────────────────


@router.get("/security-events", response_model=SecurityEventList)
async def list_security_events(
    workspace: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
    tool_name: Annotated[str | None, Query(max_length=200)] = None,
) -> SecurityEventList:
    q = select(SecurityEvent).where(SecurityEvent.workspace_id == workspace.id)
    if event_type:
        q = q.where(SecurityEvent.event_type == event_type)
    if tool_name:
        q = q.where(SecurityEvent.tool_name == tool_name)
    events = await paginate(
        db, q.order_by(SecurityEvent.detected_at.desc(), SecurityEvent.id), page, response
    )
    return SecurityEventList(items=[_event_to_response(e) for e in events])
