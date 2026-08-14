"""
Smoke-test the phase-1 gateway runtime split contracts.

Requires:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
  RUNLEDGER_WORKSPACE_ID
  RUNLEDGER_ADMIN_SECRET

Optional:
  RUNLEDGER_RUNTIME_SIGNING_SECRET

This script exercises the control-plane contract surfaces that back the planned
runledger-gateway-rs split:

  1. GET  /gateway/runtime/snapshot
  2. GET  /gateway/runtime/internal/snapshot
  3. POST /gateway/runtime/events/signed
  4. GET  /gateway/requests
  5. GET  /gateway/deployments/health
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import UTC, datetime

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")
WORKSPACE_ID = os.getenv("RUNLEDGER_WORKSPACE_ID", "")
ADMIN_SECRET = os.getenv("RUNLEDGER_ADMIN_SECRET", "")
RUNTIME_SIGNING_SECRET = os.getenv("RUNLEDGER_RUNTIME_SIGNING_SECRET", ADMIN_SECRET)

if not SESSION_KEY or not WORKSPACE_ID or not ADMIN_SECRET:
    print(
        "Error: RUNLEDGER_SESSION_KEY, RUNLEDGER_WORKSPACE_ID, and RUNLEDGER_ADMIN_SECRET are required",
        file=sys.stderr,
    )
    sys.exit(1)

SESSION_HEADERS = {
    "Authorization": f"Bearer {SESSION_KEY}",
    "Content-Type": "application/json",
}
ADMIN_HEADERS = {
    "X-Admin-Secret": ADMIN_SECRET,
}


def expect_ok(resp: httpx.Response, label: str, allowed: tuple[int, ...] = (200, 201, 202, 204)) -> dict:
    if resp.status_code not in allowed:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def signed_headers(*, workspace_id: str, body: bytes) -> dict[str, str]:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = b".".join([workspace_id.encode(), timestamp.encode(), body])
    signature = hmac.new(
        RUNTIME_SIGNING_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-RunLedger-Timestamp": timestamp,
        "X-RunLedger-Signature": signature,
    }


def ensure_route(client: httpx.Client) -> tuple[str, bool]:
    routes = expect_ok(client.get("/gateway/routes"), "list gateway routes")
    if routes["items"]:
        route_id = routes["items"][0]["id"]
        print(f"[ok] using existing route {route_id}")
        return route_id, False

    alias = f"runtime-smoke-{uuid.uuid4().hex[:8]}"
    created = expect_ok(
        client.post(
            "/gateway/routes",
            json={
                "alias": alias,
                "provider": "local",
                "target_model": "runtime-smoke-model",
                "priority": 10,
                "timeout_ms": 30000,
                "health_auto_disable": True,
            },
        ),
        "create temporary gateway route",
    )
    print(f"[ok] created temporary route {created['id']}")
    return created["id"], True


def compare_snapshots(public_snapshot: dict, internal_snapshot: dict) -> None:
    if public_snapshot["workspace"]["workspace_id"] != internal_snapshot["workspace"]["workspace_id"]:
        raise RuntimeError("workspace mismatch between public and internal runtime snapshots")
    if public_snapshot["version"] != internal_snapshot["version"]:
        raise RuntimeError(
            "snapshot version mismatch between public and internal runtime endpoints"
        )
    print(
        "[ok] runtime snapshot parity"
        f" version={public_snapshot['version']}"
        f" routes={len(public_snapshot['routes'])}"
        f" groups={len(public_snapshot['routing_groups'])}"
        f" policies={len(public_snapshot['routing_policies'])}"
    )


def main() -> None:
    created_route_id: str | None = None

    with httpx.Client(base_url=BASE_URL, headers=SESSION_HEADERS, timeout=20) as client:
        try:
            public_snapshot = expect_ok(
                client.get("/gateway/runtime/snapshot"),
                "fetch workspace runtime snapshot",
            )
            print(f"[ok] fetched workspace runtime snapshot version={public_snapshot['version']}")

            route_id, created_temp = ensure_route(client)
            if created_temp:
                created_route_id = route_id
                public_snapshot = expect_ok(
                    client.get("/gateway/runtime/snapshot"),
                    "refresh runtime snapshot after temporary route creation",
                )
                print("[ok] refreshed workspace runtime snapshot after route creation")

            request_id = str(uuid.uuid4())
            event_batch = {
                "workspace_id": WORKSPACE_ID,
                "source_service": "runledger-gateway-rs-smoke",
                "events": [
                    {
                        "event_type": "gateway.request.completed",
                        "request_id": request_id,
                        "workspace_id": WORKSPACE_ID,
                        "route_id": route_id,
                        "model_requested": public_snapshot["routes"][0]["alias"] if public_snapshot["routes"] else "runtime-smoke",
                        "model_used": public_snapshot["routes"][0]["target_model"] if public_snapshot["routes"] else "runtime-smoke-model",
                        "provider": public_snapshot["routes"][0]["provider"] if public_snapshot["routes"] else "local",
                        "status": "success",
                        "decision_reason": "runtime_split_smoke:manual",
                        "cache_hit": False,
                        "semantic_cache_hit": False,
                        "stream": False,
                        "latency_ms": 42,
                        "input_tokens": 12,
                        "output_tokens": 7,
                        "cost_usd": "0.000123",
                        "started_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    },
                    {
                        "event_type": "gateway.enforcement.applied",
                        "request_id": request_id,
                        "workspace_id": WORKSPACE_ID,
                        "route_id": route_id,
                        "action": "throttle",
                        "source": "per_user_rpm_limit",
                        "policy_version": 1,
                        "detail": {"limit": 120, "window": "minute"},
                    },
                    {
                        "event_type": "gateway.route.health",
                        "workspace_id": WORKSPACE_ID,
                        "route_id": route_id,
                        "deployment_status": "degraded",
                        "consecutive_failures": 2,
                        "health_summary": "runtime smoke health update",
                    },
                ],
            }

            body = json.dumps(event_batch, separators=(",", ":")).encode("utf-8")

            internal_snapshot = expect_ok(
                client.get(
                    "/gateway/runtime/internal/snapshot",
                    params={"workspace_id": WORKSPACE_ID},
                    headers=ADMIN_HEADERS,
                ),
                "fetch internal runtime snapshot",
            )
            compare_snapshots(public_snapshot, internal_snapshot)

            signed = expect_ok(
                client.post(
                    "/gateway/runtime/events/signed",
                    content=body,
                    headers=signed_headers(workspace_id=WORKSPACE_ID, body=body),
                ),
                "ingest signed gateway runtime event batch",
            )
            if signed["accepted"] != 3:
                raise RuntimeError(f"expected 3 accepted runtime events, got {signed['accepted']}")
            print("[ok] ingested signed gateway runtime event batch accepted=3")

            requests = expect_ok(
                client.get("/gateway/requests", params={"limit": 20}),
                "list gateway requests",
            )
            match = next((item for item in requests["items"] if item["id"] == request_id), None)
            if match is None:
                raise RuntimeError("gateway runtime request event was not persisted into gateway_requests")
            print(
                "[ok] runtime request event persisted"
                f" status={match['status']}"
                f" latency_ms={match['latency_ms']}"
            )

            health = expect_ok(
                client.get("/gateway/deployments/health"),
                "list gateway deployment health",
            )
            health_match = next((item for item in health["items"] if item["route_id"] == route_id), None)
            if health_match is None:
                raise RuntimeError("gateway route health event did not map back to deployment health")
            print(
                "[ok] runtime health event reflected in deployment health"
                f" status={health_match['deployment_status']}"
                f" failures={health_match['consecutive_health_failures']}"
            )
        finally:
            if created_route_id is not None:
                expect_ok(client.delete(f"/gateway/routes/{created_route_id}"), "delete temporary gateway route")
                print(f"[ok] deleted temporary route {created_route_id}")

    print("[done] gateway runtime split smoke test completed")


if __name__ == "__main__":
    main()
