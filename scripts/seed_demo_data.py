"""
Seed script — populates realistic demo data for the RunLedger dashboard.

Inserts:
  - Ollama + OpenAI + Anthropic pricing rows
  - 3 extra applications
  - 60 agent runs spanning the last 30 days (mix of models, statuses, users)
  - provider_calls + spans for each run
  - 5 prompts with 2-3 versions each
  - score_events (quality, relevance, latency_ok) tied to runs
  - usage_daily rollup so analytics charts show data

Run from repo root:
    cd apps/api && uv run python ../../scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import random
import sys
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../apps/api"))

from sqlalchemy import select, text
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

# ── Workspace to seed into ────────────────────────────────────────────────────
WORKSPACE_ID = uuid.UUID("313fbd0f-4515-4baf-ae6d-3ac980971433")

# ── Applications ──────────────────────────────────────────────────────────────
APPS = [
    "Customer Support Bot",
    "Code Review Agent",
    "Document Summariser",
    "Data Extractor",
]

# ── End-users ─────────────────────────────────────────────────────────────────
USERS = [
    "alice@acme.com", "bob@acme.com", "carol@acme.com",
    "dave@acme.com",  "eve@acme.com", "frank@acme.com",
]

# ── Pricing: provider → model → (input_per_1m, output_per_1m) ─────────────────
PRICING: list[tuple[str, str, str, str]] = [
    # Ollama (local — $0 cost, but track tokens + latency)
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
PROMPTS_SEED = [
    {
        "name": "customer-support-classifier",
        "description": "Classifies incoming support tickets by priority and category.",
        "versions": [
            {
                "content": "You are a customer support classifier. Given a ticket, output JSON with: priority (low/medium/high/critical), category (billing/technical/general), summary.",
                "commit_message": "Initial classifier prompt",
                "model_hint": "gpt-4o-mini",
                "variables": {},
            },
            {
                "content": "You are an expert customer support classifier. Given a ticket, output JSON with: priority (low/medium/high/critical), category (billing/technical/account/general), sentiment (positive/neutral/negative), summary. Be concise.",
                "commit_message": "Add sentiment field and account category",
                "model_hint": "gpt-4o-mini",
                "variables": {},
            },
        ],
    },
    {
        "name": "code-review-agent",
        "description": "Reviews code diffs and produces structured feedback.",
        "versions": [
            {
                "content": "You are a senior software engineer. Review the diff and list: bugs, style issues, and suggestions. Be direct.",
                "commit_message": "Initial code review prompt",
                "model_hint": "gpt-4o",
                "variables": {},
            },
            {
                "content": "You are a senior software engineer. Return JSON: { bugs: [...], style_issues: [...], suggestions: [...], overall_score: 1-10 }.",
                "commit_message": "Switch to JSON output",
                "model_hint": "gpt-4o",
                "variables": {"language": "python"},
            },
            {
                "content": "You are a senior {{language}} engineer. Return JSON: { bugs, style_issues, suggestions, security_issues, overall_score: 1-10 }.",
                "commit_message": "Add security_issues, language variable",
                "model_hint": "claude-3-5-sonnet-20241022",
                "variables": {"language": "python"},
            },
        ],
    },
    {
        "name": "document-summariser",
        "description": "Summarises long documents into structured briefs.",
        "versions": [
            {
                "content": "Summarise the following document in 3-5 bullet points. Be concise and factual.\n\n{{document}}",
                "commit_message": "Initial summariser",
                "model_hint": "llama3.2",
                "variables": {"document": ""},
            },
            {
                "content": "Summarise the following {{doc_type}} in {{num_bullets}} bullet points. Highlight decisions, action items, and risks.\n\n{{document}}",
                "commit_message": "Parameterise doc_type and bullet count",
                "model_hint": "mistral",
                "variables": {"doc_type": "document", "num_bullets": "5", "document": ""},
            },
        ],
    },
    {
        "name": "qa-evaluator",
        "description": "Evaluates Q&A pairs for accuracy and completeness.",
        "versions": [
            {
                "content": "Score the answer 0-1 on accuracy, completeness, and relevance. Output JSON: { accuracy, completeness, relevance, overall }.",
                "commit_message": "Initial QA evaluator",
                "model_hint": "gpt-4o-mini",
                "variables": {},
            },
        ],
    },
    {
        "name": "data-extractor",
        "description": "Extracts structured fields from unstructured text.",
        "versions": [
            {
                "content": "Extract {{fields}} from the text. Return as JSON. If a field is not found, return null.",
                "commit_message": "Generic extractor with variable fields",
                "model_hint": "qwen2.5",
                "variables": {"fields": "name, date, amount, currency"},
            },
            {
                "content": "Extract {{fields}} from the text. Return JSON with confidence: { field: { value, confidence: 0.0-1.0 } }.",
                "commit_message": "Add per-field confidence scores",
                "model_hint": "qwen2.5",
                "variables": {"fields": "name, date, amount, currency"},
            },
        ],
    },
]

# ── Model pool for runs (provider, model, weight) ─────────────────────────────
MODEL_POOL = [
    ("ollama",    "llama3.2",                    0.25),
    ("ollama",    "mistral",                     0.18),
    ("ollama",    "qwen2.5",                     0.08),
    ("ollama",    "gemma2",                      0.04),
    ("openai",    "gpt-4o-mini",                 0.22),
    ("openai",    "gpt-4o",                      0.12),
    ("anthropic", "claude-3-5-sonnet-20241022",  0.08),
    ("anthropic", "claude-3-haiku-20240307",     0.03),
]

FEATURES = ["chat", "summarise", "code-review", "qa", "classify", "extract"]
VERSIONS = ["v1.0", "v1.1", "v2.0", "v2.1"]

rng = random.Random(42)


# ── Helpers ───────────────────────────────────────────────────────────────────

def rand_dt(days_ago_max: int = 30, days_ago_min: int = 0) -> datetime:
    offset = timedelta(
        days=rng.randint(days_ago_min, days_ago_max),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
        seconds=rng.randint(0, 59),
    )
    return datetime.now(UTC) - offset


def rand_tokens(feature: str) -> tuple[int, int]:
    if feature in ("code-review", "extract"):
        return rng.randint(800, 3000), rng.randint(200, 800)
    if feature in ("summarise",):
        return rng.randint(2000, 8000), rng.randint(100, 400)
    return rng.randint(200, 1500), rng.randint(50, 500)


def calc_cost(provider: str, model: str, in_tok: int, out_tok: int) -> Decimal:
    for p, m, inp, out in PRICING:
        if p == provider and m == model:
            return (
                Decimal(inp) * in_tok / 1_000_000
                + Decimal(out) * out_tok / 1_000_000
            )
    return Decimal("0")


# ── Seed steps ────────────────────────────────────────────────────────────────

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
    print(f"    +{added} pricing rows")


async def seed_applications(session: AsyncSession) -> dict[str, uuid.UUID]:
    print("  Applications...")
    result = await session.execute(
        select(Application).where(Application.workspace_id == WORKSPACE_ID)
    )
    existing = {a.name: a.id for a in result.scalars().all()}
    for name in APPS:
        if name in existing:
            continue
        app = Application(workspace_id=WORKSPACE_ID, name=name)
        session.add(app)
        await session.flush()
        existing[name] = app.id
        print(f"    + app: {name}")
    return existing


async def seed_prompts(session: AsyncSession) -> None:
    print("  Prompts + versions...")
    for p_def in PROMPTS_SEED:
        exists = await session.execute(
            select(Prompt).where(
                Prompt.workspace_id == WORKSPACE_ID,
                Prompt.name == p_def["name"],
            )
        )
        prompt = exists.scalar_one_or_none()
        if not prompt:
            prompt = Prompt(
                workspace_id=WORKSPACE_ID,
                name=p_def["name"],
                description=p_def["description"],
                default_environment="production",
            )
            session.add(prompt)
            await session.flush()
            print(f"    + prompt: {p_def['name']}")

        vres = await session.execute(
            select(PromptVersion).where(PromptVersion.prompt_id == prompt.id)
            .order_by(PromptVersion.version)
        )
        existing_count = len(list(vres.scalars().all()))

        for i, v_def in enumerate(p_def["versions"]):
            if i < existing_count:
                continue
            session.add(PromptVersion(
                prompt_id=prompt.id,
                version=i + 1,
                content=v_def["content"],
                variables=v_def["variables"],
                commit_message=v_def["commit_message"],
                environment="production",
                model_hint=v_def.get("model_hint"),
            ))
        await session.flush()


async def seed_runs(
    session: AsyncSession,
    app_ids: dict[str, uuid.UUID],
) -> None:
    print("  Agent runs + provider calls + scores (60 runs)...")

    providers = [p for p, _, _ in MODEL_POOL]
    models    = [m for _, m, _ in MODEL_POOL]
    weights   = [w for _, _, w in MODEL_POOL]
    app_names = list(app_ids.keys())

    for _ in range(60):
        idx      = rng.choices(range(len(providers)), weights=weights)[0]
        provider = providers[idx]
        model    = models[idx]

        app_name   = rng.choice(app_names)
        app_id     = app_ids[app_name]
        user       = rng.choice(USERS)
        feature    = rng.choice(FEATURES)
        version    = rng.choice(VERSIONS)
        session_id = f"sess-{rng.randint(1, 20):02d}"

        started  = rand_dt(30, 0)
        duration = rng.uniform(0.4, 18.0)
        ended    = started + timedelta(seconds=duration)

        in_tok, out_tok = rand_tokens(feature)
        cost = calc_cost(provider, model, in_tok, out_tok)

        status = rng.choices(
            [RunStatusEnum.succeeded, RunStatusEnum.failed, RunStatusEnum.running],
            weights=[0.80, 0.12, 0.08],
        )[0]
        if status == RunStatusEnum.running:
            ended = None

        run_id = uuid.uuid4()
        session.add(AgentRun(
            id=run_id,
            workspace_id=WORKSPACE_ID,
            application_id=app_id,
            end_user_id=user,
            session_id=session_id,
            feature_tag=feature,
            deployment_version=version,
            status=status,
            started_at=started,
            ended_at=ended,
            total_cost_usd=cost if ended else None,
            total_input_tokens=in_tok,
            total_output_tokens=out_tok,
        ))
        await session.flush()

        span_id = uuid.uuid4()
        session.add(Span(
            id=span_id,
            run_id=run_id,
            span_type=SpanTypeEnum.llm,
            name=f"{feature}-call",
            started_at=started,
            ended_at=ended,
            status=SpanStatusEnum.succeeded if status == RunStatusEnum.succeeded else SpanStatusEnum.failed,
            cost_usd=cost if ended else None,
        ))
        await session.flush()

        session.add(ProviderCall(
            run_id=run_id,
            span_id=span_id,
            workspace_id=WORKSPACE_ID,
            provider=provider,
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=int(duration * 1000),
            cost_usd=cost if ended else None,
            status="success" if status == RunStatusEnum.succeeded else "error",
            created_at=started,
        ))
        await session.flush()

        # Score events for successful runs
        if status == RunStatusEnum.succeeded and rng.random() < 0.75:
            for score_name, lo, hi in [
                ("quality",    0.50, 1.00),
                ("relevance",  0.60, 1.00),
                ("latency_ok", 0.00, 1.00),
            ]:
                if rng.random() < 0.65:
                    session.add(ScoreEvent(
                        workspace_id=WORKSPACE_ID,
                        run_id=run_id,
                        session_id=session_id,
                        end_user_id=user,
                        name=score_name,
                        value=Decimal(str(round(rng.uniform(lo, hi), 3))),
                        source="auto-eval",
                        confidence=Decimal(str(round(rng.uniform(0.70, 1.00), 2))),
                        created_at=ended,
                    ))
            await session.flush()

    print("    done.")


async def seed_usage_daily(session: AsyncSession) -> None:
    """Aggregate provider_calls → usage_daily so analytics charts have data."""
    print("  Rolling up usage_daily...")
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
    print(f"RunLedger demo seed → workspace {WORKSPACE_ID}\n")
    engine  = create_async_engine(settings.database_url, poolclass=NullPool, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as sess:
        await seed_pricing(sess)
        app_ids = await seed_applications(sess)
        await seed_prompts(sess)
        await seed_runs(sess, app_ids)
        await seed_usage_daily(sess)
        await sess.commit()

    await engine.dispose()
    print("\nAll done ✓")


if __name__ == "__main__":
    asyncio.run(main())
