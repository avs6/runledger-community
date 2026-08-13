"""
examples/40_organization_console.py

Read-oriented example for the merged Organization Console.

Demonstrates:
  1. GET /org/profile
  2. GET /org/workspaces
  3. GET /org/members
  4. GET /settings/backups/config
  5. GET /settings/email/status
  6. GET /settings/email/preferences

This example requires a dashboard session key for an org-admin, org-manager,
or platform-admin user. A plain workspace API key is not enough because these
endpoints require an authenticated user session.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
SESSION_KEY = os.getenv("RUNLEDGER_SESSION_KEY", "")

if not SESSION_KEY:
    print("Error: RUNLEDGER_SESSION_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {SESSION_KEY}",
    "Content-Type": "application/json",
}


def check(resp: httpx.Response, label: str) -> dict | None:
    if resp.status_code != 200:
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        profile = check(client.get("/org/profile"), "org profile")
        workspaces = check(client.get("/org/workspaces"), "org workspaces")
        members = check(client.get("/org/members"), "org members")
        backup_config = check(client.get("/settings/backups/config"), "backup config")
        email_status = check(client.get("/settings/email/status"), "email status")
        email_prefs = check(client.get("/settings/email/preferences"), "email preferences")

    print("Organization Console")
    print(f"- Name: {profile['name']}")
    print(f"- Plan: {profile['plan']}")
    print(f"- Workspaces: {len(workspaces)}")
    print(f"- Members: {len(members)}")
    if backup_config:
        print(
            "- Storage override: "
            f"bucket={backup_config['bucket']} "
            f"prefix={backup_config['prefix']}"
        )
    else:
        print("- Storage override: not configured yet")
    print(
        "- Email delivery: "
        f"enabled={email_status['email_enabled']} "
        f"smtp_configured={email_status['smtp_configured']} "
        f"reports_enabled={email_status['email_reports_enabled']}"
    )
    print(
        "- Report prefs: "
        f"cadence={email_prefs['report_frequency']} "
        f"hour={email_prefs['report_hour']} "
        f"timezone={email_prefs['report_timezone']}"
    )


if __name__ == "__main__":
    main()
