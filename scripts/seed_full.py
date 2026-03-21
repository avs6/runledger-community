"""
Full seed script for RunLedger demo environment.

What this does
──────────────
1.  SCRUB  — wipe all previously seeded runs, provider_calls, spans, scores,
             prompts, prompt_versions, replay_datasets, replay_experiments,
             usage_daily, user_anomalies (keeps workspace/API keys/gateway routes/
             billing periods).

2.  PRICING — upsert pricing for all Ollama, OpenAI, Anthropic models.

3.  APPLICATIONS — 3 realistic apps.

4.  PROMPTS (3 prompts × 2 versions each)
    Each version is tied to a specific Ollama model and real prompt text.
    Runs use  deployment_version = "{prompt_name}:{version_number}"
    so the Prompts UI shows run_count, avg_cost and avg_score per version.

5.  REAL OLLAMA RUNS (via direct HTTP to Ollama)
    For each prompt version, fire N completions through Ollama,
    recording AgentRun + Span + ProviderCall + ScoreEvent rows
    with correct deployment_version so metrics wire up.

6.  BILLING PERIOD — open period covering this month.

7.  REPLAY DATASETS — one dataset per prompt grouping runs by prompt_name.

8.  REPLAY EXPERIMENTS — compare v1 vs v2 for each prompt, mark completed
    with simulated cost-projection results.

9.  TOOL REGISTRY — register 3 tools (web_search, code_executor, file_reader).

10. DAILY LEDGER SNAPSHOT — trigger the snapshot worker for yesterday.

11. USAGE_DAILY ROLLUP — aggregate provider_calls → usage_daily.

Run from repo root:
    cd apps/api && uv run python ../../scripts/seed_full.py
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
import os
import uuid
import hashlib
import hmac
from datetime import UTC, datetime, timedelta, date
from decimal import Decimal

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../apps/api"))

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.config import settings
from runledger_api.models.events import (
    AgentRun, ProviderCall, RunStatusEnum, Span, SpanStatusEnum, SpanTypeEnum,
)
from runledger_api.models.metering import ProviderPricing, UsageDaily
from runledger_api.models.tenant import Application
from runledger_api.models.prompts import Prompt, PromptVersion
from runledger_api.models.scores import ScoreEvent
from runledger_api.models.replay import ReplayDataset, ReplayExperiment
from runledger_api.models.ledger import ToolRegistry, LedgerKey, LedgerSnapshot
from runledger_api.models.billing import BillingPeriod

# ── Config ────────────────────────────────────────────────────────────────────

WORKSPACE_ID = uuid.UUID("313fbd0f-4515-4baf-ae6d-3ac980971433")
OLLAMA_URL   = "http://localhost:11434/v1"

rng = random.Random(7)

# ── Pricing ───────────────────────────────────────────────────────────────────

PRICING: list[tuple[str, str, str, str]] = [
    # Ollama — free local inference
    ("ollama", "llama3.2",              "0.00", "0.00"),
    ("ollama", "llama3.2:1b",           "0.00", "0.00"),
    ("ollama", "llama3.1",              "0.00", "0.00"),
    ("ollama", "llama3.1:8b",           "0.00", "0.00"),
    ("ollama", "mistral",               "0.00", "0.00"),
    ("ollama", "mistral-small3.1",      "0.00", "0.00"),
    ("ollama", "qwen2.5",               "0.00", "0.00"),
    ("ollama", "qwen2.5-coder:7b",      "0.00", "0.00"),
    ("ollama", "qwen2.5-coder:14b",     "0.00", "0.00"),
    ("ollama", "gemma2",                "0.00", "0.00"),
    ("ollama", "gemma3",                "0.00", "0.00"),
    ("ollama", "deepseek-coder-v2",     "0.00", "0.00"),
    ("ollama", "dolphin-llama3",        "0.00", "0.00"),
    ("ollama", "dolphin3",              "0.00", "0.00"),
    # OpenAI
    ("openai", "gpt-4o",               "2.50",  "10.00"),
    ("openai", "gpt-4o-mini",          "0.15",   "0.60"),
    ("openai", "gpt-4-turbo",         "10.00",  "30.00"),
    ("openai", "gpt-3.5-turbo",        "0.50",   "1.50"),
    ("openai", "o1-mini",              "3.00",  "12.00"),
    ("openai", "o3-mini",              "1.10",   "4.40"),
    # Anthropic
    ("anthropic", "claude-3-5-sonnet-20241022", "3.00",  "15.00"),
    ("anthropic", "claude-3-haiku-20240307",    "0.25",   "1.25"),
    ("anthropic", "claude-3-opus-20240229",    "15.00",  "75.00"),
    ("anthropic", "claude-sonnet-4-6",          "3.00",  "15.00"),
]

# ── Prompts ───────────────────────────────────────────────────────────────────
# Each prompt has 2 versions pointing at different Ollama models.
# Runs will use deployment_version = f"{name}:{version_num}"
# so prompt metrics show real run_count + avg_score.

PROMPTS = [
    {
        "name": "ticket-classifier",
        "description": "Classifies support tickets by priority and category.",
        "versions": [
            {
                "version": 1,
                "model": "llama3.2",
                "commit_message": "Initial classifier — simple JSON output",
                "content": (
                    "You are a customer support ticket classifier.\n"
                    "Given a support ticket, respond with ONLY a JSON object on one line:\n"
                    "{\"priority\": \"low|medium|high|critical\", "
                    "\"category\": \"billing|technical|general\", "
                    "\"summary\": \"one sentence\"}\n"
                    "No explanation, just the JSON."
                ),
                "questions": [
                    "My payment failed three times today and I can't access my account.",
                    "The API returns 500 errors when I call /users endpoint.",
                    "How do I change my notification preferences?",
                    "I was charged twice for the same subscription this month!",
                    "The dashboard takes forever to load on Firefox.",
                ],
            },
            {
                "version": 2,
                "model": "mistral",
                "commit_message": "Add sentiment field, stricter JSON format",
                "content": (
                    "You are an expert customer support classifier.\n"
                    "Given a support ticket, respond with ONLY this JSON on one line:\n"
                    "{\"priority\": \"low|medium|high|critical\", "
                    "\"category\": \"billing|technical|account|general\", "
                    "\"sentiment\": \"positive|neutral|negative\", "
                    "\"summary\": \"one sentence\"}\n"
                    "Be precise. No extra text."
                ),
                "questions": [
                    "My payment failed three times today and I can't access my account.",
                    "The API returns 500 errors when I call /users endpoint.",
                    "How do I change my notification preferences?",
                    "I was charged twice for the same subscription this month!",
                    "The dashboard takes forever to load on Firefox.",
                    "Your service has been incredible, saved us hours every week!",
                ],
            },
        ],
    },
    {
        "name": "doc-summariser",
        "description": "Produces concise bullet-point summaries of documents.",
        "versions": [
            {
                "version": 1,
                "model": "llama3.2",
                "commit_message": "Basic bullet summary",
                "content": (
                    "Summarise the following text in exactly 3 bullet points.\n"
                    "Be concise. Start each bullet with •\n\n"
                    "Text: {{input}}"
                ),
                "questions": [
                    "Large language models (LLMs) are AI systems trained on vast text datasets. They can generate coherent text, answer questions, translate languages, and write code. GPT-4, Claude, and Gemini are examples. Training requires massive compute and curated data. Fine-tuning adapts them to specific tasks. Safety and alignment research aims to make them helpful and harmless.",
                    "Docker containers package code and dependencies together. Unlike VMs, containers share the host OS kernel, making them lightweight. Docker Compose orchestrates multi-container applications. Images are built from Dockerfiles and stored in registries like Docker Hub. Kubernetes manages containers at scale across clusters.",
                    "PostgreSQL is an open-source relational database known for reliability and SQL compliance. It supports JSON, full-text search, and window functions. Partitioning improves performance on large tables. VACUUM reclaims storage from dead rows. Connection pooling via PgBouncer reduces overhead for high-traffic applications.",
                ],
            },
            {
                "version": 2,
                "model": "qwen2.5",
                "commit_message": "Add key decisions and risk extraction",
                "content": (
                    "Summarise the following text. Return ONLY this JSON:\n"
                    "{\"bullets\": [\"...\", \"...\", \"...\"], "
                    "\"key_decisions\": [\"...\"], "
                    "\"risks\": [\"...\"]}\n\n"
                    "Text: {{input}}"
                ),
                "questions": [
                    "Large language models (LLMs) are AI systems trained on vast text datasets. They can generate coherent text, answer questions, translate languages, and write code. GPT-4, Claude, and Gemini are examples. Training requires massive compute and curated data. Fine-tuning adapts them to specific tasks. Safety and alignment research aims to make them helpful and harmless.",
                    "Docker containers package code and dependencies together. Unlike VMs, containers share the host OS kernel, making them lightweight. Docker Compose orchestrates multi-container applications. Images are built from Dockerfiles and stored in registries like Docker Hub. Kubernetes manages containers at scale across clusters.",
                    "PostgreSQL is an open-source relational database known for reliability and SQL compliance. It supports JSON, full-text search, and window functions. Partitioning improves performance on large tables. VACUUM reclaims storage from dead rows. Connection pooling via PgBouncer reduces overhead for high-traffic applications.",
                    "Microservices architecture splits applications into small, independent services that communicate via APIs. Each service can be deployed and scaled independently. Service meshes like Istio handle observability and traffic management. The tradeoff: increased operational complexity vs. independent deployability.",
                ],
            },
        ],
    },
    {
        "name": "code-reviewer",
        "description": "Reviews code diffs and returns structured feedback.",
        "versions": [
            {
                "version": 1,
                "model": "llama3.2",
                "commit_message": "Plain-text code review",
                "content": (
                    "You are a senior software engineer doing a code review.\n"
                    "Review the following code snippet and list: bugs, style issues, and one suggestion.\n"
                    "Be brief and direct.\n\n"
                    "Code:\n{{input}}"
                ),
                "questions": [
                    "def get_user(id):\n    result = db.execute(f'SELECT * FROM users WHERE id={id}')\n    return result.fetchone()",
                    "async function fetchData(url) {\n  const res = await fetch(url)\n  return res.json()\n}",
                    "for i in range(len(items)):\n    print(items[i])\n    if items[i] == None:\n        items[i] = 'N/A'",
                    "password = request.form['password']\nif password == stored_password:\n    login(user)",
                ],
            },
            {
                "version": 2,
                "model": "gemma2",
                "commit_message": "JSON output with severity levels",
                "content": (
                    "You are a senior software engineer. Review the code and return ONLY this JSON:\n"
                    "{\"bugs\": [{\"line\": \"...\", \"severity\": \"low|medium|high|critical\", \"description\": \"...\"}], "
                    "\"style_issues\": [\"...\"], "
                    "\"suggestions\": [\"...\"], "
                    "\"overall_score\": 1-10}\n\n"
                    "Code:\n{{input}}"
                ),
                "questions": [
                    "def get_user(id):\n    result = db.execute(f'SELECT * FROM users WHERE id={id}')\n    return result.fetchone()",
                    "async function fetchData(url) {\n  const res = await fetch(url)\n  return res.json()\n}",
                    "for i in range(len(items)):\n    print(items[i])\n    if items[i] == None:\n        items[i] = 'N/A'",
                    "password = request.form['password']\nif password == stored_password:\n    login(user)",
                    "SELECT * FROM orders WHERE customer_id = ? AND status = 'pending' ORDER BY created_at DESC",
                ],
            },
        ],
    },
]

USERS = ["alice@acme.com", "bob@acme.com", "carol@acme.com", "dave@acme.com", "eve@acme.com"]
SESSIONS = [f"sess-{i:02d}" for i in range(1, 8)]

# ── Helpers ───────────────────────────────────────────────────────────────────

def rand_past_dt(days_back: int = 14) -> datetime:
    return datetime.now(UTC) - timedelta(
        days=rng.randint(0, days_back),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )


async def call_ollama(model: str, system: str, user_input: str) -> dict:
    """Fire a real completion to Ollama. Returns response dict."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_input},
                ],
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        return resp.json()


def simple_score(answer: str, prompt_version: int) -> float:
    """Heuristic quality score based on answer characteristics."""
    score = 0.5
    if len(answer) > 50:
        score += 0.1
    if "{" in answer and "}" in answer:
        score += 0.15  # JSON output is what we asked for
    if prompt_version == 2:
        score += 0.05  # v2 prompts tend to be more structured
    score += rng.uniform(-0.1, 0.15)
    return round(min(max(score, 0.3), 1.0), 3)


# ── Step 1: Scrub ─────────────────────────────────────────────────────────────

async def scrub(session: AsyncSession) -> None:
    print("  Scrubbing old seeded data...")
    # Tables without workspace_id need a join-based delete
    join_deletes = {
        "spans":          "DELETE FROM spans WHERE run_id IN (SELECT id FROM agent_runs WHERE workspace_id = :ws)",
        "outcome_events": "DELETE FROM outcome_events WHERE run_id IN (SELECT id FROM agent_runs WHERE workspace_id = :ws)",
        "prompt_versions":"DELETE FROM prompt_versions WHERE prompt_id IN (SELECT id FROM prompts WHERE workspace_id = :ws)",
    }
    for tbl, sql in join_deletes.items():
        sp = f"sp_{tbl}"
        try:
            await session.execute(text(f"SAVEPOINT {sp}"))
            await session.execute(text(sql), {"ws": str(WORKSPACE_ID)})
            await session.execute(text(f"RELEASE SAVEPOINT {sp}"))
        except Exception as e:
            await session.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
            print(f"    skip {tbl}: {type(e).__name__}")

    tables = [
        "replay_experiments", "replay_datasets",
        "score_events",
        "tool_calls", "provider_calls",
        "agent_runs",
        "prompts",
        "usage_daily", "usage_hourly",
        "user_anomalies",
        "ledger_snapshots",
        "tool_registry",
        "billing_periods",
    ]
    for tbl in tables:
        # Use SAVEPOINT so a failed DELETE doesn't abort the whole transaction
        sp = f"sp_{tbl}"
        try:
            await session.execute(text(f"SAVEPOINT {sp}"))
            await session.execute(
                text(f"DELETE FROM {tbl} WHERE workspace_id = :ws"),
                {"ws": str(WORKSPACE_ID)},
            )
            await session.execute(text(f"RELEASE SAVEPOINT {sp}"))
        except Exception as e:
            await session.execute(text(f"ROLLBACK TO SAVEPOINT {sp}"))
            print(f"    skip {tbl}: {type(e).__name__}")
    await session.flush()
    print("    done.")


# ── Step 2: Pricing ───────────────────────────────────────────────────────────

async def seed_pricing(session: AsyncSession) -> None:
    print("  Pricing...")
    now = datetime.now(UTC)
    added = 0
    for provider, model, inp, out in PRICING:
        exists = await session.execute(
            select(ProviderPricing).where(
                ProviderPricing.provider == provider,
                ProviderPricing.model == model,
                ProviderPricing.workspace_id == WORKSPACE_ID,
            )
        )
        if exists.scalar_one_or_none():
            continue
        session.add(ProviderPricing(
            workspace_id=WORKSPACE_ID,
            provider=provider,
            model=model,
            input_cost_per_1m=Decimal(inp),
            output_cost_per_1m=Decimal(out),
            effective_from=now,
        ))
        added += 1
    await session.flush()
    print(f"    +{added} rows")


# ── Step 3: Applications ──────────────────────────────────────────────────────

async def seed_applications(session: AsyncSession) -> dict[str, uuid.UUID]:
    print("  Applications...")
    names = ["Support Ops", "Dev Tools", "Content Platform"]
    result = await session.execute(
        select(Application).where(Application.workspace_id == WORKSPACE_ID)
    )
    existing = {a.name: a.id for a in result.scalars().all()}
    for name in names:
        if name not in existing:
            app = Application(workspace_id=WORKSPACE_ID, name=name)
            session.add(app)
            await session.flush()
            existing[name] = app.id
            print(f"    + {name}")
    return existing


# ── Step 4 + 5: Prompts + real Ollama runs ───────────────────────────────────

async def seed_prompts_and_runs(
    session: AsyncSession,
    app_ids: dict[str, uuid.UUID],
) -> dict[str, list[uuid.UUID]]:
    """
    For each prompt × version, create PromptVersion and fire real Ollama completions.
    Returns {prompt_name: [run_id, ...]} for dataset creation.
    """
    print("  Prompts + real Ollama runs...")
    app_list = list(app_ids.values())
    prompt_run_ids: dict[str, list[uuid.UUID]] = {}

    for p_def in PROMPTS:
        # Create prompt
        prompt = Prompt(
            workspace_id=WORKSPACE_ID,
            name=p_def["name"],
            description=p_def["description"],
            default_environment="production",
        )
        session.add(prompt)
        await session.flush()
        print(f"\n  [{p_def['name']}]")

        all_run_ids: list[uuid.UUID] = []

        for v_def in p_def["versions"]:
            # Create prompt version
            pv = PromptVersion(
                prompt_id=prompt.id,
                version=v_def["version"],
                content=v_def["content"],
                variables={"input": ""},
                commit_message=v_def["commit_message"],
                environment="production",
                model_hint=v_def["model"],
            )
            session.add(pv)
            await session.flush()

            deployment_version = f"{p_def['name']}:{v_def['version']}"
            model = v_def["model"]
            print(f"    v{v_def['version']} ({model}) — {len(v_def['questions'])} questions")

            for q in v_def["questions"]:
                user   = rng.choice(USERS)
                sess_id = rng.choice(SESSIONS)
                app_id  = rng.choice(app_list)
                started = rand_past_dt(14)

                # Render prompt content (replace {{input}} variable)
                system_prompt = v_def["content"].replace("{{input}}", "")

                print(f"      → {model}: {q[:60]}...")
                t0 = datetime.now(UTC)
                try:
                    resp = await call_ollama(model, system_prompt, q)
                    latency_ms = int((datetime.now(UTC) - t0).total_seconds() * 1000)

                    usage     = resp.get("usage", {})
                    in_tok    = usage.get("prompt_tokens", rng.randint(100, 400))
                    out_tok   = usage.get("completion_tokens", rng.randint(30, 200))
                    answer    = resp["choices"][0]["message"]["content"]
                    status    = RunStatusEnum.succeeded

                except Exception as e:
                    print(f"      ERROR: {e}")
                    latency_ms = 5000
                    in_tok, out_tok = rng.randint(100, 300), 0
                    answer = ""
                    status = RunStatusEnum.failed

                ended = started + timedelta(milliseconds=latency_ms)

                run_id  = uuid.uuid4()
                span_id = uuid.uuid4()

                session.add(AgentRun(
                    id=run_id,
                    workspace_id=WORKSPACE_ID,
                    application_id=app_id,
                    end_user_id=user,
                    session_id=sess_id,
                    feature_tag=p_def["name"],
                    deployment_version=deployment_version,
                    status=status,
                    started_at=started,
                    ended_at=ended,
                    total_cost_usd=Decimal("0"),
                    total_input_tokens=in_tok,
                    total_output_tokens=out_tok,
                ))
                await session.flush()

                session.add(Span(
                    id=span_id,
                    run_id=run_id,
                    span_type=SpanTypeEnum.llm,
                    name=f"{p_def['name']}-inference",
                    started_at=started,
                    ended_at=ended,
                    status=SpanStatusEnum.succeeded if status == RunStatusEnum.succeeded else SpanStatusEnum.failed,
                    cost_usd=Decimal("0"),
                ))
                await session.flush()

                session.add(ProviderCall(
                    run_id=run_id,
                    span_id=span_id,
                    workspace_id=WORKSPACE_ID,
                    provider="ollama",
                    model=model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    latency_ms=latency_ms,
                    cost_usd=Decimal("0"),
                    status="success" if status == RunStatusEnum.succeeded else "error",
                    created_at=started,
                ))
                await session.flush()

                # Score the output
                if status == RunStatusEnum.succeeded and answer:
                    q_score = simple_score(answer, v_def["version"])
                    r_score = round(min(q_score + rng.uniform(-0.05, 0.1), 1.0), 3)

                    for sname, sval in [("quality", q_score), ("relevance", r_score)]:
                        session.add(ScoreEvent(
                            workspace_id=WORKSPACE_ID,
                            run_id=run_id,
                            session_id=sess_id,
                            end_user_id=user,
                            name=sname,
                            value=Decimal(str(sval)),
                            source="auto-eval",
                            confidence=Decimal("0.85"),
                            created_at=ended,
                        ))
                    await session.flush()

                all_run_ids.append(run_id)

        prompt_run_ids[p_def["name"]] = all_run_ids

    return prompt_run_ids


# ── Step 6: Billing period ────────────────────────────────────────────────────

async def seed_billing_period(session: AsyncSession) -> None:
    print("  Billing period...")
    today = date.today()
    period_start = today.replace(day=1)
    period_end   = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    session.add(BillingPeriod(
        workspace_id=WORKSPACE_ID,
        period_start=period_start,
        period_end=period_end,
        status="open",
    ))
    await session.flush()
    print(f"    open period: {period_start} → {period_end}")


# ── Step 7: Replay datasets ───────────────────────────────────────────────────

async def seed_replay(
    session: AsyncSession,
    prompt_run_ids: dict[str, list[uuid.UUID]],
) -> None:
    print("  Replay datasets + experiments...")

    for prompt_name, run_ids in prompt_run_ids.items():
        if not run_ids:
            continue

        # Split v1 vs v2 runs (first half = v1, second half = v2 per prompt structure)
        n_versions = 2
        per_version = len(run_ids) // n_versions
        v1_ids = [str(r) for r in run_ids[:per_version]]
        v2_ids = [str(r) for r in run_ids[per_version:]]
        all_ids = [str(r) for r in run_ids]

        # Dataset: all runs for this prompt
        dataset = ReplayDataset(
            workspace_id=WORKSPACE_ID,
            name=f"{prompt_name} — evaluation set",
            source="live_runs",
            run_ids=all_ids,
        )
        session.add(dataset)
        await session.flush()
        print(f"    dataset: {dataset.name} ({len(all_ids)} runs)")

        # Find the models used for v1 and v2
        v1_model = next(v["model"] for p in PROMPTS if p["name"] == prompt_name
                        for v in p["versions"] if v["version"] == 1)
        v2_model = next(v["model"] for p in PROMPTS if p["name"] == prompt_name
                        for v in p["versions"] if v["version"] == 2)

        # Avg latency per version (estimated)
        v1_calls_per_run = sum(len(v["questions"]) for p in PROMPTS
                               if p["name"] == prompt_name
                               for v in p["versions"] if v["version"] == 1)
        v2_calls_per_run = sum(len(v["questions"]) for p in PROMPTS
                               if p["name"] == prompt_name
                               for v in p["versions"] if v["version"] == 2)

        # Experiment: v1 vs v2 — mark completed with projected results
        now_str = datetime.now(UTC).isoformat()
        v1_avg_lat = rng.randint(1200, 3500)
        v2_avg_lat = rng.randint(900, 2800)
        v1_avg_score = round(rng.uniform(0.60, 0.75), 3)
        v2_avg_score = round(rng.uniform(0.70, 0.88), 3)

        experiment = ReplayExperiment(
            workspace_id=WORKSPACE_ID,
            dataset_id=dataset.id,
            name=f"{prompt_name}: v1 vs v2 A/B",
            configs=[
                {
                    "label": f"v1 ({v1_model})",
                    "model": v1_model,
                    "prompt_version": 1,
                    "run_ids": v1_ids,
                },
                {
                    "label": f"v2 ({v2_model})",
                    "model": v2_model,
                    "prompt_version": 2,
                    "run_ids": v2_ids,
                },
            ],
            status="completed",
            estimated_cost_usd=Decimal("0.00"),
            results={
                "completed_at": now_str,
                "dataset_run_count": len(all_ids),
                "configs": [
                    {
                        "label": f"v1 ({v1_model})",
                        "model": v1_model,
                        "run_count": len(v1_ids),
                        "avg_cost_usd": 0.0,
                        "avg_latency_ms": v1_avg_lat,
                        "avg_score": v1_avg_score,
                        "estimated_total_cost": 0.0,
                    },
                    {
                        "label": f"v2 ({v2_model})",
                        "model": v2_model,
                        "run_count": len(v2_ids),
                        "avg_cost_usd": 0.0,
                        "avg_latency_ms": v2_avg_lat,
                        "avg_score": v2_avg_score,
                        "estimated_total_cost": 0.0,
                    },
                ],
                "deltas": [
                    {
                        "metric": "avg_score",
                        "baseline_label": f"v1 ({v1_model})",
                        "candidate_label": f"v2 ({v2_model})",
                        "baseline_value": v1_avg_score,
                        "candidate_value": v2_avg_score,
                        "delta_pct": round((v2_avg_score - v1_avg_score) / v1_avg_score * 100, 2),
                        "winner": f"v2 ({v2_model})" if v2_avg_score >= v1_avg_score else f"v1 ({v1_model})",
                    },
                    {
                        "metric": "avg_latency_ms",
                        "baseline_label": f"v1 ({v1_model})",
                        "candidate_label": f"v2 ({v2_model})",
                        "baseline_value": float(v1_avg_lat),
                        "candidate_value": float(v2_avg_lat),
                        "delta_pct": round((v2_avg_lat - v1_avg_lat) / v1_avg_lat * 100, 2),
                        "winner": f"v1 ({v1_model})" if v1_avg_lat <= v2_avg_lat else f"v2 ({v2_model})",
                    },
                ],
            },
        )
        session.add(experiment)
        await session.flush()
        print(f"    experiment: {experiment.name} → completed")


# ── Step 8: Tool registry ─────────────────────────────────────────────────────

async def seed_tools(session: AsyncSession) -> None:
    print("  Tool registry...")
    tools = [
        ("web_search",    "read",       "Searches the web for current information via SerpAPI."),
        ("code_executor", "privileged", "Executes Python code in a sandboxed environment."),
        ("file_reader",   "read",       "Reads files from the workspace filesystem."),
        ("sql_query",     "read",       "Runs read-only SQL queries against the analytics DB."),
        ("send_email",    "write",      "Sends transactional emails via SendGrid."),
    ]
    for tool_name, policy, description in tools:
        session.add(ToolRegistry(
            workspace_id=WORKSPACE_ID,
            tool_name=tool_name,
            policy=policy,
            description=description,
        ))
    await session.flush()
    print(f"    +{len(tools)} tools registered")


# ── Step 9: Ledger daily snapshot ─────────────────────────────────────────────

async def seed_ledger_snapshot(session: AsyncSession) -> None:
    print("  Ledger snapshot...")
    yesterday = date.today() - timedelta(days=1)

    # Get or create ledger key
    key_result = await session.execute(
        select(LedgerKey).where(
            LedgerKey.workspace_id == WORKSPACE_ID,
            LedgerKey.active.is_(True),
        )
    )
    ledger_key = key_result.scalar_one_or_none()
    if not ledger_key:
        ledger_key = LedgerKey(
            workspace_id=WORKSPACE_ID,
            key_value=hashlib.sha256(os.urandom(32)).hexdigest(),
            active=True,
            expires_at=datetime.now(UTC) + timedelta(days=365),
        )
        session.add(ledger_key)
        await session.flush()

    # Compute total cost and call count across all provider_calls seeded
    cost_result = await session.execute(text("""
        SELECT
            COALESCE(SUM(cost_usd), 0)::float AS total,
            COUNT(*)::int AS calls,
            json_object_agg(model, COALESCE(cost_usd, 0)) AS breakdown
        FROM provider_calls
        WHERE workspace_id = :ws
    """), {"ws": str(WORKSPACE_ID)})
    row = cost_result.one()
    total_cost = float(row.total)
    call_count = int(row.calls)
    model_breakdown = row.breakdown or {}

    body = json.dumps({
        "workspace_id": str(WORKSPACE_ID),
        "date": yesterday.isoformat(),
        "total_cost_usd": total_cost,
    }, sort_keys=True).encode()
    sig = hmac.new(ledger_key.key_value.encode(), body, hashlib.sha256).hexdigest()

    session.add(LedgerSnapshot(
        workspace_id=WORKSPACE_ID,
        snapshot_date=yesterday,
        total_cost_usd=Decimal(str(total_cost)),
        model_breakdown=model_breakdown,
        call_count=call_count,
        hash=sig,
        key_id=ledger_key.id,
    ))
    await session.flush()
    print(f"    snapshot for {yesterday}: ${total_cost:.6f}, {call_count} calls")


# ── Step 10: Usage daily rollup ───────────────────────────────────────────────

async def seed_usage_daily(session: AsyncSession) -> None:
    print("  Usage daily rollup...")
    await session.execute(text("""
        INSERT INTO usage_daily
            (workspace_id, model, provider, feature_tag, end_user_id, day,
             input_tokens, output_tokens, cost_usd, run_count, call_count)
        SELECT
            pc.workspace_id,
            pc.model,
            pc.provider,
            ar.feature_tag,
            ar.end_user_id,
            DATE(pc.created_at AT TIME ZONE 'UTC') AS day,
            SUM(COALESCE(pc.input_tokens,  0))::bigint,
            SUM(COALESCE(pc.output_tokens, 0))::bigint,
            SUM(COALESCE(pc.cost_usd,      0))::numeric,
            COUNT(DISTINCT ar.id)::int,
            COUNT(pc.id)::int
        FROM provider_calls pc
        JOIN agent_runs ar ON ar.id = pc.run_id
        WHERE pc.workspace_id = :ws
        GROUP BY
            pc.workspace_id, pc.model, pc.provider,
            ar.feature_tag, ar.end_user_id,
            DATE(pc.created_at AT TIME ZONE 'UTC')
        ON CONFLICT DO NOTHING
    """), {"ws": str(WORKSPACE_ID)})
    await session.flush()
    print("    done.")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"\nRunLedger full seed → {WORKSPACE_ID}\n{'─'*60}")
    engine  = create_async_engine(settings.database_url, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as sess:
        await scrub(sess)
        await sess.commit()

        await seed_pricing(sess)
        app_ids = await seed_applications(sess)
        await sess.commit()

        prompt_run_ids = await seed_prompts_and_runs(sess, app_ids)
        await sess.commit()

        await seed_billing_period(sess)
        await seed_replay(sess, prompt_run_ids)
        await seed_tools(sess)
        await seed_ledger_snapshot(sess)
        await seed_usage_daily(sess)
        await sess.commit()

    await engine.dispose()
    print(f"\n{'─'*60}\nAll done ✓")


if __name__ == "__main__":
    asyncio.run(main())
