"""
Example 27 — Approvals & Governance Workflow
=============================================
Expected cost: $0.00 (no LLM calls — governance API only)

Demonstrates:
- Creating a prompt version and requesting approval before promoting to production
- Listing pending approvals
- Approving a request programmatically (CI/CD integration pattern)
- The promotion gate enforced by the RunLedger API

Use-case: A prompt engineer commits a new version. An automated test suite
runs evals and, if they pass, submits an approval request. A team lead
approves via the UI or API before the version goes live.

Prerequisites:
    export RUNLEDGER_API_KEY=rl_live_...
"""

from __future__ import annotations

import os
import uuid

import httpx

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("RUNLEDGER_API_KEY", "")

client = httpx.Client(
    base_url=BASE_URL,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    timeout=15,
)

PROMPT_NAME = f"support-agent-{uuid.uuid4().hex[:6]}"


def create_prompt_and_version() -> tuple[str, int]:
    """Create a prompt and commit a new version."""
    # Create prompt
    resp = client.post("/prompts", json={"name": PROMPT_NAME, "description": "Support agent prompt"})
    resp.raise_for_status()
    print(f"  Created prompt: {PROMPT_NAME}")

    # Commit version 1
    resp = client.post(
        f"/prompts/{PROMPT_NAME}/versions",
        json={
            "content": "You are a helpful support agent. Answer the user's question: {{question}}",
            "commit_message": "Initial version — standard tone",
            "tags": ["v1", "candidate"],
        },
    )
    resp.raise_for_status()
    version = resp.json().get("version", 1)
    print(f"  Committed version {version}")
    return PROMPT_NAME, version


def request_approval(prompt_name: str, version: int) -> str:
    """Submit an approval request to promote this version to production."""
    resp = client.post(
        "/approvals",
        json={
            "resource_type": "prompt_version",
            "resource_id": f"{prompt_name}:{version}",
            "action": "promote_to_production",
            "requester_note": (
                f"Eval suite passed (BLEU +4%, cost -8%). "
                f"Requesting production promotion for {prompt_name} v{version}."
            ),
        },
    )
    resp.raise_for_status()
    approval_id = resp.json()["id"]
    print(f"  Approval requested: {approval_id[:8]}…")
    return approval_id


def list_pending_approvals() -> list[dict]:
    """List all pending approvals."""
    resp = client.get("/approvals", params={"status": "pending"})
    resp.raise_for_status()
    items = resp.json().get("items", [])
    print(f"  Pending approvals: {len(items)}")
    for item in items[:3]:
        print(
            f"    [{item['id'][:8]}…] {item['resource_type']}:{item['resource_id']}"
            f"  — {item.get('requester_note','')[:60]}"
        )
    return items


def approve_request(approval_id: str) -> None:
    """Approve the request (simulates a team lead action)."""
    resp = client.put(
        f"/approvals/{approval_id}/approve",
        json={"reviewer_note": "Eval results look good. Approved for production."},
    )
    if resp.status_code == 200:
        print(f"  ✓ Approved: {approval_id[:8]}…")
    else:
        print(f"  ✗ Approve failed: HTTP {resp.status_code} — {resp.text}")


def attempt_promote(prompt_name: str, version: int) -> None:
    """Try to promote the version. Requires an approved approval."""
    resp = client.post(
        f"/prompts/{prompt_name}/promote",
        json={"version": version, "target": "production"},
    )
    if resp.status_code == 200:
        print(f"  ✓ Promoted {prompt_name} v{version} to production")
    elif resp.status_code == 403:
        print(f"  ✗ Promotion blocked (no approved request) — expected before approval")
    else:
        print(f"  HTTP {resp.status_code}: {resp.text[:100]}")


def show_summary() -> None:
    resp = client.get("/approvals/summary")
    if resp.status_code == 200:
        s = resp.json()
        print(
            f"   pending={s.get('pending',0)}  approved={s.get('approved',0)}"
            f"  denied={s.get('denied',0)}  total={s.get('total',0)}"
        )


def main() -> None:
    print("=== RunLedger Approvals Workflow Example ===\n")

    print("1. Creating prompt and version…")
    prompt_name, version = create_prompt_and_version()

    print("\n2. Attempting promotion without approval (should be blocked)…")
    attempt_promote(prompt_name, version)

    print("\n3. Submitting approval request…")
    approval_id = request_approval(prompt_name, version)

    print("\n4. Pending approval queue:")
    list_pending_approvals()

    print("\n5. Approving the request (team lead action)…")
    approve_request(approval_id)

    print("\n6. Promoting with approved request…")
    attempt_promote(prompt_name, version)

    print("\n7. Approval summary:")
    show_summary()

    client.close()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()
