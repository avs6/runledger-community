"""
Cognitive consolidation worker (Phase 5).

Nightly job: for each recently-active workspace, recall recent episode memories from memory-svc,
distill them into durable facts/decisions via the local LLM, and store those back. This turns an
ever-growing pile of episodes into compact, reusable knowledge (like human memory consolidation).

Fail-open and best-effort: any error for a workspace is logged and skipped; the task never crashes
the worker. Scheduled via Celery beat (daily).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from runledger_api.core.celery_app import celery_app
from runledger_api.core.config import settings
from runledger_api.models.gateway import GatewayRequest

log = logging.getLogger(__name__)

MEMORY_SVC_URL = os.getenv("MEMORY_SVC_URL", "http://runledger-memory-svc:8107").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1").rstrip("/")
LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")


async def _active_workspaces() -> list[str]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    since = datetime.now(UTC) - timedelta(days=1)
    async with factory() as db:
        rows = await db.execute(
            select(GatewayRequest.workspace_id).where(GatewayRequest.created_at >= since).distinct()
        )
        ids = [str(r[0]) for r in rows.all()]
    await engine.dispose()
    return ids


async def _distill(episodes: list[str]) -> str | None:
    prompt = (
        "From these completed-task episodes, extract up to 3 durable, reusable facts or decisions "
        "worth remembering. One per line, terse. No preamble."
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                f"{OLLAMA_BASE_URL}/chat/completions",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "\n---\n".join(episodes)[:12000]},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.1,
                    "stream": False,
                },
            )
            r.raise_for_status()
            content: str = r.json()["choices"][0]["message"]["content"]
            return content.strip()
    except Exception:
        return None


async def _consolidate() -> dict[str, int]:
    workspaces = 0
    facts = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for ws in await _active_workspaces():
            try:
                r = await client.post(
                    f"{MEMORY_SVC_URL}/recall",
                    json={
                        "workspace": ws,
                        "query": "recent completed tasks",
                        "kind": "episode",
                        "k": 20,
                    },
                )
                episodes = (
                    [m.get("text", "") for m in r.json().get("memories", [])]
                    if r.status_code == 200
                    else []
                )
            except Exception:
                episodes = []
            if len(episodes) < 2:
                continue
            workspaces += 1
            summary = await _distill(episodes)
            if not summary:
                continue
            for line in [ln.strip("-• ").strip() for ln in summary.splitlines() if ln.strip()]:
                try:
                    await client.post(
                        f"{MEMORY_SVC_URL}/memory",
                        json={
                            "workspace": ws,
                            "kind": "fact",
                            "text": line,
                            "metadata": {"source": "consolidation"},
                        },
                    )
                    facts += 1
                except Exception:
                    continue
    return {"workspaces": workspaces, "facts": facts}


@celery_app.task(name="cognitive.consolidate")  # type: ignore[untyped-decorator]
def consolidate() -> dict[str, int]:
    """Distil recent episodes into durable facts for each active workspace."""
    result = asyncio.run(_consolidate())
    log.info(
        "cognitive_consolidation workspaces=%s facts=%s", result["workspaces"], result["facts"]
    )
    return result
