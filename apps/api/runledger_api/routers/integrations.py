"""
Integrations router — Slack webhook connectivity testing.

Prefix: /integrations
Auth:   Bearer API key (get_current_workspace)
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from runledger_api.core.deps import require_org_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.services.notifications import build_test_blocks, send_slack_message

router = APIRouter(
    prefix="/integrations", tags=["integrations"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()
OrgAdminDep = Annotated[tuple, Depends(require_org_admin)]


# ── Schemas ───────────────────────────────────────────────────────────────────


class SlackTestRequest(BaseModel):
    webhook_url: str


class SlackTestResponse(BaseModel):
    ok: bool
    error: str | None = None


# ── POST /integrations/slack/test ─────────────────────────────────────────────


@router.post("/slack/test", response_model=SlackTestResponse)
async def test_slack_webhook(
    body: SlackTestRequest,
    auth: OrgAdminDep,
) -> SlackTestResponse:
    """Send a test Block Kit message to the given Slack webhook URL."""
    workspace = auth[0]
    blocks = build_test_blocks()
    try:
        await send_slack_message(body.webhook_url, blocks, "RunLedger test alert")
        log.info("integrations.slack.test.ok", workspace_id=str(workspace.id))
        return SlackTestResponse(ok=True)
    except Exception as exc:
        log.warning(
            "integrations.slack.test.failed",
            workspace_id=str(workspace.id),
            error=str(exc),
        )
        return SlackTestResponse(ok=False, error=str(exc))
