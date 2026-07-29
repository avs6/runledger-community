"""
Scenario: a local RAG knowledge base — answers + embeddings, all on Ollama.

Mixes a chat model (llama3.1:8b) with an embedding model (nomic-embed-text), both
priced locally, so you can see embedding vs generation cost split out in analytics.
"""

from __future__ import annotations

import random

from scenarios._base import Sim

NAME = "ollama-local-rag"
DESCRIPTION = "Local RAG (llama3.1 + nomic-embed-text) — generation + embedding cost."

OLLAMA = "http://host.docker.internal:11434/v1"


def run(sim: Sim) -> None:
    ws = sim.workspace("DataCo", "Knowledge Base")

    ws.add_route("answer", "llama3.1:8b", priority=10, base_url=OLLAMA, semantic_cache_enabled=True)
    ws.add_route("embed", "nomic-embed-text", priority=10, base_url=OLLAMA)

    runs = ws.ingest_runs(
        160,
        # embeddings dominate volume; generation is the pricier per-call step
        models=["nomic-embed-text", "nomic-embed-text", "llama3.1:8b", "llama3.1:8b"],
        features=["doc-embed", "doc-qa", "summarize"],
        users=[f"team_{i}" for i in range(1, 8)],
        days=30,
        success_rate=0.95,
        sessions=25,
    )

    ws.add_budget("workspace", 120, period_type="monthly", action="notify")

    for r in ws.sample(runs, 30):
        if r.feature == "doc-qa" and r.success:
            ws.score(r, "relevance", round(random.uniform(0.65, 0.97), 2))
            ws.score(r, "faithfulness", round(random.uniform(0.7, 0.99), 2))
            if random.random() < 0.4:
                ws.record_outcome(r, "answer_helpful", success=True,
                                  labels={"source": "knowledge-base"})
