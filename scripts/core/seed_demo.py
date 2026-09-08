#!/usr/bin/env python3
"""Canonical REST-only demo seed for the local foundation scenario."""

from __future__ import annotations

import asyncio
import json
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from demo_scenario import DEMO_PASSWORD, ORGS, PLATFORM_ADMIN, quick_seed_marker

BASE_URL = "http://localhost:8201"
OLLAMA_BASE_URL = "http://host.docker.internal:11434/v1"
OLLAMA_MODEL = "llama3.2"
NOW = datetime.now(UTC)
random.seed(42)


class Client:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "Client":
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http:
            await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get(self, path: str, *, params: dict | None = None) -> dict | list:
        assert self._http is not None
        response = await self._http.get(path, headers=self._headers(), params=params)
        try:
            return response.json()
        except Exception:
            return {}

    async def post(self, path: str, *, json_body: dict | None = None) -> dict:
        assert self._http is not None
        response = await self._http.post(
            path,
            headers={**self._headers(), "Content-Type": "application/json"},
            content=json.dumps(json_body or {}),
        )
        try:
            return response.json()
        except Exception:
            return {}


@dataclass
class WorkspaceContext:
    org_name: str
    workspace_name: str
    workspace_id: str
    api_key: str

    @property
    def full_name(self) -> str:
        return f"{self.org_name} - {self.workspace_name}"


def _ts(days_back: int) -> tuple[str, str]:
    started_at = NOW - timedelta(
        days=days_back,
        hours=random.randint(0, 6),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    ended_at = started_at + timedelta(seconds=random.randint(2, 20))
    return started_at.isoformat(), ended_at.isoformat()


async def _healthcheck(client: Client) -> None:
    ready = await client.get("/health/ready")
    status = ready.get("status") if isinstance(ready, dict) else None
    if status != "ok":
        raise RuntimeError(f"API is not ready: {ready}")


async def _platform_login(client: Client) -> str:
    login = await client.post(
        "/auth/login",
        json_body={
            "email": PLATFORM_ADMIN["email"],
            "password": PLATFORM_ADMIN["password"],
        },
    )
    token = login.get("api_key")
    if not token:
        raise RuntimeError(f"Platform login failed: {login}")
    return token


async def _workspace_names(admin: Client) -> set[str]:
    response = await admin.get("/org/workspaces")
    items = response.get("items", response) if isinstance(response, dict) else response
    return {item.get("name", "") for item in items if isinstance(item, dict)}


async def _invite_users(admin: Client) -> None:
    for org in ORGS:
        for email, full_name, role in org["users"]:
            await admin.post(
                "/org/members/invite",
                json_body={
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                    "password": DEMO_PASSWORD,
                },
            )


async def _create_workspace(admin: Client, org_name: str, workspace_name: str) -> WorkspaceContext:
    full_name = f"{org_name} - {workspace_name}"
    created = await admin.post("/org/workspaces", json_body={"name": full_name})
    workspace_id = created.get("id")
    if not workspace_id:
        existing = await admin.get("/org/workspaces")
        items = existing.get("items", existing) if isinstance(existing, dict) else existing
        match = next(
            (
                item
                for item in items
                if isinstance(item, dict) and item.get("name") == full_name
            ),
            None,
        )
        if not match:
            raise RuntimeError(f"Could not create workspace {full_name}")
        workspace_id = match.get("id", "")
    switched = await admin.post(
        "/auth/switch-workspace",
        json_body={"workspace_id": workspace_id},
    )
    api_key = switched.get("api_key")
    if not api_key:
        raise RuntimeError(f"No API key returned for workspace {full_name}")
    return WorkspaceContext(org_name, workspace_name, workspace_id, api_key)


async def _seed_tool_registry(client: Client) -> None:
    for tool_name, description, policy, enforcement in [
        ("search_docs", "Read product and setup docs", "allow", False),
        ("lookup_logs", "Read request and audit data", "audit", False),
        ("refund_customer", "Refund a billed customer", "block", True),
    ]:
        await client.post(
            "/tools/registry",
            json_body={
                "tool_name": tool_name,
                "description": description,
                "policy": policy,
                "runtime_enforcement": enforcement,
            },
        )


async def _seed_routes(client: Client, workspace_name: str) -> None:
    alias = "qa-chat" if workspace_name == "LiteLLM Gateway" else f"{workspace_name.lower().replace(' ', '-')}-chat"
    await client.post(
        "/gateway/routes",
        json_body={
            "alias": alias,
            "provider": "ollama",
            "target_model": OLLAMA_MODEL,
            "base_url": OLLAMA_BASE_URL,
            "priority": 1,
            "semantic_cache_enabled": workspace_name == "LiteLLM Gateway",
            "health_auto_disable": True,
        },
    )


async def _seed_budget(client: Client, workspace_name: str) -> None:
    action = "block" if workspace_name == "AgentTest" else "notify"
    limit = 0.05 if workspace_name == "AgentTest" else 15.0
    await client.post(
        "/budgets",
        json_body={
            "scope_type": "workspace",
            "scope_id": None,
            "period_type": "daily",
            "limit_usd": limit,
            "action": action,
            "is_active": True,
        },
    )


async def _seed_prompts(client: Client, workspace_name: str) -> None:
    prompt_name = f"{workspace_name.lower().replace(' ', '-')}-assistant"
    await client.post(
        "/prompts",
        json_body={
            "name": prompt_name,
            "description": f"Default prompt for {workspace_name}",
            "default_environment": "production",
        },
    )
    await client.post(
        f"/prompts/{prompt_name}/versions",
        json_body={
            "content": "You are a helpful local demo assistant for {{workspace}}.",
            "variables": ["workspace"],
            "commit_message": "Initial seeded version",
        },
    )


async def _seed_runs(client: Client, feature_tag: str) -> list[str]:
    run_ids: list[str] = []
    for day in range(6):
        for _ in range(3):
            run_id = str(uuid.uuid4())
            span_id = str(uuid.uuid4())
            started_at, ended_at = _ts(day)
            prompt_tokens = random.randint(120, 480)
            completion_tokens = random.randint(60, 220)
            total_cost = round((prompt_tokens + completion_tokens) * 0.000002, 6)
            events = [
                {
                    "event_type": "run_start",
                    "run_id": run_id,
                    "end_user_id": f"user_{random.randint(1, 6):02d}",
                    "session_id": f"sess_{uuid.uuid4().hex[:10]}",
                    "feature_tag": feature_tag,
                    "deployment_version": "v1.0.0",
                    "started_at": started_at,
                    "metadata": {"seed": "canonical_demo"},
                    "intent": random.choice(["support", "routing", "analysis"]),
                },
                {
                    "event_type": "span_start",
                    "span_id": span_id,
                    "run_id": run_id,
                    "span_type": "llm",
                    "name": "ollama.chat",
                    "started_at": started_at,
                },
                {
                    "event_type": "provider_call",
                    "run_id": run_id,
                    "span_id": span_id,
                    "provider": "ollama",
                    "model": OLLAMA_MODEL,
                    "input_tokens": prompt_tokens,
                    "output_tokens": completion_tokens,
                    "latency_ms": random.randint(800, 2800),
                    "cost_usd": total_cost,
                    "status": "success",
                },
                {
                    "event_type": "span_end",
                    "span_id": span_id,
                    "run_id": run_id,
                    "status": "succeeded",
                    "ended_at": ended_at,
                    "cost_usd": total_cost,
                },
                {
                    "event_type": "run_end",
                    "run_id": run_id,
                    "status": "succeeded",
                    "ended_at": ended_at,
                    "total_cost_usd": total_cost,
                    "total_input_tokens": prompt_tokens,
                    "total_output_tokens": completion_tokens,
                },
            ]
            await client.post("/ingest/v1/batch", json_body={"events": events})
            run_ids.append(run_id)
    return run_ids


async def _seed_scores_and_outcomes(client: Client, run_ids: list[str], outcome_type: str) -> None:
    for run_id in run_ids[:8]:
        score = round(random.uniform(0.72, 0.98), 3)
        await client.post(
            "/evaluations/scores",
            json_body={
                "run_id": run_id,
                "name": "resolution_quality",
                "value": score,
                "label": "good" if score >= 0.8 else "needs_review",
                "source": "seed",
            },
        )
        await client.post(
            "/outcomes",
            json_body={
                "run_id": run_id,
                "outcome_type": outcome_type,
                "success": score >= 0.8,
                "value_usd": round(random.uniform(6, 18), 2),
            },
        )


async def _seed_workspace(context: WorkspaceContext) -> None:
    async with Client(BASE_URL, context.api_key) as workspace_client:
        await _seed_tool_registry(workspace_client)
        await _seed_routes(workspace_client, context.workspace_name)
        await _seed_budget(workspace_client, context.workspace_name)
        await _seed_prompts(workspace_client, context.workspace_name)

        feature_tag = {
            "AgentTest": "support-chat",
            "Langgraph": "langgraph-agent",
            "LiteLLM Gateway": "gateway-routing",
        }.get(context.workspace_name, context.workspace_name.lower().replace(" ", "-"))
        run_ids = await _seed_runs(workspace_client, feature_tag)

        if context.workspace_name == "AgentTest":
            await _seed_scores_and_outcomes(workspace_client, run_ids, "ticket_resolved")


async def main() -> None:
    print("RunLedger canonical demo seed")
    print("=" * 40)
    print(f"Target API: {BASE_URL}")
    print(f"Platform admin: {PLATFORM_ADMIN['email']} / {PLATFORM_ADMIN['password']}")
    print("")

    async with Client(BASE_URL) as root:
        await _healthcheck(root)
        platform_key = await _platform_login(root)

    async with Client(BASE_URL, platform_key) as admin:
        existing_names = await _workspace_names(admin)
        if quick_seed_marker() in existing_names:
            print(f"Demo data already exists ({quick_seed_marker()}).")
            print("Run cleanup or remove demo workspaces before reseeding.")
            return

        await _invite_users(admin)

        contexts: list[WorkspaceContext] = []
        for org in ORGS:
            for workspace_name in org["workspaces"]:
                context = await _create_workspace(admin, org["name"], workspace_name)
                contexts.append(context)

        for context in contexts:
            print(f"Seeding {context.full_name}")
            await _seed_workspace(context)

    print("")
    print("Seed complete.")
    print("")
    print(f"Platform admin: {PLATFORM_ADMIN['email']} / {PLATFORM_ADMIN['password']}")
    print(f"Demo users: all use password {DEMO_PASSWORD}")
    for org in ORGS:
        print(f"- {org['name']}")
        print(f"  Admin: {org['users'][0][0]}")
        print("  Users: " + ", ".join(user[0] for user in org["users"][1:]))
        print("  Workspaces: " + ", ".join(org["workspaces"]))
    print("")
    print("Dashboard: http://localhost:3201")
    print("API docs: http://localhost:8201/reference")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
