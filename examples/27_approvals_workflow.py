"""
Example 27 — Approvals with separation of duties
=================================================
Expected cost: $0.00 (no LLM calls — governance API only)

Demonstrates:
- A CI job requesting approval for a sensitive action (a prompt promotion)
- The requester being refused when it tries to approve its own request (403)
- A second identity (the reviewer) approving it
- Reading the request's audit trail, which records who asked and who decided

Use-case: a CI pipeline runs evals on a new prompt version and, if they pass, asks
for production promotion. A team lead approves it with their own key; the pipeline
can never approve itself.

Prerequisites (two different identities, both workspace admins):
    export RUNLEDGER_API_KEY=rl_live_...           # the requester (e.g. CI)
    export RUNLEDGER_APPROVER_API_KEY=rl_live_...  # the reviewer
"""

from __future__ import annotations

import os
import uuid

import httpx

BASE_URL = os.environ.get("RUNLEDGER_BASE_URL", "http://localhost:8201")
REQUESTER_KEY = os.environ.get("RUNLEDGER_API_KEY", "")
APPROVER_KEY = os.environ.get("RUNLEDGER_APPROVER_API_KEY", "")


def client(key: str) -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, headers={"Authorization": f"Bearer {key}"}, timeout=15)


def main() -> None:
    requester = client(REQUESTER_KEY)
    version_ref = f"support-agent@{uuid.uuid4().hex[:6]}"

    print("1. CI requests approval to promote a prompt version…")
    resp = requester.post(
        "/approvals",
        json={
            "request_type": "prompt_promote",
            "request": {"prompt": version_ref, "target": "production"},
            "reason": "Eval suite passed (quality +4%, cost -8%).",
        },
    )
    resp.raise_for_status()
    approval = resp.json()
    print(
        f"   {approval['id'][:8]}… status={approval['status']} requested_by={approval['requested_by']}"
    )

    print("\n2. CI tries to approve its own request…")
    own = requester.put(f"/approvals/{approval['id']}/approve", json={"note": "lgtm"})
    print(f"   HTTP {own.status_code}: {own.json().get('detail')}")  # 403: separation of duties

    if APPROVER_KEY:
        print("\n3. The reviewer approves it…")
        reviewer = client(APPROVER_KEY)
        ok = reviewer.put(
            f"/approvals/{approval['id']}/approve", json={"note": "Eval results look good."}
        )
        print(
            f"   HTTP {ok.status_code}: status={ok.json().get('status')} by {ok.json().get('decided_by')}"
        )
        again = reviewer.put(f"/approvals/{approval['id']}/deny", json={"note": "too late"})
        print(f"   a second decision → HTTP {again.status_code} (already decided)")
    else:
        print("\n3. Set RUNLEDGER_APPROVER_API_KEY to approve as a second identity.")

    print("\n4. Audit trail for this request:")
    trail = requester.get(
        "/audit/events", params={"target_type": "approval", "target_id": approval["id"]}
    )
    for event in reversed(trail.json().get("items", [])):
        print(
            f"   #{event.get('seq')} {event['action']:<22} by {event.get('actor_label') or event.get('actor_type')}"
        )


if __name__ == "__main__":
    main()
