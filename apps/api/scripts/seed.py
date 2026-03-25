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
    TenantRoleEnum,
    TenantUser,
    User,
    Workspace,
    WorkspaceRoleEnum,
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
    # ── Google Gemini ─────────────────────────────────────────────────────────
    ("google", "gemini-2.5-pro", "1.25", "10.00", None),
    ("google", "gemini-2.0-flash", "0.075", "0.30", None),
    ("google", "gemini-2.0-flash-lite", "0.019", "0.075", None),
    ("google", "gemini-1.5-pro", "1.25", "5.00", None),
    ("google", "gemini-1.5-flash", "0.075", "0.30", None),
    ("google", "gemini-1.5-flash-8b", "0.019", "0.075", None),
    # ── xAI (Grok) ───────────────────────────────────────────────────────────
    ("xai", "grok-3-latest", "3.00", "15.00", None),
    ("xai", "grok-3-mini-latest", "0.30", "0.50", None),
    ("xai", "grok-2-latest", "2.00", "10.00", "1.00"),
    ("xai", "grok-2-vision-1212", "2.00", "10.00", "1.00"),
    ("xai", "grok-beta", "5.00", "15.00", None),
    # ── Mistral ───────────────────────────────────────────────────────────────
    ("mistral", "mistral-large-latest", "2.00", "6.00", None),
    ("mistral", "mistral-medium-latest", "0.40", "2.00", None),
    ("mistral", "mistral-small-latest", "0.20", "0.60", None),
    ("mistral", "open-mistral-nemo", "0.15", "0.15", None),
    ("mistral", "codestral-latest", "0.20", "0.60", None),
    ("mistral", "mistral-embed", "0.10", "0.00", None),
    # ── Cohere ────────────────────────────────────────────────────────────────
    ("cohere", "command-r-plus", "2.50", "10.00", None),
    ("cohere", "command-r-plus-08-2024", "2.50", "10.00", None),
    ("cohere", "command-r", "0.15", "0.60", None),
    ("cohere", "command-r-08-2024", "0.15", "0.60", None),
    ("cohere", "command-light", "0.30", "0.60", None),
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

    tenant = Tenant(slug="default", name="Default Org", plan=PlanEnum.free, is_default=True)
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
    existing_user = existing.scalar_one_or_none()
    if existing_user is not None:
        # Ensure the seed user is always verified — no email confirmation needed
        if not existing_user.email_verified:
            existing_user.email_verified = True
            await session.commit()
            print("Seed user email_verified fixed.")
        else:
            print("Default user already exists — skipping.")
        return

    user = User(
        email=_DEFAULT_EMAIL,
        password_hash=bcrypt.hashpw(_DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode(),
        full_name="Platform Admin",
        is_active=True,
        is_platform_admin=True,
        email_verified=True,
    )
    session.add(user)
    await session.flush()

    # Link user as org admin on the default tenant
    tenant_result = await session.execute(select(Tenant).where(Tenant.is_default == True))  # noqa: E712
    default_tenant = tenant_result.scalar_one_or_none()
    if default_tenant is not None:
        default_tenant.owner_user_id = user.id
        session.add(
            TenantUser(tenant_id=default_tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin)
        )

    session.add(
        WorkspaceUser(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRoleEnum.workspace_admin,
        )
    )
    await session.commit()

    print("\nDashboard login (Platform Admin):")
    print(f"  Email:    {_DEFAULT_EMAIL}")
    print(f"  Password: {_DEFAULT_PASSWORD}")
    print("  URL:      http://localhost:3000")
    print("  Role:     Platform Admin (can create orgs via Sidebar → Platform Admin → Tenants)")


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
