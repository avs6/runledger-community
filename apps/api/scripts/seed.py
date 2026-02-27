"""
Seed script — creates a default tenant, workspace, application, and API key
for local development. Safe to run multiple times (idempotent).

Usage:
    cd apps/api && uv run python scripts/seed.py
"""

from __future__ import annotations

import asyncio

from runledger_api.core.db import AsyncSessionLocal
from runledger_api.models.tenant import (
    ApiKey,
    Application,
    EnvironmentEnum,
    PlanEnum,
    Tenant,
    Workspace,
)
from runledger_api.services.auth import generate_api_key
from sqlalchemy import select


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Idempotency check
        existing = await session.execute(select(Tenant).where(Tenant.slug == "default"))
        if existing.scalar_one_or_none() is not None:
            print("Seed data already exists — skipping.")
            return

        # Tenant
        tenant = Tenant(slug="default", name="Default Org", plan=PlanEnum.free)
        session.add(tenant)
        await session.flush()

        # Workspace
        workspace = Workspace(tenant_id=tenant.id, name="default")
        session.add(workspace)
        await session.flush()

        # Application
        application = Application(
            workspace_id=workspace.id,
            name="default",
            environment=EnvironmentEnum.dev,
        )
        session.add(application)
        await session.flush()

        # API Key
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


if __name__ == "__main__":
    asyncio.run(seed())
