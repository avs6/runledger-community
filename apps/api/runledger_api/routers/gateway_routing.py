from __future__ import annotations

from fastapi import APIRouter

from .gateway_shared import *

router = APIRouter()

@router.post(
    "/routing-groups",
    response_model=GatewayRoutingGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_routing_group(
    body: GatewayRoutingGroupCreate,
    auth: OrgAdminDep,
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
    await db.commit()
    await db.refresh(group)
    return _serialize_routing_group(group, [])


@router.get("/routing-groups", response_model=GatewayRoutingGroupList)
async def list_gateway_routing_groups(
    auth: OrgAdminDep,
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
        items=[_serialize_routing_group(group, routes_by_group.get(group.id, [])) for group in groups]
    )


@router.get(
    "/routing-groups/strategy-comparison",
    response_model=GatewayRoutingStrategyComparison,
)
async def gateway_routing_strategy_comparison(
    auth: OrgAdminDep,
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
                cache_hit_rate=Decimal(str(round(cache_hits / total_requests, 4))) if total_requests else Decimal("0"),
                avg_latency_ms=(
                    Decimal(str(row.avg_latency_ms)).quantize(Decimal("0.01"))
                    if row.avg_latency_ms is not None
                    else None
                ),
                error_rate=Decimal(str(round(error_count / total_requests, 4))) if total_requests else Decimal("0"),
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
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRoutingGroupResponse:
    workspace = auth[0]
    group = await db.get(GatewayRoutingGroup, group_id)
    if group is None or group.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")

    if body.alias is not None:
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
    group.updated_at = func.now()

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
    auth: OrgAdminDep,
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
    await db.delete(group)
    await db.commit()


@router.post("/routes", response_model=GatewayRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_gateway_route(
    body: GatewayRouteCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    routing_group_name: str | None = None
    if body.routing_group_id is not None:
        group = await db.get(GatewayRoutingGroup, body.routing_group_id)
        if group is None or group.workspace_id != workspace.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
        if group.alias != body.alias:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Routing group alias must match route alias")
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
    await db.commit()
    await db.refresh(route)
    return _serialize_gateway_route(route, routing_group_name=routing_group_name)


@router.get("/routes", response_model=GatewayRouteList)
async def list_gateway_routes(
    auth: OrgAdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> GatewayRouteList:
    workspace = auth[0]
    stmt = select(GatewayRoute).where(GatewayRoute.workspace_id == workspace.id)
    if not include_inactive:
        stmt = stmt.where(GatewayRoute.is_active.is_(True))
    stmt = stmt.order_by(GatewayRoute.priority.asc(), GatewayRoute.created_at.asc())
    result = await db.execute(stmt)
    routes = list(result.scalars().all())
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
            _serialize_gateway_route(route, routing_group_name=group_names.get(route.routing_group_id))
            for route in routes
        ]
    )


@router.put("/routes/{route_id}", response_model=GatewayRouteResponse)
async def update_gateway_route(
    route_id: uuid.UUID,
    body: GatewayRouteUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRouteResponse:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    routing_group_name: str | None = None

    if body.alias is not None:
        route.alias = body.alias
    if "routing_group_id" in body.model_fields_set:
        if body.routing_group_id is None:
            route.routing_group_id = None
        else:
            group = await db.get(GatewayRoutingGroup, body.routing_group_id)
            if group is None or group.workspace_id != workspace.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway routing group not found")
            target_alias = body.alias or route.alias
            if group.alias != target_alias:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Routing group alias must match route alias",
                )
            route.routing_group_id = group.id
            routing_group_name = group.name
    if body.target_model is not None:
        route.target_model = body.target_model
    if body.priority is not None:
        route.priority = body.priority
    if body.is_active is not None:
        route.is_active = body.is_active
    if "base_url" in body.model_fields_set:
        route.base_url = body.base_url
    if "api_key_env_var" in body.model_fields_set:
        route.api_key_env_var = body.api_key_env_var
    if body.config is not None:
        route.config = body.config
    if "daily_cost_limit_usd" in body.model_fields_set:
        route.daily_cost_limit_usd = body.daily_cost_limit_usd
    if "monthly_cost_limit_usd" in body.model_fields_set:
        route.monthly_cost_limit_usd = body.monthly_cost_limit_usd
    if body.pii_redaction_enabled is not None:
        route.pii_redaction_enabled = body.pii_redaction_enabled
    if body.semantic_cache_enabled is not None:
        route.semantic_cache_enabled = body.semantic_cache_enabled
    if body.context_compiler_enabled is not None:
        route.context_compiler_enabled = body.context_compiler_enabled
    if "context_compiler_config" in body.model_fields_set:
        route.context_compiler_config = body.context_compiler_config
    if body.intelligent_routing_enabled is not None:
        route.intelligent_routing_enabled = body.intelligent_routing_enabled
    if "routing_config" in body.model_fields_set:
        route.routing_config = body.routing_config
    if "per_user_rpm_limit" in body.model_fields_set:
        route.per_user_rpm_limit = body.per_user_rpm_limit
    if "fallback_config" in body.model_fields_set:
        route.fallback_config = body.fallback_config
    if body.required_tags is not None:
        route.required_tags = body.required_tags
    if body.excluded_tags is not None:
        route.excluded_tags = body.excluded_tags
    if body.retry_count is not None:
        route.retry_count = body.retry_count
    if "timeout_ms" in body.model_fields_set:
        route.timeout_ms = body.timeout_ms
    if body.cooldown_seconds is not None:
        route.cooldown_seconds = body.cooldown_seconds
    if "region" in body.model_fields_set:
        route.region = body.region
    if "mirror_config" in body.model_fields_set:
        route.mirror_config = body.mirror_config
    if body.health_auto_disable is not None:
        route.health_auto_disable = body.health_auto_disable

    await db.commit()
    await db.refresh(route)
    if route.routing_group_id is not None and routing_group_name is None:
        group = await db.get(GatewayRoutingGroup, route.routing_group_id)
        routing_group_name = group.name if group is not None else None
    return _serialize_gateway_route(route, routing_group_name=routing_group_name)


@router.delete("/routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_route(
    route_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    route = await db.get(GatewayRoute, route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    await db.delete(route)
    await db.commit()


@router.post("/policies", response_model=RoutingPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_policy(
    body: RoutingPolicyCreate,
    auth: OrgAdminDep,
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
    policy = RoutingPolicy(
        workspace_id=workspace.id,
        alias=body.alias,
        policy_type=body.policy_type,
        config=body.config,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.get("/policies", response_model=RoutingPolicyList)
async def list_routing_policies(
    auth: OrgAdminDep,
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
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    if body.policy_type is not None:
        policy.policy_type = body.policy_type
    if "config" in body.model_fields_set:
        policy.config = body.config or {}
    if body.is_active is not None:
        policy.is_active = body.is_active
    policy.updated_at = func.now()
    await db.commit()
    await db.refresh(policy)
    return RoutingPolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_policy(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    await db.delete(policy)
    await db.commit()


@router.get("/policies/{policy_id}/analysis", response_model=RoutingPolicyAnalysisResponse)
async def get_routing_policy_analysis(
    policy_id: uuid.UUID,
    auth: OrgAdminDep,
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
    auth: OrgAdminDep,
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
    policy.policy_type = "weighted"
    policy.config = {
        "weights": {str(route_id): 1.0},
        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "promoted_from": analysis.get("policy_type"),
        "winner_label": analysis.get("winner_label"),
    }
    policy.updated_at = func.now()
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
    auth: OrgAdminDep,
    db: DbDep,
) -> RoutingPolicyActionResponse:
    workspace = auth[0]
    policy = await db.get(RoutingPolicy, policy_id)
    if policy is None or policy.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Routing policy not found")
    if policy.policy_type != "canary":
        raise HTTPException(status.HTTP_409_CONFLICT, "Rollout advance is only supported for canary policies")
    config = dict(policy.config or {})
    stages = config.get("rollout_stages") if isinstance(config.get("rollout_stages"), list) else [5, 10, 25, 50, 100]
    current_pct = float(config.get("canary_pct", 0.0)) * 100
    next_stage = next((float(stage) for stage in stages if float(stage) > current_pct), None)
    if next_stage is None:
        next_stage = 100.0
    config["canary_pct"] = round(next_stage / 100.0, 4)
    config["last_advanced_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    policy.config = config
    policy.updated_at = func.now()
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
    auth: OrgAdminDep,
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
    policy.config = config
    policy.updated_at = func.now()
    await db.commit()
    return RoutingPolicyActionResponse(
        policy_id=policy.id,
        policy_type=policy.policy_type,
        summary="Rollback applied to routing policy.",
        config=config,
    )
