from __future__ import annotations

from fastapi import APIRouter

from .gateway_shared import *

router = APIRouter()


@router.get("/runtime/snapshot", response_model=GatewayRuntimeSnapshotResponse)
async def get_gateway_runtime_snapshot(
    auth: OrgAdminDep,
    db: DbDep,
) -> GatewayRuntimeSnapshotResponse:
    workspace = auth[0]
    payload = await build_gateway_runtime_snapshot(db, workspace_id=workspace.id)
    return GatewayRuntimeSnapshotResponse.model_validate(payload)


@router.get("/runtime/internal/snapshot", response_model=GatewayRuntimeSnapshotResponse)
async def get_gateway_runtime_snapshot_internal(
    _: AdminDep,
    db: DbDep,
    workspace_id: uuid.UUID = Query(...),
) -> GatewayRuntimeSnapshotResponse:
    payload = await build_gateway_runtime_snapshot(db, workspace_id=workspace_id)
    return GatewayRuntimeSnapshotResponse.model_validate(payload)


@router.post(
    "/runtime/internal/resolve-api-key",
    response_model=GatewayRuntimeApiKeyResolveResponse,
)
async def resolve_gateway_runtime_api_key(
    body: GatewayRuntimeApiKeyResolveRequest,
    _: AdminDep,
    db: DbDep,
) -> GatewayRuntimeApiKeyResolveResponse:
    workspace, api_key, oidc_auth = await _resolve_gateway_bearer_token(body.raw_key, db)
    return GatewayRuntimeApiKeyResolveResponse(
        api_key_id=api_key.id if api_key is not None else None,
        workspace_id=workspace.id,
        tenant_id=workspace.tenant_id,
        auth_mode="api_key" if api_key is not None else "oidc",
        key_prefix=api_key.key_prefix if api_key is not None else "oidc",
        ownership_type=api_key.ownership_type if api_key is not None else "oidc_session",
        owner_reference=(
            api_key.owner_reference
            if api_key is not None
            else str(getattr(oidc_auth, "subject", "") or "")
        ),
        budget_tier_id=api_key.budget_tier_id if api_key is not None else None,
        guardrail_config=api_key.guardrail_config or {} if api_key is not None else {},
        scopes=list(api_key.scopes or []) if api_key is not None else [],
    )


@router.post(
    "/runtime/internal/preflight",
    response_model=GatewayRuntimePreflightResponse,
)
async def gateway_runtime_preflight(
    body: GatewayRuntimePreflightRequest,
    _: AdminDep,
    db: DbDep,
) -> GatewayRuntimePreflightResponse:
    workspace, api_key, _oidc_auth = await _resolve_gateway_bearer_token(body.raw_key, db)

    metadata = body.body.metadata or {}
    team_name = str(metadata.get("team")) if metadata.get("team") else None
    if body.client_ip:
        await evaluate_ip_acl(
            db,
            workspace_id=workspace.id,
            api_key_id=api_key.id,
            team_name=team_name,
            client_ip=body.client_ip,
        )
    missing_metadata = await enforce_required_metadata(
        db, workspace_id=workspace.id, metadata=metadata
    )

    messages = [{"role": m.role, "content": m.content} for m in body.body.messages]
    request_tags = (
        [str(tag).strip() for tag in metadata.get("tags", [])]
        if isinstance(metadata.get("tags"), list)
        else []
    )
    if body.tags_header:
        request_tags.extend(tag.strip() for tag in body.tags_header.split(",") if tag.strip())
    request_tags = await resolve_request_tags(db, workspace.id, body.body.model, request_tags)
    preferred_region = body.region_header.strip() if body.region_header else None

    cache_entry = None
    if body.body.cache and not body.body.stream:
        cache_key = make_cache_key(body.body.model, messages)
        cache_entry = await check_cache(db, workspace.id, cache_key)
    if cache_entry is not None:
        await increment_hit_count(db, cache_entry)
        await record_gateway_request(
            db=db,
            workspace_id=workspace.id,
            model_requested=body.body.model,
            route=None,
            model_used=cache_entry.model,
            cache_hit=True,
            input_tokens=cache_entry.prompt_tokens,
            output_tokens=cache_entry.completion_tokens,
            latency_ms=0,
            req_status="cache_hit",
            decision_reason="cache_hit",
        )
        return GatewayRuntimePreflightResponse(
            api_key_id=api_key.id if api_key is not None else None,
            workspace_id=workspace.id,
            tenant_id=workspace.tenant_id,
            auth_mode="api_key" if api_key is not None else "oidc",
            model_requested=body.body.model,
            route_alias=body.body.model,
            preferred_region=preferred_region,
            request_tags=request_tags,
            missing_metadata=missing_metadata,
            cache_hit_kind="exact",
            cached_response=cache_entry.response_json,
            prepared_messages=messages,
            effective_tools=body.body.tools,
            effective_reasoning_effort=body.body.reasoning_effort,
            decision_reason="cache_hit",
            execution_steps=[],
        )

    semantic_enabled = body.body.semantic_cache
    seed_routes = await select_routes(
        db,
        workspace.id,
        body.body.model,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    if not semantic_enabled and not body.body.stream:
        semantic_enabled = bool(seed_routes and seed_routes[0].semantic_cache_enabled)
    if semantic_enabled and not body.body.stream:
        sem_hit = await semantic_cache_svc.lookup(workspace.id, body.body.model, messages)
        if sem_hit is not None:
            usage = sem_hit.get("usage") or {}
            await record_gateway_request(
                db=db,
                workspace_id=workspace.id,
                model_requested=body.body.model,
                route=None,
                model_used=body.body.model,
                cache_hit=True,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                latency_ms=0,
                req_status="cache_hit",
                decision_reason="semantic_cache_hit",
            )
            return GatewayRuntimePreflightResponse(
                api_key_id=api_key.id if api_key is not None else None,
                workspace_id=workspace.id,
                tenant_id=workspace.tenant_id,
                auth_mode="api_key" if api_key is not None else "oidc",
                model_requested=body.body.model,
                route_alias=body.body.model,
                preferred_region=preferred_region,
                request_tags=request_tags,
                missing_metadata=missing_metadata,
                cache_hit_kind="semantic",
                cached_response=sem_hit,
                prepared_messages=messages,
                effective_tools=body.body.tools,
                effective_reasoning_effort=body.body.reasoning_effort,
                semantic_cache_enabled=True,
                decision_reason="semantic_cache_hit",
                execution_steps=[],
            )

    compiler_enabled = body.body.context_compiler
    compiler_config: dict[str, Any] | None = None
    if context_compiler.enabled() and seed_routes:
        compiler_config = seed_routes[0].context_compiler_config
        compiler_enabled = compiler_enabled or seed_routes[0].context_compiler_enabled
    effective_tools = body.body.tools
    if compiler_enabled:
        messages, effective_tools, _ = await context_compiler.compile_messages(
            messages,
            compiler_config,
            workspace=str(workspace.id),
            tools=body.body.tools,
        )

    route_alias = body.body.model
    effective_reasoning_effort = body.body.reasoning_effort
    ir_decision: dict[str, Any] | None = None
    ir_enabled = body.body.intelligent_routing
    routing_config: dict[str, Any] | None = None
    if intelligent_router.enabled() and seed_routes:
        routing_config = seed_routes[0].routing_config
        ir_enabled = ir_enabled or seed_routes[0].intelligent_routing_enabled
    if ir_enabled:
        ir_decision = await intelligent_router.classify(messages, routing_config)
        if ir_decision and ir_decision.get("alias"):
            route_alias = str(ir_decision["alias"])
            if ir_decision.get("reasoning_effort") and effective_reasoning_effort is None:
                effective_reasoning_effort = str(ir_decision["reasoning_effort"])
        elif routing_config:
            on_fail = routing_config.get("on_failure")
            if isinstance(on_fail, str) and on_fail != "passthrough":
                route_alias = (routing_config.get("tiers") or {}).get(on_fail, route_alias)

    guardrails_enabled = not getattr(workspace, "guardrail_bypass", False) and not (
        (getattr(api_key, "guardrail_config", {}) or {}).get("disabled", False)
    )
    key_guardrail_ids = (getattr(api_key, "guardrail_config", {}) or {}).get("guardrail_ids")
    if guardrails_enabled:
        guardrail_ids = (
            [uuid.UUID(g) for g in body.body.guardrails]
            if body.body.guardrails
            else ([uuid.UUID(g) for g in key_guardrail_ids] if key_guardrail_ids else None)
        )
        pre_texts = [str(m.get("content", "")) for m in messages if m.get("content")]
        gr_decision, gr_results, _ = await evaluate_guardrails(
            db,
            workspace.id,
            "pre_call",
            texts=pre_texts,
            structured_messages=messages,
            model=body.body.model,
            end_user_id=body.end_user_id,
            guardrail_ids=guardrail_ids,
        )
        if gr_decision == "block":
            blocked_reason = next(
                (r["reason"] for r in gr_results if r["decision"] == "block"),
                "Blocked by guardrail",
            )
            raise HTTPException(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, blocked_reason)
        if gr_decision == "modify":
            for result in gr_results:
                if result.get("modified_texts") and result["decision"] == "modify":
                    for idx, message in enumerate(messages):
                        if message.get("content") and idx < len(result["modified_texts"]):
                            messages[idx]["content"] = result["modified_texts"][idx]

    primary_route, primary_reason = await choose_route_for_alias(
        db,
        workspace.id,
        route_alias,
        messages,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    if primary_route is None:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No active gateway routes configured for alias '{route_alias}'",
        )
    decision_reason = (
        str(ir_decision.get("reason"))
        if ir_decision and ir_decision.get("reason")
        else primary_reason
    )
    if missing_metadata:
        decision_reason = f"{decision_reason}|metadata_warn:{','.join(missing_metadata)}"

    queue: list[dict[str, Any]] = [{"alias": route_alias, "rule": None, "trigger": "primary"}]
    visited_aliases = {route_alias}
    first_fallback_cfg = primary_route.fallback_config or {}
    fallback_rules = []
    if isinstance(first_fallback_cfg, dict):
        fallback_rules = [
            rule
            for rule in first_fallback_cfg.get("fallbacks", [])
            if isinstance(rule, dict) and isinstance(rule.get("alias"), str) and rule.get("alias")
        ]
    for alias in (
        first_fallback_cfg.get("aliases", []) if isinstance(first_fallback_cfg, dict) else []
    ):
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            queue.append({"alias": alias, "rule": None, "trigger": "configured"})
            visited_aliases.add(alias)
    for alias in body.body.fallback_aliases or []:
        if isinstance(alias, str) and alias and alias not in visited_aliases:
            queue.append({"alias": alias, "rule": None, "trigger": "request"})
            visited_aliases.add(alias)

    execution_steps = []
    queue_index = 0
    while queue_index < len(queue):
        step = queue[queue_index]
        queue_index += 1
        alias_to_try = str(step["alias"])
        rule = step.get("rule") if isinstance(step.get("rule"), dict) else None
        trigger = str(step.get("trigger") or "fallback")
        step_messages = _apply_prompt_overrides(messages, rule)
        step_temperature = _override_value(body.body.temperature, rule, "temperature")
        step_max_tokens = _override_value(body.body.max_tokens, rule, "max_tokens")
        step_top_p = _override_value(body.body.top_p, rule, "top_p")
        step_frequency_penalty = _override_value(
            body.body.frequency_penalty, rule, "frequency_penalty"
        )
        step_presence_penalty = _override_value(
            body.body.presence_penalty, rule, "presence_penalty"
        )
        step_seed = _override_value(body.body.seed, rule, "seed")
        step_stop = _override_value(body.body.stop, rule, "stop")
        step_response_format = _override_value(body.body.response_format, rule, "response_format")
        step_tools = _override_value(effective_tools, rule, "tools")
        step_tool_choice = _override_value(body.body.tool_choice, rule, "tool_choice")
        step_reasoning_effort = _override_value(
            effective_reasoning_effort, rule, "reasoning_effort"
        )
        timeout_override_ms = (
            body.stream_timeout_ms
            if body.body.stream
            else (body.completion_timeout_ms or body.timeout_ms)
        )
        if rule and rule.get("completion_timeout_ms") is not None and not body.body.stream:
            timeout_override_ms = int(rule["completion_timeout_ms"])
        selected_route, selected_reason = await choose_route_for_alias(
            db,
            workspace.id,
            alias_to_try,
            step_messages,
            request_tags=request_tags,
            preferred_region=preferred_region,
        )
        routes_for_alias = await select_routes(
            db,
            workspace.id,
            alias_to_try,
            request_tags=request_tags,
            preferred_region=preferred_region,
        )
        if not routes_for_alias or selected_route is None:
            continue
        ordered_routes = [selected_route] + [
            route for route in routes_for_alias if route.id != selected_route.id
        ]
        if trigger == "primary":
            for fallback_rule in fallback_rules:
                fallback_alias = str(fallback_rule["alias"])
                if fallback_alias not in visited_aliases:
                    queue.append(
                        {"alias": fallback_alias, "rule": fallback_rule, "trigger": "policy"}
                    )
                    visited_aliases.add(fallback_alias)
        for route in ordered_routes:
            if route.cooldown_until is not None and route.cooldown_until > datetime.now(UTC):
                continue
            try:
                await check_cost_cap(db, route, workspace.id)
                if body.end_user_id and route.per_user_rpm_limit:
                    from runledger_api.core.redis import get_redis  # noqa: PLC0415

                    redis = await get_redis()
                    await check_per_user_rpm(
                        redis,
                        workspace.id,
                        body.end_user_id,
                        route.id,
                        route.per_user_rpm_limit,
                    )
            except HTTPException:
                continue
            step_forward_messages = (
                redact_messages(step_messages)
                if body.body.stream and route.pii_redaction_enabled
                else step_messages
            )
            step_request = _runtime_request_body(
                body=body.body,
                route=route,
                messages=step_forward_messages,
                tools=step_tools,
                reasoning_effort=step_reasoning_effort,
            )
            step_request["temperature"] = step_temperature
            step_request["max_tokens"] = step_max_tokens
            step_request["top_p"] = step_top_p
            step_request["frequency_penalty"] = step_frequency_penalty
            step_request["presence_penalty"] = step_presence_penalty
            step_request["seed"] = step_seed
            step_request["stop"] = step_stop
            step_request["response_format"] = step_response_format
            step_request["tool_choice"] = step_tool_choice
            direct_provider = _runtime_direct_provider_request(
                route=route,
                request_body=step_request,
                stream=body.body.stream,
            )
            execution_steps.append(
                {
                    "route_id": route.id,
                    "alias": alias_to_try,
                    "provider": route.provider,
                    "target_model": route.target_model,
                    "execution_mode": "direct_http"
                    if direct_provider is not None
                    else "python_adapter",
                    "base_url": route.base_url,
                    "api_key_env_var": route.api_key_env_var,
                    "priority": route.priority,
                    "timeout_ms": timeout_override_ms or route.timeout_ms,
                    "retry_count": route.retry_count,
                    "region": route.region,
                    "deployment_status": route.deployment_status,
                    "trigger": trigger,
                    "required_error_triggers": (
                        [
                            str(item).strip()
                            for item in (rule.get("on", []) if isinstance(rule, dict) else [])
                            if str(item).strip()
                        ]
                        if trigger in {"policy", "timeout", "content_policy", "context_window"}
                        else []
                    ),
                    "decision_reason": decision_reason
                    if trigger == "primary"
                    else f"{trigger}:{selected_reason}",
                    "request_method": "POST",
                    "request_url": direct_provider[0] if direct_provider is not None else None,
                    "request_headers": direct_provider[1] if direct_provider is not None else {},
                    "request_body": step_request,
                }
            )

    if not execution_steps:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No runnable gateway routes remained for alias '{route_alias}'",
        )

    return GatewayRuntimePreflightResponse(
        api_key_id=api_key.id if api_key is not None else None,
        workspace_id=workspace.id,
        tenant_id=workspace.tenant_id,
        auth_mode="api_key" if api_key is not None else "oidc",
        model_requested=body.body.model,
        route_alias=route_alias,
        preferred_region=preferred_region,
        request_tags=request_tags,
        missing_metadata=missing_metadata,
        prepared_messages=messages,
        effective_tools=effective_tools,
        effective_reasoning_effort=effective_reasoning_effort,
        compiler_enabled=compiler_enabled,
        compiler_config=compiler_config,
        semantic_cache_enabled=semantic_enabled,
        guardrails_enabled=guardrails_enabled,
        ir_decision=ir_decision,
        decision_reason=decision_reason,
        execution_steps=execution_steps,
    )


@router.post(
    "/runtime/internal/finalize",
    response_model=GatewayRuntimeFinalizeResponse,
)
async def gateway_runtime_finalize(
    body: GatewayRuntimeFinalizeRequest,
    _: AdminDep,
    db: DbDep,
) -> GatewayRuntimeFinalizeResponse:
    workspace = await db.get(Workspace, body.workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    route = await db.get(GatewayRoute, body.route_id)
    if route is None or route.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")

    if body.guardrails_enabled:
        response_content = ""
        choices = body.response_json.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            response_content = msg.get("content", "") or ""
        if response_content:
            import asyncio  # noqa: PLC0415

            post_coro = evaluate_guardrails(
                db,
                workspace.id,
                "post_call",
                texts=[response_content],
                structured_messages=body.prepared_messages,
                model=body.model_requested,
                end_user_id=body.end_user_id,
            )
            during_coro = evaluate_guardrails(
                db,
                workspace.id,
                "during_call",
                texts=[
                    str(m.get("content", "")) for m in body.prepared_messages if m.get("content")
                ]
                + [response_content],
                structured_messages=body.prepared_messages,
                model=body.model_requested,
                end_user_id=body.end_user_id,
            )
            (post_result, during_result) = await asyncio.gather(post_coro, during_coro)
            for phase_decision, phase_results, _ in [post_result, during_result]:
                if phase_decision == "block":
                    blocked_reason = next(
                        (r["reason"] for r in phase_results if r["decision"] == "block"),
                        "Response blocked by guardrail",
                    )
                    raise HTTPException(
                        status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, blocked_reason
                    )

    usage = body.response_json.get("usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    if body.cache:
        cache_key = make_cache_key(body.model_requested, body.prepared_messages)
        await store_cache(
            db=db,
            workspace_id=workspace.id,
            cache_key=cache_key,
            model=route.target_model,
            response_json=body.response_json,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )
    if body.semantic_cache_enabled:
        await semantic_cache_svc.store(
            workspace_id=workspace.id,
            model=body.model_requested,
            messages=body.prepared_messages,
            response_json=body.response_json,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )
    gateway_overhead_ms = max((body.total_wall_ms or 0) - (body.latency_ms or 0), 0)
    await record_gateway_request(
        db=db,
        workspace_id=workspace.id,
        model_requested=body.model_requested,
        route=route,
        model_used=route.target_model,
        cache_hit=False,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=body.latency_ms,
        req_status="success",
        decision_reason=body.decision_reason,
        config_fingerprint=_config_fingerprint(
            model_used=route.target_model,
            semantic_cache=body.semantic_cache_enabled,
            compiler_enabled=body.compiler_enabled,
            compiler_config=body.compiler_config,
            ir_decision=body.ir_decision,
        )
        | {
            "provider_latency_ms": body.latency_ms,
            "total_wall_ms": body.total_wall_ms,
            "gateway_overhead_ms": gateway_overhead_ms,
            "region": route.region,
        },
        segment_key=_segment_key(body.model_requested, body.ir_decision),
    )
    return GatewayRuntimeFinalizeResponse(ok=True)


@router.post("/runtime/internal/provider-execute")
async def gateway_runtime_provider_execute(
    body: GatewayRuntimeProviderExecuteRequest,
    _: AdminDep,
    db: DbDep,
) -> Any:
    route = await db.get(GatewayRoute, body.route_id)
    if route is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    messages = list(body.request_body.get("messages") or [])
    kwargs = {
        "temperature": body.request_body.get("temperature"),
        "max_tokens": body.request_body.get("max_tokens"),
        "top_p": body.request_body.get("top_p"),
        "frequency_penalty": body.request_body.get("frequency_penalty"),
        "presence_penalty": body.request_body.get("presence_penalty"),
        "seed": body.request_body.get("seed"),
        "stop": body.request_body.get("stop"),
        "response_format": body.request_body.get("response_format"),
        "tools": body.request_body.get("tools"),
        "tool_choice": body.request_body.get("tool_choice"),
        "reasoning_effort": body.request_body.get("reasoning_effort"),
    }
    if body.stream:

        async def _provider_stream() -> AsyncGenerator[bytes]:
            async for chunk in stream_request(
                route=route,
                messages=messages,
                timeout_override_ms=body.timeout_ms,
                **kwargs,
            ):
                yield chunk

        return StreamingResponse(_provider_stream(), media_type="text/event-stream")

    return await forward_request(
        route=route,
        messages=messages,
        **kwargs,
    )


@router.post("/runtime/internal/route-result")
async def gateway_runtime_route_result(
    body: GatewayRuntimeRouteResultRequest,
    _: AdminDep,
    db: DbDep,
) -> dict[str, bool]:
    route = await db.get(GatewayRoute, body.route_id)
    if route is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    route.last_health_check_at = datetime.now(UTC)
    if body.success:
        route.consecutive_health_failures = 0
        route.disabled_reason = None
        route.cooldown_until = None
    else:
        route.consecutive_health_failures = (route.consecutive_health_failures or 0) + 1
        route.disabled_reason = body.error_detail
        if body.transient and route.cooldown_seconds:
            route.cooldown_until = datetime.now(UTC) + timedelta(seconds=route.cooldown_seconds)
    await db.commit()
    return {"ok": True}


@router.post("/runtime/internal/mirror")
async def gateway_runtime_mirror(
    body: GatewayRuntimeMirrorRequest,
    _: AdminDep,
    db: DbDep,
) -> dict[str, bool]:
    route = await db.get(GatewayRoute, body.route_id)
    if route is None or route.workspace_id != body.workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gateway route not found")
    mirror_cfg = route.mirror_config or {}
    mirror_alias = mirror_cfg.get("alias") if isinstance(mirror_cfg, dict) else None
    mirror_pct = (
        float(mirror_cfg.get("sample_pct", 0))
        if isinstance(mirror_cfg, dict) and mirror_cfg.get("sample_pct") is not None
        else 0.0
    )
    if not mirror_alias or mirror_pct <= 0 or random.random() >= mirror_pct:
        return {"ok": True}

    messages = list(body.request_body.get("messages") or [])
    mirror_route, _ = await choose_route_for_alias(
        db,
        body.workspace_id,
        str(mirror_alias),
        messages,
        request_tags=body.request_tags,
        preferred_region=body.preferred_region,
    )
    if mirror_route is None:
        return {"ok": True}

    try:
        started = time.monotonic()
        mirror_response = await forward_request(
            route=mirror_route,
            messages=messages,
            temperature=body.request_body.get("temperature"),
            max_tokens=body.request_body.get("max_tokens"),
            top_p=body.request_body.get("top_p"),
            frequency_penalty=body.request_body.get("frequency_penalty"),
            presence_penalty=body.request_body.get("presence_penalty"),
            seed=body.request_body.get("seed"),
            stop=body.request_body.get("stop"),
            response_format=body.request_body.get("response_format"),
            tools=body.request_body.get("tools"),
            tool_choice=body.request_body.get("tool_choice"),
            reasoning_effort=body.request_body.get("reasoning_effort"),
        )
        similarity = _shadow_similarity(
            _response_text(body.response_json),
            _response_text(mirror_response),
        )
        usage = mirror_response.get("usage") or {}
        await record_gateway_request(
            db=db,
            workspace_id=body.workspace_id,
            model_requested=f"mirror:{body.model_requested}",
            route=mirror_route,
            model_used=mirror_route.target_model,
            cache_hit=False,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=int((time.monotonic() - started) * 1000),
            req_status="success",
            decision_reason=f"mirror:{route.alias}->{mirror_alias}|shadow_compare:{similarity:.3f}",
        )
    except Exception as exc:  # noqa: BLE001
        await record_gateway_request(
            db=db,
            workspace_id=body.workspace_id,
            model_requested=f"mirror:{body.model_requested}",
            route=mirror_route,
            model_used=mirror_route.target_model,
            cache_hit=False,
            input_tokens=None,
            output_tokens=None,
            latency_ms=None,
            req_status="error",
            decision_reason=f"mirror:{route.alias}->{mirror_alias}|shadow_error",
        )
        log.warning("gateway_runtime_mirror_failed route_id=%s error=%s", str(route.id), str(exc))
    return {"ok": True}


@router.post(
    "/runtime/events/signed",
    response_model=GatewayRuntimeEventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_signed_gateway_runtime_events(
    request: Request,
    db: DbDep,
    x_runledger_signature: str = Header(..., alias="X-RunLedger-Signature"),
    x_runledger_timestamp: str = Header(..., alias="X-RunLedger-Timestamp"),
) -> GatewayRuntimeEventBatchResponse:
    raw_body = await request.body()
    try:
        payload = GatewayRuntimeEventBatchRequest.model_validate_json(raw_body)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid gateway runtime event payload"
        ) from exc
    verify_gateway_runtime_signature(
        workspace_id=str(payload.workspace_id),
        timestamp=x_runledger_timestamp,
        body=raw_body,
        signature=x_runledger_signature,
    )
    accepted = await ingest_gateway_runtime_events(
        db,
        workspace_id=payload.workspace_id,
        source_service=payload.source_service,
        events=[event.model_dump(mode="json") for event in payload.events],
    )
    return GatewayRuntimeEventBatchResponse(accepted=accepted)
