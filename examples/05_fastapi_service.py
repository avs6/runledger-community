"""
Example 5 — FastAPI service with per-request context and propagation headers.

What this demonstrates
──────────────────────
- Attaching RunLedger context to every HTTP request via middleware
- end_user_id extracted from a JWT / auth header (simulated here)
- propagation_headers() for forwarding context to downstream services
- from_headers() for restoring context in a receiving service
- async context (async with rl.context(...))

Install the SDK (not on PyPI yet — install from source)
────────────────────────────────────────────────────────
Option A — local path (recommended if you have the repo):
    pip install -e "/path/to/runledger/packages/sdk[openai]"

Option B — directly from GitHub (no clone needed):
    pip install "runledger-sdk[openai] @ git+https://github.com/avs6/runledger.git#subdirectory=packages/sdk"

Also install:
    pip install openai fastapi uvicorn python-dotenv

Run it
──────
    # Copy .env.example → .env and fill in your values, then:
    uvicorn 05_fastapi_service:app --reload

    curl -X POST http://localhost:8000/chat \\
         -H "Content-Type: application/json" \\
         -H "X-User-Id: user-eve" \\
         -d '{"message": "What is Python?"}'

Key .env variables used here:
    RUNLEDGER_API_KEY    — your workspace API key
    RUNLEDGER_BASE_URL   — http://localhost:8000  (local Docker stack)
    RUNLEDGER_LOCAL      — set "true" to print events instead of sending to the API
    OPENAI_API_KEY       — your OpenAI key
"""

from __future__ import annotations

import os

import openai
from dotenv import load_dotenv
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from runledger_sdk import RunLedger

load_dotenv()

LOCAL_MODE = os.getenv("RUNLEDGER_LOCAL", "false").lower() in ("1", "true", "yes")

app = FastAPI(title="RunLedger FastAPI Demo")

rl = RunLedger(local=LOCAL_MODE)
rl.instrument()

openai_client = openai.AsyncOpenAI()


# ── Request / response models ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    run_id: str


# ── Routes ────────────────────────────────────────────────────────────────────


@app.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> ChatResponse:
    """
    Chat endpoint.  RunLedger context is set per-request so every LLM call
    is attributed to the right user, session, and feature.
    """
    async with rl.context(
        end_user_id=x_user_id or "anonymous",
        session_id=x_session_id or body.session_id,
        feature_tag="chat-api",
    ) as run_id:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": body.message},
            ],
        )
        answer = response.choices[0].message.content or ""

    return ChatResponse(answer=answer, run_id=run_id)


@app.post("/summarise")
async def summarise(
    body: ChatRequest,
    x_user_id: str | None = Header(default=None),
) -> JSONResponse:
    """
    Shows propagation headers — the context is forwarded to a downstream
    service (simulated here as a second OpenAI call).
    """
    async with rl.context(
        end_user_id=x_user_id or "anonymous",
        feature_tag="summarise-api",
    ) as run_id:
        # These headers carry run_id, end_user_id, feature_tag forward
        propagation = rl.propagation_headers()

        # In production: httpx.post("http://other-service/...", headers=propagation)
        # Here we simulate the downstream work inline:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarise in 10 words or fewer."},
                {"role": "user", "content": body.message},
            ],
        )
        summary = response.choices[0].message.content or ""

    return JSONResponse(
        {
            "summary": summary,
            "run_id": run_id,
            "propagation_headers": propagation,
        }
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await rl.aflush()
