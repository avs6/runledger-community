"""
Example 185 — Write-only secrets, rotation and the audit hash chain
====================================================================
Expected cost: $0.00 (control-plane API only)

Demonstrates:
- Storing a search-provider credential: the API returns it masked ("••••••••")
- Updating other fields while sending the mask back, which keeps the stored value
- Listing the secret inventory (age, last rotation, encrypting key)
- Rotating the secret and reading its own audit timeline
- Verifying the workspace's audit hash chain

Prerequisites:
    export RUNLEDGER_API_KEY=rl_live_...   # a workspace admin's key
"""

from __future__ import annotations

import os
import uuid

import httpx

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8201")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
MASK = "••••••••"

http = httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)


def main() -> None:
    name = f"web-search-{uuid.uuid4().hex[:6]}"
    print("1. Store a search provider with a bearer token…")
    tool = http.post(
        "/search-tools",
        json={
            "name": name,
            "tool_type": "web",
            "auth_type": "bearer",
            "auth_config": {"token": "sk-search-original", "header_name": "X-Key"},
        },
    )
    tool.raise_for_status()
    tool_id = tool.json()["id"]
    print(f"   auth_config as returned: {tool.json()['auth_config']}")  # token is masked

    print("\n2. Change the header name; send the mask to keep the token…")
    http.put(
        f"/search-tools/{tool_id}",
        json={"auth_config": {"token": MASK, "header_name": "X-Api-Key"}},
    ).raise_for_status()

    print("\n3. Secret inventory:")
    inventory = http.get("/security/secrets").json()
    print(
        f"   primary key: {inventory['primary_key_id']}  derived key in use: {inventory['using_derived_key']}"
    )
    secret = next(s for s in inventory["items"] if s["owner_id"] == tool_id)
    print(
        f"   {secret['label']}: {secret['age_days']}d ({secret['age_status']}), "
        f"rotations={secret['rotation_count']}, key={secret['key_id']}"
    )

    print("\n4. Rotate it…")
    rotated = http.post(
        f"/security/secrets/{secret['id']}/rotate", json={"values": {"token": "sk-search-rotated"}}
    ).json()
    print(f"   rotations={rotated['rotation_count']} last rotated by {rotated['rotated_by_label']}")

    print("\n5. The secret's audit timeline:")
    timeline = http.get(
        "/audit/events", params={"target_type": "secret", "target_id": secret["id"]}
    ).json()
    for event in reversed(timeline["items"]):
        print(f"   {event['created_at'][:19]} {event['action']:<15} by {event.get('actor_label')}")

    print("\n6. Verify the workspace audit chain:")
    verification = http.get("/audit/verify").json()
    print(
        f"   ok={verification['ok']} checked={verification['checked']} head={verification['head_hash'][:16]}…"
    )

    http.delete(f"/search-tools/{tool_id}")


if __name__ == "__main__":
    main()
