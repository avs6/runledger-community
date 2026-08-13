"""
Smoke-test the merged Organization Console control-plane flows.

Requires:
  RUNLEDGER_BASE_URL
  RUNLEDGER_SESSION_KEY

Optional:
  ORG_SLACK_WEBHOOK_URL
  ORG_EXPORT_WEBHOOK_URL

This script intentionally avoids org creation/deletion because those are
platform lifecycle actions owned by /organizations, not the org console.
"""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")
SLACK_WEBHOOK_URL = os.getenv("ORG_SLACK_WEBHOOK_URL", "")
EXPORT_WEBHOOK_URL = os.getenv("ORG_EXPORT_WEBHOOK_URL", "")

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
    workspace_name = f"Org Console Smoke {uuid.uuid4().hex[:8]}"

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=15) as client:
        profile = expect_ok(client.get("/org/profile"), "get org profile")
        print(f"[ok] Loaded org profile for {profile['name']}")

        members = expect_ok(client.get("/org/members"), "list org members")
        print(f"[ok] Loaded {len(members)} org members")

        email_status = expect_ok(client.get("/settings/email/status"), "get email status")
        print(
            "[ok] Email status "
            f"enabled={email_status['email_enabled']} "
            f"smtp={email_status['smtp_configured']} "
            f"reports={email_status['email_reports_enabled']}"
        )

        email_prefs = expect_ok(
            client.get("/settings/email/preferences"),
            "get email preferences",
        )
        original_template = email_prefs["report_template"]
        next_template = "summary" if original_template != "summary" else "detailed"

        updated_prefs = expect_ok(
            client.put(
                "/settings/email/preferences",
                json={"report_template": next_template},
            ),
            "update email preferences",
        )
        print(f"[ok] Updated report template to {updated_prefs['report_template']}")

        expect_ok(
            client.put(
                "/settings/email/preferences",
                json={"report_template": original_template},
            ),
            "restore email preferences",
        )
        print(f"[ok] Restored report template to {original_template}")

        backup_config = expect_ok(
            client.get("/settings/backups/config"),
            "get backup config",
            allowed=(200,),
        )
        print(f"[ok] Loaded storage override config: {backup_config.get('bucket', '') or 'not configured'}")

        created_workspace = expect_ok(
            client.post("/org/workspaces", json={"name": workspace_name}),
            "create workspace",
        )
        workspace_id = created_workspace["id"]
        print(f"[ok] Created workspace {workspace_name}")

        expect_ok(
            client.put(
                f"/org/workspaces/{workspace_id}/status",
                json={"status": "suspended"},
            ),
            "suspend workspace",
        )
        expect_ok(
            client.put(
                f"/org/workspaces/{workspace_id}/status",
                json={"status": "active"},
            ),
            "reactivate workspace",
        )
        print("[ok] Suspended and reactivated workspace")

        expect_ok(
            client.delete(f"/org/workspaces/{workspace_id}"),
            "delete workspace",
        )
        print("[ok] Deleted workspace")

        if SLACK_WEBHOOK_URL:
            slack_result = expect_ok(
                client.post(
                    "/integrations/slack/test",
                    json={"webhook_url": SLACK_WEBHOOK_URL},
                ),
                "slack test",
            )
            print(f"[ok] Slack test result: {slack_result['ok']}")
        else:
            print("[skip] Slack test skipped because ORG_SLACK_WEBHOOK_URL is not set")

        if EXPORT_WEBHOOK_URL:
            destination = expect_ok(
                client.post(
                    "/budgets/notifications",
                    json={
                        "channel": "webhook",
                        "destination_url": EXPORT_WEBHOOK_URL,
                        "events": ["budget.breach"],
                    },
                ),
                "create webhook destination",
            )
            destination_id = destination["id"]
            print("[ok] Created webhook destination")

            test_result = expect_ok(
                client.post(f"/budgets/notifications/{destination_id}/test", json={}),
                "test webhook destination",
            )
            print(f"[ok] Webhook test result: {test_result['ok']}")

            deliveries = expect_ok(
                client.get(f"/budgets/notifications/{destination_id}/deliveries"),
                "list webhook deliveries",
            )
            print(f"[ok] Webhook deliveries recorded: {len(deliveries['items'])}")

            expect_ok(
                client.delete(f"/budgets/notifications/{destination_id}"),
                "delete webhook destination",
            )
            print("[ok] Deleted webhook destination")
        else:
            print("[skip] Webhook destination smoke test skipped because ORG_EXPORT_WEBHOOK_URL is not set")

    print("[done] Organization Console smoke test completed")


if __name__ == "__main__":
    main()
