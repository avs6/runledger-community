"""
Semantic Cache service (PDF gap #1).

Qdrant-backed nearest-neighbour cache over request embeddings, with a MANDATORY scope key
so a cache hit can never cross a tenant / model / knowledge-version / security boundary
(the leakage warning called out in the gap analysis).

Scope key = {tenant, model, system_prompt_hash, knowledge_version, security_scope}
All scope fields are matched EXACTLY as a Qdrant filter; only vectors within the same scope
are eligible for a similarity hit.

Endpoints
---------
GET  /health
POST /lookup {text, scope, threshold?}                         → {hit, score, payload}
POST /store  {text, scope, response, prompt_tokens, ...}       → {stored, id}

Embeddings come from the shared embedding-svc (single model of record); this service never
embeds locally.
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

QDRANT_URL = os.getenv("QDRANT_URL", "http://runledger-qdrant:6333")
EMBEDDING_SVC_URL = os.getenv("EMBEDDING_SVC_URL", "http://runledger-embedding-svc:8100")
COLLECTION = os.getenv("SEMANTIC_CACHE_COLLECTION", "semantic_cache")
DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
DEFAULT_TTL_SECONDS = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", str(24 * 3600)))
VECTOR_DIM = int(os.getenv("EMBEDDING_DIM", "384"))  # bge-small-en-v1.5

app = FastAPI(title="RunLedger Semantic Cache", version="0.1.0")
_client = QdrantClient(url=QDRANT_URL)

# Scope fields that must all match for a hit to be valid.
_SCOPE_FIELDS = ("tenant", "model", "system_prompt_hash", "knowledge_version", "security_scope")


def _ensure_collection() -> None:
    existing = {c.name for c in _client.get_collections().collections}
    if COLLECTION not in existing:
        _client.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=VECTOR_DIM, distance=qm.Distance.COSINE),
        )


@app.on_event("startup")
def _startup() -> None:
    _ensure_collection()


async def _embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.post(f"{EMBEDDING_SVC_URL}/embed", json={"texts": [text]})
        resp.raise_for_status()
        return resp.json()["embeddings"][0]


class Scope(BaseModel):
    tenant: str
    model: str
    system_prompt_hash: str = ""
    knowledge_version: str = ""
    security_scope: str = ""


def _scope_filter(scope: Scope) -> qm.Filter:
    now = int(time.time())
    must: list[qm.FieldCondition] = [
        qm.FieldCondition(key=f, match=qm.MatchValue(value=getattr(scope, f)))
        for f in _SCOPE_FIELDS
    ]
    # Not-yet-expired: expires_at is a stored epoch; keep entries with expires_at > now.
    must.append(qm.FieldCondition(key="expires_at", range=qm.Range(gt=now)))
    return qm.Filter(must=must)


class LookupRequest(BaseModel):
    text: str
    scope: Scope
    threshold: float | None = None


class LookupResponse(BaseModel):
    hit: bool
    score: float | None = None
    payload: dict | None = None


class StoreRequest(BaseModel):
    text: str
    scope: Scope
    response: dict
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    ttl_seconds: int | None = None


class StoreResponse(BaseModel):
    stored: bool
    id: str


@app.get("/health")
def health() -> dict[str, object]:
    ok = True
    try:
        _client.get_collections()
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "collection": COLLECTION}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/lookup", response_model=LookupResponse)
async def lookup(req: LookupRequest) -> LookupResponse:
    threshold = req.threshold if req.threshold is not None else DEFAULT_THRESHOLD
    vector = await _embed(req.text)
    result = _client.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=_scope_filter(req.scope),
        limit=1,
        score_threshold=threshold,
        with_payload=True,
    )
    hits = result.points
    if not hits:
        return LookupResponse(hit=False)
    top = hits[0]
    return LookupResponse(hit=True, score=top.score, payload=(top.payload or {}).get("response"))


@app.post("/store", response_model=StoreResponse)
async def store(req: StoreRequest) -> StoreResponse:
    vector = await _embed(req.text)
    ttl = req.ttl_seconds if req.ttl_seconds is not None else DEFAULT_TTL_SECONDS
    point_id = str(uuid.uuid4())
    payload = {
        **{f: getattr(req.scope, f) for f in _SCOPE_FIELDS},
        "response": req.response,
        "prompt_tokens": req.prompt_tokens,
        "completion_tokens": req.completion_tokens,
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + ttl,
    }
    _client.upsert(
        collection_name=COLLECTION,
        points=[qm.PointStruct(id=point_id, vector=vector, payload=payload)],
    )
    return StoreResponse(stored=True, id=point_id)
