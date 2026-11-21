"""
Prompt compression service (Phase 3).

Wraps Microsoft LLMLingua-2 (MIT) — a small token-classifier that drops low-information tokens
to hit a target keep-rate while preserving task performance. CPU-only (no GPU) but, unlike the
rest of the optimization layer, it needs PyTorch + transformers, so it runs in its own opt-in
container. Lossy → the Context Compiler only calls it when explicitly enabled per route.

Model aliases (extensible — add more here / via env):
  bert-base-multilingual  → microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank  (default, fast)
  xlm-roberta-large       → microsoft/llmlingua-2-xlm-roberta-large-meetingbank             (higher quality)

Endpoints
---------
GET  /health
POST /compress { text, rate?, target_tokens?, model?, force_tokens? }
     → { compressed_text, original_tokens, compressed_tokens, ratio, model }
"""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

MODEL_ALIASES = {
    "bert-base-multilingual": "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    "xlm-roberta-large": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
}
DEFAULT_MODEL = os.getenv("COMPRESSION_MODEL", "bert-base-multilingual")
# Tokens/punctuation always kept, so structure and instructions survive compression.
FORCE_TOKENS = ["\n", ".", "?", "!", ":"]

app = FastAPI(title="RunLedger Compression Service", version="0.1.0")


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


def _resolve(model: str | None) -> str:
    name = (model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(name, name)  # allow a full HF model id too


@lru_cache(maxsize=2)
def _compressor(model_name: str):
    # Imported lazily so the container starts (and /health responds) before the model loads.
    from llmlingua import PromptCompressor  # noqa: PLC0415

    return PromptCompressor(model_name=model_name, use_llmlingua2=True, device_map="cpu")


class CompressRequest(BaseModel):
    text: str = Field(..., min_length=1)
    rate: float = 0.5  # fraction of tokens to KEEP (lower = more aggressive)
    target_tokens: int | None = None
    model: str | None = None
    force_tokens: list[str] | None = None


class CompressResponse(BaseModel):
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    ratio: float
    model: str


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "default_model": DEFAULT_MODEL, "aliases": list(MODEL_ALIASES)}


@app.get("/health/ready")
def readiness() -> dict[str, object]:
    return health()


@app.post("/compress", response_model=CompressResponse)
def compress(req: CompressRequest) -> CompressResponse:
    model_name = _resolve(req.model)
    kwargs: dict[str, object] = {"force_tokens": req.force_tokens or FORCE_TOKENS}
    if req.target_tokens is not None:
        kwargs["target_token"] = req.target_tokens
    else:
        kwargs["rate"] = req.rate
    result = _compressor(model_name).compress_prompt(req.text, **kwargs)
    original = int(result.get("origin_tokens", 0))
    compressed = int(result.get("compressed_tokens", 0))
    ratio = float(compressed / original) if original else 1.0
    return CompressResponse(
        compressed_text=result.get("compressed_prompt", req.text),
        original_tokens=original,
        compressed_tokens=compressed,
        ratio=round(ratio, 4),
        model=model_name,
    )
