"""
Seed the development database with a default tenant, workspace, and admin user.

Run with:
    cd apps/api && uv run python scripts/seed_dev.py

Or inside Docker:
    docker compose -f infra/docker-compose.yml exec api uv run python scripts/seed_dev.py
"""

from __future__ import annotations

import asyncio
import uuid

import bcrypt
from runledger_api.core.config import settings
from runledger_api.models.tenant import Tenant, User, Workspace, WorkspaceUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_EMAIL = "admin@runledger.local"
DEFAULT_PASSWORD = "runledger"
TENANT_SLUG = "runledger-dev"
TENANT_NAME = "RunLedger Dev"
WORKSPACE_NAME = "Default Workspace"


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]

    async with async_session() as session:
        # ── Tenant ────────────────────────────────────────────────────────────
        result = await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=uuid.uuid4(), slug=TENANT_SLUG, name=TENANT_NAME)
            session.add(tenant)
            await session.flush()
            print(f"Created tenant: {tenant.name} ({tenant.id})")
        else:
            print(f"Tenant already exists: {tenant.name} ({tenant.id})")

        # ── Workspace ─────────────────────────────────────────────────────────
        result = await session.execute(select(Workspace).where(Workspace.tenant_id == tenant.id))
        workspace = result.scalar_one_or_none()
        if workspace is None:
            workspace = Workspace(id=uuid.uuid4(), tenant_id=tenant.id, name=WORKSPACE_NAME)
            session.add(workspace)
            await session.flush()
            print(f"Created workspace: {workspace.name} ({workspace.id})")
        else:
            print(f"Workspace already exists: {workspace.name} ({workspace.id})")

        # ── User ──────────────────────────────────────────────────────────────
        result = await session.execute(select(User).where(User.email == DEFAULT_EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            pw_hash = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
            user = User(id=uuid.uuid4(), email=DEFAULT_EMAIL, password_hash=pw_hash)
            session.add(user)
            await session.flush()
            print(f"Created user: {user.email} ({user.id})")
        else:
            print(f"User already exists: {user.email} ({user.id})")

        # ── WorkspaceUser ─────────────────────────────────────────────────────
        result = await session.execute(
            select(WorkspaceUser).where(
                WorkspaceUser.user_id == user.id,
                WorkspaceUser.workspace_id == workspace.id,
            )
        )
        wu = result.scalar_one_or_none()
        if wu is None:
            wu = WorkspaceUser(
                id=uuid.uuid4(),
                workspace_id=workspace.id,
                user_id=user.id,
                role="admin",
            )
            session.add(wu)
            await session.flush()
            print("Linked user → workspace (role=admin)")
        else:
            print("WorkspaceUser link already exists")

        await session.commit()

    await engine.dispose()
    print()
    print("Seed complete.")
    print(f"  Email:    {DEFAULT_EMAIL}")
    print(f"  Password: {DEFAULT_PASSWORD}")
    print(f"  Workspace ID: {workspace.id}")


if __name__ == "__main__":
    asyncio.run(seed())
