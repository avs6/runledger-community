from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_workspace,
    require_workspace_admin,
    require_workspace_writer,
    validate_workspace_status,
)
from runledger_api.core.ratelimit import ingest_rate_limit
from runledger_api.core.redis import get_redis
from runledger_api.models.events import AgentRun
from runledger_api.models.ingest_dead_letters import IngestDeadLetter
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.events import (
    AgentRunResponse,
    BatchIngestRequest,
    DeadLetterList,
    DeadLetterReplayResult,
    DeadLetterResponse,
    IngestEvent,
    WebhookIngestRequest,
)
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.ingest_signing import verify_signed_ingest, workspace_signing_secret
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


WorkflowHeader = Annotated[
    str | None,
    Header(
        alias="X-RunLedger-Workflow",
        max_length=255,
        description="Workflow id, feature_tag or name for runs in this request "
        "that don't name one themselves.",
    ),
]


def apply_workflow_header(
    events: list[dict[str, Any]], workflow: str | None
) -> list[dict[str, Any]]:
    """Stamp the X-RunLedger-Workflow header on run_start events without a workflow.

    The pipeline resolves it inside the sending workspace, so a foreign id is ignored.
    """
    if workflow:
        for event in events:
            if event.get("event_type") == "run_start" and not (
                event.get("workflow_id") or event.get("workflow")
            ):
                event["workflow"] = workflow.strip()[:255]
    return events


def _queue_events(workspace_id: str, events: list[dict[str, object]]) -> int:
    if not events:
        return 0
    process_events_task.delay(
        workspace_id=workspace_id,
        events=events,
    )
    return len(events)


@router.post("/events", status_code=202, dependencies=[Depends(require_workspace_writer)])
async def ingest_event(
    event: IngestEvent,
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
    x_runledger_workflow: WorkflowHeader = None,
) -> dict[str, int]:
    """Ingest a single event. Returns 202 immediately; processing is async."""
    accepted = _queue_events(
        str(workspace.id),
        apply_workflow_header(  # type: ignore[arg-type]
            attribute_to_sending_key(request, [event.model_dump(mode="json")]),
            x_runledger_workflow,
        ),
    )
    log.debug("event_accepted", workspace_id=str(workspace.id), event_type=event.event_type)
    return {"accepted": accepted}


@router.post("/batch", status_code=202, dependencies=[Depends(require_workspace_writer)])
async def ingest_batch(
    payload: BatchIngestRequest,
    request: Request,
    workspace: WorkspaceDep,
    db: DbDep,
    x_runledger_workflow: WorkflowHeader = None,
) -> dict[str, int]:
    """Ingest a batch of events. Returns 202 immediately."""
    accepted = _queue_events(
        str(workspace.id),
        apply_workflow_header(  # type: ignore[arg-type]
            attribute_to_sending_key(request, [e.model_dump(mode="json") for e in payload.events]),
            x_runledger_workflow,
        ),
    )
    log.debug("batch_accepted", workspace_id=str(workspace.id), count=accepted)
    return {"accepted": accepted}


@router.post("/signed", status_code=202)
async def ingest_signed_webhook(
    request: Request,
    db: DbDep,
    redis: Annotated[Redis, Depends(get_redis)],
    x_runledger_signature: str = Header(..., alias="X-RunLedger-Signature"),
    x_runledger_timestamp: str = Header(..., alias="X-RunLedger-Timestamp"),
    x_runledger_nonce: str = Header("", alias="X-RunLedger-Nonce"),
) -> dict[str, int]:
    """
    Ingest a signed webhook payload — for tools that can only fire webhooks.

    There is deliberately no unsigned variant: the body names the destination
    workspace, so the HMAC signature is what proves the sender may write to it.

    Signature: hex(HMAC_SHA256(workspace_secret,
    "<workspace_id>.<timestamp>.<nonce>." + raw_body)). The workspace secret comes
    from ``GET /ingest/v1/signing-secret``; each nonce is accepted once.
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
    await verify_signed_ingest(
        redis,
        workspace_id=str(payload.workspace_id),
        version=int(getattr(workspace, "ingest_signing_version", 1) or 1),
        timestamp=x_runledger_timestamp,
        nonce=x_runledger_nonce,
        body=raw_body,
        signature=x_runledger_signature,
    )
    accepted = _queue_events(
        str(workspace.id),
        # Signed webhooks carry no key: strip any client-claimed api_key_id.
        attribute_to_sending_key(request, [e.model_dump(mode="json") for e in payload.events]),  # type: ignore[arg-type]
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


# ── Dead letters ───────────────────────────────────────────────────────────────
# Events the pipeline could not apply. Workspace admins inspect, replay (re-queue
# through the normal pipeline, which is idempotent) or discard them.

AdminDep = Annotated[tuple[Any, ...], Depends(require_workspace_admin)]


async def _get_dead_letter(
    db: AsyncSession, workspace_id: Any, item_id: uuid.UUID
) -> IngestDeadLetter:
    item = await db.get(IngestDeadLetter, item_id)
    if item is None or item.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dead letter not found")
    return item


def _requeue(workspace_id: Any, items: list[IngestDeadLetter]) -> int:
    events = [{**item.event, "_dead_letter_id": str(item.id)} for item in items]
    return _queue_events(str(workspace_id), events)  # type: ignore[arg-type]


@router.get("/dead-letters", response_model=DeadLetterList)
async def list_dead_letters(
    auth: AdminDep,
    db: DbDep,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(pending|replayed|discarded)$")
    ] = "pending",
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DeadLetterList:
    """List events the pipeline failed to apply (newest first)."""
    workspace = auth[0]
    filters = [IngestDeadLetter.workspace_id == workspace.id]
    if status_filter:
        filters.append(IngestDeadLetter.status == status_filter)
    total = (
        await db.execute(select(func.count()).select_from(IngestDeadLetter).where(*filters))
    ).scalar_one()
    rows = (
        await db.execute(
            select(IngestDeadLetter)
            .where(*filters)
            .order_by(IngestDeadLetter.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    return DeadLetterList(
        items=[DeadLetterResponse.model_validate(r) for r in rows], total=int(total)
    )


@router.get("/dead-letters/{item_id}", response_model=DeadLetterResponse)
async def get_dead_letter(item_id: uuid.UUID, auth: AdminDep, db: DbDep) -> DeadLetterResponse:
    return DeadLetterResponse.model_validate(await _get_dead_letter(db, auth[0].id, item_id))


@router.post("/dead-letters/{item_id}/replay", response_model=DeadLetterReplayResult)
async def replay_dead_letter(
    item_id: uuid.UUID, auth: AdminDep, db: DbDep
) -> DeadLetterReplayResult:
    """Re-queue one event. It is marked ``replayed`` when the pipeline applies it."""
    item = await _get_dead_letter(db, auth[0].id, item_id)
    if item.status == "replayed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Event was already replayed")
    return DeadLetterReplayResult(requeued=_requeue(auth[0].id, [item]))


@router.post("/dead-letters/replay", response_model=DeadLetterReplayResult)
async def replay_pending_dead_letters(
    auth: AdminDep,
    db: DbDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> DeadLetterReplayResult:
    """Re-queue up to ``limit`` pending events, oldest first."""
    workspace = auth[0]
    items = list(
        (
            await db.execute(
                select(IngestDeadLetter)
                .where(
                    IngestDeadLetter.workspace_id == workspace.id,
                    IngestDeadLetter.status == "pending",
                )
                .order_by(IngestDeadLetter.created_at.asc())
                .limit(limit)
            )
        ).scalars()
    )
    return DeadLetterReplayResult(requeued=_requeue(workspace.id, items) if items else 0)


@router.delete("/dead-letters/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_dead_letter(item_id: uuid.UUID, auth: AdminDep, db: DbDep) -> None:
    """Discard an event (kept as ``discarded`` for the audit trail until retention)."""
    workspace, user = auth[0], auth[1]
    item = await _get_dead_letter(db, workspace.id, item_id)
    item.status = "discarded"
    await emit_audit_event(
        db,
        workspace.id,
        "ingest.dead_letter.discarded",
        actor_user_id=getattr(user, "id", None),
        target_type="ingest_dead_letter",
        target_id=str(item.id),
        before={"event_type": item.event_type, "error": item.error[:500]},
    )
    await db.commit()


# ── Signed-ingest secret (per workspace) ───────────────────────────────────────


@router.get("/signing-secret")
async def get_signing_secret(auth: AdminDep) -> dict[str, Any]:
    """This workspace's secret for ``POST /ingest/v1/signed`` (workspace admins)."""
    workspace = auth[0]
    version = int(getattr(workspace, "ingest_signing_version", 1) or 1)
    return {
        "workspace_id": str(workspace.id),
        "version": version,
        "secret": workspace_signing_secret(workspace.id, version),
        "signature": "hex(HMAC_SHA256(secret, '<workspace_id>.<timestamp>.<nonce>.' + body))",
        "headers": ["X-RunLedger-Signature", "X-RunLedger-Timestamp", "X-RunLedger-Nonce"],
    }


@router.post("/signing-secret/rotate")
async def rotate_signing_secret(auth: AdminDep, db: DbDep) -> dict[str, Any]:
    """Rotate the workspace's signing secret; the previous one stops working at once."""
    workspace, user = auth[0], auth[1]
    target = await db.get(Workspace, workspace.id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    target.ingest_signing_version = int(target.ingest_signing_version or 1) + 1
    await emit_audit_event(
        db,
        target.id,
        "ingest.signing_secret.rotated",
        actor_user_id=getattr(user, "id", None),
        target_type="workspace",
        target_id=str(target.id),
        after={"version": target.ingest_signing_version},
    )
    await db.commit()
    return {
        "workspace_id": str(target.id),
        "version": target.ingest_signing_version,
        "secret": workspace_signing_secret(target.id, target.ingest_signing_version),
    }
