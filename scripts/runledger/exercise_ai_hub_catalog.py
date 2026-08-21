"""
Smoke-test the AI Hub model-catalog flow.

Requires:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY

This script uses the real management APIs behind /ai-hub and leaves the
workspace clean after the dedicated CRUD flow completes.
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
    sys.exit(1)

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
    model_name = f"ai-hub-smoke-{suffix}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20) as client:
        initial = expect_ok(client.get("/hub/models"), "list initial model cards")
        initial_count = len(initial["items"])
        print(f"[ok] initial model-card count: {initial_count}")

        created = expect_ok(
            client.post(
                "/hub/models",
                json={
                    "name": model_name,
                    "provider": "ollama",
                    "description": "AI Hub smoke test card",
                    "capabilities": ["chat", "reasoning"],
                    "context_window": 65536,
                    "input_cost_per_1k": 0.0003,
                    "output_cost_per_1k": 0.0006,
                    "tags": ["smoke", "catalog"],
                    "is_featured": False,
                    "is_public": True,
                },
            ),
            "create model card",
        )
        model_id = created["id"]
        print(f"[ok] created model card {created['name']}")

        fetched = expect_ok(client.get(f"/hub/models/{model_id}"), "get created model card")
        assert fetched["name"] == model_name
        print("[ok] fetched created model card")

        filtered = expect_ok(client.get("/hub/models", params={"provider": "ollama"}), "filter model cards by provider")
        assert any(item["id"] == model_id for item in filtered["items"])
        print("[ok] provider filter returned the created card")

        updated = expect_ok(
            client.put(
                f"/hub/models/{model_id}",
                json={
                    "is_featured": True,
                    "is_deprecated": True,
                    "deprecation_notice": "Smoke-test deprecation note",
                    "tags": ["smoke", "catalog", "updated"],
                    "capabilities": ["chat", "reasoning", "tools"],
                },
            ),
            "update model card",
        )
        assert updated["is_featured"] is True
        assert updated["is_deprecated"] is True
        print("[ok] updated model card flags and metadata")

        access = expect_ok(
            client.post(f"/hub/models/{model_id}/request-access"),
            "request model access",
        )
        assert access["total_requests"] >= 1
        print(f"[ok] recorded access request count={access['total_requests']}")

        sync_result = expect_ok(
            client.post("/hub/sync-provider", json={"provider": "openai"}),
            "sync provider catalog",
        )
        print(
            "[ok] synced provider catalog "
            f"provider={sync_result['provider']} added={sync_result['models_added']}"
        )

        cost_posture = expect_ok(
            client.get(f"/hub/models/{model_id}/cost-posture"),
            "model cost posture",
        )
        assert cost_posture["model_name"] == model_name
        assert "active_budget_count" in cost_posture
        assert "billing_period_count" in cost_posture
        print(
            f"[ok] cost posture: budgets={cost_posture['active_budget_count']}, "
            f"spend={cost_posture['current_spend_usd']}, "
            f"billing_periods={cost_posture['billing_period_count']}"
        )

        gov_status = expect_ok(
            client.get(f"/hub/models/{model_id}/governance"),
            "model governance status",
        )
        assert gov_status["model_name"] == model_name
        assert "approval_count" in gov_status
        assert "audit_event_count" in gov_status
        assert "tool_policy_count" in gov_status
        print(
            f"[ok] governance: approvals={gov_status['approval_count']}, "
            f"audit_events={gov_status['audit_event_count']}, "
            f"tool_policies={gov_status['tool_policy_count']}"
        )

        expect_ok(client.delete(f"/hub/models/{model_id}"), "delete model card")
        print("[ok] deleted smoke-test model card")

        final_listing = expect_ok(client.get("/hub/models"), "list final model cards")
        final_count = len(final_listing["items"])
        print(f"[ok] final model-card count: {final_count}")

    print("[done] AI Hub smoke test completed")


if __name__ == "__main__":
    main()
