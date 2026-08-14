"""Gateway control-plane router aggregator.

The live OpenAI-compatible gateway runtime now lives in the Rust service under
`apps/gateway-rs`. This module only composes the remaining Python control-plane,
management, and runtime-support endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from runledger_api.core.ratelimit import ingest_rate_limit

from . import (
    gateway_legacy,
    gateway_observability,
    gateway_passthrough,
    gateway_routing,
    gateway_runtime,
)

router = APIRouter(
    prefix="/gateway",
    tags=["gateway"],
    dependencies=[Depends(ingest_rate_limit)],
)
router.include_router(gateway_legacy.router)
router.include_router(gateway_routing.router)
router.include_router(gateway_passthrough.router)
router.include_router(gateway_runtime.router)
router.include_router(gateway_observability.router)
