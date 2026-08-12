"""
MCP Server Registry API.

Prefix: /mcp-registry
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /mcp-registry                              Register MCP server
GET    /mcp-registry                              List MCP servers
GET    /mcp-registry/{id}                         Get MCP server
PUT    /mcp-registry/{id}                         Update MCP server
DELETE /mcp-registry/{id}                         Deactivate MCP server
GET    /mcp-registry/tools                        List available tools (filtered by permissions)
POST   /mcp-registry/tools/call                   Call a tool through RunLedger
GET    /mcp-registry/tool-calls                   List recent tool calls
POST   /mcp-registry/permissions                  Grant permission
GET    /mcp-registry/permissions                  List permissions
DELETE /mcp-registry/permissions/{id}             Revoke permission
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.mcp_registry import McpPermission, McpServer, McpToolCall
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.mcp_registry import (
    McpPermissionCreate,
    McpPermissionList,
    McpPermissionResponse,
    McpServerCreate,
    McpServerList,
    McpServerResponse,
    McpServerUpdate,
    McpToolCallList,
    McpToolCallRequest,
    McpToolCallResponse,
    McpToolListItem,
    McpToolListResponse,
)

log = structlog.get_logger()
router = APIRouter(prefix="/mcp-registry", tags=["mcp-registry"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _server_to_response(s: McpServer) -> McpServerResponse:
    return McpServerResponse(
        id=s.id,
        workspace_id=s.workspace_id,
        name=s.name,
        description=s.description,
        transport=s.transport,
        url=s.url,
        command=s.command,
        args=s.args or [],
        env=s.env or {},
        auth_type=s.auth_type,
        discovered_tools=s.discovered_tools or [],
        discovered_resources=s.discovered_resources or [],
        discovered_prompts=s.discovered_prompts or [],
        health_status=s.health_status,
        last_health_check=s.last_health_check,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
        tool_count=len(s.discovered_tools or []),
        resource_count=len(s.discovered_resources or []),
        prompt_count=len(s.discovered_prompts or []),
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.post("", response_model=McpServerResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(management_rate_limit)])
async def register_server(body: McpServerCreate, ws: WorkspaceDep, db: DbDep) -> McpServerResponse:
    srv = McpServer(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        transport=body.transport,
        url=body.url,
        command=body.command,
        args=body.args,
        env=body.env,
        auth_type=body.auth_type,
        auth_config=body.auth_config,
    )
    db.add(srv)
    await db.commit()
    await db.refresh(srv)
    return _server_to_response(srv)


@router.get("", response_model=McpServerList, dependencies=[Depends(analytics_rate_limit)])
async def list_servers(
    ws: WorkspaceDep,
    db: DbDep,
    include_inactive: bool = False,
) -> McpServerList:
    q = select(McpServer).where(McpServer.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(McpServer.is_active.is_(True))
    q = q.order_by(McpServer.name)
    rows = (await db.execute(q)).scalars().all()
    return McpServerList(items=[_server_to_response(s) for s in rows])


@router.get("/tools", response_model=McpToolListResponse, dependencies=[Depends(analytics_rate_limit)])
async def list_tools(ws: WorkspaceDep, db: DbDep) -> McpToolListResponse:
    rows = (await db.execute(
        select(McpServer)
        .where(McpServer.workspace_id == ws.id, McpServer.is_active.is_(True))
    )).scalars().all()
    items: list[McpToolListItem] = []
    for s in rows:
        for t in s.discovered_tools or []:
            items.append(McpToolListItem(
                server_id=s.id,
                server_name=s.name,
                tool_name=t.get("name", ""),
                description=t.get("description"),
            ))
    return McpToolListResponse(items=items)


@router.get("/tool-calls", response_model=McpToolCallList, dependencies=[Depends(analytics_rate_limit)])
async def list_tool_calls(
    ws: WorkspaceDep,
    db: DbDep,
    limit: int = Query(50, ge=1, le=200),
) -> McpToolCallList:
    rows = (await db.execute(
        select(McpToolCall)
        .where(McpToolCall.workspace_id == ws.id)
        .order_by(McpToolCall.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return McpToolCallList(items=[McpToolCallResponse(
        id=c.id, mcp_server_id=c.mcp_server_id, tool_name=c.tool_name,
        arguments=c.arguments or {}, result=c.result, cost_usd=c.cost_usd,
        latency_ms=c.latency_ms, status=c.status, error=c.error, created_at=c.created_at,
    ) for c in rows])


@router.get("/{server_id}", response_model=McpServerResponse, dependencies=[Depends(analytics_rate_limit)])
async def get_server(server_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> McpServerResponse:
    srv = (await db.execute(
        select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not srv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found")
    return _server_to_response(srv)


@router.put("/{server_id}", response_model=McpServerResponse, dependencies=[Depends(management_rate_limit)])
async def update_server(server_id: uuid.UUID, body: McpServerUpdate, ws: WorkspaceDep, db: DbDep) -> McpServerResponse:
    srv = (await db.execute(
        select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not srv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(srv, k, v)
    srv.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(srv)
    return _server_to_response(srv)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(management_rate_limit)])
async def deactivate_server(server_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    await db.execute(
        update(McpServer)
        .where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
        .values(is_active=False, updated_at=datetime.now(UTC))
    )
    await db.commit()


@router.post("/tools/call", response_model=McpToolCallResponse,
             dependencies=[Depends(management_rate_limit)])
async def call_tool(body: McpToolCallRequest, ws: WorkspaceDep, db: DbDep) -> McpToolCallResponse:
    srv = (await db.execute(
        select(McpServer).where(McpServer.id == body.server_id, McpServer.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not srv or not srv.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found or inactive")

    # 1. Govern and filter tool call through ToolPolicy, Guardrails & Plugin Hooks
    from runledger_api.services.plugin_runner import govern_and_filter_tool_call  # noqa: PLC0415

    gov_res = await govern_and_filter_tool_call(
        db, ws.id, srv.id, body.tool_name, body.arguments
    )

    call_status = "success"
    result_data = None
    if gov_res.get("status") == "require_approval":
        call_status = "pending_approval"
        result_data = {
            "status": "pending_approval",
            "approval_id": gov_res.get("approval_id"),
            "reason": gov_res.get("reason"),
            "message": gov_res.get("message"),
        }

    call = McpToolCall(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        mcp_server_id=srv.id,
        tool_name=body.tool_name,
        arguments=body.arguments,
        status=call_status,
        result=result_data,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return McpToolCallResponse(
        id=call.id, mcp_server_id=call.mcp_server_id, tool_name=call.tool_name,
        arguments=call.arguments, result=call.result, cost_usd=call.cost_usd,
        latency_ms=call.latency_ms, status=call.status, error=call.error,
        created_at=call.created_at,
    )


# ── Permissions ──────────────────────────────────────────────────────────────


@router.post("/permissions", response_model=McpPermissionResponse,
             status_code=status.HTTP_201_CREATED, dependencies=[Depends(management_rate_limit)])
async def grant_permission(body: McpPermissionCreate, ws: WorkspaceDep, db: DbDep) -> McpPermissionResponse:
    perm = McpPermission(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        mcp_server_id=body.mcp_server_id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        allowed_tools=body.allowed_tools,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return McpPermissionResponse(
        id=perm.id, workspace_id=perm.workspace_id, mcp_server_id=perm.mcp_server_id,
        scope_type=perm.scope_type, scope_id=perm.scope_id, allowed_tools=perm.allowed_tools,
        created_at=perm.created_at,
    )


@router.get("/permissions", response_model=McpPermissionList,
            dependencies=[Depends(analytics_rate_limit)])
async def list_permissions(ws: WorkspaceDep, db: DbDep) -> McpPermissionList:
    rows = (await db.execute(
        select(McpPermission).where(McpPermission.workspace_id == ws.id)
        .order_by(McpPermission.created_at.desc())
    )).scalars().all()
    return McpPermissionList(items=[McpPermissionResponse(
        id=p.id, workspace_id=p.workspace_id, mcp_server_id=p.mcp_server_id,
        scope_type=p.scope_type, scope_id=p.scope_id, allowed_tools=p.allowed_tools,
        created_at=p.created_at,
    ) for p in rows])


@router.delete("/permissions/{perm_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(management_rate_limit)])
async def revoke_permission(perm_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    result = await db.execute(
        select(McpPermission).where(McpPermission.id == perm_id, McpPermission.workspace_id == ws.id)
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Permission not found")
    await db.delete(perm)
    await db.commit()


DEFAULT_POPULAR_MCP_SERVERS = [
    {
        "name": "GitHub MCP Server",
        "description": "Repo inspection, PR management, issues, and code search via GitHub API",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "discovered_tools": [
            {"name": "create_issue", "description": "Create an issue in a GitHub repository"},
            {"name": "get_file_contents", "description": "Read file contents from a repository"},
            {"name": "create_or_update_file", "description": "Commit file changes to a branch"},
            {"name": "create_pull_request", "description": "Create a new pull request"},
            {"name": "search_code", "description": "Search code across repositories"},
        ],
    },
    {
        "name": "PostgreSQL MCP Server",
        "description": "Database schema inspection, query execution, and tabular data analysis",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "discovered_tools": [
            {"name": "query", "description": "Run a read-only SQL query against Postgres"},
            {"name": "list_tables", "description": "List all tables and views in database"},
            {"name": "describe_table", "description": "Inspect column data types and foreign keys"},
        ],
    },
    {
        "name": "Brave Search MCP Server",
        "description": "Web search & local site search capabilities powered by Brave Search API",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "discovered_tools": [
            {"name": "brave_web_search", "description": "Execute web search query"},
            {"name": "brave_local_search", "description": "Search local business & points of interest"},
        ],
    },
    {
        "name": "Puppeteer MCP Server",
        "description": "Headless browser automation, web page rendering, and UI screenshot testing",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "discovered_tools": [
            {"name": "puppeteer_navigate", "description": "Navigate to URL in headless Chromium"},
            {"name": "puppeteer_screenshot", "description": "Capture screenshot of current page"},
            {"name": "puppeteer_click", "description": "Click an element by CSS selector"},
        ],
    },
    {
        "name": "FileSystem MCP Server",
        "description": "Secure workspace directory access, file reading, and editing",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"],
        "discovered_tools": [
            {"name": "read_file", "description": "Read content from workspace file"},
            {"name": "write_file", "description": "Write or update content of a file"},
            {"name": "list_directory", "description": "List contents of a directory"},
        ],
    },
]


@router.post("/seed-defaults", dependencies=[Depends(management_rate_limit)])
async def seed_default_mcp_servers(ws: WorkspaceDep, db: DbDep) -> dict:
    added = 0
    for srv_def in DEFAULT_POPULAR_MCP_SERVERS:
        existing = (await db.execute(
            select(McpServer).where(McpServer.workspace_id == ws.id, McpServer.name == srv_def["name"])
        )).scalar_one_or_none()
        if not existing:
            srv = McpServer(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                name=srv_def["name"],
                description=srv_def["description"],
                transport=srv_def["transport"],
                command=srv_def.get("command"),
                args=srv_def.get("args"),
                discovered_tools=srv_def.get("discovered_tools"),
                health_status="healthy",
                is_active=True,
            )
            db.add(srv)
            added += 1
    await db.commit()
    return {"status": "seeded", "servers_added": added, "total": len(DEFAULT_POPULAR_MCP_SERVERS)}
