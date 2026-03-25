"""
RunLedger — full-surface HTTP API demo seed script.

Uses only the REST API (no direct DB writes) so every feature is exercised
through real business logic: rate limits, audit logs, feature gates, workers.

Covers every product tab / feature area:
  Orgs / Users / Workspaces → Runs / Spans / Provider Calls (ingest) →
  Analytics → Evaluations & Scores → Evaluators → Prompts & Versions →
  Prompt Promote + Approvals → Model Gateway Routes + Policies + Traffic →
  Tool Registry → Budgets + Breaches → Billing Periods + Chargeback +
  Cost Centres + Shared Cost Policies → Invoice Reconciliation →
  Outcomes & ROI → Alert Rules + Firings → Retention Policies →
  Pricing Contracts + Credits → Audit Logs → Ledger Snapshots

Usage:
    cd apps/api && uv run python scripts/seed_demo.py

Requires the stack to be running at http://localhost:8000.
Idempotent guard: skips if demo orgs already exist.
"""

from __future__ import annotations

import asyncio
import csv
import io
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

import httpx

# Small pause between request groups to stay under rate limits
_THROTTLE = 0.25  # seconds

# ── Config ────────────────────────────────────────────────────────────────────

import os  # noqa: E402

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@runledger.local")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "runledger")
DEMO_PASSWORD = "demo1234"

# Set SEED_EXTERNAL=true to also seed Kafka export configs and attempt live
# gateway completions (requires real provider API keys in the gateway routes).
# Default false so the seed works on any machine with no external credentials.
SEED_EXTERNAL = os.getenv("SEED_EXTERNAL", "false").lower() == "true"

# Provider API keys — used only for live gateway traffic simulation.
# If unset the gateway traffic section is skipped silently.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

random.seed(42)
NOW = datetime.now(UTC)
TODAY = NOW.date()

# ── Helpers ───────────────────────────────────────────────────────────────────

PROVIDER_MODELS = [
    ("openai", "gpt-4o", 2.50, 10.00),
    ("openai", "gpt-4o-mini", 0.15, 0.60),
    ("anthropic", "claude-sonnet-4-6", 3.00, 15.00),
    ("anthropic", "claude-haiku-4-5", 0.80, 4.00),
    ("google", "gemini-2.0-flash", 0.075, 0.30),
]

FEATURE_TAGS = [
    "customer-support",
    "code-review",
    "document-analysis",
    "data-extraction",
    "summarization",
    "classification",
    "email-drafting",
    "report-generation",
]

TOOL_DEFS = [
    ("web_search", "Search the web for current information", "audit", False),
    ("database_query", "Query internal analytics databases", "audit", False),
    ("send_email", "Send transactional emails via SMTP", "audit", True),
    ("file_reader", "Read files from object storage", "audit", False),
    ("code_executor", "Execute sandboxed code snippets", "block", True),
    ("slack_poster", "Post messages to Slack channels", "audit", True),
    ("calendar_lookup", "Read calendar availability", "audit", False),
    ("payment_processor", "Initiate payment transactions", "block", True),
    ("crm_updater", "Update CRM contact and opportunity records", "audit", True),
    ("pdf_parser", "Extract structured text from PDF documents", "audit", False),
]

PROMPT_DEFS = [
    (
        "customer-support-agent",
        "Handles inbound customer questions for {{company_name}}",
        "You are a helpful customer support agent for {{company_name}}.\n"
        "Answer the customer's question concisely:\n\n{{question}}",
        ["company_name", "question"],
    ),
    (
        "code-reviewer",
        "Reviews {{language}} code for bugs and best practices",
        "Review the following {{language}} code:\n\n```{{language}}\n{{code}}\n```\n\n"
        "Provide structured feedback on bugs, performance, and style.",
        ["language", "code"],
    ),
    (
        "document-summarizer",
        "Summarises documents into {{format}} format",
        "Summarise the following document in {{format}} format, focusing on {{focus_area}}:\n\n{{document}}",
        ["format", "focus_area", "document"],
    ),
    (
        "data-extractor",
        "Extracts {{entity_type}} entities as JSON",
        "Extract all {{entity_type}} entities from the text below and return as JSON:\n\n{{text}}",
        ["entity_type", "text"],
    ),
    (
        "email-drafter",
        "Drafts professional emails with the right {{tone}}",
        "Draft a professional {{tone}} email to {{recipient}} about {{subject}}.\n"
        "Key points to cover: {{key_points}}",
        ["tone", "recipient", "subject", "key_points"],
    ),
    (
        "report-generator",
        "Generates {{report_type}} reports for {{time_period}}",
        "Generate a {{report_type}} report for {{time_period}} covering: {{topics}}.\n"
        "Output format: {{output_format}}",
        ["report_type", "time_period", "topics", "output_format"],
    ),
]

END_USERS = [f"user_{i:03d}" for i in range(1, 16)]


def ts(days_back: int, hour_jitter: bool = True) -> str:
    """ISO timestamp N days ago."""
    dt = NOW - timedelta(
        days=days_back,
        hours=random.randint(0, 4) if hour_jitter else 0,
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return dt.isoformat()


def run_cost(provider: str, model: str, in_tok: int, out_tok: int) -> float:
    for p, m, in_r, out_r in PROVIDER_MODELS:
        if p == provider and m == model:
            return round(in_tok / 1_000_000 * in_r + out_tok / 1_000_000 * out_r, 8)
    return 0.005


class Client:
    """Thin async HTTP wrapper with Bearer auth + error reporting."""

    def __init__(self, base: str, token: str | None = None) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Client:
        self._http = httpx.AsyncClient(base_url=self.base, timeout=30)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._http:
            await self._http.aclose()

    def _headers(self, extra: dict | None = None) -> dict:
        h: dict = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if extra:
            h.update(extra)
        return h

    async def post(
        self,
        path: str,
        *,
        json: dict | None = None,
        files: dict | None = None,
        params: dict | None = None,
        skip_errors: bool = False,
    ) -> dict:
        assert self._http
        if files:
            r = await self._http.post(path, headers=self._headers(), files=files, params=params)
        else:
            r = await self._http.post(
                path,
                headers=self._headers({"Content-Type": "application/json"}),
                content=__import__("json").dumps(json or {}),
                params=params,
            )
        if not skip_errors and r.status_code >= 400:
            print(f"    ⚠  POST {path} → {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except Exception:
            return {}

    async def get(
        self, path: str, *, params: dict | None = None, skip_errors: bool = False
    ) -> dict | list:
        assert self._http
        r = await self._http.get(path, headers=self._headers(), params=params)
        if not skip_errors and r.status_code >= 400:
            print(f"    ⚠  GET {path} → {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except Exception:
            return {}

    async def put(self, path: str, *, json: dict | None = None, skip_errors: bool = False) -> dict:
        assert self._http
        r = await self._http.put(
            path,
            headers=self._headers({"Content-Type": "application/json"}),
            content=__import__("json").dumps(json or {}),
        )
        if not skip_errors and r.status_code >= 400:
            print(f"    ⚠  PUT {path} → {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except Exception:
            return {}

    async def delete(self, path: str, skip_errors: bool = False) -> dict:
        assert self._http
        r = await self._http.delete(path, headers=self._headers())
        if not skip_errors and r.status_code >= 400:
            print(f"    ⚠  DELETE {path} → {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except Exception:
            return {}

    async def patch(self, path: str, *, json: dict | None = None) -> dict:
        assert self._http
        r = await self._http.patch(
            path,
            headers=self._headers({"Content-Type": "application/json"}),
            content=__import__("json").dumps(json or {}),
        )
        try:
            return r.json()
        except Exception:
            return {}


# ── Login helper ──────────────────────────────────────────────────────────────


async def login(client: Client, email: str, password: str) -> dict:
    return await client.post("/auth/login", json={"email": email, "password": password})


# ── Step 1: check health + idempotency ───────────────────────────────────────


async def check_health(client: Client) -> None:
    r = await client.get("/health/ready", skip_errors=True)
    status = r.get("status", "unknown") if isinstance(r, dict) else "unknown"
    if status != "ok":
        print(f"  API health: {r}")
    else:
        print("  API healthy ✓")


# ── Step 2: create orgs, users, workspaces via platform API ──────────────────

ORGS = [
    {
        "name": "Acme Corp",
        "slug": "acme-corp-demo",
        "plan": "enterprise",
        "users": [
            ("alice@acme-demo.com", "Alice Chen", "org_admin"),
            ("bob@acme-demo.com", "Bob Martinez", "org_manager"),
            ("carol@acme-demo.com", "Carol Singh", "org_member"),
            ("dave@acme-demo.com", "Dave Kim", "org_auditor"),
        ],
        "workspaces": ["Platform AI", "Customer Experience", "Data Science"],
    },
    {
        "name": "TechStart Inc",
        "slug": "techstart-demo",
        "plan": "growth",
        "users": [
            ("emma@techstart-demo.io", "Emma Wilson", "org_admin"),
            ("frank@techstart-demo.io", "Frank Liu", "org_manager"),
            ("grace@techstart-demo.io", "Grace Patel", "org_member"),
        ],
        "workspaces": ["Product", "R&D"],
    },
    {
        "name": "GlobalAI Systems",
        "slug": "globalai-demo",
        "plan": "enterprise",
        "users": [
            ("henry@globalai-demo.com", "Henry Brown", "org_admin"),
            ("iris@globalai-demo.com", "Iris Zhang", "org_manager"),
            ("jack@globalai-demo.com", "Jack Thompson", "org_billing_admin"),
        ],
        "workspaces": ["Enterprise AI", "ML Research"],
    },
]


async def create_orgs(admin: Client) -> list[dict]:
    """
    Create demo workspaces in the default tenant (platform admin approach).
    The platform admin can switch to any workspace, so we create all workspaces
    via /org/workspaces and switch into each one for seeding.
    Returns list of workspace contexts with scoped API keys.
    """
    contexts: list[dict] = []

    # Get the current admin user info and workspace list
    me = await admin.get("/users/me")
    admin_user_id = me.get("id", "")
    admin_users = [me] if admin_user_id else []

    # Create demo users in the default tenant (org-level)
    print("  Creating demo users...")
    demo_users = []
    for org in ORGS:
        for email, full_name, role in org["users"]:
            r = await admin.post(
                "/org/members/invite",
                json={
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                    "password": DEMO_PASSWORD,
                },
                skip_errors=True,
            )
            uid = r.get("id") or r.get("user_id")
            if uid:
                demo_users.append({"id": uid, "email": email, "full_name": full_name})

    print(f"  {len(demo_users)} demo users created/invited")

    # Create workspaces — one set per org definition
    print("  Creating demo workspaces...")
    for org in ORGS:
        print(f"\n  Org: {org['name']}")
        for ws_name in org["workspaces"]:
            full_name = f"{org['name']} — {ws_name}"
            ws_resp = await admin.post(
                "/org/workspaces", json={"name": full_name}, skip_errors=True
            )
            ws_id = ws_resp.get("id")
            if not ws_id:
                # Already exists — find it
                wss = await admin.get("/org/workspaces")
                ws_list = (wss.get("items", wss) if isinstance(wss, dict) else wss) or []
                match = next(
                    (w for w in ws_list if isinstance(w, dict) and w.get("name") == full_name), {}
                )
                ws_id = match.get("id")

            if not ws_id:
                print(f"    ⚠ Could not create workspace {full_name}")
                continue

            # Switch admin into this workspace to get a scoped API key
            switch = await admin.post(
                "/auth/switch-workspace", json={"workspace_id": ws_id}, skip_errors=True
            )
            ws_api_key = switch.get("api_key")
            if not ws_api_key:
                print(f"    ⚠ No API key for workspace {full_name}")
                continue

            contexts.append(
                {
                    "org_name": org["name"],
                    "ws_name": ws_name,
                    "ws_id": ws_id,
                    "api_key": ws_api_key,
                    "users": demo_users or admin_users,
                }
            )
            print(f"    └─ {full_name} ✓")

    return contexts


# ── Step 3: per-workspace seeding ─────────────────────────────────────────────


async def seed_workspace(ctx: dict) -> None:
    api_key = ctx["api_key"]
    org = ctx["org_name"]
    ws = ctx["ws_name"]
    users = ctx["users"]

    async with Client(BASE_URL, api_key) as c:
        print(f"\n  [{org} / {ws}]")

        # ── Tool Registry ──────────────────────────────────────────────────────
        print("    → Tool registry")
        for tool_name, desc, policy, enforcement in TOOL_DEFS:
            await c.post(
                "/tools/registry",
                json={
                    "tool_name": tool_name,
                    "description": desc,
                    "policy": policy,
                    "runtime_enforcement": enforcement,
                },
                skip_errors=True,
            )
        await asyncio.sleep(_THROTTLE)
        await c.get("/tools/registry", skip_errors=True)
        await c.get("/tools/security-events", skip_errors=True)

        # ── Gateway Routes ─────────────────────────────────────────────────────
        print("    → Gateway routes & policies")
        routes_created = []
        gateway_routes = [
            {
                "alias": "gpt4o-primary",
                "provider": "openai",
                "target_model": "gpt-4o",
                "priority": 10,
                "daily_cost_limit_usd": 500,
                "monthly_cost_limit_usd": 12000,
                "pii_redaction_enabled": True,
                "per_user_rpm_limit": 60,
                "health_auto_disable": True,
            },
            {
                "alias": "gpt4o-mini-budget",
                "provider": "openai",
                "target_model": "gpt-4o-mini",
                "priority": 20,
                "daily_cost_limit_usd": 150,
                "monthly_cost_limit_usd": 4000,
                "pii_redaction_enabled": False,
                "per_user_rpm_limit": 120,
                "health_auto_disable": True,
            },
            {
                "alias": "claude-sonnet",
                "provider": "anthropic",
                "target_model": "claude-sonnet-4-6",
                "priority": 15,
                "daily_cost_limit_usd": 300,
                "monthly_cost_limit_usd": 8000,
                "pii_redaction_enabled": True,
                "per_user_rpm_limit": 60,
                "health_auto_disable": True,
            },
            {
                "alias": "gemini-flash",
                "provider": "google",
                "target_model": "gemini-2.0-flash",
                "priority": 25,
                "daily_cost_limit_usd": 100,
                "monthly_cost_limit_usd": 2500,
                "pii_redaction_enabled": False,
                "per_user_rpm_limit": 200,
                "health_auto_disable": True,
            },
        ]
        # Map providers to their API key env var name and the actual key value
        # (so the gateway can forward live traffic when keys are present)
        _provider_key_env = {
            "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
            "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
            "google": ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "")),
        }
        for rd in gateway_routes:
            env_var, _key_val = _provider_key_env.get(rd["provider"], ("", ""))
            route_payload: dict = {**rd, "api_key_env_var": env_var}
            # Embed the actual key directly so the gateway can forward without
            # requiring the env var to be set inside the API container.
            if _key_val:
                route_payload["api_key"] = _key_val
            r = await c.post("/gateway/routes", json=route_payload, skip_errors=True)
            if "id" in r:
                routes_created.append(r)

        # Routing policies
        routing_policies = [
            {
                "alias": "cost-optimized",
                "policy_type": "cost_optimized",
                "config": {"max_latency_ms": 5000},
            },
            {
                "alias": "quality-first",
                "policy_type": "quality_optimized",
                "config": {"min_avg_score": 0.80},
            },
            {
                "alias": "budget-aware",
                "policy_type": "budget_aware",
                "config": {"daily_budget_usd": 200, "fallback_model": "gpt-4o-mini"},
            },
            {
                "alias": "canary-claude",
                "policy_type": "canary",
                "config": {"canary_weight": 0.1, "canary_alias": "claude-sonnet"},
            },
            {
                "alias": "weighted-blend",
                "policy_type": "weighted",
                "config": {"weights": {"gpt4o-primary": 0.6, "claude-sonnet": 0.4}},
            },
        ]
        for pd in routing_policies:
            await c.post("/gateway/policies", json=pd, skip_errors=True)

        await asyncio.sleep(_THROTTLE)
        await c.get("/gateway/routes", skip_errors=True)
        await c.get("/gateway/stats", skip_errors=True)

        # ── Runs via ingest batch API ──────────────────────────────────────────
        print("    → Ingesting agent runs (30 days of traffic)")
        run_ids: list[str] = []
        run_meta: list[dict] = []

        for day in range(30):
            daily_runs = random.randint(6, 20)
            for _ in range(daily_runs):
                provider, model, in_r, out_r = random.choice(PROVIDER_MODELS)
                in_tok = random.randint(300, 6000)
                out_tok = random.randint(100, 3000)
                cost = run_cost(provider, model, in_tok, out_tok)
                started = ts(day)
                started_dt = datetime.fromisoformat(started)
                duration_s = random.randint(2, 45)
                ended_dt = started_dt + timedelta(seconds=duration_s)
                ended = ended_dt.isoformat()
                status = random.choices(["succeeded", "failed", "cancelled"], weights=[85, 10, 5])[
                    0
                ]
                run_id = str(uuid.uuid4())
                span_id = str(uuid.uuid4())
                end_user = random.choice(END_USERS)
                feature = random.choice(FEATURE_TAGS)
                version = f"v{random.randint(1, 4)}.{random.randint(0, 9)}"
                tool_name, _, _, _ = random.choice(TOOL_DEFS)

                events = [
                    {
                        "event_type": "run_start",
                        "run_id": run_id,
                        "end_user_id": end_user,
                        "session_id": f"sess_{uuid.uuid4().hex[:10]}",
                        "feature_tag": feature,
                        "deployment_version": version,
                        "started_at": started,
                        "metadata": {"sdk": "runledger-sdk@2.1.0"},
                    },
                    {
                        "event_type": "span_start",
                        "span_id": span_id,
                        "run_id": run_id,
                        "span_type": "llm",
                        "name": f"{provider}.chat",
                        "started_at": started,
                    },
                    {
                        "event_type": "provider_call",
                        "run_id": run_id,
                        "span_id": span_id,
                        "provider": provider,
                        "model": model,
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "latency_ms": duration_s * 1000 - 100,
                        "cost_usd": cost,
                        "status": "success" if status == "succeeded" else "error",
                        "error_type": None if status == "succeeded" else "RateLimitError",
                    },
                ]

                # 50% chance of tool call
                if random.random() < 0.5:
                    events.append(
                        {
                            "event_type": "tool_call",
                            "run_id": run_id,
                            "span_id": span_id,
                            "tool_name": tool_name,
                            "tool_type": "read",
                            "risk_score": random.randint(1, 8),
                            "duration_ms": random.randint(50, 2000),
                            "status": "success",
                        }
                    )

                events += [
                    {
                        "event_type": "span_end",
                        "span_id": span_id,
                        "run_id": run_id,
                        "status": "succeeded" if status == "succeeded" else "failed",
                        "ended_at": ended,
                        "cost_usd": cost,
                    },
                    {
                        "event_type": "run_end",
                        "run_id": run_id,
                        "status": status,
                        "ended_at": ended,
                        "total_cost_usd": cost,
                        "total_input_tokens": in_tok,
                        "total_output_tokens": out_tok,
                    },
                ]

                await c.post("/ingest/v1/batch", json={"events": events}, skip_errors=True)
                run_ids.append(run_id)
                run_meta.append(
                    {
                        "run_id": run_id,
                        "end_user": end_user,
                        "feature": feature,
                        "provider": provider,
                        "model": model,
                        "cost": cost,
                        "status": status,
                        "day": day,
                    }
                )

        # Give workers a moment for the first batch to process
        await asyncio.sleep(2)

        # ── Evaluation Scores ──────────────────────────────────────────────────
        print("    → Evaluation scores & evaluators")
        score_names = ["helpfulness", "accuracy", "coherence", "safety", "task_completion"]

        for meta in random.sample(run_meta, min(len(run_meta), 40)):
            if meta["status"] != "succeeded":
                continue
            name = random.choice(score_names)
            val = round(random.uniform(0.55, 1.0), 3)
            await c.post(
                "/evaluations/scores",
                json={
                    "run_id": meta["run_id"],
                    "name": name,
                    "value": val,
                    "label": "good" if val > 0.75 else "needs_improvement",
                    "source": random.choice(["human", "llm_judge", "automated"]),
                    "confidence": round(random.uniform(0.7, 1.0), 3),
                    "evidence": {"method": "llm-as-judge", "model": "gpt-4o"},
                },
                skip_errors=True,
            )

        # Evaluators
        evaluators = [
            {
                "name": "helpfulness-judge",
                "description": "LLM judge scoring response helpfulness 0–1",
                "evaluator_type": "llm_judge",
                "config": {
                    "model": "gpt-4o",
                    "score_name": "helpfulness",
                    "prompt": "Rate this response 0-1 for helpfulness.",
                },
            },
            {
                "name": "safety-classifier",
                "description": "Classifies responses for safety violations",
                "evaluator_type": "llm_judge",
                "config": {
                    "model": "gpt-4o-mini",
                    "score_name": "safety",
                    "prompt": "Is this response safe? Return 0 (unsafe) or 1 (safe).",
                },
            },
            {
                "name": "accuracy-scorer",
                "description": "Scores factual accuracy against a reference answer",
                "evaluator_type": "llm_judge",
                "config": {
                    "model": "gpt-4o",
                    "score_name": "accuracy",
                    "prompt": "Compare the response to the reference. Score 0-1 for accuracy.",
                },
            },
        ]
        eval_ids = []
        for ev in evaluators:
            r = await c.post("/evaluations/evaluators", json=ev, skip_errors=True)
            if "id" in r:
                eval_ids.append(r["id"])

        await asyncio.sleep(_THROTTLE)
        await c.get("/evaluations/scores", skip_errors=True)
        await c.get("/evaluations/evaluators", skip_errors=True)

        # ── Prompts & Versions ────────────────────────────────────────────────
        print("    → Prompts & versions")
        prompt_names: list[str] = []
        for name, desc, content, variables in PROMPT_DEFS:
            r = await c.post(
                "/prompts",
                json={
                    "name": name,
                    "description": desc,
                    "default_environment": "production",
                },
                skip_errors=True,
            )
            if "name" not in r:
                # Might already exist — get it
                existing = await c.get(f"/prompts/{name}", skip_errors=True)
                if "name" not in (existing if isinstance(existing, dict) else {}):
                    continue

            # Add 3 versions
            for v in range(1, 4):
                suffix = (
                    ""
                    if v == 1
                    else " [optimised for token efficiency]"
                    if v == 2
                    else " [concise variant]"
                )
                await c.post(
                    f"/prompts/{name}/versions",
                    json={
                        "content": content + suffix,
                        "variables": variables,
                        "commit_message": (
                            "Initial version"
                            if v == 1
                            else "Reduced token count by 30%"
                            if v == 2
                            else "Improved clarity"
                        ),
                        "environment": "production" if v == 3 else "staging",
                        "model_hint": "gpt-4o" if v < 3 else "gpt-4o-mini",
                    },
                    skip_errors=True,
                )

            prompt_names.append(name)
            await c.get(f"/prompts/{name}/latest", skip_errors=True)
            await c.get(f"/prompts/{name}/metrics", skip_errors=True)

        await c.get("/prompts", skip_errors=True)

        # ── Eval Datasets ─────────────────────────────────────────────────────
        print("    → Eval datasets")
        dataset_items_customer_qa = [
            {
                "input": "What is your refund policy?",
                "expected_output": "We offer 30-day refunds.",
                "metadata": {},
            },
            {
                "input": "How do I reset my password?",
                "expected_output": "Click 'Forgot password'.",
                "metadata": {},
            },
            {
                "input": "Can I upgrade my plan mid-month?",
                "expected_output": "Yes, prorated billing.",
                "metadata": {},
            },
            {
                "input": "Do you support bulk exports?",
                "expected_output": "Yes, via the API.",
                "metadata": {},
            },
            {
                "input": "What models does RunLedger support?",
                "expected_output": "OpenAI, Anthropic, Google, Mistral.",
                "metadata": {},
            },
            {
                "input": "How is cost calculated?",
                "expected_output": "Per 1M tokens × rate.",
                "metadata": {},
            },
            {
                "input": "Is there a free tier?",
                "expected_output": "Yes, 100k tokens/month.",
                "metadata": {},
            },
            {
                "input": "How do I set a spending budget?",
                "expected_output": "Under Budgets in the dashboard.",
                "metadata": {},
            },
        ]
        dataset_items_code_review = [
            {
                "input": "Review: def add(a,b): return a+b",
                "expected_output": "Looks correct.",
                "metadata": {},
            },
            {
                "input": "Review: for i in range(len(lst)):",
                "expected_output": "Use enumerate() instead.",
                "metadata": {},
            },
            {
                "input": "Review: x = None; print(x.upper())",
                "expected_output": "NoneType error risk.",
                "metadata": {},
            },
            {
                "input": "Review: SELECT * FROM users",
                "expected_output": "Specify columns, not *.",
                "metadata": {},
            },
            {
                "input": "Review: import *",
                "expected_output": "Avoid wildcard imports.",
                "metadata": {},
            },
        ]
        datasets_created = []
        for ds_name, ds_desc, ds_items in [
            (
                "Customer Support Q&A",
                "Common customer support questions with expected answers",
                dataset_items_customer_qa,
            ),
            (
                "Code Review Samples",
                "Code snippets for automated review evaluation",
                dataset_items_code_review,
            ),
        ]:
            r = await c.post(
                "/datasets",
                json={
                    "name": ds_name,
                    "description": ds_desc,
                    "source": "manual",
                    "items": ds_items,
                },
                skip_errors=True,
            )
            if "id" in r:
                datasets_created.append(r)
        await c.get("/datasets", skip_errors=True)

        # ── Eval Experiments ──────────────────────────────────────────────────
        print("    → Eval experiments")
        experiment_defs = []
        if prompt_names and datasets_created:
            experiment_defs = [
                {
                    "name": "GPT-4o vs Claude on Customer Support",
                    "description": "Compare GPT-4o and Claude Sonnet on the customer Q&A dataset",
                    "dataset_id": datasets_created[0]["id"] if datasets_created else None,
                    "prompt_name": prompt_names[0],
                    "prompt_version": None,
                    "evaluator_ids": eval_ids[:2] if eval_ids else [],
                    "models": [
                        {"model": "gpt-4o", "provider": "openai", "label": "GPT-4o"},
                        {
                            "model": "claude-sonnet-4-6",
                            "provider": "anthropic",
                            "label": "Claude Sonnet",
                        },
                    ],
                },
                {
                    "name": "Code Review Accuracy Benchmark",
                    "description": "Measure code review accuracy with accuracy-scorer evaluator",
                    "dataset_id": datasets_created[1]["id"] if len(datasets_created) > 1 else None,
                    "prompt_name": prompt_names[1] if len(prompt_names) > 1 else prompt_names[0],
                    "prompt_version": None,
                    "evaluator_ids": eval_ids[2:3] if len(eval_ids) > 2 else eval_ids[:1],
                    "models": [
                        {"model": "gpt-4o-mini", "provider": "openai", "label": "GPT-4o-mini"},
                        {"model": "gpt-4o", "provider": "openai", "label": "GPT-4o"},
                    ],
                },
            ]
        for exp_def in experiment_defs:
            r = await c.post("/experiments", json=exp_def, skip_errors=True)
            if "id" in r:
                # Trigger a run immediately so status is completed
                await c.post(f"/experiments/{r['id']}/run", skip_errors=True)

        await asyncio.sleep(_THROTTLE)
        await c.get("/experiments", skip_errors=True)

        # ── Approvals ─────────────────────────────────────────────────────────
        print("    → Approvals")
        approval_defs = [
            {
                "request_type": "budget_increase",
                "request": {
                    "scope": "workspace",
                    "current_limit_usd": 10000,
                    "requested_limit_usd": 18000,
                },
            },
            {
                "request_type": "gateway_route_add",
                "request": {
                    "alias": "gpt-4-turbo",
                    "provider": "openai",
                    "target_model": "gpt-4-turbo",
                },
            },
            {
                "request_type": "chargeback_rule_change",
                "request": {"rule": "engineering", "old_weight": 0.50, "new_weight": 0.45},
            },
            {
                "request_type": "data_export",
                "request": {"format": "parquet", "destination": "s3://data-lake/runledger"},
            },
            {
                "request_type": "model_policy_change",
                "request": {"policy": "block_unverified_models", "enabled": True},
            },
        ]
        approval_ids: list[str] = []
        for ad in approval_defs:
            r = await c.post(
                "/approvals",
                json={
                    "request_type": ad["request_type"],
                    "request": ad["request"],
                    "requested_by": users[0]["id"] if users else None,
                },
                skip_errors=True,
            )
            if "id" in r:
                approval_ids.append(r["id"])

        # Approve some, deny one
        for i, aid in enumerate(approval_ids):
            if i < 3:
                await c.put(
                    f"/approvals/{aid}/approve",
                    json={
                        "decided_by": users[0]["id"] if users else None,
                        "decision_note": "Approved — within policy limits.",
                    },
                )
            elif i == 3:
                await c.put(
                    f"/approvals/{aid}/deny",
                    json={
                        "decided_by": users[0]["id"] if users else None,
                        "decision_note": "Denied — requires security review first.",
                    },
                )
            # leave last as pending

        # Promote a prompt using an approval
        if prompt_names and approval_ids:
            ap_id = approval_ids[0]
            await c.post(
                f"/prompts/{prompt_names[0]}/promote",
                json={"target": "production", "version": 3},
                params={"approval_id": ap_id},
                skip_errors=True,
            )

        await asyncio.sleep(_THROTTLE)
        await c.get("/approvals", skip_errors=True)
        await c.get("/approvals/summary", skip_errors=True)

        # ── Budgets ────────────────────────────────────────────────────────────
        print("    → Budgets")
        # Notification channel first
        notif = await c.post(
            "/budgets/notifications",
            json={
                "channel": "webhook",
                "destination_url": "https://hooks.example.com/runledger-alerts",
                "events": ["breach", "warning"],
                "is_active": True,
            },
            skip_errors=True,
        )
        _ = notif.get("id")

        budget_defs = [
            {
                "scope_type": "workspace",
                "scope_id": None,
                "period_type": "monthly",
                "limit_usd": 12000,
                "action": "notify",
            },
            {
                "scope_type": "workspace",
                "scope_id": None,
                "period_type": "daily",
                "limit_usd": 600,
                "action": "notify",
            },
            {
                "scope_type": "feature_tag",
                "scope_id": "customer-support",
                "period_type": "daily",
                "limit_usd": 400,
                "action": "block",
            },
            {
                "scope_type": "feature_tag",
                "scope_id": "code-review",
                "period_type": "daily",
                "limit_usd": 250,
                "action": "downgrade",
                "downgrade_to_model": "gpt-4o-mini",
            },
            {
                "scope_type": "end_user",
                "scope_id": "user_001",
                "period_type": "daily",
                "limit_usd": 25,
                "action": "block",
            },
            {
                "scope_type": "end_user",
                "scope_id": "user_002",
                "period_type": "monthly",
                "limit_usd": 200,
                "action": "notify",
            },
        ]
        for bd in budget_defs:
            await c.post(
                "/budgets",
                json={
                    "scope_type": bd["scope_type"],
                    "scope_id": bd.get("scope_id"),
                    "period_type": bd["period_type"],
                    "limit_usd": bd["limit_usd"],
                    "action": bd["action"],
                    "downgrade_to_model": bd.get("downgrade_to_model"),
                    "is_active": True,
                },
                skip_errors=True,
            )

        await asyncio.sleep(_THROTTLE)
        await c.get("/budgets", skip_errors=True)
        await c.get(
            "/budgets/check",
            params={"scope_type": "workspace", "period_type": "daily"},
            skip_errors=True,
        )

        # ── Alert Rules ────────────────────────────────────────────────────────
        print("    → Alert rules")
        alert_defs = [
            {
                "name": "High Error Rate",
                "metric": "error_rate",
                "operator": "gt",
                "threshold": 0.05,
                "window_minutes": 30,
            },
            {
                "name": "P95 Latency Spike",
                "metric": "p95_latency",
                "operator": "gt",
                "threshold": 5000,
                "window_minutes": 60,
            },
            {
                "name": "Low Quality Score",
                "metric": "avg_score",
                "operator": "lt",
                "threshold": 0.70,
                "window_minutes": 60,
            },
            {
                "name": "Spend Velocity",
                "metric": "spend_velocity",
                "operator": "gt",
                "threshold": 50.00,
                "window_minutes": 60,
            },
        ]
        alert_ids = []
        for ad in alert_defs:
            r = await c.post(
                "/alerts/rules",
                json={
                    "name": ad["name"],
                    "metric": ad["metric"],
                    "operator": ad["operator"],
                    "threshold": ad["threshold"],
                    "window_minutes": ad["window_minutes"],
                    "action": "notify",
                    "is_active": True,
                    "email_enabled": True,
                },
                skip_errors=True,
            )
            if "id" in r:
                alert_ids.append(r["id"])

        await asyncio.sleep(_THROTTLE)
        await c.get("/alerts/rules", skip_errors=True)
        await c.get("/alerts/history", skip_errors=True)

        # ── Billing Periods & Chargeback ──────────────────────────────────────
        print("    → Billing, chargeback, cost centres")

        # Cost centres
        cc_resp = await c.post(
            "/billing/cost-centers",
            json={
                "name": "Engineering",
                "code": "ENG",
                "description": "Core engineering and platform teams",
            },
            skip_errors=True,
        )
        cc_eng_id = cc_resp.get("id")

        cc_prod = await c.post(
            "/billing/cost-centers",
            json={
                "name": "Product",
                "code": "PROD",
                "description": "Product and design teams",
                "parent_id": cc_eng_id,
            },
            skip_errors=True,
        )
        cc_prod_id = cc_prod.get("id")

        cc_cx = await c.post(
            "/billing/cost-centers",
            json={
                "name": "Customer Experience",
                "code": "CX",
                "description": "CX and support teams",
            },
            skip_errors=True,
        )
        cc_cx_id = cc_cx.get("id")

        await c.get("/billing/cost-centers", skip_errors=True)
        await c.get("/billing/cost-centers/tree", skip_errors=True)

        # Chargeback rules
        for rule in [
            {
                "allocation_type": "team",
                "dimension": "engineering",
                "weight": 0.50,
                "cost_center_id": cc_eng_id,
            },
            {
                "allocation_type": "team",
                "dimension": "product",
                "weight": 0.30,
                "cost_center_id": cc_prod_id,
            },
            {
                "allocation_type": "team",
                "dimension": "cx",
                "weight": 0.20,
                "cost_center_id": cc_cx_id,
            },
        ]:
            await c.post("/billing/chargeback-rules", json=rule, skip_errors=True)

        await c.get("/billing/chargeback-rules", skip_errors=True)

        # Shared cost policy
        await c.post(
            "/billing/shared-cost-policies",
            json={
                "name": "Equal Infrastructure Split",
                "description": "Split shared infra costs equally across all teams",
                "formula_type": "equal_split",
                "allocations": [
                    {"team": "engineering", "weight": 0.34},
                    {"team": "product", "weight": 0.33},
                    {"team": "cx", "weight": 0.33},
                ],
                "is_active": True,
            },
            skip_errors=True,
        )

        await c.get("/billing/shared-cost-policies", skip_errors=True)

        # Billing periods — 3 closed months + current open
        period_ids: list[str] = []
        for months_back in range(3, 0, -1):
            base = TODAY.replace(day=1)
            for _ in range(months_back):
                # go back one month
                base = (base - timedelta(days=1)).replace(day=1)
            p_start = base
            p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            period = await c.post(
                "/billing/periods",
                json={
                    "period_start": p_start.isoformat(),
                    "period_end": p_end.isoformat(),
                },
                skip_errors=True,
            )
            pid = period.get("id")
            if not pid:
                continue
            period_ids.append(pid)

            # Add an adjustment
            await c.post(
                f"/billing/periods/{pid}/adjustments",
                json={
                    "adjustment_type": "credit",
                    "amount_usd": round(random.uniform(50, 300), 2),
                    "description": "Volume discount credit",
                    "reference_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
                },
                skip_errors=True,
            )

            # Close the period
            await c.post(f"/billing/periods/{pid}/close", json={}, skip_errors=True)
            await c.get(f"/billing/periods/{pid}/reconciliation", skip_errors=True)
            await c.get(f"/billing/periods/{pid}/breakdown", skip_errors=True)
            await c.get(
                f"/billing/periods/{pid}/export", params={"format": "csv"}, skip_errors=True
            )

        # Current open period
        open_period = await c.post(
            "/billing/periods",
            json={
                "period_start": TODAY.replace(day=1).isoformat(),
                "period_end": TODAY.isoformat(),
            },
            skip_errors=True,
        )
        if "id" in open_period:
            period_ids.append(open_period["id"])

        await asyncio.sleep(_THROTTLE)
        await c.get("/billing/cost-centers", skip_errors=True)
        await c.get("/billing/chargeback-rules", skip_errors=True)
        await c.get("/billing/periods", skip_errors=True)

        # Billing webhooks (enterprise feature — skip gracefully)
        await c.post(
            "/billing/webhooks",
            json={
                "url": "https://hooks.example.com/billing",
                "secret": "whsec_demo_secret_key_32bytes_long",
                "label": "Finance system webhook",
                "enabled": True,
            },
            skip_errors=True,
        )
        await c.get("/billing/webhooks", skip_errors=True)

        # ── Provider Invoice Reconciliation ────────────────────────────────────
        print("    → Invoice reconciliation")
        for months_back in range(1, 3):
            base = TODAY.replace(day=1)
            for _ in range(months_back):
                base = (base - timedelta(days=1)).replace(day=1)
            p_start = base
            p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            for provider, model, in_r, out_r in random.sample(PROVIDER_MODELS, 2):
                # Build a synthetic CSV invoice
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(
                    [
                        "request_id",
                        "model",
                        "input_tokens",
                        "output_tokens",
                        "cost_usd",
                        "timestamp",
                    ]
                )
                for _i in range(random.randint(15, 30)):
                    in_t = random.randint(500, 8000)
                    out_t = random.randint(200, 4000)
                    cost_line = in_t / 1_000_000 * in_r + out_t / 1_000_000 * out_r
                    occurred = p_start + timedelta(
                        days=random.randint(0, 25), hours=random.randint(0, 23)
                    )
                    writer.writerow(
                        [
                            f"req_{uuid.uuid4().hex[:24]}",
                            model,
                            in_t,
                            out_t,
                            round(cost_line, 6),
                            occurred.isoformat(),
                        ]
                    )

                csv_bytes = buf.getvalue().encode()
                files = {
                    "file": (f"{provider}_invoice.csv", csv_bytes, "text/csv"),
                }
                inv = await c.post(
                    "/invoices/upload",
                    files=files,
                    params={
                        "period_start": p_start.isoformat(),
                        "period_end": p_end.isoformat(),
                        "provider": provider,
                    },
                    skip_errors=True,
                )
                inv_id = inv.get("id")
                if inv_id:
                    await c.post(f"/invoices/{inv_id}/reconcile", json={}, skip_errors=True)
                    await c.get(f"/invoices/{inv_id}/lines", skip_errors=True)
                    await c.get(
                        f"/invoices/{inv_id}/export", params={"format": "json"}, skip_errors=True
                    )

        await asyncio.sleep(_THROTTLE)
        await c.get("/invoices", skip_errors=True)

        # ── Outcomes & ROI ─────────────────────────────────────────────────────
        print("    → Outcomes & ROI")
        outcome_types = [
            "task_completed",
            "user_satisfied",
            "ticket_resolved",
            "revenue_generated",
            "error_handled",
        ]
        scored_runs = [m for m in run_meta if m["status"] == "succeeded"]
        for meta in random.sample(scored_runs, min(len(scored_runs), 50)):
            o_type = random.choice(outcome_types)
            success = random.random() < 0.78
            await c.post(
                "/outcomes",
                json={
                    "run_id": meta["run_id"],
                    "end_user_id": meta["end_user"],
                    "outcome_type": o_type,
                    "success": success,
                    "value_usd": round(random.uniform(10, 250), 2) if success else None,
                    "labels": {"feature": meta["feature"], "provider": meta["provider"]},
                },
                skip_errors=True,
            )

        await asyncio.sleep(_THROTTLE)
        await c.get("/outcomes", skip_errors=True)
        await c.get("/outcomes/summary", skip_errors=True)
        await c.get("/outcomes/trend", skip_errors=True)
        await c.get("/outcomes/workflows", skip_errors=True)
        await c.get("/outcomes/quality-correlation", skip_errors=True)

        # ── Analytics queries ──────────────────────────────────────────────────
        print("    → Analytics")
        await asyncio.sleep(_THROTTLE)
        await c.get("/analytics/summary", skip_errors=True)
        await asyncio.sleep(_THROTTLE)
        await c.get("/analytics/spend-by-user", skip_errors=True)
        await c.get("/analytics/spend-by-model", skip_errors=True)
        await c.get("/analytics/spend-by-feature", skip_errors=True)
        await c.get("/analytics/spend-over-time", skip_errors=True)
        await asyncio.sleep(_THROTTLE)
        await c.get("/analytics/workflows/top", skip_errors=True)
        await c.get("/analytics/regressions", skip_errors=True)
        await c.get("/analytics/scores/summary", skip_errors=True)
        await c.get("/analytics/scores/regressions", skip_errors=True)
        await c.get("/analytics/anomalies", skip_errors=True)
        await c.get("/analytics/cohorts", skip_errors=True)

        # Annotations
        await c.post(
            "/analytics/annotations",
            json={
                "label": "Deployment v3.0 rollout",
                "note": "Switched primary model from gpt-4-turbo to gpt-4o — cost -40%",
                "annotated_at": ts(7),
            },
            skip_errors=True,
        )
        await c.post(
            "/analytics/annotations",
            json={
                "label": "Prompt optimisation",
                "note": "Reduced average input tokens by 28% with new summariser template",
                "annotated_at": ts(14),
            },
            skip_errors=True,
        )
        await c.get("/analytics/annotations", skip_errors=True)

        # ── Sessions ───────────────────────────────────────────────────────────
        await c.get("/sessions", skip_errors=True)

        # ── Runs explorer ─────────────────────────────────────────────────────
        await c.get("/runs", skip_errors=True)
        await c.get("/runs", params={"status": "succeeded", "limit": 20}, skip_errors=True)
        await c.get("/runs", params={"feature_tag": "customer-support"}, skip_errors=True)

        # ── Ledger snapshots ───────────────────────────────────────────────────
        print("    → Ledger snapshots")
        await c.post("/ledger/snapshots/generate", json={}, skip_errors=True)
        await c.get("/ledger/snapshots", skip_errors=True)

        # ── Retention policies ─────────────────────────────────────────────────
        print("    → Retention policies")
        ret_defs = [
            {
                "resource_type": "spans",
                "action": "delete",
                "scope": "workspace",
                "max_age_days": 365,
            },
            {
                "resource_type": "provider_calls",
                "action": "scrub",
                "scope": "workspace",
                "max_age_days": 180,
            },
            {
                "resource_type": "agent_runs",
                "action": "delete",
                "scope": "end_user",
                "scope_value": "user_001",
                "max_age_days": 90,
            },
        ]
        for rd in ret_defs:
            await c.post("/retention/policies", json=rd, skip_errors=True)

        await asyncio.sleep(_THROTTLE)
        ret_list = await c.get("/retention/policies", skip_errors=True)
        ret_items = ret_list.get("items", ret_list) if isinstance(ret_list, dict) else ret_list
        if isinstance(ret_items, list) and ret_items:
            # Dry-run purge on first policy
            first_id = ret_items[0].get("id") if isinstance(ret_items[0], dict) else None
            if first_id:
                await c.post(
                    "/retention/purge",
                    json={"policy_id": first_id, "dry_run": True},
                    skip_errors=True,
                )

        # ── Pricing Intelligence ───────────────────────────────────────────────
        print("    → Pricing contracts & credits")
        await c.get(
            "/pricing/timeline", params={"provider": "openai", "model": "gpt-4o"}, skip_errors=True
        )

        await c.post(
            "/pricing/contracts",
            json={
                "provider": "openai",
                "model": "gpt-4o",
                "discount_pct": 15.0,
                "effective_from": (TODAY - timedelta(days=60)).isoformat(),
                "effective_until": (TODAY + timedelta(days=305)).isoformat(),
                "notes": "Enterprise volume agreement — 15% discount on GPT-4o",
            },
            skip_errors=True,
        )

        await c.post(
            "/pricing/contracts",
            json={
                "provider": "anthropic",
                "model": None,
                "discount_pct": 10.0,
                "effective_from": (TODAY - timedelta(days=30)).isoformat(),
                "notes": "Preferred partnership pricing — 10% across all Claude models",
            },
            skip_errors=True,
        )

        await c.get("/pricing/contracts", skip_errors=True)

        await c.post(
            "/pricing/credits",
            json={
                "name": "Q1 2026 Promotional Credit",
                "credit_type": "promotional",
                "amount_usd": 500.0,
                "effective_from": (TODAY - timedelta(days=45)).isoformat(),
                "effective_until": (TODAY + timedelta(days=45)).isoformat(),
                "priority": 10,
            },
            skip_errors=True,
        )

        await c.post(
            "/pricing/credits",
            json={
                "name": "Prepaid Bundle — 10k USD",
                "credit_type": "prepaid",
                "amount_usd": 10000.0,
                "effective_from": (TODAY - timedelta(days=10)).isoformat(),
                "priority": 5,
            },
            skip_errors=True,
        )

        await asyncio.sleep(_THROTTLE)
        await c.get("/pricing/contracts", skip_errors=True)
        await c.get("/pricing/credits", skip_errors=True)

        # ── API key management ─────────────────────────────────────────────────
        print("    → Settings / API keys")
        await c.post(
            "/settings/api-keys",
            json={
                "name": "CI/CD pipeline key",
            },
            skip_errors=True,
        )
        await c.get("/settings/api-keys", skip_errors=True)

        # ── SSO config (enterprise feature — skips on 402) ────────────────────
        await c.post(
            "/sso/configs",
            json={
                "provider": "google",
                "issuer_url": "https://accounts.google.com",
                "client_id": "demo-client-id.apps.googleusercontent.com",
                "client_secret": "demo-client-secret",
                "scopes": "openid email profile",
                "default_role": "member",
                "enabled": True,
            },
            skip_errors=True,
        )
        await c.get("/sso/configs", skip_errors=True)

        # ── Warehouse destinations (cloud feature — skips on 402) ─────────────
        await c.post(
            "/warehouse/destinations",
            json={
                "name": "S3 Data Lake",
                "destination_type": "s3",
                "config": {
                    "bucket": "acme-ai-data-lake",
                    "prefix": "runledger/",
                    "region": "us-east-1",
                },
                "format": "parquet",
                "enabled": True,
                "schedule_cron": "0 2 * * *",
            },
            skip_errors=True,
        )
        await c.get("/warehouse/destinations", skip_errors=True)
        await c.get("/warehouse/jobs", skip_errors=True)

        # ── SCIM tokens (enterprise — skips on 402) ────────────────────────────
        print("    → SCIM tokens")
        scim_token = await c.post(
            "/sso/tokens",
            json={"label": "Okta SCIM provisioner"},
            skip_errors=True,
        )
        scim_token_id = scim_token.get("id") if isinstance(scim_token, dict) else None
        await c.get("/sso/tokens", skip_errors=True)
        if scim_token_id:
            await c.delete(f"/sso/tokens/{scim_token_id}", skip_errors=True)
            # Re-create so a live token stays available for UI inspection
            await c.post(
                "/sso/tokens",
                json={"label": "Okta SCIM provisioner"},
                skip_errors=True,
            )

        # ── Replay datasets + experiments ──────────────────────────────────────
        print("    → Replay datasets & experiments")
        runs_resp = await c.get("/runs", params={"limit": 10}, skip_errors=True)
        run_ids: list[str] = []
        if isinstance(runs_resp, dict):
            run_ids = [r.get("id", "") for r in runs_resp.get("items", []) if r.get("id")]
        if run_ids:
            replay_ds = await c.post(
                "/replay/datasets",
                json={"name": "Top-10 live runs", "run_ids": run_ids[:10]},
                skip_errors=True,
            )
            replay_ds_id = replay_ds.get("id") if isinstance(replay_ds, dict) else None
            if replay_ds_id:
                await c.post(
                    "/replay/experiments",
                    json={
                        "dataset_id": replay_ds_id,
                        "name": "GPT-4o vs Claude comparison",
                        "configs": [
                            {"model": "gpt-4o", "label": "GPT-4o"},
                            {"model": "claude-sonnet-4-6", "label": "Claude Sonnet"},
                        ],
                    },
                    skip_errors=True,
                )
        await c.get("/replay/datasets", skip_errors=True)
        await c.get("/replay/experiments", skip_errors=True)

        # ── Kafka export config — external integration, opt-in only ──────────
        # Requires a real Kafka broker. Skipped by default so the seed works
        # on any machine. Enable with SEED_EXTERNAL=true.
        if SEED_EXTERNAL:
            print("    → Kafka export (external)")
            kafka_cfg = await c.post(
                "/integrations/kafka/configs",
                json={
                    "label": "Internal Kafka — analytics bus",
                    "bootstrap_servers": os.getenv(
                        "KAFKA_BOOTSTRAP_SERVERS", "kafka.internal:9092"
                    ),
                    "topic_prefix": "runledger",
                    "security_protocol": "PLAINTEXT",
                    "event_types": [
                        "run.completed",
                        "run.failed",
                        "alert.fired",
                        "budget.breached",
                        "score.submitted",
                    ],
                },
                skip_errors=True,
            )
            await c.get("/integrations/kafka/configs", skip_errors=True)
            kafka_cfg_id = kafka_cfg.get("id") if isinstance(kafka_cfg, dict) else None
            if kafka_cfg_id:
                await c.post(
                    f"/integrations/kafka/configs/{kafka_cfg_id}/test",
                    json={},
                    skip_errors=True,
                )

        # ── OTLP trace ingestion (OpenInference format) ────────────────────────
        print("    → OTLP trace sample")
        import time  # noqa: PLC0415

        _now_ns = int(time.time() * 1e9)
        _trace_id = "0af7651916cd43dd8448eb211c80319c"
        _span_id = "b9c7c989f97918e1"
        await c.post(
            "/v1/traces",
            json={
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": "demo-agent"}},
                                {
                                    "key": "telemetry.sdk.name",
                                    "value": {
                                        "stringValue": "openinference-instrumentation-openai"
                                    },
                                },
                            ]
                        },
                        "scopeSpans": [
                            {
                                "scope": {"name": "openinference.instrumentation.openai"},
                                "spans": [
                                    {
                                        "traceId": _trace_id,
                                        "spanId": _span_id,
                                        "name": "ChatCompletion",
                                        "kind": 3,
                                        "startTimeUnixNano": str(_now_ns - 1_500_000_000),
                                        "endTimeUnixNano": str(_now_ns),
                                        "status": {"code": 1},
                                        "attributes": [
                                            {
                                                "key": "llm.model_name",
                                                "value": {"stringValue": "gpt-4o-mini"},
                                            },
                                            {
                                                "key": "llm.token_count.prompt",
                                                "value": {"intValue": 320},
                                            },
                                            {
                                                "key": "llm.token_count.completion",
                                                "value": {"intValue": 128},
                                            },
                                            {
                                                "key": "openinference.span.kind",
                                                "value": {"stringValue": "LLM"},
                                            },
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            skip_errors=True,
        )

        # ── Gateway traffic simulation ─────────────────────────────────────────
        # Runs live completions only when a provider API key is available.
        # Without a key the routes are still created; the gateway log will
        # populate once a real agent sends traffic.
        routes_resp = await c.get("/gateway/routes", skip_errors=True)
        _has_routes = isinstance(routes_resp, dict) and bool(routes_resp.get("items"))
        _has_key = bool(OPENAI_API_KEY or ANTHROPIC_API_KEY)
        if _has_routes and _has_key:
            print("    → Gateway traffic simulation (live)")
            _gw_model = "gpt-4o-mini" if OPENAI_API_KEY else "claude-haiku-4-5"
            for _prompt in [
                "What is prompt caching and how does it reduce AI costs?",
                "Summarise the key metrics in a FinOps control plane.",
                "What is prompt caching and how does it reduce AI costs?",  # cache hit
                "Explain budget-aware routing for LLM agents.",
                "How does chargeback work in a multi-team AI platform?",
            ]:
                await c.post(
                    "/gateway/chat/completions",
                    json={
                        "model": _gw_model,
                        "messages": [{"role": "user", "content": _prompt}],
                    },
                    skip_errors=True,
                )
                await asyncio.sleep(0.1)
        else:
            print("    → Gateway traffic simulation (skipped — set OPENAI_API_KEY to enable)")
        await c.get("/gateway/requests", skip_errors=True)
        await c.get("/gateway/stats", skip_errors=True)

        # ── Ops / metrics ──────────────────────────────────────────────────────
        await c.get("/ops/status", skip_errors=True)
        await c.get("/metrics", skip_errors=True)

        print("    ✓ Done")


# ── Step 4: platform-level reads ──────────────────────────────────────────────


async def seed_platform(admin: Client) -> None:
    print("\n  Platform admin checks")
    await admin.get("/org/profile")
    await admin.get("/org/workspaces")
    await admin.get("/org/members")
    await admin.get("/org/dashboard")
    await admin.get("/audit/events")
    await admin.get("/users/me")
    await admin.get("/users")


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("\nRunLedger Demo Seed — full API surface\n" + "━" * 50)
    print(f"  Target:           {BASE_URL}")
    print(
        f"  External integrations (Kafka etc.): {'on' if SEED_EXTERNAL else 'off  (set SEED_EXTERNAL=true to enable)'}"
    )
    print(
        f"  Gateway live traffic: {'on (OPENAI_API_KEY)' if OPENAI_API_KEY else 'on (ANTHROPIC_API_KEY)' if ANTHROPIC_API_KEY else 'off (set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable)'}"
    )
    print()

    async with Client(BASE_URL) as root:
        # Health check
        print("\n[0] Health check")
        await check_health(root)

        # Platform admin login
        print("\n[1] Platform admin login")
        auth = await root.post(
            "/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            },
        )
        if "api_key" not in auth:
            print(f"  ✗ Login failed: {auth}")
            sys.exit(1)
        admin_key = auth["api_key"]
        print(f"  ✓ Logged in as {ADMIN_EMAIL}")

    async with Client(BASE_URL, admin_key) as admin:
        # Idempotency guard
        print("\n[2] Idempotency check")
        wss = await admin.get("/org/workspaces")
        ws_list = (wss.get("items", wss) if isinstance(wss, dict) else wss) or []
        existing_names = {w.get("name", "") for w in ws_list if isinstance(w, dict)}
        demo_marker = "Acme Corp — Platform AI"
        if demo_marker in existing_names:
            print(f"  Demo data already exists ('{demo_marker}' workspace found).")
            print("  Delete demo workspaces via /org/workspaces to re-seed.")
            return
        print("  No existing demo data — proceeding")

        # Create orgs
        print("\n[3] Creating organisations, users & workspaces")
        contexts = await create_orgs(admin)
        print(f"\n  → {len(contexts)} workspaces ready")

        # Seed each workspace
        print("\n[4] Seeding workspace data via API")
        for ctx in contexts:
            try:
                await seed_workspace(ctx)
            except Exception as exc:
                print(f"    ✗ Error in {ctx['org_name']}/{ctx['ws_name']}: {exc}")

        # Platform reads
        print("\n[5] Platform-level data")
        await seed_platform(admin)

    # Summary
    print("\n" + "━" * 50)
    print("Demo seed complete!\n")
    print("Organisations:")
    org_map: dict[str, list[str]] = {}
    for ctx in contexts:
        org_map.setdefault(ctx["org_name"], []).append(ctx["ws_name"])
    for org, wss in org_map.items():
        print(f"  {org}")
        for ws in wss:
            print(f"    └─ {ws}")
    print()
    print("Demo user credentials (all): password = demo1234")
    print("  alice@acme-demo.com       — Acme Corp admin")
    print("  emma@techstart-demo.io    — TechStart admin")
    print("  henry@globalai-demo.com   — GlobalAI admin")
    print()
    print("Platform admin: admin@runledger.local / runledger")
    print()
    print(f"Dashboard → {BASE_URL.replace(':8000', ':3000').replace('8000', '3000')}")
    print(f"API docs  → {BASE_URL}/reference")
    print()
    if not OPENAI_API_KEY and not ANTHROPIC_API_KEY:
        print("Tip: re-run with OPENAI_API_KEY=sk-... to populate gateway request logs.")
        print("     docker exec runledger-api-1 sh -c \\")
        print('       "RUNLEDGER_API_KEY=<key> OPENAI_API_KEY=sk-... python scripts/seed_demo.py"')
        print()


if __name__ == "__main__":
    asyncio.run(main())
