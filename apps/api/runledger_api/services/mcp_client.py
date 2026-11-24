"""Minimal MCP client for registered HTTP servers (review cd:S-04).

Speaks MCP over HTTP (JSON-RPC 2.0, "streamable HTTP" transport): ``initialize`` →
``notifications/initialized`` → ``tools/list`` or ``tools/call``. Responses may be
plain JSON or a ``text/event-stream`` carrying the JSON-RPC message.

``stdio`` servers run on the agent's machine (Claude Desktop, Cursor, the local
bridge), so the control plane cannot execute them; :class:`McpNotExecutable` says so
instead of pretending the call ran.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from runledger_api.models.mcp_registry import McpServer
from runledger_api.services.egress import EgressBlocked, check_url

PROTOCOL_VERSION = "2025-06-18"
_TIMEOUT_S = 20.0
_CLIENT_INFO = {"name": "runledger-mcp-proxy", "version": "1.0"}


class McpError(Exception):
    """The MCP server could not be reached or returned a protocol error."""


class McpNotExecutable(McpError):
    """The server's transport can't be executed by the control plane (stdio)."""


@dataclass
class McpCallResult:
    result: dict[str, Any]
    latency_ms: int
    is_error: bool


def _headers(server: McpServer, session_id: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
    }
    auth = server.auth_config or {}
    token = auth.get("token") or auth.get("api_key") or auth.get("bearer_token")
    if token and (server.auth_type or "bearer") in {"bearer", "api_key", "token"}:
        header_name = auth.get("header") or "Authorization"
        headers[str(header_name)] = (
            f"Bearer {token}" if header_name.lower() == "authorization" else str(token)
        )
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return headers


def _parse_message(resp: httpx.Response, request_id: int) -> dict[str, Any]:
    content_type = resp.headers.get("content-type", "")
    messages: list[dict[str, Any]] = []
    if "text/event-stream" in content_type:
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                try:
                    messages.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:
                    continue
    else:
        body = resp.json()
        messages = body if isinstance(body, list) else [body]
    for msg in messages:
        if isinstance(msg, dict) and msg.get("id") == request_id:
            if "error" in msg:
                err = msg["error"] or {}
                raise McpError(f"MCP error {err.get('code')}: {err.get('message')}")
            return msg.get("result") or {}
    raise McpError("MCP server returned no response for the request")


async def _rpc(
    client: httpx.AsyncClient,
    server: McpServer,
    method: str,
    params: dict[str, Any] | None,
    request_id: int,
    session_id: str | None,
) -> tuple[dict[str, Any], str | None]:
    resp = await client.post(
        str(server.url),
        headers=_headers(server, session_id),
        json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
    )
    if resp.status_code >= 400:
        raise McpError(f"MCP server returned HTTP {resp.status_code} for {method}")
    return _parse_message(resp, request_id), resp.headers.get("mcp-session-id") or session_id


async def _session(client: httpx.AsyncClient, server: McpServer) -> str | None:
    _, session_id = await _rpc(
        client,
        server,
        "initialize",
        {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": _CLIENT_INFO},
        1,
        None,
    )
    await client.post(
        str(server.url),
        headers=_headers(server, session_id),
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    return session_id


def _check_executable(server: McpServer) -> None:
    if (server.transport or "http").lower() == "stdio" or not server.url:
        raise McpNotExecutable(
            "stdio MCP servers run on the agent's machine; govern them with "
            "runledger.filter_mcp_tool or POST /tool-policies/check, or register an HTTP endpoint"
        )
    try:
        check_url(str(server.url))
    except EgressBlocked as exc:
        raise McpError(f"MCP server URL refused: {exc}") from exc


async def call_tool(
    server: McpServer,
    tool_name: str,
    arguments: dict[str, Any] | None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> McpCallResult:
    _check_executable(server)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_S, follow_redirects=False, transport=transport
        ) as client:
            session_id = await _session(client, server)
            result, _ = await _rpc(
                client,
                server,
                "tools/call",
                {"name": tool_name, "arguments": arguments or {}},
                2,
                session_id,
            )
    except httpx.HTTPError as exc:
        raise McpError(f"MCP server unreachable: {exc}") from exc
    return McpCallResult(
        result=result,
        latency_ms=int((time.perf_counter() - started) * 1000),
        is_error=bool(result.get("isError")),
    )


async def list_tools(
    server: McpServer, *, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict[str, Any]]:
    _check_executable(server)
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_S, follow_redirects=False, transport=transport
        ) as client:
            session_id = await _session(client, server)
            result, _ = await _rpc(client, server, "tools/list", {}, 2, session_id)
    except httpx.HTTPError as exc:
        raise McpError(f"MCP server unreachable: {exc}") from exc
    tools = result.get("tools") or []
    return [
        {
            "name": t.get("name", ""),
            "description": t.get("description"),
            "input_schema": t.get("inputSchema"),
        }
        for t in tools
        if isinstance(t, dict) and t.get("name")
    ]
