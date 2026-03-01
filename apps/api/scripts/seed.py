"""
Seed script — creates a default tenant, workspace, application, API key,
and provider pricing data for local development.

Safe to run multiple times (idempotent).

Usage:
    cd apps/api && uv run python scripts/seed.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import bcrypt
from runledger_api.core.db import AsyncSessionLocal
from runledger_api.models.metering import ProviderPricing
from runledger_api.models.tenant import (
    ApiKey,
    Application,
    EnvironmentEnum,
    PlanEnum,
    Tenant,
    User,
    Workspace,
    WorkspaceUser,
)
from runledger_api.services.auth import generate_api_key
from sqlalchemy import select

# Effective from 2025-01-01 UTC — update as providers change pricing
_PRICING_EFFECTIVE_FROM = datetime(2025, 1, 1, tzinfo=UTC)

# (provider, model, input_per_1m, output_per_1m, cached_input_per_1m)
_PRICING_DATA: list[tuple[str, str, str, str, str | None]] = [
    # ── OpenAI ────────────────────────────────────────────────────────────────
    ("openai", "gpt-4o", "2.50", "10.00", "1.25"),
    ("openai", "gpt-4o-mini", "0.15", "0.60", "0.075"),
    ("openai", "gpt-4-turbo", "10.00", "30.00", "5.00"),
    ("openai", "gpt-3.5-turbo", "0.50", "1.50", None),
    ("openai", "o1", "15.00", "60.00", "7.50"),
    ("openai", "o3-mini", "1.10", "4.40", "0.55"),
    # ── Anthropic ─────────────────────────────────────────────────────────────
    ("anthropic", "claude-opus-4-6", "15.00", "75.00", None),
    ("anthropic", "claude-sonnet-4-6", "3.00", "15.00", None),
    ("anthropic", "claude-haiku-4-5", "0.80", "4.00", None),
    # ── Google ────────────────────────────────────────────────────────────────
    ("google", "gemini-1.5-pro", "1.25", "5.00", None),
    ("google", "gemini-1.5-flash", "0.075", "0.30", None),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        await _seed_tenant(session)
        await _seed_pricing(session)
        # Always look up the workspace so _seed_user runs even on re-runs
        result = await session.execute(select(Workspace).where(Workspace.name == "default"))
        workspace = result.scalar_one_or_none()
        if workspace:
            await _seed_user(session, workspace)


async def _seed_tenant(session: object) -> Workspace | None:
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)

    existing = await session.execute(select(Tenant).where(Tenant.slug == "default"))
    if existing.scalar_one_or_none() is not None:
        print("Tenant seed data already exists — skipping.")
        return None

    tenant = Tenant(slug="default", name="Default Org", plan=PlanEnum.free)
    session.add(tenant)
    await session.flush()

    workspace = Workspace(tenant_id=tenant.id, name="default")
    session.add(workspace)
    await session.flush()

    application = Application(
        workspace_id=workspace.id,
        name="default",
        environment=EnvironmentEnum.dev,
    )
    session.add(application)
    await session.flush()

    raw_key, key_hash, key_prefix = generate_api_key(EnvironmentEnum.dev)
    api_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name="dev-key",
        scopes=[],
    )
    session.add(api_key)
    await session.commit()

    print(f"Tenant:    {tenant.slug}  ({tenant.id})")
    print(f"Workspace: {workspace.name}  ({workspace.id})")
    print(f"API Key:   {raw_key}")
    print("\nSave the API key — it won't be shown again.")
    return workspace


async def _seed_user(session: object, workspace: Workspace) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)

    _DEFAULT_EMAIL = "admin@runledger.local"
    _DEFAULT_PASSWORD = "runledger"

    existing = await session.execute(select(User).where(User.email == _DEFAULT_EMAIL))
    if existing.scalar_one_or_none() is not None:
        print("Default user already exists — skipping.")
        return

    user = User(
        email=_DEFAULT_EMAIL,
        password_hash=bcrypt.hashpw(_DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode(),
    )
    session.add(user)
    await session.flush()

    workspace_user = WorkspaceUser(
        workspace_id=workspace.id,
        user_id=user.id,
        role="admin",
    )
    session.add(workspace_user)
    await session.commit()

    print("\nDashboard login:")
    print(f"  Email:    {_DEFAULT_EMAIL}")
    print(f"  Password: {_DEFAULT_PASSWORD}")
    print("  URL:      http://localhost:3000")


async def _seed_pricing(session: object) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    assert isinstance(session, AsyncSession)

    # Check if pricing data already exists
    existing = await session.execute(
        select(ProviderPricing).where(
            ProviderPricing.provider == "openai",
            ProviderPricing.model == "gpt-4o",
            ProviderPricing.workspace_id.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        print("Provider pricing already seeded — skipping.")
        return

    for provider, model, in_rate, out_rate, cached_rate in _PRICING_DATA:
        session.add(
            ProviderPricing(
                provider=provider,
                model=model,
                input_cost_per_1m=Decimal(in_rate),
                output_cost_per_1m=Decimal(out_rate),
                cached_input_cost_per_1m=Decimal(cached_rate) if cached_rate else None,
                effective_from=_PRICING_EFFECTIVE_FROM,
                workspace_id=None,
            )
        )

    await session.commit()
    print(f"Seeded {len(_PRICING_DATA)} provider pricing rows.")


if __name__ == "__main__":
    asyncio.run(seed())
