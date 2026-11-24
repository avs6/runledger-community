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
POST   /mcp-registry/{id}/discover                Connect, refresh tools and real health status
GET    /mcp-registry/tools                        List discovered tools
POST   /mcp-registry/tools/call                   Governed call: policy → (hold | block | execute)
GET    /mcp-registry/tool-calls                   List recent tool calls (filters: status, server, tool)
POST   /mcp-registry/tool-calls/{id}/resume       Execute a held call once its approval is approved

Per-server permissions are ToolPolicy rows with scope_type ``mcp_server`` (see
/tool-policies); the separate, never-enforced permission table was removed (S-23).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_key_scope,
    require_workspace_admin,
    require_workspace_writer,
)
from runledger_api.core.pagination import PageDep, paginate, paginate_list
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.core.scopes import MCP, WRITE
from runledger_api.models.approvals import Approval
from runledger_api.models.mcp_registry import McpServer, McpToolCall
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.mcp_registry import (
    McpDiscoverResponse,
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
from runledger_api.services import mcp_client
from runledger_api.services import plugin_runner as governance
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.sessions import resolve_principal_user_id

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


@router.post(
    "",
    response_model=McpServerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
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
    await db.flush()
    await emit_audit_event(
        db,
        ws.id,
        "mcp_server.created",
        target_type="mcp_server",
        target_id=str(srv.id),
        after={"name": srv.name, "transport": srv.transport, "url": srv.url},
    )
    await db.commit()
    await db.refresh(srv)
    return _server_to_response(srv)


@router.get("", response_model=McpServerList, dependencies=[Depends(analytics_rate_limit)])
async def list_servers(
    ws: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    include_inactive: bool = False,
) -> McpServerList:
    q = select(McpServer).where(McpServer.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(McpServer.is_active.is_(True))
    q = q.order_by(McpServer.name, McpServer.id)
    rows = await paginate(db, q, page, response)
    return McpServerList(items=[_server_to_response(s) for s in rows])


@router.get(
    "/tools", response_model=McpToolListResponse, dependencies=[Depends(analytics_rate_limit)]
)
async def list_tools(
    ws: WorkspaceDep, db: DbDep, page: PageDep, response: Response
) -> McpToolListResponse:
    rows = (
        (
            await db.execute(
                select(McpServer).where(
                    McpServer.workspace_id == ws.id, McpServer.is_active.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    items: list[McpToolListItem] = []
    for s in rows:
        for t in s.discovered_tools or []:
            items.append(
                McpToolListItem(
                    server_id=s.id,
                    server_name=s.name,
                    tool_name=t.get("name", ""),
                    description=t.get("description"),
                )
            )
    return McpToolListResponse(items=paginate_list(items, page, response))


@router.get(
    "/tool-calls", response_model=McpToolCallList, dependencies=[Depends(analytics_rate_limit)]
)
async def list_tool_calls(
    ws: WorkspaceDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    status_filter: Annotated[str | None, Query(alias="status", max_length=32)] = None,
    server_id: uuid.UUID | None = None,
    tool_name: Annotated[str | None, Query(max_length=200)] = None,
) -> McpToolCallList:
    q = select(McpToolCall).where(McpToolCall.workspace_id == ws.id)
    if status_filter:
        q = q.where(McpToolCall.status == status_filter)
    if server_id:
        q = q.where(McpToolCall.mcp_server_id == server_id)
    if tool_name:
        q = q.where(McpToolCall.tool_name == tool_name)
    rows = await paginate(
        db, q.order_by(McpToolCall.created_at.desc(), McpToolCall.id), page, response
    )
    return McpToolCallList(items=[_call_to_response(c) for c in rows])


@router.get(
    "/{server_id}", response_model=McpServerResponse, dependencies=[Depends(analytics_rate_limit)]
)
async def get_server(server_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> McpServerResponse:
    srv = (
        await db.execute(
            select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not srv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found")
    return _server_to_response(srv)


@router.put(
    "/{server_id}",
    response_model=McpServerResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def update_server(
    server_id: uuid.UUID, body: McpServerUpdate, ws: WorkspaceDep, db: DbDep
) -> McpServerResponse:
    srv = (
        await db.execute(
            select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if not srv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(srv, k, v)
    srv.updated_at = datetime.now(UTC)
    await emit_audit_event(
        db,
        ws.id,
        "mcp_server.updated",
        target_type="mcp_server",
        target_id=str(srv.id),
        after={k: v for k, v in changes.items() if k not in {"auth_config", "env"}},
    )
    await db.commit()
    await db.refresh(srv)
    return _server_to_response(srv)


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def deactivate_server(server_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    await db.execute(
        update(McpServer)
        .where(McpServer.id == server_id, McpServer.workspace_id == ws.id)
        .values(is_active=False, updated_at=datetime.now(UTC))
    )
    await emit_audit_event(
        db, ws.id, "mcp_server.deactivated", target_type="mcp_server", target_id=str(server_id)
    )
    await db.commit()


def _call_to_response(c: McpToolCall) -> McpToolCallResponse:
    return McpToolCallResponse(
        id=c.id,
        mcp_server_id=c.mcp_server_id,
        tool_name=c.tool_name,
        arguments=c.arguments or {},
        result=c.result,
        cost_usd=c.cost_usd,
        latency_ms=c.latency_ms,
        status=c.status,
        error=c.error,
        created_at=c.created_at,
        decision=c.decision,
        policy_name=c.policy_name,
        approval_id=c.approval_id,
        end_user_id=c.end_user_id,
    )


async def _active_server(db: AsyncSession, ws_id: uuid.UUID, server_id: uuid.UUID) -> McpServer:
    srv = (
        await db.execute(
            select(McpServer).where(McpServer.id == server_id, McpServer.workspace_id == ws_id)
        )
    ).scalar_one_or_none()
    if not srv or not srv.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MCP server not found or inactive")
    return srv


async def _execute(call: McpToolCall, srv: McpServer) -> None:
    """Run the tool on the MCP server and record the real outcome on ``call``."""
    try:
        outcome = await mcp_client.call_tool(srv, call.tool_name, call.arguments or {})
    except mcp_client.McpNotExecutable as exc:
        call.status = "not_executed"
        call.error = str(exc)
        return
    except mcp_client.McpError as exc:
        call.status = "error"
        call.error = str(exc)[:2000]
        return
    call.result = outcome.result
    call.latency_ms = outcome.latency_ms
    call.status = "error" if outcome.is_error else "success"
    call.error = "tool returned isError" if outcome.is_error else None


@router.post(
    "/tools/call",
    response_model=McpToolCallResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_writer)],
)
async def call_tool(
    body: McpToolCallRequest,
    request: Request,
    response: Response,
    ws: WorkspaceDep,
    db: DbDep,
) -> McpToolCallResponse:
    """Governed MCP proxy (review S-01, cd:S-04).

    The one tool-policy evaluator decides; ``block`` → 403 (recorded), approval →
    202 with a real ``approval_id`` (resume after approval), otherwise the tool is
    executed on the registered HTTP MCP server and its real result is stored.
    """
    api_key = getattr(request.state, "api_key", None)
    require_key_scope(api_key, MCP | WRITE)
    srv = await _active_server(db, ws.id, body.server_id)
    principal = await resolve_principal_user_id(
        db, api_key=api_key, end_user_id=body.end_user_id, workspace=ws
    )
    ctx = await governance.build_context(
        db,
        ws.id,
        body.tool_name,
        api_key=api_key,
        principal_user_id=principal,
        end_user_id=body.end_user_id,
        server_id=srv.id,
        arguments=body.arguments,
        feature_tag=body.feature_tag,
        tool_type="mcp",
    )
    call = McpToolCall(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        mcp_server_id=srv.id,
        api_key_id=getattr(api_key, "id", None),
        tool_name=body.tool_name,
        arguments=body.arguments,
        end_user_id=body.end_user_id,
        status="pending",
    )
    try:
        decision = await governance.govern_tool_call(
            db,
            ws.id,
            ctx,
            source="mcp_registry",
            approval_id=body.approval_id,
            hold_type=governance.MCP_HOLD_TYPE,
            requested_by=str(principal) if principal else None,
            hold_extra={"mcp_call_id": str(call.id), "server_name": srv.name},
        )
    except governance.ToolCallBlocked as exc:
        call.status, call.decision = "blocked", "block"
        call.policy_name, call.error = exc.decision.policy_name, exc.decision.reason
        db.add(call)
        await db.commit()
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Tool call '{body.tool_name}' blocked: {exc.decision.reason}",
        ) from exc
    except governance.ToolCallHeld as exc:
        call.status, call.decision = "pending_approval", "require_approval"
        call.policy_name, call.approval_id = exc.decision.policy_name, exc.approval_id
        call.result = {"approval_id": str(exc.approval_id), "reason": exc.decision.reason}
        db.add(call)
        await db.commit()
        await db.refresh(call)
        response.status_code = status.HTTP_202_ACCEPTED
        response.headers["X-RunLedger-Approval-Id"] = str(exc.approval_id)
        return _call_to_response(call)

    call.decision, call.policy_name = decision.action, decision.policy_name
    await _execute(call, srv)
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return _call_to_response(call)


@router.post(
    "/tool-calls/{call_id}/resume",
    response_model=McpToolCallResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_writer)],
)
async def resume_tool_call(
    call_id: uuid.UUID, request: Request, ws: WorkspaceDep, db: DbDep
) -> McpToolCallResponse:
    """Execute a held call once its Approval is approved (409 while pending)."""
    require_key_scope(getattr(request.state, "api_key", None), MCP | WRITE)
    call = (
        await db.execute(
            select(McpToolCall).where(McpToolCall.id == call_id, McpToolCall.workspace_id == ws.id)
        )
    ).scalar_one_or_none()
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool call not found")
    if call.status != "pending_approval" or call.approval_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Tool call is {call.status}, not held")
    approval = await db.get(Approval, call.approval_id)
    if approval is None or approval.workspace_id != ws.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Approval not found")
    if approval.status == "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Approval is still pending")
    if approval.status != "approved":
        call.status, call.error = "denied", f"approval {approval.status}"
        await db.commit()
        await db.refresh(call)
        return _call_to_response(call)
    srv = await _active_server(db, ws.id, call.mcp_server_id)
    call.decision = "allow"
    await _execute(call, srv)
    await db.commit()
    await db.refresh(call)
    return _call_to_response(call)


@router.post(
    "/{server_id}/discover",
    response_model=McpDiscoverResponse,
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def discover_server(server_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> McpDiscoverResponse:
    """Connect to the server, refresh ``discovered_tools`` and record real health."""
    srv = await _active_server(db, ws.id, server_id)
    error: str | None = None
    try:
        srv.discovered_tools = await mcp_client.list_tools(srv)
        srv.health_status = "healthy"
    except mcp_client.McpNotExecutable as exc:
        srv.health_status, error = "client_side", str(exc)
    except mcp_client.McpError as exc:
        srv.health_status, error = "unreachable", str(exc)[:500]
    srv.last_health_check = datetime.now(UTC)
    srv.updated_at = datetime.now(UTC)
    await db.commit()
    return McpDiscoverResponse(
        server_id=srv.id,
        health_status=srv.health_status,
        tool_count=len(srv.discovered_tools or []),
        error=error,
    )


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
            {
                "name": "brave_local_search",
                "description": "Search local business & points of interest",
            },
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


@router.post(
    "/seed-defaults",
    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)],
)
async def seed_default_mcp_servers(ws: WorkspaceDep, db: DbDep) -> dict:
    added = 0
    for srv_def in DEFAULT_POPULAR_MCP_SERVERS:
        existing = (
            await db.execute(
                select(McpServer).where(
                    McpServer.workspace_id == ws.id, McpServer.name == srv_def["name"]
                )
            )
        ).scalar_one_or_none()
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
                health_status="client_side",
                is_active=True,
            )
            db.add(srv)
            added += 1
    await db.commit()
    return {"status": "seeded", "servers_added": added, "total": len(DEFAULT_POPULAR_MCP_SERVERS)}
