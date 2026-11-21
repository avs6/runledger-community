from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_workspace_writer,
    validate_workspace_status,
)
from runledger_api.core.ratelimit import ingest_rate_limit
from runledger_api.models.events import AgentRun
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.events import (
    AgentRunResponse,
    BatchIngestRequest,
    IngestEvent,
    WebhookIngestRequest,
)
from runledger_api.workers.pipeline import process_events_task

log = structlog.get_logger()

router = APIRouter(prefix="/ingest/v1", tags=["ingest"], dependencies=[Depends(ingest_rate_limit)])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


_KEY_ATTRIBUTED_EVENTS = {"run_start", "provider_call"}


def attribute_to_sending_key(
    request: Request, events: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Stamp the authenticated API key on run and model-call events.

    This is what ties SDK / OTLP traffic to its key for API-key budgets, analytics,
    chargeback and filters. The value always comes from the credential that sent the
    request — never from the payload — so a client cannot attribute spend to another key.
    Events sent with an OIDC token (no key) are left unattributed.
    """
    api_key = getattr(request.state, "api_key", None)
    key_id = str(api_key.id) if api_key is not None else None
    for event in events:
        if event.get("event_type") in _KEY_ATTRIBUTED_EVENTS:
            event["api_key_id"] = key_id
    return events


def _queue_events(workspace_id: str, events: list[dict[str, object]]) -> int:
    if not events:
        return 0
    process_events_task.delay(
        workspace_id=workspace_id,
        events=events,
    )
    return len(events)


def _verify_signed_ingest(
    *,
    workspace_id: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> None:
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ingest timestamp") from exc
    now = datetime.now(UTC)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    if abs(now - ts) > timedelta(minutes=5):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signed ingest timestamp expired")

    payload = b".".join([workspace_id.encode(), timestamp.encode(), body])
    expected = hmac.new(
        settings.effective_ingest_signing_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid ingest signature")


@router.post("/events", status_code=202, dependencies=[Depends(require_workspace_writer)])
async def ingest_event(
    event: IngestEvent,
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, int]:
    """Ingest a single event. Returns 202 immediately; processing is async."""
    accepted = _queue_events(
        str(workspace.id),
        attribute_to_sending_key(request, [event.model_dump(mode="json")]),  # type: ignore[arg-type]
    )
    log.debug("event_accepted", workspace_id=str(workspace.id), event_type=event.event_type)
    return {"accepted": accepted}


@router.post("/batch", status_code=202, dependencies=[Depends(require_workspace_writer)])
async def ingest_batch(
    payload: BatchIngestRequest,
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
) -> dict[str, int]:
    """Ingest a batch of events. Returns 202 immediately."""
    accepted = _queue_events(
        str(workspace.id),
        attribute_to_sending_key(request, [e.model_dump(mode="json") for e in payload.events]),  # type: ignore[arg-type]
    )
    log.debug("batch_accepted", workspace_id=str(workspace.id), count=accepted)
    return {"accepted": accepted}


@router.post("/signed", status_code=202)
async def ingest_signed_webhook(
    request: Request,
    db: DbDep,
    x_runledger_signature: str = Header(..., alias="X-RunLedger-Signature"),
    x_runledger_timestamp: str = Header(..., alias="X-RunLedger-Timestamp"),
) -> dict[str, int]:
    """
    Ingest a signed webhook payload — for tools that can only fire webhooks.

    There is deliberately no unsigned variant: the body names the destination
    workspace, so the HMAC signature is what proves the sender may write to it.

    Signature format:
      hex(HMAC_SHA256(signing_secret, "<workspace_id>.<timestamp>.<raw_body>"))
    """
    raw_body = await request.body()
    try:
        body_json = json.loads(raw_body)
        payload = WebhookIngestRequest.model_validate(body_json)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook payload") from exc

    workspace = await db.get(Workspace, payload.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    await validate_workspace_status(workspace, db)
    _verify_signed_ingest(
        workspace_id=str(payload.workspace_id),
        timestamp=x_runledger_timestamp,
        body=raw_body,
        signature=x_runledger_signature,
    )
    accepted = _queue_events(
        str(workspace.id),
        [e.model_dump(mode="json") for e in payload.events],
    )
    log.debug("signed_webhook_accepted", workspace_id=str(workspace.id), count=accepted)
    return {"accepted": accepted}


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(
    workspace: WorkspaceDep,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AgentRun]:
    """List agent runs for the authenticated workspace, newest first."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.workspace_id == workspace.id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
