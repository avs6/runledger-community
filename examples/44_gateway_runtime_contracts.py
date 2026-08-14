"""
Example 44 - Gateway runtime contracts

Shows how a future data-plane service can:
  1. fetch the effective gateway runtime snapshot
  2. fetch the internal snapshot variant
  3. sign and post runtime events back into RunLedger
  4. call the internal preflight bridge used by the Rust runtime

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
  RUNLEDGER_WORKSPACE_ID
  RUNLEDGER_ADMIN_SECRET

Optional:
  RUNLEDGER_RUNTIME_SIGNING_SECRET
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
        "ERROR: RUNLEDGER_SESSION_KEY, RUNLEDGER_WORKSPACE_ID, and RUNLEDGER_ADMIN_SECRET are required",
        file=sys.stderr,
    )
    sys.exit(1)


def sign_runtime_payload(workspace_id: str, body: bytes) -> dict[str, str]:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    signature = hmac.new(
        RUNTIME_SIGNING_SECRET.encode(),
        b".".join([workspace_id.encode(), timestamp.encode(), body]),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-RunLedger-Timestamp": timestamp,
        "X-RunLedger-Signature": signature,
    }


with httpx.Client(base_url=BASE_URL, timeout=20) as client:
    session_headers = {"Authorization": f"Bearer {SESSION_KEY}"}
    public_snapshot = client.get("/gateway/runtime/snapshot", headers=session_headers)
    public_snapshot.raise_for_status()
    public_json = public_snapshot.json()
    print(
        "Public runtime snapshot:",
        public_json["version"],
        f"routes={len(public_json['routes'])}",
    )

    internal_snapshot = client.get(
        "/gateway/runtime/internal/snapshot",
        params={"workspace_id": WORKSPACE_ID},
        headers={"X-Admin-Secret": ADMIN_SECRET},
    )
    internal_snapshot.raise_for_status()
    internal_json = internal_snapshot.json()
    print("Internal runtime snapshot:", internal_json["version"])

    preflight = client.post(
        "/gateway/runtime/internal/preflight",
        headers={"X-Admin-Secret": ADMIN_SECRET},
        json={
            "raw_key": SESSION_KEY,
            "body": {
                "model": public_json["routes"][0]["alias"] if public_json["routes"] else "runtime-smoke",
                "messages": [{"role": "user", "content": "hello from runtime preflight"}],
                "stream": False,
                "cache": False,
            },
        },
    )
    preflight.raise_for_status()
    preflight_json = preflight.json()
    print(
        "Runtime preflight:",
        f"steps={len(preflight_json['execution_steps'])}",
        f"route_alias={preflight_json['route_alias']}",
    )

    event_batch = {
        "workspace_id": WORKSPACE_ID,
        "source_service": "runledger-gateway-rs-example",
        "events": [
            {
                "event_type": "gateway.enforcement.applied",
                "request_id": str(uuid.uuid4()),
                "workspace_id": WORKSPACE_ID,
                "action": "throttle",
                "source": "per_user_rpm_limit",
                "policy_version": 1,
                "detail": {"limit": 120, "window": "minute"},
            }
        ],
    }
    body = json.dumps(event_batch, separators=(",", ":")).encode("utf-8")
    ingest = client.post(
        "/gateway/runtime/events/signed",
        content=body,
        headers=sign_runtime_payload(WORKSPACE_ID, body),
    )
    ingest.raise_for_status()
    print("Signed runtime events accepted:", ingest.json()["accepted"])
