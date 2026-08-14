"""
examples/42_ai_hub_catalog.py

Exercise the AI Hub model-catalog lifecycle with a dashboard session key:
  1. create a model card
  2. list and fetch it
  3. update metadata and deprecation fields
  4. record an access request
  5. sync a provider baseline
  6. delete the created model card

Required env vars:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")

if not SESSION_KEY:
    print("Error: RUNLEDGER_SESSION_KEY not set", file=sys.stderr)
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"Bearer {SESSION_KEY}",
    "Content-Type": "application/json",
}


def expect_ok(resp: httpx.Response, label: str, allowed: tuple[int, ...] = (200, 201, 204)) -> dict:
    if resp.status_code not in allowed:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    model_name = f"workspace-demo-model-{suffix}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        created = expect_ok(
            client.post(
                "/hub/models",
                json={
                    "name": model_name,
                    "provider": "ollama",
                    "description": "Workspace demo model card",
                    "capabilities": ["chat", "reasoning"],
                    "context_window": 32768,
                    "input_cost_per_1k": 0.0001,
                    "output_cost_per_1k": 0.0002,
                    "tags": ["demo", "workspace"],
                    "is_featured": False,
                    "is_public": True,
                },
            ),
            "create model card",
        )
        model_id = created["id"]
        print(f"[ok] created model card {created['name']}")

        listing = expect_ok(client.get("/hub/models"), "list model cards")
        print(f"[ok] listed {len(listing['items'])} model cards")

        fetched = expect_ok(client.get(f"/hub/models/{model_id}"), "get model card")
        print(f"[ok] fetched provider {fetched['provider']}")

        updated = expect_ok(
            client.put(
                f"/hub/models/{model_id}",
                json={
                    "description": "Workspace demo model card updated",
                    "capabilities": ["chat", "reasoning", "tools"],
                    "tags": ["demo", "workspace", "featured-candidate"],
                    "is_featured": True,
                    "is_deprecated": True,
                    "deprecation_notice": "Replace with the promoted workspace default after validation.",
                },
            ),
            "update model card",
        )
        print(f"[ok] updated model card; deprecated={updated['is_deprecated']}")

        access = expect_ok(
            client.post(f"/hub/models/{model_id}/request-access"),
            "request model access",
        )
        print(f"[ok] recorded access request count={access['total_requests']}")

        synced = expect_ok(
            client.post(
                "/hub/sync-provider",
                json={"provider": "openai"},
            ),
            "sync provider baseline",
        )
        print(f"[ok] synced provider {synced['provider']} with {synced['models_added']} added cards")

        expect_ok(client.delete(f"/hub/models/{model_id}"), "delete model card")
        print("[ok] deleted created model card")

    print("[done] AI Hub catalog example completed")


if __name__ == "__main__":
    main()
