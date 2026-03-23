"""
RunLedger MCP Server.

Exposes RunLedger data as MCP tools so Claude Desktop, Claude Code, and any
MCP-compatible client can query runs, analytics, budgets, and prompts.

The MCP server is mounted directly inside the RunLedger API at /mcp using
the streamable-HTTP transport — no separate container or process needed.

Connecting from Claude Code (CLI):
    claude mcp add --transport http runledger http://localhost:8000/mcp

Connecting from Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "runledger": {
          "url": "http://localhost:8000/mcp"
        }
      }
    }

The RUNLEDGER_API_KEY env var must be set to a valid workspace API key.
The server calls back to itself via http://localhost:8000 (loopback).
"""

from __future__ import annotations

import os
from typing import Any, cast

import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")

mcp = FastMCP(
    name="RunLedger",
    instructions=(
        "RunLedger is an Agent FinOps Control Plane. "
        "Use these tools to query agent run history, costs, analytics, "
        "budgets, alerts, and prompts for AI applications."
    ),
)

# ── HTTP helper ───────────────────────────────────────────────────────────────


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a synchronous GET request to the RunLedger API."""
    resp = httpx.get(
        f"{BASE_URL}{path}",
        params=params,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=15.0,
    )
    resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_runs(
    limit: int = 20,
    status: str | None = None,
    feature_tag: str | None = None,
    end_user_id: str | None = None,
) -> dict[str, Any]:
    """
    List recent agent runs.

    Parameters
    ----------
    limit: Maximum number of runs to return (default 20, max 100).
    status: Filter by status — 'running', 'succeeded', 'failed', 'cancelled'.
    feature_tag: Filter by feature tag (e.g. 'support-chat', 'code-review').
    end_user_id: Filter by end-user identifier.
    """
    params: dict[str, Any] = {"limit": min(limit, 100)}
    if status:
        params["status"] = status
    if feature_tag:
        params["feature_tag"] = feature_tag
    if end_user_id:
        params["end_user_id"] = end_user_id
    return _get("/runs", params)


@mcp.tool()
def get_run(run_id: str) -> dict[str, Any]:
    """
    Get full details of a single agent run including spans, provider calls, and tool calls.

    Parameters
    ----------
    run_id: The UUID of the run.
    """
    return _get(f"/runs/{run_id}")


@mcp.tool()
def get_analytics_summary(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """
    Get analytics summary: total spend, run count, token usage, cost delta vs prior period.

    Parameters
    ----------
    from_date: ISO 8601 start datetime (e.g. '2026-01-01T00:00:00Z'). Defaults to 7 days ago.
    to_date: ISO 8601 end datetime. Defaults to now.
    """
    params: dict[str, Any] = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return _get("/analytics/summary", params)


@mcp.tool()
def get_spend_by_model(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """
    Get cost breakdown by model (e.g. gpt-4o, claude-3-5-sonnet, llama2).

    Parameters
    ----------
    from_date: ISO 8601 start datetime.
    to_date: ISO 8601 end datetime.
    """
    params: dict[str, Any] = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return _get("/analytics/spend-by-model", params)


@mcp.tool()
def list_budgets() -> dict[str, Any]:
    """List all configured spend budgets for this workspace."""
    return _get("/budgets")


@mcp.tool()
def check_budget(
    end_user_id: str | None = None,
    feature_tag: str | None = None,
) -> dict[str, Any]:
    """
    Check whether the current spend is within budget limits.

    Returns 'allowed': true/false, 'action' (block/throttle/notify/downgrade),
    and the triggering budget_id if blocked.

    Parameters
    ----------
    end_user_id: Check budget for this specific end user.
    feature_tag: Check budget for this feature tag.
    """
    params: dict[str, Any] = {}
    if end_user_id:
        params["end_user_id"] = end_user_id
    if feature_tag:
        params["feature_tag"] = feature_tag
    return _get("/budgets/check", params)


@mcp.tool()
def list_alert_rules() -> dict[str, Any]:
    """List all configured alert rules (error rate, latency, spend velocity, score thresholds)."""
    return _get("/alerts/rules")


@mcp.tool()
def get_alert_history(limit: int = 20) -> dict[str, Any]:
    """
    Get recent alert firings.

    Parameters
    ----------
    limit: Number of recent firings to return (default 20).
    """
    return _get("/alerts/history", {"limit": min(limit, 100)})


@mcp.tool()
def list_prompts() -> dict[str, Any]:
    """List all registered prompts in the prompt registry."""
    return _get("/prompts")


@mcp.tool()
def get_prompt(name: str, environment: str = "production") -> dict[str, Any]:
    """
    Get the latest version of a prompt.

    Parameters
    ----------
    name: Prompt name (slug, e.g. 'support-agent').
    environment: Target environment — 'production', 'staging', or 'dev'.
    """
    return _get(f"/prompts/{name}/latest", {"environment": environment})


@mcp.tool()
def get_cost_regressions() -> dict[str, Any]:
    """
    Detect agent workflows whose cost per run increased >20% vs the prior 7 days.
    Returns a list of regressions with workflow name, current cost, prior cost, and change %.
    """
    return _get("/analytics/regressions")


@mcp.tool()
def get_sessions(limit: int = 20) -> dict[str, Any]:
    """
    List recent multi-turn sessions (groups of runs sharing a session_id).

    Parameters
    ----------
    limit: Number of sessions to return (default 20).
    """
    return _get("/sessions", {"limit": min(limit, 100)})


# ── Resources ─────────────────────────────────────────────────────────────────


@mcp.resource("runledger://workspace/stats")
def workspace_stats() -> str:
    """Current workspace KPI snapshot — spend, runs, tokens (last 7 days)."""
    try:
        data = _get("/analytics/summary")
        return (
            f"RunLedger Workspace Stats (last 7 days)\n"
            f"Total Spend: ${float(data.get('total_cost_usd', 0)):.4f}\n"
            f"Agent Runs: {data.get('run_count', 0)}\n"
            f"Input Tokens: {data.get('total_input_tokens', 0):,}\n"
            f"Output Tokens: {data.get('total_output_tokens', 0):,}\n"
            f"Cost Change vs Prior 7d: {data.get('cost_delta_pct') or 'N/A'}%"
        )
    except Exception as exc:
        return f"Unable to fetch workspace stats: {exc}"


# ── Entry point (standalone stdio — for local development only) ───────────────

if __name__ == "__main__":
    # Run as standalone stdio server (e.g. for testing with `mcp dev`).
    # In production the server is mounted inside the FastAPI app at /mcp.
    mcp.run(transport="stdio")
