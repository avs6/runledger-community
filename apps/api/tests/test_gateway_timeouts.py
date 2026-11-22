"""Per-request timeout overrides never touch the shared route (review G-20)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from runledger_api.services import gateway_providers
from runledger_api.services.gateway import forward_request
from runledger_api.services.gateway_providers import _http_timeout, timeout_override


def _route() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openai", config={"completion_timeout_ms": 30_000}, timeout_ms=60_000
    )


def test_override_applies_to_its_kind_only_and_leaves_route_alone() -> None:
    route = _route()
    assert _http_timeout(route, stream=False) == 30.0
    with timeout_override(stream=False, timeout_ms=5_000):
        assert _http_timeout(route, stream=False) == 5.0
        assert _http_timeout(route, stream=True) == 60.0  # stream calls keep the route's
    assert _http_timeout(route, stream=False) == 30.0
    assert route.config == {"completion_timeout_ms": 30_000} and route.timeout_ms == 60_000


@pytest.mark.asyncio
async def test_forward_request_honours_completion_override(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[float] = []

    class Adapter:
        async def forward(self, route: Any, messages: Any, **_: Any) -> dict[str, Any]:
            seen.append(_http_timeout(route, stream=False))
            return {"ok": True}

    monkeypatch.setattr(gateway_providers, "get_adapter", lambda provider: Adapter())
    route = _route()
    await forward_request(route, [], None, None, timeout_override_ms=2_500)
    await forward_request(route, [], None, None)
    assert seen == [2.5, 30.0]
    assert route.config == {"completion_timeout_ms": 30_000} and route.timeout_ms == 60_000


@pytest.mark.asyncio
async def test_concurrent_requests_keep_their_own_override() -> None:
    route = _route()

    async def call(ms: int) -> float:
        with timeout_override(stream=False, timeout_ms=ms):
            await asyncio.sleep(0.01)
            return _http_timeout(route, stream=False)

    assert await asyncio.gather(call(1_000), call(9_000)) == [1.0, 9.0]
