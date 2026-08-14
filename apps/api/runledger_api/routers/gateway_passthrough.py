from __future__ import annotations

from fastapi import APIRouter

from .gateway_shared import *

router = APIRouter()

@router.post(
    "/passthrough",
    response_model=GatewayPassThroughEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_gateway_passthrough_endpoint(
    body: GatewayPassThroughEndpointCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointResponse:
    workspace = auth[0]
    endpoint = GatewayPassThroughEndpoint(
        workspace_id=workspace.id,
        slug=body.slug,
        path_prefix=body.path_prefix,
        upstream_base_url=body.upstream_base_url,
        auth_type=body.auth_type,
        auth_config=body.auth_config,
        header_config=body.header_config,
        default_query=body.default_query,
        timeout_ms=body.timeout_ms,
        rate_limit_rpm=body.rate_limit_rpm,
        cost_per_call_usd=body.cost_per_call_usd,
        is_active=body.is_active,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return GatewayPassThroughEndpointResponse.model_validate(endpoint)


@router.get("/passthrough", response_model=GatewayPassThroughEndpointList)
async def list_gateway_passthrough_endpoints(
    auth: OrgAdminDep,
    db: DbDep,
    include_inactive: bool = Query(False),
) -> GatewayPassThroughEndpointList:
    workspace = auth[0]
    stmt = select(GatewayPassThroughEndpoint).where(
        GatewayPassThroughEndpoint.workspace_id == workspace.id
    )
    if not include_inactive:
        stmt = stmt.where(GatewayPassThroughEndpoint.is_active.is_(True))
    stmt = stmt.order_by(GatewayPassThroughEndpoint.slug.asc())
    items = (await db.execute(stmt)).scalars().all()
    return GatewayPassThroughEndpointList(
        items=[GatewayPassThroughEndpointResponse.model_validate(item) for item in items]
    )


@router.put("/passthrough/{endpoint_id}", response_model=GatewayPassThroughEndpointResponse)
async def update_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    body: GatewayPassThroughEndpointUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointResponse:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(endpoint, field, value)

    await db.commit()
    await db.refresh(endpoint)
    return GatewayPassThroughEndpointResponse.model_validate(endpoint)


@router.delete("/passthrough/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")
    await db.delete(endpoint)
    await db.commit()


@router.post("/passthrough/{endpoint_id}/test", response_model=GatewayPassThroughTestResponse)
async def test_gateway_passthrough_endpoint(
    endpoint_id: uuid.UUID,
    body: GatewayPassThroughTestRequest,
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughTestResponse:
    workspace = auth[0]
    endpoint = await db.get(GatewayPassThroughEndpoint, endpoint_id)
    if endpoint is None or endpoint.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    target_url = _build_passthrough_target_url(
        endpoint,
        upstream_path=body.path or "",
        query_params=body.query,
    )
    timeout_seconds = max(1.0, endpoint.timeout_ms / 1000)
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=body.method.upper(),
                url=target_url,
                json=body.body_json if body.body_json is not None else None,
                headers=_build_passthrough_headers(endpoint, source_headers=body.headers),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Upstream test failed: {exc!s}") from exc

    preview = upstream_response.text[:1000] if upstream_response.text else None
    return GatewayPassThroughTestResponse(
        ok=upstream_response.status_code < 400,
        status_code=upstream_response.status_code,
        latency_ms=int((time.monotonic() - started) * 1000),
        target_url=target_url,
        response_preview=preview,
        headers={
            key: value
            for key, value in upstream_response.headers.items()
            if key.lower() in _PASSTHROUGH_ALLOWED_RESPONSE_HEADERS
        },
    )


@router.get("/passthrough/stats", response_model=GatewayPassThroughEndpointStatsList)
async def list_gateway_passthrough_stats(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayPassThroughEndpointStatsList:
    workspace = auth[0]
    endpoints = list(
        (
            await db.execute(
                select(GatewayPassThroughEndpoint)
                .where(GatewayPassThroughEndpoint.workspace_id == workspace.id)
                .order_by(GatewayPassThroughEndpoint.slug.asc())
            )
        )
        .scalars()
        .all()
    )
    items: list[GatewayPassThroughEndpointStats] = []
    for endpoint in endpoints:
        requested_model = f"passthrough:{endpoint.slug}"
        row = (
            await db.execute(
                select(
                    func.count(GatewayRequest.id).label("total_requests"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.status != "error")
                    .label("success_count"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.status == "error")
                    .label("error_count"),
                    func.avg(GatewayRequest.latency_ms).label("avg_latency_ms"),
                    func.percentile_cont(0.5).within_group(GatewayRequest.latency_ms).label("p50_latency_ms"),
                    func.percentile_cont(0.95).within_group(GatewayRequest.latency_ms).label("p95_latency_ms"),
                    func.percentile_cont(0.99).within_group(GatewayRequest.latency_ms).label("p99_latency_ms"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.created_at >= func.now() - sa.text("INTERVAL '1 hour'"))
                    .label("last_hour_requests"),
                    func.count(GatewayRequest.id)
                    .filter(GatewayRequest.created_at >= func.now() - sa.text("INTERVAL '24 hours'"))
                    .label("last_24h_requests"),
                )
                .where(
                    GatewayRequest.workspace_id == workspace.id,
                    GatewayRequest.model_requested == requested_model,
                )
            )
        ).one()
        total_requests = int(row.total_requests or 0)
        last_hour_requests = int(row.last_hour_requests or 0)
        last_24h_requests = int(row.last_24h_requests or 0)
        estimated_total_cost = (
            (endpoint.cost_per_call_usd or Decimal("0")) * Decimal(total_requests)
            if endpoint.cost_per_call_usd is not None
            else None
        )
        estimated_24h_cost = (
            (endpoint.cost_per_call_usd or Decimal("0")) * Decimal(last_24h_requests)
            if endpoint.cost_per_call_usd is not None
            else None
        )
        utilization = None
        if endpoint.rate_limit_rpm:
            utilization = Decimal(str(round(last_hour_requests / (endpoint.rate_limit_rpm * 60), 4)))
        items.append(
            GatewayPassThroughEndpointStats(
                endpoint_id=endpoint.id,
                slug=endpoint.slug,
                total_requests=total_requests,
                success_count=int(row.success_count or 0),
                error_count=int(row.error_count or 0),
                avg_latency_ms=Decimal(str(round(float(row.avg_latency_ms), 2))) if row.avg_latency_ms is not None else None,
                p50_latency_ms=Decimal(str(round(float(row.p50_latency_ms), 2))) if row.p50_latency_ms is not None else None,
                p95_latency_ms=Decimal(str(round(float(row.p95_latency_ms), 2))) if row.p95_latency_ms is not None else None,
                p99_latency_ms=Decimal(str(round(float(row.p99_latency_ms), 2))) if row.p99_latency_ms is not None else None,
                last_hour_requests=last_hour_requests,
                rate_limit_rpm=endpoint.rate_limit_rpm,
                rate_limit_utilization_pct=utilization,
                estimated_total_cost_usd=estimated_total_cost,
                estimated_24h_cost_usd=estimated_24h_cost,
            )
        )
    return GatewayPassThroughEndpointStatsList(items=items)


@router.api_route(
    "/passthrough/{slug}",
    methods=["GET"],
    operation_id="execute_gateway_passthrough_endpoint_root_get",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["POST"],
    operation_id="execute_gateway_passthrough_endpoint_root_post",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["PUT"],
    operation_id="execute_gateway_passthrough_endpoint_root_put",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["PATCH"],
    operation_id="execute_gateway_passthrough_endpoint_root_patch",
)
@router.api_route(
    "/passthrough/{slug}",
    methods=["DELETE"],
    operation_id="execute_gateway_passthrough_endpoint_root_delete",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["GET"],
    operation_id="execute_gateway_passthrough_endpoint_path_get",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["POST"],
    operation_id="execute_gateway_passthrough_endpoint_path_post",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["PUT"],
    operation_id="execute_gateway_passthrough_endpoint_path_put",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["PATCH"],
    operation_id="execute_gateway_passthrough_endpoint_path_patch",
)
@router.api_route(
    "/passthrough/{slug}/{upstream_path:path}",
    methods=["DELETE"],
    operation_id="execute_gateway_passthrough_endpoint_path_delete",
)
async def execute_gateway_passthrough_endpoint(
    slug: str,
    request: Request,
    db: DbDep,
    upstream_path: str = "",
) -> Response:
    workspace, api_key = await _resolve_gateway_workspace(request, db)
    await evaluate_ip_acl(
        db,
        workspace_id=workspace.id,
        api_key_id=api_key.id if api_key is not None else None,
        team_name=None,
        client_ip=get_client_ip(
            request.headers.get("x-forwarded-for"),
            request.client.host if request.client else None,
        ),
    )

    stmt = select(GatewayPassThroughEndpoint).where(
        GatewayPassThroughEndpoint.workspace_id == workspace.id,
        GatewayPassThroughEndpoint.slug == slug,
        GatewayPassThroughEndpoint.is_active.is_(True),
    )
    endpoint = (await db.execute(stmt)).scalar_one_or_none()
    if endpoint is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pass-through endpoint not found")

    merged_query = {key: value for key, value in request.query_params.multi_items()}
    target_url = _build_passthrough_target_url(
        endpoint,
        upstream_path=upstream_path,
        query_params=merged_query,
    )

    raw_body = await request.body()
    timeout_seconds = max(1.0, endpoint.timeout_ms / 1000)
    if endpoint.rate_limit_rpm:
        from runledger_api.core.redis import get_redis  # noqa: PLC0415

        redis = await get_redis()
        now = int(time.time())
        bucket = now // 60
        key = f"gateway:passthrough:rpm:{workspace.id}:{endpoint.id}:{bucket}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 120)
        if count > endpoint.rate_limit_rpm:
            await record_gateway_request(
                db=db,
                workspace_id=workspace.id,
                model_requested=f"passthrough:{slug}",
                route=None,
                model_used=endpoint.upstream_base_url,
                cache_hit=False,
                input_tokens=None,
                output_tokens=None,
                latency_ms=0,
                req_status="error",
                decision_reason=f"passthrough:{slug}|rate_limited",
                config_fingerprint={
                    "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
                    "endpoint_slug": slug,
                    "passthrough": True,
                },
                segment_key=slug,
            )
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Pass-through endpoint rate limit exceeded")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            upstream_response = await client.request(
                method=request.method,
                url=target_url,
                content=raw_body if raw_body else None,
                headers=_build_passthrough_headers(endpoint, request),
            )
    except httpx.HTTPError as exc:
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=f"passthrough:{slug}",
            route=None,
            model_used=endpoint.upstream_base_url,
            cache_hit=False,
            input_tokens=None,
            output_tokens=None,
            latency_ms=int((time.monotonic() - t0) * 1000),
            req_status="error",
            decision_reason=f"passthrough:{slug}|upstream_error",
            config_fingerprint={
                "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
                "endpoint_slug": slug,
                "passthrough": True,
            },
            segment_key=slug,
        )
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Upstream request failed: {exc!s}") from exc

    await record_gateway_request(
        db=db,
        workspace_id=workspace.id,
        model_requested=f"passthrough:{slug}",
        route=None,
        model_used=endpoint.upstream_base_url,
        cache_hit=False,
        input_tokens=None,
        output_tokens=None,
        latency_ms=int((time.monotonic() - t0) * 1000),
        req_status="success" if upstream_response.status_code < 400 else "error",
        decision_reason=f"passthrough:{slug}",
        config_fingerprint={
            "assigned_cost_usd": str(endpoint.cost_per_call_usd or Decimal("0")),
            "endpoint_slug": slug,
            "passthrough": True,
            "rate_limit_rpm": endpoint.rate_limit_rpm,
        },
        segment_key=slug,
    )

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() in _PASSTHROUGH_ALLOWED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
