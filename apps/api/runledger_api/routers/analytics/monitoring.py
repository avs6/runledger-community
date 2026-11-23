"""Monitoring feeds with server-side time ranges and paging (review O-18).

The Monitoring page used to fetch the newest 100 rows of each feed and filter the
time preset in the browser, so "30 days" really meant "the last 100 events". These
endpoints apply ``from``/``to``, type and search filters in SQL and page with
``limit``/``offset`` plus ``X-Total-Count``.

Access matches the source feeds: security events for any workspace reader; alert
firings and gateway requests for org admins (as ``/alerts/history`` and
``/gateway/requests``).
"""

from __future__ import annotations

from runledger_api.core.deps import require_org_admin
from runledger_api.models.alerts import AlertFiring, AlertRule
from runledger_api.models.gateway import GatewayRequest
from runledger_api.schemas.alerts import AlertFiringResponse, AlertHistoryList
from runledger_api.schemas.gateway import GatewayRequestList, GatewayRequestResponse
from runledger_api.schemas.tools import SecurityEventList, SecurityEventResponse

from ._shared import *  # noqa: F403

OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]


def _window(from_dt: str | None, to_dt: str | None) -> tuple[datetime, datetime]:
    t_to = _parse_dt(to_dt, _default_to())
    return _parse_dt(from_dt, t_to - timedelta(days=7)), t_to


@router.get("/monitoring/security-events", response_model=SecurityEventList)
async def monitoring_security_events(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    event_type: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SecurityEventList:
    t_from, t_to = _window(from_dt, to_dt)
    where: list[Any] = [
        SecurityEvent.workspace_id == workspace.id,
        SecurityEvent.detected_at >= t_from,
        SecurityEvent.detected_at < t_to,
    ]
    if event_type:
        where.append(SecurityEvent.event_type == event_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        where.append(
            or_(
                SecurityEvent.event_type.ilike(like),
                SecurityEvent.tool_name.ilike(like),
                SecurityEvent.end_user_id.ilike(like),
            )
        )
    total = (await db.execute(select(func.count(SecurityEvent.id)).where(*where))).scalar_one()
    response.headers["X-Total-Count"] = str(total)
    rows = (
        await db.execute(
            select(SecurityEvent)
            .where(*where)
            .order_by(SecurityEvent.detected_at.desc(), SecurityEvent.id)
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    return SecurityEventList(
        items=[
            SecurityEventResponse(
                id=str(e.id),
                workspace_id=str(e.workspace_id),
                event_type=e.event_type,
                tool_name=e.tool_name,
                end_user_id=e.end_user_id,
                run_id=str(e.run_id) if e.run_id else None,
                details=e.details or {},
                detected_at=e.detected_at,
            )
            for e in rows
        ]
    )


@router.get("/monitoring/alerts", response_model=AlertHistoryList)
async def monitoring_alerts(
    auth: OrgAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    state: Annotated[str | None, Query(pattern="^(firing|resolved)$")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AlertHistoryList:
    workspace: Workspace = auth[0]
    t_from, t_to = _window(from_dt, to_dt)
    where: list[Any] = [
        AlertFiring.workspace_id == workspace.id,
        AlertFiring.fired_at >= t_from,
        AlertFiring.fired_at < t_to,
    ]
    if state == "firing":
        where.append(AlertFiring.resolved_at.is_(None))
    elif state == "resolved":
        where.append(AlertFiring.resolved_at.is_not(None))
    if q and q.strip():
        where.append(AlertRule.name.ilike(f"%{q.strip()}%"))
    base = select(AlertFiring, AlertRule.name.label("rule_name")).join(
        AlertRule, AlertFiring.rule_id == AlertRule.id
    )
    total = (
        await db.execute(
            select(func.count(AlertFiring.id))
            .join(AlertRule, AlertFiring.rule_id == AlertRule.id)
            .where(*where)
        )
    ).scalar_one()
    response.headers["X-Total-Count"] = str(total)
    rows = (
        await db.execute(
            base.where(*where)
            .order_by(AlertFiring.fired_at.desc(), AlertFiring.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return AlertHistoryList(
        items=[
            AlertFiringResponse(
                id=firing.id,
                rule_id=firing.rule_id,
                workspace_id=firing.workspace_id,
                fired_at=firing.fired_at,
                metric_value=firing.metric_value,
                resolved_at=firing.resolved_at,
                rule_name=rule_name,
            )
            for firing, rule_name in rows
        ]
    )


@router.get("/monitoring/gateway-requests", response_model=GatewayRequestList)
async def monitoring_gateway_requests(
    auth: OrgAdminDep,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    from_dt: Annotated[str | None, Query(alias="from")] = None,
    to_dt: Annotated[str | None, Query(alias="to")] = None,
    status: Annotated[str | None, Query(max_length=32)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GatewayRequestList:
    workspace: Workspace = auth[0]
    t_from, t_to = _window(from_dt, to_dt)
    where: list[Any] = [
        GatewayRequest.workspace_id == workspace.id,
        GatewayRequest.created_at >= t_from,
        GatewayRequest.created_at < t_to,
    ]
    if status:
        where.append(GatewayRequest.status == status)
    if q and q.strip():
        like = f"%{q.strip()}%"
        where.append(
            or_(GatewayRequest.model_requested.ilike(like), GatewayRequest.model_used.ilike(like))
        )
    total = (await db.execute(select(func.count(GatewayRequest.id)).where(*where))).scalar_one()
    response.headers["X-Total-Count"] = str(total)
    rows = (
        await db.execute(
            select(GatewayRequest)
            .where(*where)
            .order_by(GatewayRequest.created_at.desc(), GatewayRequest.id)
            .limit(limit)
            .offset(offset)
        )
    ).scalars()
    return GatewayRequestList(
        items=[GatewayRequestResponse.model_validate(r) for r in rows], total=total
    )
