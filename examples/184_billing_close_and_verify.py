"""
examples/184_billing_close_and_verify.py

Close a billing period and verify its signed export:

  1. Create a period for last month (overlapping periods are refused).
  2. Add a credit, then close: the lines and totals are frozen and signed with the
     workspace's billing key, so usage that arrives later won't change the bill.
  3. Download the signed JSON export and verify it two ways: with POST /billing/verify
     and offline with the workspace key (HMAC-SHA256 over canonical JSON).
  4. Optionally reopen it with a reason (RUNLEDGER_REOPEN=1).

Required env vars:
  RUNLEDGER_API_KEY   an org admin's session key
Optional:
  RUNLEDGER_BASE_URL  (default http://localhost:8201)
"""

from __future__ import annotations

import calendar
import hashlib
import hmac
import json
import os
import sys
from datetime import date

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8201").rstrip("/")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")


def main() -> None:
    if not API_KEY:
        print("Error: set RUNLEDGER_API_KEY", file=sys.stderr)
        raise SystemExit(1)
    http = httpx.Client(
        base_url=BASE_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=60
    )

    today = date.today()
    year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    start, end = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    created = http.post(
        "/billing/periods", json={"period_start": str(start), "period_end": str(end)}
    )
    if created.status_code == 409:
        print(f"[skip] {created.json()['detail']}")
        return
    created.raise_for_status()
    period = created.json()
    print(f"[ok] period {period['period_start']}..{period['period_end']}")

    http.post(
        f"/billing/periods/{period['id']}/adjustments",
        json={"adjustment_type": "credit", "amount_usd": "1.00", "description": "example credit"},
    ).raise_for_status()

    preview = http.get(f"/billing/periods/{period['id']}/breakdown").json()
    print(f"[ok] closing: gross {preview['gross_cost_usd']}, net {preview['net_cost_usd']}")
    snapshot = http.post(f"/billing/periods/{period['id']}/close").json()
    print(f"[ok] closed and signed with {snapshot['signing_key_id']}")

    signed = http.get(
        f"/billing/periods/{period['id']}/export", params={"format": "signed_json"}
    ).json()
    payload = {k: v for k, v in signed.items() if k not in ("signature", "signing_key_id")}
    online = http.post(
        "/billing/verify",
        json={
            "payload": payload,
            "signature": signed["signature"],
            "signing_key_id": signed["signing_key_id"],
        },
    ).json()
    key = http.get("/billing/signing-key").json()["key"]
    offline = hmac.new(
        key.encode(), json.dumps(payload, sort_keys=True, default=str).encode(), hashlib.sha256
    ).hexdigest()
    print(
        f"[ok] signature valid online: {online['valid']}, offline: {offline == signed['signature']}"
    )

    if os.getenv("RUNLEDGER_REOPEN") == "1":
        http.post(
            f"/billing/periods/{period['id']}/reopen", json={"reason": "example"}
        ).raise_for_status()
        print("[ok] reopened")


if __name__ == "__main__":
    main()
