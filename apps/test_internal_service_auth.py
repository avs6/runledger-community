"""Every optimization microservice refuses calls without the internal service token.

Run with:  uv run --project apps/api pytest apps/test_internal_service_auth.py

Services whose heavy runtime dependencies (models, embedded DBs) are not installed
locally are skipped; the middleware is identical in all of them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

APPS = Path(__file__).parent
SERVICES = [
    "memory-svc",
    "kg-svc",
    "skill-registry",
    "context-compiler-svc",
    "embedding-svc",
    "semantic-cache-svc",
    "reranker-svc",
    "compression-svc",
    "router-svc",
    "flywheel-svc",
]


def _load(service: str, token: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", token)
    monkeypatch.setenv("SKILLS_DATA_DIR", str(APPS / ".pytest-skills"))
    path = APPS / service / "app.py"
    spec = importlib.util.spec_from_file_location(f"svc_{service.replace('-', '_')}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:  # heavy optional deps not installed locally
        pytest.skip(f"{service}: {exc}")
    finally:
        sys.modules.pop(spec.name, None)
    return module.app


def test_every_service_has_the_middleware() -> None:
    for service in SERVICES:
        source = (APPS / service / "app.py").read_text(encoding="utf-8")
        assert "_require_internal_token" in source, service
        assert "x-internal-token" in source, service


@pytest.mark.parametrize("service", SERVICES)
def test_service_requires_internal_token(service: str, monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(_load(service, "s3cret", monkeypatch), raise_server_exceptions=False)
    assert client.get("/health").status_code == 200
    assert client.post("/anything", json={}).status_code == 401
    assert (
        client.post("/anything", json={}, headers={"x-internal-token": "nope"}).status_code == 401
    )
    # With the right token the request passes the middleware (404: no such route).
    ok = client.post("/anything", json={}, headers={"x-internal-token": "s3cret"})
    assert ok.status_code not in (401, 503)


@pytest.mark.parametrize("service", ["skill-registry", "flywheel-svc"])
def test_service_without_configured_token_refuses_traffic(
    service: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = TestClient(_load(service, "", monkeypatch), raise_server_exceptions=False)
    assert client.get("/health").status_code == 200
    resp = client.post("/anything", json={}, headers={"x-internal-token": ""})
    assert resp.status_code == 503
