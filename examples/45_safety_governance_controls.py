"""
examples/45_safety_governance_controls.py

Demonstrates a small Safety & Governance control-plane workflow:

1. create a scoped data-capture override
2. register an OIDC provider
3. create an IP ACL rule
4. create a taxonomy tag
5. create an auto-tagging rule
6. fetch the governance audit pack

This script expects an org-admin or platform-admin session-style bearer token.
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("RUNLEDGER_API_KEY", "")

if not API_KEY:
    print("Error: RUNLEDGER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def check(resp: httpx.Response, label: str) -> dict:
    if resp.status_code not in (200, 201, 204):
        print(f"{label} failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 204:
        return {}
    return resp.json()


def main() -> None:
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=15) as client:
        capture = check(
            client.put(
                "/settings/capture-policy/scopes",
                json={
                    "scope_type": "agent",
                    "scope_id": "support-bot",
                    "privacy_mode": "SAMPLED",
                    "sampled_rate": 0.1,
                },
            ),
            "capture scope",
        )
        print("capture scope:", capture)

        oidc = check(
            client.post(
                "/security/oidc-providers",
                json={
                    "name": "Example OIDC",
                    "issuer_url": "https://issuer.example.com",
                    "audience": "runledger",
                    "claim_mappings": {"workspace_id": "workspace_id"},
                },
            ),
            "oidc provider",
        )
        print("oidc provider:", oidc["id"])

        acl = check(
            client.post(
                "/security/ip-acl",
                json={
                    "scope_type": "workspace",
                    "cidr": "203.0.113.0/24",
                    "action": "allow",
                    "priority": 100,
                    "description": "Example governance control",
                },
            ),
            "ip acl rule",
        )
        print("ip acl:", acl["id"])

        tag = check(
            client.post(
                "/tags",
                json={
                    "category": "workflow",
                    "key": "workflow",
                    "value": "support",
                    "description": "Support workflow traffic",
                },
            ),
            "tag",
        )
        print("tag:", tag["id"])

        rule = check(
            client.post(
                "/tags/auto-rules",
                json={
                    "name": "Support prompt classifier",
                    "match_type": "contains",
                    "match_field": "prompt",
                    "match_pattern": "ticket",
                    "tag_key": "workflow",
                    "tag_value": "support",
                    "priority": 50,
                },
            ),
            "auto-tag rule",
        )
        print("auto-tag rule:", rule["id"])

        pack = check(client.get("/governance/audit-pack"), "governance audit pack")
        print("governance summary:", pack.get("summary", {}))


if __name__ == "__main__":
    main()
