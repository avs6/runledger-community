"""Canonical demo scenario shared by scripts, labs, and runbooks."""

from __future__ import annotations

from typing import Iterable

PLATFORM_ADMIN = {
    "email": "admin@runledger.local",
    "password": "runledger",
    "full_name": "RunLedger Platform Admin",
}

DEMO_PASSWORD = "runledger"

ORGS = [
    {
        "name": "HomeLab",
        "slug": "homelab",
        "plan": "starter",
        "users": [
            ("admin@homelab.com", "HomeLab Admin", "org_admin"),
            ("user1@homelab.com", "HomeLab User 1", "org_member"),
            ("user2@homelab.com", "HomeLab User 2", "org_member"),
        ],
        "workspaces": ["AgentTest"],
    },
    {
        "name": "LocalAIAgentStack",
        "slug": "local-ai-agent-stack",
        "plan": "enterprise",
        "users": [
            ("admin@localstack.com", "Local Stack Admin", "org_admin"),
            ("user1@localstack.com", "Local Stack User 1", "org_member"),
            ("user2@localstack.com", "Local Stack User 2", "org_member"),
        ],
        "workspaces": [
            "LiteLLM Gateway",
            "OpenWebUI",
            "Codex",
            "Langgraph",
            "HermesAgent",
            "Claude Desktop",
            "OpenAICodes",
            "PythonAgents",
        ],
    },
]

LAB_WORKSPACE_MAP = {
    "inline_sdk": ("HomeLab", "AgentTest"),
    "budget_enforcement": ("HomeLab", "AgentTest"),
    "outcomes_scores": ("HomeLab", "AgentTest"),
    "otlp": ("LocalAIAgentStack", "Langgraph"),
    "gateway": ("LocalAIAgentStack", "LiteLLM Gateway"),
    "mcp": ("LocalAIAgentStack", "LiteLLM Gateway"),
}


def workspace_full_name(org_name: str, workspace_name: str) -> str:
    return f"{org_name} - {workspace_name}"


def quick_seed_marker() -> str:
    return workspace_full_name("HomeLab", "AgentTest")


def iter_demo_users() -> Iterable[tuple[str, str, str]]:
    for org in ORGS:
        for user in org["users"]:
            yield user


def scenario_lines() -> list[str]:
    lines = [
        f"Platform admin: {PLATFORM_ADMIN['email']} / {PLATFORM_ADMIN['password']}",
        "",
        "Organizations:",
    ]
    for org in ORGS:
        lines.append(f"- {org['name']}")
        lines.append(f"  Admin: {org['users'][0][0]}")
        lines.append("  Users: " + ", ".join(user[0] for user in org["users"][1:]))
        lines.append("  Workspaces: " + ", ".join(org["workspaces"]))
    return lines
