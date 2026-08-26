"""Canonical published MCP tool list for RunLedger-connected agent skills."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunLedgerMcpTool:
    name: str
    purpose: str


RUNLEDGER_PUBLISHED_SKILL_TOOLS: tuple[RunLedgerMcpTool, ...] = (
    RunLedgerMcpTool(
        "runledger.budget_check",
        "Check whether work is inside workspace budget limits.",
    ),
    RunLedgerMcpTool(
        "runledger.policy_check",
        "Evaluate policy before risky, expensive, or sensitive actions.",
    ),
    RunLedgerMcpTool(
        "runledger.record_outcome", "Record the final task outcome and close the loop."
    ),
    RunLedgerMcpTool(
        "runledger.query_runs",
        "Look up recent runs for debugging or similar-task context.",
    ),
    RunLedgerMcpTool(
        "runledger.query_costs", "Inspect cost, token, and savings trends."
    ),
    RunLedgerMcpTool(
        "runledger.recommend_route",
        "Choose a model route with cost, latency, and policy awareness.",
    ),
    RunLedgerMcpTool(
        "runledger.filter_mcp_tool", "Approve or deny downstream MCP tool usage."
    ),
)


def published_skill_tool_names() -> list[str]:
    return [tool.name for tool in RUNLEDGER_PUBLISHED_SKILL_TOOLS]


def published_skill_tool_markdown() -> str:
    lines = ["# RunLedger MCP Tools", ""]
    for tool in RUNLEDGER_PUBLISHED_SKILL_TOOLS:
        lines.append(f"- `{tool.name}`: {tool.purpose}")
    return "\n".join(lines) + "\n"
