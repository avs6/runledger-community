#!/usr/bin/env python3
"""
Proxy a local stdio MCP client to RunLedger's streamable HTTP MCP endpoint.

Use this when an IDE or desktop agent can only launch local stdio MCP servers.
The bridge reads JSON-RPC messages from stdin, forwards them to /mcp/, and writes
the RunLedger MCP response back to stdout.

Environment:
  RUNLEDGER_BASE_URL  Defaults to http://localhost:8201
  RUNLEDGER_API_KEY   Workspace-scoped RunLedger API key
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib import error, request


BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

# Force unbuffered line-by-line stdio output regardless of launcher environment
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(line_buffering=True)
    except Exception:
        pass


def _jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    res: dict[str, Any] = {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
    }
    if message_id is not None:
        res["id"] = message_id
    else:
        res["id"] = 0
    return res


def _post_to_runledger(payload: dict[str, Any]) -> dict[str, Any] | None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}/mcp/",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    opener = request.build_opener(request.ProxyHandler({}))
    with opener.open(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        if not raw.strip():
            return None
        if raw.startswith("event:"):
            for line in raw.splitlines():
                if line.startswith("data: "):
                    return json.loads(line.removeprefix("data: "))
        return json.loads(raw)


def main() -> int:
    if not API_KEY:
        print(
            json.dumps(_jsonrpc_error(0, -32000, "RUNLEDGER_API_KEY is required")),
            flush=True,
        )
        return 1

    for line in sys.stdin:
        if not line.strip():
            continue
        payload = None
        try:
            payload = json.loads(line)
            is_notification = not isinstance(payload, dict) or ("id" not in payload) or (payload.get("id") is None)
            if is_notification:
                try:
                    _post_to_runledger(payload)
                except Exception:
                    pass
                continue  # MCP / JSON-RPC specification: Notifications MUST NOT write responses to stdout

            response = _post_to_runledger(payload)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_error(0, -32700, f"Invalid JSON: {exc}")
        except error.HTTPError as exc:
            msg_id = payload.get("id") if (isinstance(payload, dict) and payload.get("id") is not None) else 0
            response = _jsonrpc_error(msg_id, -32000, exc.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - bridge must report failures to the MCP client
            msg_id = payload.get("id") if (isinstance(payload, dict) and payload.get("id") is not None) else 0
            response = _jsonrpc_error(msg_id, -32000, str(exc))

        if response is not None:
            print(json.dumps(response), flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
