from __future__ import annotations

from fastapi import APIRouter

from .gateway_shared import *

router = APIRouter()


@router.post("/chat/completions")
async def gateway_chat_completions(
    body: GatewayCompletionRequest,
    _request: Request,
) -> Any:
    # Live gateway execution moved to the Rust data-plane service in apps/gateway-rs.
    # Keep this stub so humans and AI agents looking for the old Python runtime path
    # are redirected to the hard-cut Rust implementation instead of reviving it here.
    """
    Compatibility stub for the retired Python inline gateway runtime.

    The live OpenAI-compatible data plane now runs on `runledger-gateway-rs`.
    This control-plane route remains mounted only to fail fast and point
    stale callers at the Rust runtime during the hard cut.
    """
    _ = body
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "The Python inline gateway runtime has been removed. "
            "Use the Rust gateway runtime service at http://localhost:8210/gateway/chat/completions."
        ),
    )


# Routes CRUD
