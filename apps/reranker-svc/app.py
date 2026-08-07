"""
Reranker service (Phase 2).

Cross-encoder reranking on CPU via fastembed's ONNX TextCrossEncoder — the same ONNX stack
as embedding-svc, no torch. Loads multiple backends and picks per request so the Context
Compiler (and the dashboard) can choose a model per route.

Model aliases (GUI-friendly → fastembed model name):
  flashrank | minilm  → Xenova/ms-marco-MiniLM-L-6-v2   (fast, default)
  bge-reranker-base   → BAAI/bge-reranker-base           (higher quality)
  jina-tiny           → jinaai/jina-reranker-v1-tiny-en  (tiny)

Endpoints
---------
GET  /health
POST /rerank { query, passages: [str], model?, top_k? }
     → { model, results: [{ index, score }] }   # sorted by score desc
"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI
from fastembed.rerank.cross_encoder import TextCrossEncoder
from pydantic import BaseModel, Field

# GUI/config alias → actual fastembed model name.
MODEL_ALIASES = {
    "flashrank": "Xenova/ms-marco-MiniLM-L-6-v2",
    "minilm": "Xenova/ms-marco-MiniLM-L-6-v2",
    "minilm-l12": "Xenova/ms-marco-MiniLM-L-12-v2",
    "bge-reranker-base": "BAAI/bge-reranker-base",
    "jina-tiny": "jinaai/jina-reranker-v1-tiny-en",
}
DEFAULT_MODEL = os.getenv("RERANKER_MODEL", "flashrank")

app = FastAPI(title="RunLedger Reranker Service", version="0.1.0")


def _resolve(model: str | None) -> str:
    name = (model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(name, name)  # allow a full fastembed name too


@lru_cache(maxsize=4)
def _encoder(model_name: str) -> TextCrossEncoder:
    # Lazily loaded + cached per model for the process lifetime.
    return TextCrossEncoder(model_name=model_name)


class RerankRequest(BaseModel):
    query: str
    passages: list[str] = Field(..., min_length=1)
    model: str | None = None
    top_k: int | None = None


class RerankResult(BaseModel):
    index: int
    score: float


class RerankResponse(BaseModel):
    model: str
    results: list[RerankResult]


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "default_model": DEFAULT_MODEL, "aliases": list(MODEL_ALIASES)}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest) -> RerankResponse:
    model_name = _resolve(req.model)
    scores = list(_encoder(model_name).rerank(req.query, req.passages))
    ranked = sorted(
        (RerankResult(index=i, score=float(s)) for i, s in enumerate(scores)),
        key=lambda r: r.score,
        reverse=True,
    )
    if req.top_k is not None:
        ranked = ranked[: req.top_k]
    return RerankResponse(model=model_name, results=ranked)
