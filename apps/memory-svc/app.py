"""
Memory service (Phase 5) — a scoped wrapper over Letta (MemGPT).

Presents a clean, workspace-scoped store/recall API for typed memories (fact / preference /
decision / episode) and hides Letta's agent model: each workspace maps to a Letta agent
(`ws-<workspace_id>`), memories are stored as archival-memory passages, and recall is an archival
search. Letta runs against its own dedicated Postgres+pgvector DB (runledger-memory-db) and uses the
host Ollama for its LLM + embeddings.

Fail-open: if Letta is unavailable, store/recall degrade to empty results rather than erroring, so the
Context Compiler and MCP clients never break.

Endpoints
---------
GET  /health
POST /memory  { workspace, kind, text, metadata? }        (store)
POST /recall  { workspace, query, kind?, k? }             (semantic recall)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://runledger-letta:8283").rstrip("/")
# Fully local by default: an Ollama chat model for the (barely-used) agent LLM, and a local Ollama
# embedding model for archival memory. All configurable — point EMBEDDING_MODEL at any local text
# embedding model you have pulled (e.g. nomic-embed-text). Set LETTA_MODEL=letta/letta-free to use
# Letta's hosted inference instead.
LETTA_MODEL = os.getenv("LETTA_MODEL", "ollama/llama3.1:8b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
OLLAMA_EMBED_ENDPOINT = os.getenv("OLLAMA_EMBED_ENDPOINT", "http://host.docker.internal:11434/v1").rstrip("/")
TIMEOUT = float(os.getenv("MEMORY_TIMEOUT_SECONDS", "30"))

app = FastAPI(title="RunLedger Memory Service", version="0.1.0")

# workspace_id → letta agent_id (process cache)
_agents: dict[str, str] = {}


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}


async def _get_or_create_agent(client: httpx.AsyncClient, workspace: str) -> str | None:
    if workspace in _agents:
        return _agents[workspace]
    name = f"ws-{workspace}"
    try:
        r = await client.get(f"{LETTA_BASE_URL}/v1/agents/", params={"name": name})
        if r.status_code == 200 and r.json():
            aid = r.json()[0]["id"]
            _agents[workspace] = aid
            return aid
    except Exception as exc:  # noqa: BLE001
        log.warning("letta_list_agents_failed error=%s", str(exc))
    try:
        payload = {
            "name": name,
            "model": LETTA_MODEL,
            # Explicit local embedding config — Letta's auto-discovery skips embedding-only
            # Ollama models, so we register the one we want directly.
            "embedding_config": {
                "embedding_endpoint_type": "ollama",
                "embedding_endpoint": OLLAMA_EMBED_ENDPOINT,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dim": EMBEDDING_DIM,
                "embedding_chunk_size": 300,
            },
            "memory_blocks": [
                {"label": "persona", "value": "I am a scoped memory store for one workspace."},
                {"label": "human", "value": ""},
            ],
        }
        r = await client.post(f"{LETTA_BASE_URL}/v1/agents/", json=payload, headers=_headers())
        r.raise_for_status()
        aid = r.json()["id"]
        _agents[workspace] = aid
        return aid
    except Exception as exc:  # noqa: BLE001
        log.warning("letta_create_agent_failed error=%s", str(exc))
        return None


class StoreRequest(BaseModel):
    workspace: str
    kind: str = "fact"  # fact | preference | decision | episode
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecallRequest(BaseModel):
    workspace: str
    query: str
    kind: str | None = None
    k: int = 5


@app.get("/health")
async def health() -> dict[str, object]:
    reachable = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{LETTA_BASE_URL}/v1/health/")
            reachable = r.status_code < 500
    except Exception:
        reachable = False
    return {"status": "ok", "letta_reachable": reachable, "letta": LETTA_BASE_URL}


@app.post("/memory")
async def store(req: StoreRequest) -> dict[str, object]:
    # Encode kind + metadata into the passage so recall can surface/filter it.
    passage = json.dumps({"kind": req.kind, "metadata": req.metadata}) + "\n" + req.text
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        agent_id = await _get_or_create_agent(client, req.workspace)
        if not agent_id:
            return {"stored": False, "reason": "letta_unavailable"}
        try:
            r = await client.post(
                f"{LETTA_BASE_URL}/v1/agents/{agent_id}/archival-memory/",
                json={"text": passage},
                headers=_headers(),
            )
            r.raise_for_status()
            return {"stored": True, "kind": req.kind}
        except Exception as exc:  # noqa: BLE001 — fail-open
            log.warning("memory_store_failed error=%s", str(exc))
            return {"stored": False, "reason": str(exc)[:120]}


@app.post("/recall")
async def recall(req: RecallRequest) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        agent_id = _agents.get(req.workspace) or await _get_or_create_agent(client, req.workspace)
        if not agent_id:
            return {"memories": []}
        try:
            r = await client.get(
                f"{LETTA_BASE_URL}/v1/agents/{agent_id}/archival-memory/",
                params={"search": req.query, "limit": req.k},
            )
            r.raise_for_status()
            items = r.json() if isinstance(r.json(), list) else r.json().get("passages", [])
            # Letta's archival search threshold can be strict on long queries — fall back to
            # the most recent passages so recall still surfaces relevant memory.
            if not items:
                r2 = await client.get(
                    f"{LETTA_BASE_URL}/v1/agents/{agent_id}/archival-memory/",
                    params={"limit": req.k},
                )
                items = r2.json() if isinstance(r2.json(), list) else []
        except Exception as exc:  # noqa: BLE001 — fail-open
            log.warning("memory_recall_failed error=%s", str(exc))
            return {"memories": []}
    memories = []
    for it in items[: req.k]:
        text = it.get("text", "") if isinstance(it, dict) else str(it)
        kind, body = _split_passage(text)
        if req.kind and kind != req.kind:
            continue
        memories.append({"kind": kind, "text": body})
    return {"memories": memories}


def _split_passage(text: str) -> tuple[str, str]:
    if "\n" in text:
        head, body = text.split("\n", 1)
        try:
            meta = json.loads(head)
            return meta.get("kind", "fact"), body
        except Exception:  # noqa: BLE001
            pass
    return "fact", text
