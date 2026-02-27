"""
Example 5 — FastAPI service with per-request context and propagation headers.

What this demonstrates
──────────────────────
- Attaching RunLedger context to every HTTP request via middleware
- end_user_id extracted from a JWT / auth header (simulated here)
- propagation_headers() for forwarding context to downstream services
- from_headers() for restoring context in a receiving service
- async context (async with rl.context(...))

Run it
──────
    pip install fastapi uvicorn
    export RUNLEDGER_API_KEY=rl_live_...
    export OPENAI_API_KEY=sk-...
    uv run uvicorn examples.05_fastapi_service:app --reload

    curl -X POST http://localhost:8000/chat \\
         -H "Content-Type: application/json" \\
         -H "X-User-Id: user-eve" \\
         -d '{"message": "What is Python?"}'
"""

from __future__ import annotations

import openai
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from runledger_sdk import RunLedger

app = FastAPI(title="RunLedger FastAPI Demo")

rl = RunLedger(local=True)  # set local=False + RUNLEDGER_API_KEY for live API
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
