"""
Real vector search against Qdrant for the Vector Stores page (review B-19).

Search-test embeds the query with the in-cluster embedding service and searches
the collection in Qdrant. Collection counters come from Qdrant itself
(``sync_collection``), not from request counting. When either service is not
reachable the caller gets an explicit error instead of an empty "success".

Embeddings are self-hosted (embedding-svc), so a query has no per-call provider
cost; ``embed_cost`` and ``query_cost`` stay 0 and the UI says so.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from runledger_api.core.config import settings


class VectorSearchUnavailable(RuntimeError):
    """Qdrant or the embedding service could not be reached or refused the call."""


def qdrant_url() -> str:
    return os.environ.get("QDRANT_URL", "http://localhost:6333").rstrip("/")


def embedding_url() -> str:
    return os.environ.get("EMBEDDING_SVC_URL", "http://localhost:8100").rstrip("/")


def _qdrant_headers() -> dict[str, str]:
    key = os.environ.get("QDRANT_API_KEY")
    return {"api-key": key} if key else {}


async def embed(text: str, client: httpx.AsyncClient) -> list[float]:
    try:
        resp = await client.post(
            f"{embedding_url()}/embed",
            json={"texts": [text]},
            headers=settings.internal_service_headers,
        )
    except httpx.HTTPError as exc:
        raise VectorSearchUnavailable(
            f"Embedding service unreachable at {embedding_url()}: {exc.__class__.__name__}"
        ) from exc
    if resp.status_code >= 400:
        raise VectorSearchUnavailable(f"Embedding service returned {resp.status_code}")
    vectors = resp.json().get("embeddings") or []
    if not vectors:
        raise VectorSearchUnavailable("Embedding service returned no vector")
    return [float(x) for x in vectors[0]]


async def search(
    collection: str,
    text: str,
    *,
    top_k: int,
    threshold: float | None,
    client: httpx.AsyncClient | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Embed ``text`` and search ``collection``; returns (hits, latency_ms)."""
    own = client is None
    http = client or httpx.AsyncClient(timeout=15.0)
    started = time.monotonic()
    try:
        vector = await embed(text, http)
        body: dict[str, Any] = {"vector": vector, "limit": top_k, "with_payload": True}
        if threshold is not None:
            body["score_threshold"] = threshold
        try:
            resp = await http.post(
                f"{qdrant_url()}/collections/{collection}/points/search",
                json=body,
                headers=_qdrant_headers(),
            )
        except httpx.HTTPError as exc:
            raise VectorSearchUnavailable(
                f"Qdrant unreachable at {qdrant_url()}: {exc.__class__.__name__}"
            ) from exc
        if resp.status_code == 404:
            raise VectorSearchUnavailable(f"Qdrant has no collection '{collection}'")
        if resp.status_code >= 400:
            raise VectorSearchUnavailable(f"Qdrant search returned {resp.status_code}")
        hits = [
            {
                "score": float(h.get("score") or 0),
                "payload": h.get("payload") or {},
                "id": h.get("id"),
            }
            for h in resp.json().get("result") or []
        ]
        return hits, int((time.monotonic() - started) * 1000)
    finally:
        if own:
            await http.aclose()


async def collection_info(
    collection: str, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Point count, vector size and status of a Qdrant collection."""
    own = client is None
    http = client or httpx.AsyncClient(timeout=10.0)
    try:
        try:
            resp = await http.get(
                f"{qdrant_url()}/collections/{collection}", headers=_qdrant_headers()
            )
        except httpx.HTTPError as exc:
            raise VectorSearchUnavailable(
                f"Qdrant unreachable at {qdrant_url()}: {exc.__class__.__name__}"
            ) from exc
        if resp.status_code == 404:
            raise VectorSearchUnavailable(f"Qdrant has no collection '{collection}'")
        if resp.status_code >= 400:
            raise VectorSearchUnavailable(f"Qdrant returned {resp.status_code}")
        result = resp.json().get("result") or {}
        vectors = (result.get("config") or {}).get("params", {}).get("vectors") or {}
        size = vectors.get("size") if isinstance(vectors, dict) else None
        distance = vectors.get("distance") if isinstance(vectors, dict) else None
        return {
            "points_count": int(result.get("points_count") or result.get("vectors_count") or 0),
            "dimensions": int(size) if size else None,
            "distance": str(distance).lower() if distance else None,
            "status": str(result.get("status") or "unknown"),
        }
    finally:
        if own:
            await http.aclose()
