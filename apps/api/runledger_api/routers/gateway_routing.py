from __future__ import annotations

from types import SimpleNamespace

from fastapi import APIRouter, Response

from runledger_api.core import role_matrix
from runledger_api.core.deps import require_workspace_admin
from runledger_api.core.pagination import PageDep, paginate
from runledger_api.schemas.gateway import (
    ROUTE_CONFIG_FIELDS,
    GatewayRoleMatrixResponse,
    GatewayRouteChangePreview,
    GatewayRouteFieldChange,
    GatewayRoutePreviewCandidate,
    GatewayRoutePreviewRequest,
    GatewayRoutePreviewResponse,
)
from runledger_api.services.admin_audit import audit_change, changed_only, snapshot
from runledger_api.services.gateway_controls import _lookup_model_rates, cost_cap_pricing_error

from .gateway_shared import *

router = APIRouter()

# Role matrix (review G-17): reads need a workspace admin, writes an org admin. Both
# names resolve to the shared dependencies, so overrides and the matrix stay in sync.
RoutesReadDep = Annotated[
    tuple[Workspace, User, Any], Depends(role_matrix.gateway_role("routes", "read"))
]
RoutesWriteDep = Annotated[
    tuple[Workspace, User, TenantUser | None],
    Depends(role_matrix.gateway_role("routes", "write")),
]
assert role_matrix.gateway_role("routes", "read") is require_workspace_admin
assert role_matrix.gateway_role("routes", "write") is require_org_admin

GROUP_FIELDS = (
    "alias",
    "name",
    "description",
    "match_tags",
    "default_tags",
    "strategy_type",
    "strategy_config",
    "is_active",
)
ROUTE_FIELDS = (
    "alias",
    "routing_group_id",
    "provider",
    "target_model",
    "base_url",
    "api_key_env_var",
    "priority",
    "is_active",
    "config",
    "daily_cost_limit_usd",
    "monthly_cost_limit_usd",
    "pii_redaction_enabled",
    "semantic_cache_enabled",
    "context_compiler_enabled",
    "context_compiler_config",
    "intelligent_routing_enabled",
    "routing_config",
    "per_user_rpm_limit",
    "fallback_config",
    "required_tags",
    "excluded_tags",
    "retry_count",
    "timeout_ms",
    "cooldown_seconds",
    "region",
    "mirror_config",
    "health_auto_disable",
)
POLICY_FIELDS = ("alias", "policy_type", "config", "is_active")


@router.get("/role-matrix", response_model=GatewayRoleMatrixResponse)
async def gateway_role_matrix(
    request: Request, workspace: WorkspaceDep, db: DbDep
) -> GatewayRoleMatrixResponse:
    """The gateway admin role matrix and what the caller may do (review G-17)."""
    level = await role_matrix.caller_level(request, workspace, db)
    return GatewayRoleMatrixResponse(
        levels=list(role_matrix.LEVELS),
        matrix={k: dict(v) for k, v in role_matrix.GATEWAY_ROLE_MATRIX.items()},
        caller_level=level,
        capabilities=role_matrix.capabilities(level),
    )


@router.post(
    "/routing-groups",
    response_model=GatewayRoutingGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_routing_group(
    body: GatewayRoutingGroupCreate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = GatewayRoutingGroup(
        workspace_id=workspace.id,
        alias=body.alias,
        name=body.name,
        description=body.description,
        match_tags=body.match_tags,
        default_tags=body.default_tags,
        strategy_type=body.strategy_type,
        strategy_config=body.strategy_config,
        is_active=body.is_active,
    )
    db.add(group)
    await db.flush()
    await audit_change(
        db,
        workspace.id,
        "gateway_routing_group.created",
        auth=auth,
        target_type="gateway_routing_group",
        target_id=group.id,
        after=snapshot(group, GROUP_FIELDS),
    )
    await db.commit()
    await db.refresh(group)
    return _serialize_routing_group(group, [])


@router.get("/routing-groups", response_model=GatewayRoutingGroupList)
async def list_gateway_routing_groups(
    auth: RoutesReadDep,
    db: DbDep,
    alias: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> GatewayRoutingGroupList:
    workspace = auth[0]
    stmt = select(GatewayRoutingGroup).where(GatewayRoutingGroup.workspace_id == workspace.id)
    if alias:
        stmt = stmt.where(GatewayRoutingGroup.alias == alias)
    if not include_inactive:
        stmt = stmt.where(GatewayRoutingGroup.is_active.is_(True))
    stmt = stmt.order_by(
        GatewayRoutingGroup.alias.asc(),
        GatewayRoutingGroup.name.asc(),
        GatewayRoutingGroup.created_at.asc(),
    )
    groups = list((await db.execute(stmt)).scalars().all())
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.workspace_id == workspace.id)
                .order_by(GatewayRoute.alias.asc(), GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    routes_by_group: dict[uuid.UUID, list[GatewayRoute]] = {}
    for route in routes:
        if route.routing_group_id is not None:
            routes_by_group.setdefault(route.routing_group_id, []).append(route)
    return GatewayRoutingGroupList(
        items=[
            _serialize_routing_group(group, routes_by_group.get(group.id, [])) for group in groups
        ]
    )


@router.get(
    "/routing-groups/strategy-comparison",
    response_model=GatewayRoutingStrategyComparison,
)
async def gateway_routing_strategy_comparison(
    auth: RoutesReadDep,
    db: DbDep,
) -> GatewayRoutingStrategyComparison:
    workspace = auth[0]
    groups = list(
        (
            await db.execute(
                select(GatewayRoutingGroup).where(GatewayRoutingGroup.workspace_id == workspace.id)
            )
        )
        .scalars()
        .all()
    )
    group_map = {group.id: group for group in groups}
    routes = list(
        (await db.execute(select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)))
        .scalars()
        .all()
    )
    routes_by_group: dict[uuid.UUID | None, list[GatewayRoute]] = {}
    for route in routes:
        routes_by_group.setdefault(route.routing_group_id, []).append(route)

    rows = (
        await db.execute(
            select(
                GatewayRoute.routing_group_id,
                GatewayRoute.alias,
                func.count(GatewayRequest.id).label("total_requests"),
                func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
                func.count(GatewayRequest.id)
                .filter(GatewayRequest.cache_hit.is_(True))
                .label("cache_hits"),
                func.count(GatewayRequest.id)
                .filter(GatewayRequest.status == "error")
                .label("error_count"),
            )
            .select_from(GatewayRequest)
            .join(GatewayRoute, GatewayRequest.route_id == GatewayRoute.id, isouter=True)
            .where(GatewayRequest.workspace_id == workspace.id)
            .group_by(GatewayRoute.routing_group_id, GatewayRoute.alias)
        )
    ).all()
    items: list[GatewayRoutingStrategyComparisonItem] = []
    for row in rows:
        total_requests = int(row.total_requests or 0)
        cache_hits = int(row.cache_hits or 0)
        error_count = int(row.error_count or 0)
        group = group_map.get(row.routing_group_id)
        group_routes = routes_by_group.get(row.routing_group_id, [])
        items.append(
            GatewayRoutingStrategyComparisonItem(
                routing_group_id=row.routing_group_id,
                alias=row.alias or "ungrouped",
                group_name=group.name if group is not None else "Ungrouped",
                strategy_type=group.strategy_type if group is not None else "manual",
                total_requests=total_requests,
                cache_hit_rate=Decimal(str(round(cache_hits / total_requests, 4)))
                if total_requests
                else Decimal("0"),
                avg_latency_ms=(
                    Decimal(str(row.avg_latency_ms)).quantize(Decimal("0.01"))
                    if row.avg_latency_ms is not None
                    else None
                ),
                error_rate=Decimal(str(round(error_count / total_requests, 4)))
                if total_requests
                else Decimal("0"),
                active_routes=sum(1 for route in group_routes if route.is_active),
                default_tags=list(group.default_tags or []) if group is not None else [],
                match_tags=list(group.match_tags or []) if group is not None else [],
            )
        )
    return GatewayRoutingStrategyComparison(items=items)


@router.put("/routing-groups/{group_id}", response_model=GatewayRoutingGroupResponse)
async def update_gateway_routing_group(
    group_id: uuid.UUID,
    body: GatewayRoutingGroupUpdate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")

    before = snapshot(group, GROUP_FIELDS)
    if body.alias is not None and body.alias != group.alias:
        # Alias invariant (review G-11): every route in a group shares the group's alias.
        # Renaming a group with member routes would silently break that, so refuse it.
        members = (
            await db.execute(
                select(func.count(GatewayRoute.id)).where(GatewayRoute.routing_group_id == group.id)
            )
        ).scalar_one()
        if members:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{members} route(s) in this group use alias '{group.alias}'; move them "
                "out of the group or change their alias first",
            )
        group.alias = body.alias
    if body.name is not None:
        group.name = body.name
    if "description" in body.model_fields_set:
        group.description = body.description
    if body.match_tags is not None:
        group.match_tags = body.match_tags
    if body.default_tags is not None:
        group.default_tags = body.default_tags
    if body.strategy_type is not None:
        group.strategy_type = body.strategy_type
    if "strategy_config" in body.model_fields_set:
        group.strategy_config = body.strategy_config
    if body.is_active is not None:
        group.is_active = body.is_active
    b, a = changed_only(before, snapshot(group, GROUP_FIELDS))
    group.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "gateway_routing_group.updated",
        auth=auth,
        target_type="gateway_routing_group",
        target_id=group.id,
        before=b,
        after=a,
    )

    await db.commit()
    await db.refresh(group)
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(GatewayRoute.routing_group_id == group.id)
                .order_by(GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    return _serialize_routing_group(group, routes)


@router.delete("/routing-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_routing_group(
    group_id: uuid.UUID,
    auth: RoutesWriteDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")

    grouped_routes = list(
        (await db.execute(select(GatewayRoute).where(GatewayRoute.routing_group_id == group.id)))
        .scalars()
        .all()
    )
    for route in grouped_routes:
        route.routing_group_id = None
    await audit_change(
        db,
        workspace.id,
        "gateway_routing_group.deleted",
        auth=auth,
        target_type="gateway_routing_group",
        target_id=group.id,
        before={
            **snapshot(group, GROUP_FIELDS),
            "ungrouped_route_ids": [str(r.id) for r in grouped_routes],
        },
    )
    await db.delete(group)
    await db.commit()


async def _require_cap_pricing(
    db: AsyncSession, provider: str, model: str, workspace_id: uuid.UUID
) -> None:
    """A cost cap needs a price to be enforced: 422 for an unpriced hosted model
    instead of silently guessing one at request time (review G-17)."""
    reason = await cost_cap_pricing_error(
        db, provider=provider, model=model, workspace_id=workspace_id
    )
    if reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, reason)


def _validate_route_target(
    auth: Any, provider: str | None, base_url: str | None, api_key_env_var: str | None
) -> None:
    """Credential and host rules for a route (review S-02), see provider_credentials."""
    from runledger_api.services.provider_credentials import (  # noqa: PLC0415
        RouteConfigRejected,
        validate_route,
    )

    user = auth[1] if len(auth) > 1 else None
    try:
        validate_route(
            provider=provider,
            base_url=base_url,
            api_key_env_var=api_key_env_var,
            is_platform_admin=bool(getattr(user, "is_platform_admin", False)),
        )
    except RouteConfigRejected as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/routes", response_model=GatewayRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_gateway_route(
    body: GatewayRouteCreate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    _validate_route_target(auth, body.provider, body.base_url, body.api_key_env_var)
    if body.daily_cost_limit_usd is not None or body.monthly_cost_limit_usd is not None:
        await _require_cap_pricing(db, body.provider, body.target_model, workspace.id)
    routing_group_name: str | None = None
    if body.routing_group_id is not None:
        group = await db.get(GatewayRoutingGroup, body.routing_group_id)
        if group is None or group.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
        if group.alias != body.alias:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Routing group alias must match route alias"
            )
        routing_group_name = group.name
    route = GatewayRoute(
        workspace_id=workspace.id,
        routing_group_id=body.routing_group_id,
        alias=body.alias,
        provider=body.provider,
        target_model=body.target_model,
        base_url=body.base_url,
        api_key_env_var=body.api_key_env_var,
        priority=body.priority,
        config=body.config,
        daily_cost_limit_usd=body.daily_cost_limit_usd,
        monthly_cost_limit_usd=body.monthly_cost_limit_usd,
        pii_redaction_enabled=body.pii_redaction_enabled,
        semantic_cache_enabled=body.semantic_cache_enabled,
        context_compiler_enabled=body.context_compiler_enabled,
        context_compiler_config=body.context_compiler_config,
        intelligent_routing_enabled=body.intelligent_routing_enabled,
        routing_config=body.routing_config,
        per_user_rpm_limit=body.per_user_rpm_limit,
        fallback_config=body.fallback_config,
        required_tags=body.required_tags,
        excluded_tags=body.excluded_tags,
        retry_count=body.retry_count,
        timeout_ms=body.timeout_ms,
        cooldown_seconds=body.cooldown_seconds,
        region=body.region,
        mirror_config=body.mirror_config,
        health_auto_disable=body.health_auto_disable,
    )
    db.add(route)
    await db.flush()
    await audit_change(
        db,
        workspace.id,
        "gateway_route.created",
        auth=auth,
        target_type="gateway_route",
        target_id=route.id,
        after=snapshot(route, ROUTE_FIELDS),
    )
    await db.commit()
    await db.refresh(route)
    return _serialize_gateway_route(route, routing_group_name=routing_group_name)


@router.get("/routes", response_model=GatewayRouteList)
async def list_gateway_routes(
    auth: RoutesReadDep,
    db: DbDep,
    page: PageDep,
    response: Response,
    include_inactive: bool = Query(False),
) -> GatewayRouteList:
    workspace = auth[0]
    stmt = select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(GatewayRoute.is_active.is_(True))
    stmt = stmt.order_by(
        GatewayRoute.priority.asc(), GatewayRoute.created_at.asc(), GatewayRoute.id
    )
    routes = await paginate(db, stmt, page, response)
    group_names: dict[uuid.UUID, str] = {}
    group_ids = [route.routing_group_id for route in routes if route.routing_group_id is not None]
    if group_ids:
        group_result = await db.execute(
            select(GatewayRoutingGroup.id, GatewayRoutingGroup.name).where(
                GatewayRoutingGroup.id.in_(group_ids)
            )
        )
        group_names = {row.id: row.name for row in group_result.all()}
    return GatewayRouteList(
        items=[
            _serialize_gateway_route(
                route, routing_group_name=group_names.get(route.routing_group_id)
            )
            for route in routes
        ]
    )


def _merge_config(base: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """JSON merge-patch: nested dicts merge, a ``None`` value removes the key."""
    out = dict(base or {})
    for key, value in patch.items():
        if value is None:
            out.pop(key, None)
        elif isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_config(out[key], value)
        else:
            out[key] = value
    return out


# Set when sent and not null (null means "leave as is" for these).
_ROUTE_NON_NULL_FIELDS = (
    "alias",
    "target_model",
    "priority",
    "is_active",
    "pii_redaction_enabled",
    "semantic_cache_enabled",
    "context_compiler_enabled",
    "intelligent_routing_enabled",
    "required_tags",
    "excluded_tags",
    "retry_count",
    "cooldown_seconds",
    "health_auto_disable",
)
# Set whenever sent; null clears the value.
_ROUTE_NULLABLE_FIELDS = (
    "base_url",
    "api_key_env_var",
    "daily_cost_limit_usd",
    "monthly_cost_limit_usd",
    "per_user_rpm_limit",
    "timeout_ms",
    "region",
)


def _planned_route_changes(route: GatewayRoute, body: GatewayRouteUpdate) -> dict[str, Any]:
    """Field -> new value for every field this update would change (no I/O).

    Shared by the update itself and the change preview, so the diff the dashboard shows
    is exactly what saving does. ``routing_group_id`` is handled by the caller.
    """
    sent = body.model_fields_set
    planned: dict[str, Any] = {}
    for name in _ROUTE_NON_NULL_FIELDS:
        value = getattr(body, name)
        if name in sent and value is not None:
            planned[name] = value
    for name in _ROUTE_NULLABLE_FIELDS:
        if name in sent:
            planned[name] = getattr(body, name)
    for name in ROUTE_CONFIG_FIELDS:
        if name not in sent:
            continue
        value = getattr(body, name)
        if body.merge_configs and value is not None:
            planned[name] = _merge_config(getattr(route, name), value)
        else:
            planned[name] = value
    return {k: v for k, v in planned.items() if getattr(route, k) != v}


async def _resolve_route_group(
    db: AsyncSession,
    workspace: Workspace,
    route: GatewayRoute,
    body: GatewayRouteUpdate,
    planned: dict[str, Any],
) -> GatewayRoutingGroup | None:
    """Validate the route's group after the update (alias invariant, review G-11).

    Returns the group the route will belong to (or None). Raises 404 for a foreign or
    missing group and 400 when the route alias and its group alias would differ.
    """
    target_alias = planned.get("alias", route.alias)
    if "routing_group_id" in body.model_fields_set:
        if body.routing_group_id is None:
            return None
        group = await db.get(GatewayRoutingGroup, body.routing_group_id)
        if group is None or group.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
    elif route.routing_group_id is not None:
        group = await db.get(GatewayRoutingGroup, route.routing_group_id)
        if group is None:
            return None
    else:
        return None
    if group.alias != target_alias:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Routing group alias '{group.alias}' must match route alias '{target_alias}'; "
            "move the route out of the group to change its alias",
        )
    return group


def _route_change_warnings(route: GatewayRoute, planned: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if "alias" in planned:
        warnings.append(
            f"Clients calling '{route.alias}' stop reaching this route; "
            f"'{planned['alias']}' starts reaching it on the next request."
        )
    if planned.get("is_active") is False:
        warnings.append("The route stops serving traffic on the next request.")
    if "target_model" in planned:
        warnings.append("Cost caps and pricing are re-checked against the new model.")
    if "fallback_config" in planned and not planned["fallback_config"]:
        warnings.append("All fallbacks are removed from this route.")
    return warnings


@router.put("/routes/{route_id}", response_model=GatewayRouteResponse)
async def update_gateway_route(
    route_id: uuid.UUID,
    body: GatewayRouteUpdate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")

    planned = _planned_route_changes(route, body)
    group = await _resolve_route_group(db, workspace, route, body, planned)
    if {"base_url", "api_key_env_var"} & planned.keys():
        _validate_route_target(
            auth,
            route.provider,
            planned.get("base_url", route.base_url),
            planned.get("api_key_env_var", route.api_key_env_var),
        )
    before = snapshot(route, ROUTE_FIELDS)
    for name, value in planned.items():
        setattr(route, name, value)
    route.routing_group_id = group.id if group is not None else None

    caps_touched = bool(
        {"daily_cost_limit_usd", "monthly_cost_limit_usd", "target_model"} & planned.keys()
    )
    if caps_touched and (
        route.daily_cost_limit_usd is not None or route.monthly_cost_limit_usd is not None
    ):
        await _require_cap_pricing(db, route.provider, route.target_model, workspace.id)

    b, a = changed_only(before, snapshot(route, ROUTE_FIELDS))
    if a:
        await audit_change(
            db,
            workspace.id,
            "gateway_route.updated",
            auth=auth,
            target_type="gateway_route",
            target_id=route.id,
            before=b,
            after=a,
        )
    await db.commit()
    await db.refresh(route)
    return _serialize_gateway_route(
        route, routing_group_name=group.name if group is not None else None
    )


@router.post("/routes/{route_id}/preview-change", response_model=GatewayRouteChangePreview)
async def preview_gateway_route_change(
    route_id: uuid.UUID,
    body: GatewayRouteUpdate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> GatewayRouteChangePreview:
    """The field-level diff a PUT with this body would apply, validated, without saving."""
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    planned = _planned_route_changes(route, body)
    group = await _resolve_route_group(db, workspace, route, body, planned)
    new_group_id = group.id if group is not None else None
    if new_group_id != route.routing_group_id:
        planned["routing_group_id"] = new_group_id
    if {"base_url", "api_key_env_var"} & planned.keys():
        _validate_route_target(
            auth,
            route.provider,
            planned.get("base_url", route.base_url),
            planned.get("api_key_env_var", route.api_key_env_var),
        )
    before = snapshot(route, ROUTE_FIELDS)
    after = snapshot(SimpleNamespace(**{**before, **planned}), ROUTE_FIELDS)
    return GatewayRouteChangePreview(
        route_id=route.id,
        changes=[
            GatewayRouteFieldChange(field=name, before=before.get(name), after=after.get(name))
            for name in ROUTE_FIELDS
            if name in planned
        ],
        warnings=_route_change_warnings(route, planned),
    )


async def _latency_by_route(
    db: AsyncSession, workspace_id: uuid.UUID, route_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[Decimal | None, Decimal | None, int]]:
    """p50, p95 latency and sample size per route over the last 7 days of traffic."""
    if not route_ids:
        return {}
    since = datetime.now(UTC) - timedelta(days=7)
    rows = await db.execute(
        select(
            GatewayRequest.route_id,
            func.percentile_cont(0.5).within_group(GatewayRequest.latency_ms),
            func.percentile_cont(0.95).within_group(GatewayRequest.latency_ms),
            func.count(GatewayRequest.id),
        )
        .where(
            GatewayRequest.workspace_id == workspace_id,
            GatewayRequest.route_id.in_(route_ids),
            GatewayRequest.created_at >= since,
            GatewayRequest.latency_ms.is_not(None),
        )
        .group_by(GatewayRequest.route_id)
    )
    out: dict[uuid.UUID, tuple[Decimal | None, Decimal | None, int]] = {}
    for route_id, p50, p95, n in rows.all():
        out[route_id] = (
            Decimal(str(round(float(p50), 1))) if p50 is not None else None,
            Decimal(str(round(float(p95), 1))) if p95 is not None else None,
            int(n or 0),
        )
    return out


@router.post("/routes/preview", response_model=GatewayRoutePreviewResponse)
async def preview_gateway_route(
    body: GatewayRoutePreviewRequest,
    auth: RoutesReadDep,
    db: DbDep,
) -> GatewayRoutePreviewResponse:
    """Test request (dry run): which route an alias resolves to, what it would cost and
    how fast that route has been. Uses the same selection code as the runtime; no
    provider is called and nothing is recorded."""
    workspace = auth[0]
    messages = [{"role": "user", "content": body.prompt}]
    tags = [t.strip() for t in body.tags if t.strip()]
    candidates = await select_routes(
        db, workspace.id, body.model, request_tags=tags, preferred_region=body.region
    )
    chosen, reason = await choose_route_for_alias(
        db, workspace.id, body.model, messages, request_tags=tags, preferred_region=body.region
    )
    policy = (
        await db.execute(
            select(RoutingPolicy).where(
                RoutingPolicy.workspace_id == workspace.id,
                RoutingPolicy.alias == body.model,
                RoutingPolicy.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    est_in = max(1, len(body.prompt) // 4)
    est_out = body.expected_output_tokens
    latency = await _latency_by_route(db, workspace.id, [r.id for r in candidates])
    warnings: list[str] = []
    items: list[GatewayRoutePreviewCandidate] = []
    for route in candidates:
        rates = await _lookup_model_rates(db, route.target_model, route.provider, workspace.id)
        cost = (
            (Decimal(est_in) * rates[0] + Decimal(est_out) * rates[1]) / Decimal(1_000_000)
            if rates is not None
            else None
        )
        p50, p95, n = latency.get(route.id, (None, None, 0))
        items.append(
            GatewayRoutePreviewCandidate(
                route_id=route.id,
                provider=route.provider,
                target_model=route.target_model,
                priority=route.priority,
                region=route.region,
                selected=chosen is not None and route.id == chosen.id,
                est_cost_usd=cost.quantize(Decimal("0.00000001")) if cost is not None else None,
                p50_latency_ms=p50,
                p95_latency_ms=p95,
                sample_size=n,
                note=None if rates is not None else "No price for this model",
            )
        )
    if not candidates:
        warnings.append(f"No active route serves '{body.model}' with these tags and region.")
    selected = next((c for c in items if c.selected), None)
    if selected is not None and selected.est_cost_usd is None:
        warnings.append("The chosen route has no price: cost caps and budgets can't count it.")
    fallback_cfg = (chosen.fallback_config or {}) if chosen is not None else {}
    fallback_aliases = [
        a for a in (fallback_cfg.get("aliases") or []) if isinstance(a, str) and a
    ] + [
        str(r["alias"])
        for r in (fallback_cfg.get("fallbacks") or [])
        if isinstance(r, dict) and r.get("alias")
    ]
    return GatewayRoutePreviewResponse(
        alias=body.model,
        decision_reason=reason,
        policy_type=policy.policy_type if policy is not None else None,
        selected_route_id=chosen.id if chosen is not None else None,
        est_input_tokens=est_in,
        est_output_tokens=est_out,
        est_cost_usd=selected.est_cost_usd if selected is not None else None,
        p50_latency_ms=selected.p50_latency_ms if selected is not None else None,
        fallback_aliases=fallback_aliases,
        candidates=items,
        warnings=warnings,
    )


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_route(
    route_id: uuid.UUID,
    auth: RoutesWriteDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    await audit_change(
        db,
        workspace.id,
        "gateway_route.deleted",
        auth=auth,
        target_type="gateway_route",
        target_id=route.id,
        before=snapshot(route, ROUTE_FIELDS),
    )
    await db.delete(route)
    await db.commit()


async def _validate_policy_routes(
    db: AsyncSession, workspace_id: uuid.UUID, alias: str, config: dict[str, Any] | None
) -> None:
    """Every route a policy names must be this workspace's and serve the policy's alias
    (review G-12). Checks ``weights`` keys, ``canary_route_id`` and ``variants[].route_id``."""
    cfg = config or {}
    named: set[str] = set()
    weights = cfg.get("weights")
    if isinstance(weights, dict):
        named.update(str(k) for k in weights)
    if cfg.get("canary_route_id"):
        named.add(str(cfg["canary_route_id"]))
    variants = cfg.get("variants")
    if isinstance(variants, list):
        named.update(
            str(v["route_id"]) for v in variants if isinstance(v, dict) and v.get("route_id")
        )
    if not named:
        return
    ids: list[uuid.UUID] = []
    for raw in named:
        try:
            ids.append(uuid.UUID(raw))
        except ValueError:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"'{raw}' is not a route id"
            ) from None
    found = {
        row.id: row.alias
        for row in (
            await db.execute(
                select(GatewayRoute.id, GatewayRoute.alias).where(
                    GatewayRoute.workspace_id == workspace_id, GatewayRoute.id.in_(ids)
                )
            )
        ).all()
    }
    for route_id in ids:
        if route_id not in found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Gateway route {route_id} not found")
        if found[route_id] != alias:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Route {route_id} serves '{found[route_id]}', not this policy's alias '{alias}'",
            )


@router.post("/policies", response_model=RoutingPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_policy(
    body: RoutingPolicyCreate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    existing = (
        await db.execute(
            select(RoutingPolicy).where(
                RoutingPolicy.workspace_id == workspace.id,
                RoutingPolicy.alias == body.alias,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Routing policy already exists for alias")
    await _validate_policy_routes(db, workspace.id, body.alias, body.config)
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        alias=body.alias,
        policy_type=body.policy_type,
        config=body.config,
    )
    db.add(policy)
    await db.flush()
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.created",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        after=snapshot(policy, POLICY_FIELDS),
    )
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/policies", response_model=RoutingPolicyList)
async def list_routing_policies(
    auth: RoutesReadDep,
    db: DbDep,
) -> RoutingPolicyList:
    workspace = auth[0]
    items = list(
        (
            await db.execute(
                select(RoutingPolicy)
                .where(RoutingPolicy.workspace_id == workspace.id)
                .order_by(RoutingPolicy.alias.asc(), RoutingPolicy.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return RoutingPolicyList(items=[RoutingPolicyResponse.model_validate(item) for item in items])


@router.put("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def update_routing_policy(
    policy_id: uuid.UUID,
    body: RoutingPolicyUpdate,
    auth: RoutesWriteDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    before = snapshot(policy, POLICY_FIELDS)
    if "config" in body.model_fields_set:
        await _validate_policy_routes(db, workspace.id, policy.alias, body.config)
    if body.policy_type is not None:
        policy.policy_type = body.policy_type
    if "config" in body.model_fields_set:
        policy.config = body.config or {}
    if body.is_active is not None:
        policy.is_active = body.is_active
    b, a = changed_only(before, snapshot(policy, POLICY_FIELDS))
    policy.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.updated",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        before=b,
        after=a,
    )
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_policy(
    policy_id: uuid.UUID,
    auth: RoutesWriteDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.deleted",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        before=snapshot(policy, POLICY_FIELDS),
    )
    await db.delete(policy)
    await db.commit()


@router.get("/policies/{policy_id}/analysis", response_model=RoutingPolicyAnalysisResponse)
async def get_routing_policy_analysis(
    policy_id: uuid.UUID,
    auth: RoutesReadDep,
    db: DbDep,
) -> RoutingPolicyAnalysisResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    analysis = await analyze_routing_policy(db, workspace.id, policy)
    return RoutingPolicyAnalysisResponse(**analysis)


@router.post("/policies/{policy_id}/promote", response_model=RoutingPolicyActionResponse)
async def promote_routing_policy_variant(
    policy_id: uuid.UUID,
    body: RoutingPolicyPromotionRequest,
    auth: RoutesWriteDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    analysis = await analyze_routing_policy(db, workspace.id, policy)
    if policy.policy_type == "ab_test":
        if analysis.get("confidence") == "insufficient_data":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                analysis.get("summary") or "Not enough A/B test traffic to promote a winner",
            )
        significance_p_value = analysis.get("significance_p_value")
        significance_threshold = float((policy.config or {}).get("significance_threshold", 0.05))
        if significance_p_value is None or float(significance_p_value) >= significance_threshold:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A/B result is not yet statistically significant at p<{significance_threshold:.4f}",
            )
    route_id = body.route_id or analysis.get("winner_route_id")
    if route_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No winner available to promote")
    # Ownership + alias check (review G-12): only this workspace's routes for this alias.
    await _validate_policy_routes(db, workspace.id, policy.alias, {"weights": {str(route_id): 1}})
    before = snapshot(policy, POLICY_FIELDS)
    policy.policy_type = "weighted"
    policy.config = {
        "weights": {str(route_id): 1.0},
        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "promoted_from": analysis.get("policy_type"),
        "winner_label": analysis.get("winner_label"),
    }
    policy.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.promoted",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        before=before,
        after=snapshot(policy, POLICY_FIELDS),
    )
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary=f"Promoted {analysis.get('winner_label') or route_id} to 100% traffic.",
        config=policy.config or {},
    )


@router.post("/policies/{policy_id}/rollout/advance", response_model=RoutingPolicyActionResponse)
async def advance_canary_rollout(
    policy_id: uuid.UUID,
    auth: RoutesWriteDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    if policy.policy_type != "canary":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Rollout advance is only supported for canary policies"
        )
    config = dict(policy.config or {})
    stages = (
        config.get("rollout_stages")
        if isinstance(config.get("rollout_stages"), list)
        else [5, 10, 25, 50, 100]
    )
    current_pct = float(config.get("canary_pct", 0.0)) * 100
    next_stage = next((float(stage) for stage in stages if float(stage) > current_pct), None)
    if next_stage is None:
        next_stage = 100.0
    before_pct = (policy.config or {}).get("canary_pct")
    config["canary_pct"] = round(next_stage / 100.0, 4)
    config["last_advanced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    policy.config = config
    policy.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.rollout_advanced",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        before={"canary_pct": before_pct},
        after={"canary_pct": config["canary_pct"]},
    )
    await db.commit()
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary=f"Advanced canary rollout to {next_stage:.0f}%.",
        config=config,
    )


@router.post("/policies/{policy_id}/rollback", response_model=RoutingPolicyActionResponse)
async def rollback_policy_rollout(
    policy_id: uuid.UUID,
    auth: RoutesWriteDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    config = dict(policy.config or {})
    if policy.policy_type == "canary":
        config["canary_pct"] = 0.0
    elif policy.policy_type == "ab_test":
        config["auto_promote"] = False
    config["rollback_triggered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    before = snapshot(policy, POLICY_FIELDS)
    policy.config = config
    policy.updated_at = func.now()
    await audit_change(
        db,
        workspace.id,
        "gateway_policy.rolled_back",
        auth=auth,
        target_type="routing_policy",
        target_id=policy.id,
        before=before,
        after=snapshot(policy, POLICY_FIELDS),
    )
    await db.commit()
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary="Rollback applied to routing policy.",
        config=config,
    )


# ── Get by id (review G-25) ─────────────────────────────────────────────────────
# Declared last so fixed paths such as /routing-groups/strategy-comparison match first.


@router.get("/routes/{route_id}", response_model=GatewayRouteResponse)
async def get_gateway_route(
    route_id: uuid.UUID,
    auth: RoutesReadDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    group_name = None
    if route.routing_group_id is not None:
        group = await db.get(GatewayRoutingGroup, route.routing_group_id)
        group_name = group.name if group is not None else None
    return _serialize_gateway_route(route, routing_group_name=group_name)


@router.get("/policies/{policy_id}", response_model=RoutingPolicyResponse)
async def get_routing_policy(
    policy_id: uuid.UUID,
    auth: RoutesReadDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/routing-groups/{group_id}", response_model=GatewayRoutingGroupResponse)
async def get_gateway_routing_group(
    group_id: uuid.UUID,
    auth: RoutesReadDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(
                    GatewayRoute.workspace_id == workspace.id,
                    GatewayRoute.routing_group_id == group.id,
                )
                .order_by(GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    return _serialize_routing_group(group, routes)
