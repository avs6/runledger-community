#!/usr/bin/env python3
"""Seed dedicated Gateway Routes without overriding cloud model aliases."""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path("apps/api").resolve()))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from runledger_api.core.config import settings
from runledger_api.models.gateway import GatewayRoute
from runledger_api.models.tenant import Workspace


async def main():
    raw_url = str(settings.database_url)
    db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://") if "asyncpg" not in raw_url else raw_url
    engine = create_async_engine(db_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Delete any SWE-1.6 Slow override routes
        await session.execute(delete(GatewayRoute).where(GatewayRoute.alias == "SWE-1.6 Slow"))
        await session.commit()

        # Dedicated separate local routes
        aliases = [
            ("ollama/qwen2.5-coder", "ollama", "qwen2.5-coder", "http://localhost:11434/v1", 10),
            ("qwen2.5-coder", "ollama", "qwen2.5-coder", "http://localhost:11434/v1", 10),
            ("devin/local-coder", "ollama", "qwen2.5-coder", "http://localhost:11434/v1", 10),
        ]

        workspaces = (await session.execute(select(Workspace))).scalars().all()
        for ws in workspaces:
            for alias, provider, target_model, base_url, priority in aliases:
                existing = (
                    await session.execute(
                        select(GatewayRoute).where(
                            GatewayRoute.workspace_id == ws.id,
                            GatewayRoute.alias == alias,
                        )
                    )
                ).scalar_one_or_none()
                if not existing:
                    session.add(
                        GatewayRoute(
                            workspace_id=ws.id,
                            alias=alias,
                            provider=provider,
                            target_model=target_model,
                            base_url=base_url,
                            priority=priority,
                            is_active=True,
                        )
                    )
        await session.commit()
        print("Updated Gateway routes: SWE-1.6 Slow alias removed, separate devin/local-coder added!")

if __name__ == "__main__":
    asyncio.run(main())
