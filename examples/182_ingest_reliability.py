"""
examples/182_ingest_reliability.py

Reliable ingest, end to end:

  1. Send a batch with client ids (tool_call_id / event_id) so retries are applied once.
  2. Inspect dead letters: events the pipeline could not apply, with the error.
     Replay them once the cause is fixed, or discard them.
  3. Send the same events from a tool that can only fire webhooks, signed with the
     workspace's own secret and a single-use nonce.

Required env vars:
  RUNLEDGER_BASE_URL       (default http://localhost:8201)
  RUNLEDGER_API_KEY        a key with the ingest scope (steps 1)
  RUNLEDGER_SESSION_KEY    a workspace admin's dashboard session key (steps 2-3)
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

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
INGEST_KEY = os.getenv("RUNLEDGER_API_KEY", "")
ADMIN_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")


def now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> None:
    if not INGEST_KEY or not ADMIN_KEY:
        print("Error: set RUNLEDGER_API_KEY and RUNLEDGER_SESSION_KEY", file=sys.stderr)
        raise SystemExit(1)
    ingest = {"Authorization": f"Bearer {INGEST_KEY}"}
    admin = {"Authorization": f"Bearer {ADMIN_KEY}"}

    # 1. Idempotent batch: the explicit tool_call_id makes a retry harmless.
    run_id = str(uuid.uuid4())
    events = [
        {
            "event_type": "run_start",
            "run_id": run_id,
            "started_at": now(),
            "feature_tag": "support-triage",
        },
        {
            "event_type": "tool_call",
            "run_id": run_id,
            "tool_call_id": str(uuid.uuid4()),
            "tool_name": "kb_search",
            "status": "success",
        },
        {"event_type": "run_end", "run_id": run_id, "status": "succeeded", "ended_at": now()},
    ]
    for attempt in (1, 2):  # simulate a client retry
        resp = httpx.post(f"{BASE_URL}/ingest/v1/batch", headers=ingest, json={"events": events})
        print(f"[ok] batch attempt {attempt}: {resp.status_code} {resp.json()}")

    # 2. Dead letters: failed events with their error; replay or discard.
    dead = httpx.get(f"{BASE_URL}/ingest/v1/dead-letters", headers=admin).json()
    print(f"[ok] {dead['total']} pending dead letter(s)")
    for item in dead["items"][:3]:
        print(f"     {item['event_type']} run={item['run_id']} error={item['error'][:80]}")
    # httpx.post(f"{BASE_URL}/ingest/v1/dead-letters/replay", headers=admin)  # replay all

    # 3. Signed webhook with the workspace secret and a single-use nonce.
    secret = httpx.get(f"{BASE_URL}/ingest/v1/signing-secret", headers=admin).json()
    workspace_id = secret["workspace_id"]
    body = json.dumps({"workspace_id": workspace_id, "events": events[:1]}).encode()
    timestamp, nonce = now(), uuid.uuid4().hex
    signature = hmac.new(
        secret["secret"].encode(),
        f"{workspace_id}.{timestamp}.{nonce}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-RunLedger-Timestamp": timestamp,
        "X-RunLedger-Nonce": nonce,
        "X-RunLedger-Signature": signature,
    }
    first = httpx.post(f"{BASE_URL}/ingest/v1/signed", headers=headers, content=body)
    replay = httpx.post(f"{BASE_URL}/ingest/v1/signed", headers=headers, content=body)
    print(
        f"[ok] signed webhook: {first.status_code}; replayed nonce: {replay.status_code} (409 expected)"
    )


if __name__ == "__main__":
    main()
