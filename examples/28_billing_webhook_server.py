"""
Example 28 — Billing Webhook Verification Server
=================================================
Expected cost: $0.00 (webhook receiver — no LLM calls)

Demonstrates:
- Registering a billing webhook in RunLedger
- A minimal FastAPI server that receives and verifies HMAC-signed payloads
- Parsing the billing.period.closed event and extracting chargeback breakdown

Run this example in two terminals:
    Terminal 1: python 28_billing_webhook_server.py server
    Terminal 2: python 28_billing_webhook_server.py register

Or use ngrok to expose locally for testing:
    ngrok http 9000
    python 28_billing_webhook_server.py register --url https://<ngrok-id>.ngrok.io/hook

Prerequisites:
    pip install fastapi uvicorn
    export RUNLEDGER_API_KEY=rl_live_...
    export WEBHOOK_SECRET=my-shared-secret-at-least-8-chars
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "replace-me-with-a-real-secret")
BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
LISTEN_PORT = int(os.environ.get("WEBHOOK_PORT", "9000"))


# ── Signature verification ─────────────────────────────────────────────────────


def verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify the X-RunLedger-Signature header.

    RunLedger signs payloads as:  sha256=<hex-hmac-sha256>
    """
    if not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[7:]
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected_sig)


# ── Webhook server ─────────────────────────────────────────────────────────────


def run_server() -> None:
    try:
        import uvicorn
        from fastapi import FastAPI, Header, HTTPException, Request
    except ImportError:
        print("ERROR: pip install fastapi uvicorn")
        sys.exit(1)

    server_app = FastAPI(title="RunLedger Webhook Receiver")

    @server_app.post("/hook")
    async def receive_billing_webhook(
        request: Request,
        x_runledger_signature: str | None = Header(default=None, alias="X-RunLedger-Signature"),
        x_runledger_event: str | None = Header(default=None, alias="X-RunLedger-Event"),
    ) -> dict:
        body = await request.body()

        # 1. Verify HMAC signature
        if not x_runledger_signature or not verify_signature(body, x_runledger_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # 2. Parse the payload
        payload = json.loads(body)
        event = payload.get("event")

        print(f"\n{'='*60}")
        print(f"EVENT: {event}")
        print(f"  period_id      = {payload.get('period_id','')[:8]}…")
        print(f"  workspace_id   = {payload.get('workspace_id','')[:8]}…")
        print(f"  period         = {payload.get('period_start')} → {payload.get('period_end')}")
        print(f"  total_cost_usd = ${float(payload.get('total_cost_usd', 0)):.4f}")
        print(f"  snapshot_sig   = {payload.get('snapshot_signature','')[:16]}…")

        breakdown = payload.get("chargeback_breakdown", [])
        if breakdown:
            print(f"  chargeback_breakdown ({len(breakdown)} rules):")
            for rule in breakdown:
                print(
                    f"    {rule['dimension']:20s}  {rule['allocation_type']:12s}"
                    f"  {float(rule['weight'])*100:.0f}%  → ${float(rule['allocated_usd']):.4f}"
                )
        print(f"{'='*60}")

        # 3. In production: push to GL / Slack / ERP here
        return {"ok": True, "event": event}

    print(f"Webhook server listening on http://0.0.0.0:{LISTEN_PORT}/hook")
    print(f"Verify secret: {WEBHOOK_SECRET[:4]}{'*'*max(0,len(WEBHOOK_SECRET)-4)}")
    uvicorn.run(server_app, host="0.0.0.0", port=LISTEN_PORT, log_level="warning")


# ── Register webhook in RunLedger ─────────────────────────────────────────────


def register_webhook(url: str | None = None) -> None:
    import httpx

    webhook_url = url or f"http://localhost:{LISTEN_PORT}/hook"
    print(f"Registering webhook: {webhook_url}")

    resp = httpx.post(
        f"{BASE_URL}/billing/webhooks",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "url": webhook_url,
            "secret": WEBHOOK_SECRET,
            "label": "Example billing receiver",
        },
        timeout=10,
    )
    if resp.status_code == 201:
        data = resp.json()
        print(f"✓ Registered webhook: {data['id'][:8]}…")
        print(f"  url   = {data['url']}")
        print(f"  label = {data['label']}")
        print(f"\nNow close a billing period to trigger it:")
        print(f"  POST {BASE_URL}/billing/periods/<period_id>/close")
    else:
        print(f"✗ Failed: HTTP {resp.status_code} — {resp.text}")


# ── Signature test ─────────────────────────────────────────────────────────────


def test_verification() -> None:
    """Self-test the verify_signature function."""
    body = b'{"event":"billing.period.closed","total_cost_usd":"42.00"}'
    secret = "test-secret"
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(body, sig, secret), "Signature verification failed"
    assert not verify_signature(body, sig, "wrong-secret"), "Should reject wrong secret"
    assert not verify_signature(body, "sha256=invalid", secret), "Should reject bad sig"
    print("✓ Signature verification tests passed")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    url_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "server":
        run_server()
    elif cmd == "register":
        register_webhook(url_arg)
    elif cmd == "test":
        print("=== RunLedger Billing Webhook Example ===\n")
        test_verification()
        print("\nUsage:")
        print("  python 28_billing_webhook_server.py server     # start receiver")
        print("  python 28_billing_webhook_server.py register   # register in RunLedger")
        print("  python 28_billing_webhook_server.py register <url>  # custom URL")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
