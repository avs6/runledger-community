"""
MCP (Model Context Protocol) tool-call tracking.

Patches an ``mcp.ClientSession`` so that every ``call_tool`` invocation is
captured as a ``tool_call`` event in RunLedger.

Usage::

    from mcp import ClientSession
    import runledger_sdk

    rl = runledger_sdk.RunLedger(api_key="rl_live_...")

    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        rl.instrument_mcp(session)  # patch this session
        # All tool calls through `session.call_tool(...)` are now tracked.
"""

from __future__ import annotations

import time
import uuid as _uuid_mod
from typing import TYPE_CHECKING, Any

import structlog

from runledger_sdk.context import get_run_id

if TYPE_CHECKING:
    from runledger_sdk.transport import SyncTransport

log = structlog.get_logger()


def instrument_mcp_session(session: Any, transport: SyncTransport) -> None:
    """
    Patch ``session.call_tool`` to emit ``tool_call`` events for every MCP
    tool invocation.

    Parameters
    ----------
    session:
        An ``mcp.ClientSession`` instance after ``initialize()`` has been called.
    transport:
        The RunLedger SyncTransport (from ``rl._get_sync_transport()``).
    """
    original_call_tool = session.call_tool

    async def patched_call_tool(
        name: str, arguments: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        run_id = get_run_id()
        tool_call_id = str(_uuid_mod.uuid4())
        t0 = time.perf_counter()

        try:
            result = await original_call_tool(name, arguments, **kwargs)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_tool_call_event(
                    run_id=run_id,
                    tool_call_id=tool_call_id,
                    name=name,
                    tool_type=_infer_tool_type(name),
                    duration_ms=duration_ms,
                    status="success",
                )
            )
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            transport.enqueue(
                _build_tool_call_event(
                    run_id=run_id,
                    tool_call_id=tool_call_id,
                    name=name,
                    tool_type=_infer_tool_type(name),
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(exc).__name__,
                )
            )
            raise

    session.call_tool = patched_call_tool
    log.info("runledger_mcp_session_instrumented", session=repr(session))


def _build_tool_call_event(
    run_id: str,
    tool_call_id: str,
    name: str,
    tool_type: str,
    duration_ms: int,
    status: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_type": "tool_call",
        "run_id": run_id,
        "tool_call_id": tool_call_id,
        "tool_name": name,
        "tool_type": tool_type,
        "duration_ms": duration_ms,
        "status": status,
    }
    if error_type:
        event["error_type"] = error_type
    return event


# ── Heuristics ─────────────────────────────────────────────────────────────────

_WRITE_KEYWORDS = frozenset(
    [
        "write",
        "create",
        "update",
        "delete",
        "insert",
        "edit",
        "post",
        "put",
        "patch",
        "remove",
        "send",
    ]
)
_PRIVILEGED_KEYWORDS = frozenset(
    [
        "exec",
        "execute",
        "run",
        "shell",
        "bash",
        "eval",
        "admin",
        "sudo",
        "deploy",
        "migrate",
    ]
)


def _infer_tool_type(name: str) -> str:
    """Classify MCP tool as read / write / privileged based on its name."""
    lower = name.lower()
    if any(k in lower for k in _PRIVILEGED_KEYWORDS):
        return "privileged"
    if any(k in lower for k in _WRITE_KEYWORDS):
        return "write"
    return "read"
