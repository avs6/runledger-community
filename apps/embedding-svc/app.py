"""
Embedding service — the single embedding model of record for the optimization layer.

CPU-only (fastembed / ONNX). Every vector surface (semantic cache, episode store, RAG)
embeds through this one service so vectors stay comparable across the system.

Endpoints
---------
GET  /health          → {"status": "ok", "model": ..., "dim": ...}
POST /embed           → {"model", "dim", "embeddings": [[float, ...], ...]}
"""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastembed import TextEmbedding
from pydantic import BaseModel, Field

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

app = FastAPI(title="RunLedger Embedding Service", version="0.1.0")


# ── Internal access control ──────────────────────────────────────────────────
# Only RunLedger components may call this service: every request except the
# /health probes must carry X-Internal-Token == INTERNAL_SERVICE_TOKEN. Callers pass
# workspace ids they have already authorized, so this service must never be
# reachable by end users directly. With no token configured the service refuses
# all non-health traffic rather than running open.
_INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")


@app.middleware("http")
async def _require_internal_token(request: Request, call_next: Any) -> Any:
    if request.url.path.startswith("/health"):
        return await call_next(request)
    if not _INTERNAL_TOKEN:
        return JSONResponse({"detail": "INTERNAL_SERVICE_TOKEN is not configured"}, status_code=503)
    supplied = request.headers.get("x-internal-token", "")
    if not hmac.compare_digest(supplied.encode(), _INTERNAL_TOKEN.encode()):
        return JSONResponse({"detail": "Internal service token required"}, status_code=401)
    return await call_next(request)


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # Loaded lazily on first request; cached for the process lifetime.
    return TextEmbedding(model_name=EMBEDDING_MODEL)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    model: str | None = None  # reserved; only EMBEDDING_MODEL is served today


class EmbedResponse(BaseModel):
    model: str
    dim: int
    embeddings: list[list[float]]


@app.get("/health")
def health() -> dict[str, object]:
    # Report dim without forcing a model load unless already loaded.
    return {"status": "ok", "model": EMBEDDING_MODEL}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vectors = [v.tolist() for v in _model().embed(req.texts)]
    dim = len(vectors[0]) if vectors else 0
    return EmbedResponse(model=EMBEDDING_MODEL, dim=dim, embeddings=vectors)
