"""
API Playground.

Prefix: /playground
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /playground/sessions                    Create a session
GET    /playground/sessions                    List sessions
GET    /playground/sessions/{id}               Get session detail
PUT    /playground/sessions/{id}               Update session
DELETE /playground/sessions/{id}               Delete session
POST   /playground/send                        Send a request
GET    /playground/history                     Recent requests
GET    /playground/history/{id}                Get request detail
GET    /playground/models                      Route aliases to pick from
POST   /playground/compare                     Compare models side-by-side

Send and compare run through gateway-rs with the caller API key, so Playground
traffic gets the same governance, routing, metering and run records as production
(review B-10).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_writer
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.playground import PlaygroundRequest, PlaygroundSession
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.playground import (
    PlaygroundCompareRequest,
    PlaygroundCompareResponse,
    PlaygroundModel,
    PlaygroundModelList,
    PlaygroundRequestListResponse,
    PlaygroundRequestResponse,
    PlaygroundSendRequest,
    PlaygroundSessionCreate,
    PlaygroundSessionListResponse,
    PlaygroundSessionResponse,
    PlaygroundSessionUpdate,
)
from runledger_api.services import gateway_client

log = structlog.get_logger()
router = APIRouter(prefix="/playground", tags=["playground"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _session_to_response(s: PlaygroundSession) -> PlaygroundSessionResponse:
    return PlaygroundSessionResponse(
        id=s.id,
        workspace_id=s.workspace_id,
        name=s.name,
        system_prompt=s.system_prompt,
        mode=s.mode,
        is_favorite=s.is_favorite,
        config=s.config or {},
        created_by=s.created_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _request_to_response(r: PlaygroundRequest) -> PlaygroundRequestResponse:
    return PlaygroundRequestResponse(
        id=r.id,
        workspace_id=r.workspace_id,
        session_id=r.session_id,
        model=r.model,
        provider=r.provider,
        system_prompt=r.system_prompt,
        user_prompt=r.user_prompt,
        parameters=r.parameters or {},
        response_text=r.response_text,
        input_tokens=r.input_tokens,
        output_tokens=r.output_tokens,
        cost_usd=r.cost_usd,
        latency_ms=r.latency_ms,
        status=r.status,
        route_decision=r.route_decision,
        error=r.error,
        gateway_request_id=r.gateway_request_id,
        run_id=r.run_id,
        created_at=r.created_at,
    )


# ── Sessions ───────────────────────────────────────────────────────────────


@router.post(
    "/sessions",
    response_model=PlaygroundSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def create_session(
    body: PlaygroundSessionCreate, ws: WorkspaceDep, db: DbDep
) -> PlaygroundSessionResponse:
    sess = PlaygroundSession(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name=body.name,
        system_prompt=body.system_prompt,
        mode=body.mode,
        config=body.config,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return _session_to_response(sess)


@router.get(
    "/sessions",
    response_model=PlaygroundSessionListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_sessions(
    ws: WorkspaceDep,
    db: DbDep,
    favorites_only: bool = Query(False),
    access_group_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PlaygroundSessionListResponse:
    q = select(PlaygroundSession).where(PlaygroundSession.workspace_id == ws.id)
    count_q = select(func.count(PlaygroundSession.id)).where(
        PlaygroundSession.workspace_id == ws.id
    )
    if favorites_only:
        q = q.where(PlaygroundSession.is_favorite.is_(True))
        count_q = count_q.where(PlaygroundSession.is_favorite.is_(True))
    if access_group_id:
        import uuid as _uuid

        from runledger_api.models.access_groups import AccessGroupMember

        member_rows = (
            (
                await db.execute(
                    select(AccessGroupMember.user_id).where(
                        AccessGroupMember.group_id == _uuid.UUID(access_group_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        member_ids = [str(uid) for uid in member_rows]
        q = q.where(PlaygroundSession.created_by.in_(member_ids))
        count_q = count_q.where(PlaygroundSession.created_by.in_(member_ids))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (
            await db.execute(
                q.order_by(PlaygroundSession.updated_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return PlaygroundSessionListResponse(
        sessions=[_session_to_response(s) for s in rows],
        total=total,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=PlaygroundSessionResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_session(
    session_id: uuid.UUID, ws: WorkspaceDep, db: DbDep
) -> PlaygroundSessionResponse:
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == ws.id,
        )
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return _session_to_response(sess)


@router.put(
    "/sessions/{session_id}",
    response_model=PlaygroundSessionResponse,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def update_session(
    session_id: uuid.UUID,
    body: PlaygroundSessionUpdate,
    ws: WorkspaceDep,
    db: DbDep,
) -> PlaygroundSessionResponse:
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == ws.id,
        )
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(sess, field, val)
    sess.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(sess)
    return _session_to_response(sess)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def delete_session(session_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == ws.id,
        )
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    await db.delete(sess)
    await db.commit()


# ── Send Request ───────────────────────────────────────────────────────────

# Sampling parameters the Playground forwards to the gateway; anything else is dropped.
_ALLOWED_PARAMS = (
    "temperature",
    "max_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "seed",
    "stop",
)


def _gateway_params(parameters: dict[str, Any]) -> dict[str, Any]:
    return {k: parameters[k] for k in _ALLOWED_PARAMS if parameters.get(k) is not None}


def _messages(system_prompt: str | None, user_prompt: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _require_bearer(request: Request) -> str:
    authorization = gateway_client.bearer_from_headers(request.headers)
    if authorization is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Playground calls run through the gateway with your API key; send it as a Bearer token",
        )
    return authorization


def _record(
    ws: Workspace,
    outcome: gateway_client.GatewayCallResult,
    *,
    model: str,
    system_prompt: str | None,
    user_prompt: str,
    parameters: dict[str, Any],
    session_id: uuid.UUID | None,
    provider: str | None = None,
) -> PlaygroundRequest:
    """Persist what the gateway really did with one Playground prompt."""
    return PlaygroundRequest(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        session_id=session_id,
        model=model,
        provider=provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        parameters=parameters,
        status="completed" if outcome.ok else "failed",
        response_text=outcome.text,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        cost_usd=outcome.cost_usd,
        latency_ms=outcome.latency_ms,
        route_decision=(f"cache:{outcome.cache}" if outcome.cache else outcome.model),
        error=None if outcome.ok else f"[{outcome.status_code}] {outcome.error}",
        run_id=outcome.run_id,
    )


@router.get(
    "/models",
    response_model=PlaygroundModelList,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_models(ws: WorkspaceDep, db: DbDep) -> PlaygroundModelList:
    """Model choices for the Playground: this workspace's active gateway route aliases."""
    aliases = await gateway_client.list_route_aliases(db, ws.id)
    return PlaygroundModelList(items=[PlaygroundModel(**a) for a in aliases])


@router.post(
    "/send",
    response_model=PlaygroundRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def send_request(
    body: PlaygroundSendRequest, request: Request, ws: WorkspaceDep, db: DbDep
) -> PlaygroundRequestResponse:
    """Run one prompt through the gateway (governance, routing, metering, a recorded run)."""
    authorization = _require_bearer(request)
    outcome = await gateway_client.chat_completion(
        authorization,
        model=body.model,
        messages=_messages(body.system_prompt, body.user_prompt),
        params=_gateway_params(body.parameters),
        metadata={"feature_tag": "playground", "source": "playground"},
        tags=["playground"],
    )
    outcome = await gateway_client.attach_run(db, ws.id, outcome)
    req = _record(
        ws,
        outcome,
        model=body.model,
        system_prompt=body.system_prompt,
        user_prompt=body.user_prompt,
        parameters=body.parameters,
        session_id=body.session_id,
        provider=body.provider,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _request_to_response(req)


# ── History ────────────────────────────────────────────────────────────────


@router.get(
    "/history",
    response_model=PlaygroundRequestListResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def list_history(
    ws: WorkspaceDep,
    db: DbDep,
    session_id: uuid.UUID | None = Query(None),
    model: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PlaygroundRequestListResponse:
    q = select(PlaygroundRequest).where(PlaygroundRequest.workspace_id == ws.id)
    count_q = select(func.count(PlaygroundRequest.id)).where(
        PlaygroundRequest.workspace_id == ws.id
    )
    if session_id:
        q = q.where(PlaygroundRequest.session_id == session_id)
        count_q = count_q.where(PlaygroundRequest.session_id == session_id)
    if model:
        q = q.where(PlaygroundRequest.model == model)
        count_q = count_q.where(PlaygroundRequest.model == model)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        (
            await db.execute(
                q.order_by(PlaygroundRequest.created_at.desc()).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return PlaygroundRequestListResponse(
        requests=[_request_to_response(r) for r in rows],
        total=total,
    )


@router.get(
    "/history/{request_id}",
    response_model=PlaygroundRequestResponse,
    dependencies=[Depends(analytics_rate_limit)],
)
async def get_request(
    request_id: uuid.UUID, ws: WorkspaceDep, db: DbDep
) -> PlaygroundRequestResponse:
    result = await db.execute(
        select(PlaygroundRequest).where(
            PlaygroundRequest.id == request_id,
            PlaygroundRequest.workspace_id == ws.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return _request_to_response(req)


# ── Compare ────────────────────────────────────────────────────────────────


@router.post(
    "/compare",
    response_model=PlaygroundCompareResponse,
    dependencies=[Depends(require_workspace_writer), Depends(management_rate_limit)],
)
async def compare_models(
    body: PlaygroundCompareRequest, request: Request, ws: WorkspaceDep, db: DbDep
) -> PlaygroundCompareResponse:
    """Send the same prompt to 2-5 route aliases through the gateway, side by side."""
    authorization = _require_bearer(request)
    group = str(uuid.uuid4())
    outcomes = await asyncio.gather(
        *[
            gateway_client.chat_completion(
                authorization,
                model=model_name,
                messages=_messages(body.system_prompt, body.user_prompt),
                params=_gateway_params(body.parameters),
                metadata={"feature_tag": "playground", "source": "playground.compare"},
                tags=["playground"],
            )
            for model_name in body.models
        ]
    )
    results: list[PlaygroundRequest] = []
    for model_name, outcome in zip(body.models, outcomes, strict=True):
        attached = await gateway_client.attach_run(db, ws.id, outcome)
        req = _record(
            ws,
            attached,
            model=model_name,
            system_prompt=body.system_prompt,
            user_prompt=body.user_prompt,
            parameters={**body.parameters, "compare_group": group},
            session_id=body.session_id,
        )
        db.add(req)
        results.append(req)

    await db.commit()
    for r in results:
        await db.refresh(r)

    return PlaygroundCompareResponse(
        compare_group=group,
        results=[_request_to_response(r) for r in results],
    )
