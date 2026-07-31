#!/usr/bin/env python3
"""Validate the canonical RunLedger MCP endpoint.

This checks the streamable-HTTP handshake and confirms the Phase 1A control-plane
tools are visible to an MCP client.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib import request


REQUIRED_TOOLS = {
    "runledger.budget_check",
    "runledger.policy_check",
    "runledger.recommend_route",
    "runledger.record_run_start",
    "runledger.record_span",
    "runledger.record_tool_call",
    "runledger.record_model_call",
    "runledger.record_outcome",
    "runledger.query_runs",
    "runledger.query_costs",
    "runledger.query_optimizations",
    "runledger.filter_mcp_tool",
}


def parse_response(raw: str) -> dict[str, Any]:
    if raw.startswith("event:"):
        for line in raw.splitlines():
            if line.startswith("data: "):
                return json.loads(line.removeprefix("data: "))
    return json.loads(raw)


def rpc(endpoint: str, api_key: str, payload: dict[str, Any], session_id: str | None = None) -> tuple[dict[str, Any], str | None]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {api_key}",
    }
    if session_id:
        headers["mcp-session-id"] = session_id

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return parse_response(body), resp.headers.get("mcp-session-id") or session_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RunLedger MCP streamable-HTTP connectivity.")
    parser.add_argument("--endpoint", default=os.getenv("RUNLEDGER_MCP_ENDPOINT", "http://localhost:8201/mcp"))
    parser.add_argument("--api-key", default=os.getenv("RUNLEDGER_API_KEY", ""))
    args = parser.parse_args()

    if not args.api_key:
        print("RUNLEDGER_API_KEY or --api-key is required", file=sys.stderr)
        return 2

    init, session_id = rpc(
        args.endpoint,
        args.api_key,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "runledger-mcp-validator", "version": "1.0"},
            },
        },
    )
    if "error" in init:
        raise SystemExit(f"initialize failed: {init['error']}")

    tools_response, _ = rpc(
        args.endpoint,
        args.api_key,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        session_id,
    )
    if "error" in tools_response:
        raise SystemExit(f"tools/list failed: {tools_response['error']}")

    tools = {item.get("name") for item in tools_response.get("result", {}).get("tools", [])}
    missing = sorted(REQUIRED_TOOLS - tools)
    if missing:
        raise SystemExit(f"missing required MCP tools: {', '.join(missing)}")

    print(f"MCP endpoint ok: {args.endpoint}")
    print(f"Required tools visible: {len(REQUIRED_TOOLS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
