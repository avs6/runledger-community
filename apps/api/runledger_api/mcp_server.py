"""
RunLedger MCP Server.

Exposes RunLedger as an MCP-native Agent FinOps control plane. Agents can use
RunLedger inline for policy and budget checks, or out of band to record runs,
spans, model calls, tool calls, outcomes, and optimization evidence.

The MCP server is mounted inside the RunLedger API at /mcp using streamable HTTP.
It can also run as a local stdio server for desktop clients and development.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.getenv("RUNLEDGER_API_KEY", "")
BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")

mcp = FastMCP(
    name="RunLedger",
    streamable_http_path="/",
    instructions=(
        "RunLedger is an AI Operations Ledger and Agent FinOps control plane. "
        "Use it before expensive work to check budgets and policies, during work "
        "to record spans/model/tool calls, and after work to record outcomes and "
        "query optimization opportunities."
    ),
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = httpx.get(
        f"{BASE_URL}{path}",
        params=params,
        headers=_headers(),
        timeout=15.0,
    )
    resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    resp = httpx.post(
        f"{BASE_URL}{path}",
        json=body,
        headers=_headers(),
        timeout=15.0,
    )
    resp.raise_for_status()
    if resp.status_code == 204:
        return {}
    return cast(dict[str, Any], resp.json())


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _decimal_to_str(value: float | int | str | Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


# ---------------------------------------------------------------------------
# Canonical RunLedger MCP tools
# ---------------------------------------------------------------------------


@mcp.tool(name="runledger.budget_check")
def runledger_budget_check(
    end_user_id: str | None = None,
    feature_tag: str | None = None,
) -> dict[str, Any]:
    """Check whether current workspace spend is inside configured budget limits."""
    params: dict[str, Any] = {}
    if end_user_id:
        params["end_user_id"] = end_user_id
    if feature_tag:
        params["feature_tag"] = feature_tag
    return _get("/budgets/check", params)


@mcp.tool(name="runledger.policy_check")
def runledger_policy_check(
    end_user_id: str | None = None,
    feature_tag: str | None = None,
    tool_name: str | None = None,
    model_alias: str | None = None,
) -> dict[str, Any]:
    """Evaluate the unified RunLedger runtime policy gate for an agent action."""
    return _post(
        "/policies/check",
        {
            "end_user_id": end_user_id,
            "feature_tag": feature_tag,
            "tool_name": tool_name,
            "model_alias": model_alias,
        },
    )


@mcp.tool(name="runledger.recommend_route")
def runledger_recommend_route(
    model_alias: str,
    end_user_id: str | None = None,
    feature_tag: str | None = None,
) -> dict[str, Any]:
    """
    Recommend whether an agent should use a model alias now.

    This is intentionally conservative: it combines the real policy gate with
    pending optimization recommendations when the flywheel service is available.
    """
    policy = runledger_policy_check(
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        model_alias=model_alias,
    )
    optimizations: dict[str, Any]
    try:
        optimizations = _get(
            "/gateway/flywheel/recommendations", {"status": "pending", "limit": 10}
        )
    except Exception as exc:
        optimizations = {"items": [], "warning": f"Optimization lookup unavailable: {exc}"}

    return {
        "requested_alias": model_alias,
        "allowed": policy.get("allowed", True),
        "decision": policy.get("decision", "allow"),
        "reasons": policy.get("reasons", []),
        "downgrade_model": policy.get("downgrade_model"),
        "gateway_route_available": policy.get("gateway_route_available"),
        "optimization_recommendations": optimizations.get("items", []),
    }


@mcp.tool(name="runledger.record_run_start")
def runledger_record_run_start(
    run_id: str | None = None,
    end_user_id: str | None = None,
    session_id: str | None = None,
    feature_tag: str | None = None,
    deployment_version: str | None = None,
    agent: str | None = None,
    intent: str | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    """Start a RunLedger run for an agent task and return the run_id to reuse."""
    resolved_run_id = run_id or str(uuid.uuid4())
    metadata = {k: v for k, v in {"agent": agent, "intent": intent, "task": task}.items() if v}
    _post(
        "/ingest/v1/events",
        {
            "event_type": "run_start",
            "run_id": resolved_run_id,
            "end_user_id": end_user_id,
            "session_id": session_id,
            "feature_tag": feature_tag,
            "deployment_version": deployment_version,
            "started_at": _iso_now(),
            "metadata": metadata or None,
        },
    )
    return {"accepted": 1, "run_id": resolved_run_id}


@mcp.tool(name="runledger.record_span")
def runledger_record_span(
    run_id: str,
    name: str,
    span_type: Literal["chain", "llm", "tool", "agent", "retrieval"] = "agent",
    span_id: str | None = None,
    parent_span_id: str | None = None,
    status: Literal["running", "succeeded", "failed"] = "succeeded",
    cost_usd: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a complete span for an agent, tool, model, chain, or retrieval step."""
    resolved_span_id = span_id or str(uuid.uuid4())
    now = _iso_now()
    events: list[dict[str, Any]] = [
        {
            "event_type": "span_start",
            "span_id": resolved_span_id,
            "run_id": run_id,
            "parent_span_id": parent_span_id,
            "span_type": span_type,
            "name": name,
            "started_at": now,
        },
        {
            "event_type": "span_end",
            "span_id": resolved_span_id,
            "run_id": run_id,
            "status": status,
            "ended_at": now,
            "cost_usd": _decimal_to_str(cost_usd),
            "metadata": metadata,
        },
    ]
    _post("/ingest/v1/batch", {"events": events})
    return {"accepted": len(events), "span_id": resolved_span_id}


@mcp.tool(name="runledger.record_tool_call")
def runledger_record_tool_call(
    run_id: str,
    tool_name: str,
    span_id: str | None = None,
    tool_type: Literal["read", "write", "privileged"] = "read",
    risk_score: int | None = None,
    duration_ms: int | None = None,
    status: str = "succeeded",
) -> dict[str, Any]:
    """Record a tool call made by an agent."""
    _post(
        "/ingest/v1/events",
        {
            "event_type": "tool_call",
            "run_id": run_id,
            "span_id": span_id,
            "tool_name": tool_name,
            "tool_type": tool_type,
            "risk_score": risk_score,
            "duration_ms": duration_ms,
            "status": status,
        },
    )
    return {"accepted": 1}


@mcp.tool(name="runledger.record_model_call")
def runledger_record_model_call(
    run_id: str,
    provider: str,
    model: str,
    span_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_input_tokens: int | None = None,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    status: str = "succeeded",
    error_type: str | None = None,
) -> dict[str, Any]:
    """Record an LLM/provider call, including token and cost details."""
    _post(
        "/ingest/v1/events",
        {
            "event_type": "provider_call",
            "run_id": run_id,
            "span_id": span_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens,
            "latency_ms": latency_ms,
            "cost_usd": _decimal_to_str(cost_usd),
            "status": status,
            "error_type": error_type,
        },
    )
    return {"accepted": 1}


@mcp.tool(name="runledger.record_outcome")
def runledger_record_outcome(
    run_id: str,
    outcome_type: str,
    success: bool,
    labels: dict[str, Any] | None = None,
    total_cost_usd: float | None = None,
    total_input_tokens: int | None = None,
    total_output_tokens: int | None = None,
    final_status: Literal["succeeded", "failed", "cancelled"] = "succeeded",
) -> dict[str, Any]:
    """Record task outcome and close the run with final cost/token totals."""
    now = _iso_now()
    events: list[dict[str, Any]] = [
        {
            "event_type": "outcome",
            "run_id": run_id,
            "outcome_type": outcome_type,
            "success": success,
            "labels": labels,
        },
        {
            "event_type": "run_end",
            "run_id": run_id,
            "status": final_status,
            "ended_at": now,
            "total_cost_usd": _decimal_to_str(total_cost_usd),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
    ]
    _post("/ingest/v1/batch", {"events": events})
    return {"accepted": len(events), "run_id": run_id}


@mcp.tool(name="runledger.query_runs")
def runledger_query_runs(
    limit: int = 20,
    status: str | None = None,
    feature_tag: str | None = None,
    end_user_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Query recent runs for this workspace."""
    params: dict[str, Any] = {"limit": min(limit, 100)}
    if status:
        params["status"] = status
    if feature_tag:
        params["feature_tag"] = feature_tag
    if end_user_id:
        params["end_user_id"] = end_user_id
    if model:
        params["model"] = model
    return _get("/runs", params)


@mcp.tool(name="runledger.query_costs")
def runledger_query_costs(
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Query spend, token, model, and feature-tag cost breakdowns."""
    params: dict[str, Any] = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return {
        "summary": _get("/analytics/summary", params),
        "by_model": _get("/analytics/spend-by-model", params),
        "by_feature": _get("/analytics/spend-by-feature", params),
    }


@mcp.tool(name="runledger.query_optimizations")
def runledger_query_optimizations(
    status: str = "pending",
    limit: int = 20,
) -> dict[str, Any]:
    """Query cost-quality optimization recommendations and recent cost regressions."""
    data: dict[str, Any] = {}
    try:
        data["flywheel_settings"] = _get("/gateway/flywheel/settings")
        data["recommendations"] = _get(
            "/gateway/flywheel/recommendations",
            {"status": status, "limit": min(limit, 100)},
        )
    except Exception as exc:
        data["recommendations_error"] = str(exc)
    try:
        data["cost_regressions"] = _get("/analytics/regressions")
    except Exception as exc:
        data["regressions_error"] = str(exc)
    return data


@mcp.tool(name="runledger.filter_mcp_tool")
def runledger_filter_mcp_tool(
    tool_name: str,
    end_user_id: str | None = None,
    feature_tag: str | None = None,
    model_alias: str | None = None,
) -> dict[str, Any]:
    """Check whether an agent may invoke a downstream MCP/tool by workspace policy."""
    return runledger_policy_check(  # type: ignore[no-any-return]
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        tool_name=tool_name,
        model_alias=model_alias,
    )


# ---------------------------------------------------------------------------
# Backward-compatible aliases from the original MCP server
# ---------------------------------------------------------------------------


@mcp.tool()
def list_runs(
    limit: int = 20,
    status: str | None = None,
    feature_tag: str | None = None,
    end_user_id: str | None = None,
) -> dict[str, Any]:
    """List recent agent runs. Prefer runledger.query_runs for new clients."""
    return runledger_query_runs(  # type: ignore[no-any-return]
        limit=limit,
        status=status,
        feature_tag=feature_tag,
        end_user_id=end_user_id,
    )


@mcp.tool()
def get_run(run_id: str) -> dict[str, Any]:
    """Get full details of a single agent run."""
    return _get(f"/runs/{run_id}")


@mcp.tool()
def get_analytics_summary(
    from_date: str | None = None, to_date: str | None = None
) -> dict[str, Any]:
    """Get analytics summary. Prefer runledger.query_costs for new clients."""
    params: dict[str, Any] = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return _get("/analytics/summary", params)


@mcp.tool()
def get_spend_by_model(from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
    """Get cost breakdown by model."""
    params: dict[str, Any] = {}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    return _get("/analytics/spend-by-model", params)


@mcp.tool()
def list_budgets() -> dict[str, Any]:
    """List workspace budgets."""
    return _get("/budgets")


@mcp.tool()
def check_budget(end_user_id: str | None = None, feature_tag: str | None = None) -> dict[str, Any]:
    """Check workspace budgets. Prefer runledger.budget_check for new clients."""
    return runledger_budget_check(end_user_id=end_user_id, feature_tag=feature_tag)  # type: ignore[no-any-return]


@mcp.tool()
def list_alert_rules() -> dict[str, Any]:
    """List alert rules."""
    return _get("/alerts/rules")


@mcp.tool()
def get_alert_history(limit: int = 20) -> dict[str, Any]:
    """Get recent alert firings."""
    return _get("/alerts/history", {"limit": min(limit, 100)})


@mcp.tool()
def list_prompts() -> dict[str, Any]:
    """List registered prompts."""
    return _get("/prompts")


@mcp.tool()
def get_prompt(name: str, environment: str = "production") -> dict[str, Any]:
    """Get the latest prompt version."""
    return _get(f"/prompts/{name}/latest", {"environment": environment})


@mcp.tool()
def get_cost_regressions() -> dict[str, Any]:
    """Detect workflows whose cost per run regressed."""
    return _get("/analytics/regressions")


@mcp.tool()
def get_sessions(limit: int = 20) -> dict[str, Any]:
    """List recent multi-turn sessions."""
    return _get("/sessions", {"limit": min(limit, 100)})


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("runledger://orgs/{org_id}/summary")
def org_summary(org_id: str) -> str:
    """Current org summary. API-key scope controls which data is returned."""
    try:
        data = _get("/analytics/summary")
        return (
            f"RunLedger organization summary for {org_id}\n"
            f"Spend: ${float(data.get('total_cost_usd', 0)):.4f}\n"
            f"Runs: {data.get('run_count', 0)}\n"
            f"Input tokens: {data.get('total_input_tokens', 0):,}\n"
            f"Output tokens: {data.get('total_output_tokens', 0):,}"
        )
    except Exception as exc:
        return f"Unable to fetch organization summary: {exc}"


@mcp.resource("runledger://workspaces/{workspace_id}/budget")
def workspace_budget(workspace_id: str) -> str:
    """Workspace budget state."""
    try:
        return str(_get("/budgets"))
    except Exception as exc:
        return f"Unable to fetch budget for {workspace_id}: {exc}"


@mcp.resource("runledger://workspaces/{workspace_id}/routes")
def workspace_routes(workspace_id: str) -> str:
    """Workspace routing availability from policy checks."""
    return (
        f"Route details for {workspace_id} are available through "
        "runledger.recommend_route and gateway configuration in RunLedger."
    )


@mcp.resource("runledger://workspaces/{workspace_id}/provider-profiles")
def workspace_provider_profiles(workspace_id: str) -> str:
    """Workspace provider pricing/profile guidance."""
    try:
        return str(_get("/providers/pricing"))
    except Exception as exc:
        return f"Unable to fetch provider profiles for {workspace_id}: {exc}"


@mcp.resource("runledger://workspaces/{workspace_id}/recent-runs")
def workspace_recent_runs(workspace_id: str) -> str:
    """Recent runs for a workspace."""
    try:
        return str(runledger_query_runs(limit=20))
    except Exception as exc:
        return f"Unable to fetch recent runs for {workspace_id}: {exc}"


@mcp.resource("runledger://workspaces/{workspace_id}/optimization-recommendations")
def workspace_optimization_recommendations(workspace_id: str) -> str:
    """Optimization recommendations for a workspace."""
    return str(runledger_query_optimizations(limit=20))


@mcp.resource("runledger://runs/{run_id}/trace")
def run_trace(run_id: str) -> str:
    """Run trace graph and detail for request exploration."""
    try:
        return str({"detail": _get(f"/runs/{run_id}"), "graph": _get(f"/runs/{run_id}/graph")})
    except Exception as exc:
        return f"Unable to fetch run trace {run_id}: {exc}"


@mcp.resource("runledger://policies/{workspace_id}/tool-policy")
def workspace_tool_policy(workspace_id: str) -> str:
    """Tool registry policy for a workspace."""
    try:
        return str(_get("/tools/registry"))
    except Exception as exc:
        return f"Unable to fetch tool policy for {workspace_id}: {exc}"


@mcp.resource("runledger://docs/agent-instructions")
def agent_instructions() -> str:
    """Default instructions agents should follow when connected to RunLedger."""
    return (
        "Before expensive or risky work, call runledger.budget_check and "
        "runledger.policy_check. Start each task with runledger.record_run_start. "
        "Record model calls, tool calls, and spans as work happens. Finish with "
        "runledger.record_outcome so RunLedger can track cost, quality, routing, "
        "business impact, and savings."
    )


@mcp.resource("runledger://workspace/stats")
def workspace_stats() -> str:
    """Backward-compatible workspace KPI snapshot."""
    return org_summary("current")  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt(name="runledger_start_agent_task")
def runledger_start_agent_task(task: str, intent: str = "agent_task") -> str:
    return (
        f"Start a RunLedger run for this task: {task}. "
        f"Use intent '{intent}', then record spans, model calls, tool calls, and outcome."
    )


@mcp.prompt(name="runledger_choose_model_route")
def runledger_choose_model_route(model_alias: str, task: str) -> str:
    return (
        f"Before calling model alias '{model_alias}' for '{task}', run "
        "runledger.recommend_route and follow any block or downgrade decision."
    )


@mcp.prompt(name="runledger_record_task_outcome")
def runledger_record_task_outcome(run_id: str, result: str) -> str:
    return (
        f"Record the final outcome for RunLedger run {run_id}. "
        f"Summarize business result '{result}', include quality labels, and close the run."
    )


@mcp.prompt(name="runledger_optimize_prompt")
def runledger_optimize_prompt(prompt_name: str) -> str:
    return (
        f"Analyze RunLedger costs, outcomes, and prompt history for '{prompt_name}'. "
        "Recommend lower-cost routes, caching, compression, or prompt changes."
    )


@mcp.prompt(name="runledger_debug_expensive_request")
def runledger_debug_expensive_request(run_id: str) -> str:
    return (
        f"Use runledger://runs/{run_id}/trace and runledger.query_costs to explain "
        "why this request was expensive and what should be optimized next."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
