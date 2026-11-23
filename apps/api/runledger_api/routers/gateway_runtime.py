from __future__ import annotations

from decimal import Decimal

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from runledger_api.core.config import settings
from runledger_api.core.redis import get_redis
from runledger_api.core.scopes import GATEWAY as GATEWAY_SCOPE
from runledger_api.core.scopes import normalize_scopes
from runledger_api.services.budgets import (
    check_budget_throttle,
    check_provider_profile_budgets,
    check_request_budgets,
    record_budget_spend,
)
from runledger_api.services.gateway_cache import get_cache_profile, record_cache_outcome
from runledger_api.services.gateway_controls import rpm_subject
from runledger_api.services.gateway_decision import (
    DecisionTrace,
    link_guardrail_events_to_run,
)
from runledger_api.services.gateway_hotpath import is_missing, request_memo, ttl_cache
from runledger_api.services.gateway_prompts import apply_resolved_prompt, resolve_prompt_ref
from runledger_api.services.sessions import resolve_principal_user_id

from .gateway_shared import *

log = structlog.get_logger()

# Providers that accept stream_options.include_usage (OpenAI-compatible).
_STREAM_USAGE_PROVIDERS = {"openai", "azure", "vllm", "groq", "ollama", "local"}


router = APIRouter()


def _metadata_text(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, "", []):
            return str(value)[:255]
    return None


def _feature_tag_from(metadata: dict[str, Any], request_tags: list[str]) -> str | None:
    """The workflow / feature tag a gateway request is attributed to."""
    feature_tag = _metadata_text(
        metadata,
        "runledger.feature_tag",
        "feature_tag",
        "feature",
        "workflow",
        "workflow_type",
    )
    if feature_tag is None and request_tags:
        feature_tag = request_tags[0][:255]
    return feature_tag


async def _route_alias_for_model(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    model: str,
    request_tags: list[str],
    preferred_region: str | None,
) -> str | None:
    """Resolve a budget's downgrade model to a gateway alias.

    The model may be given as a route alias or as a provider model name.
    """
    if await select_routes(
        db, workspace_id, model, request_tags=request_tags, preferred_region=preferred_region
    ):
        return model
    alias = (
        await db.execute(
            select(GatewayRoute.alias)
            .where(
                GatewayRoute.workspace_id == workspace_id,
                GatewayRoute.target_model == model,
                GatewayRoute.is_active.is_(True),
            )
            .order_by(GatewayRoute.priority.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return str(alias) if alias else None


def _budget_exceeded(budget_id: str | None, detail: str) -> HTTPException:
    headers = {"X-Cost-Cap-Reason": "budget_exceeded"}
    if budget_id:
        headers["X-Budget-Id"] = budget_id
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail, headers=headers)


# Request fields that change the model's answer; part of the cache key (review G-07).
_CACHE_PARAM_FIELDS = (
    "tools",
    "tool_choice",
    "response_format",
    "temperature",
    "top_p",
    "seed",
    "max_tokens",
    "stop",
    "n",
    "frequency_penalty",
    "presence_penalty",
    "reasoning_effort",
    "logit_bias",
    "parallel_tool_calls",
)


def _cache_params(request: Any) -> dict[str, Any]:
    data = (
        request.model_dump(exclude_none=True) if hasattr(request, "model_dump") else dict(request)
    )
    return {k: data[k] for k in _CACHE_PARAM_FIELDS if k in data}


def _semantic_scope(api_key: Any, end_user_id: str | None, params: dict[str, Any]) -> str:
    """Semantic-cache scope: the caller (API key + end user) and a hash of the request
    parameters, so answers are reused only for the same caller and settings (G-06)."""
    import hashlib  # noqa: PLC0415
    import json  # noqa: PLC0415

    key_id = str(api_key.id) if api_key is not None else "oidc"
    p_hash = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[
        :16
    ]
    return f"key:{key_id}|user:{end_user_id or ''}|params:{p_hash}"


def _guardrail_texts(messages: list[dict[str, Any]]) -> tuple[list[int], list[str]]:
    """(message positions, texts) for the string-content messages guardrails inspect."""
    positions = [
        i for i, m in enumerate(messages) if isinstance(m.get("content"), str) and m["content"]
    ]
    return positions, [messages[i]["content"] for i in positions]


def _apply_modified_texts(
    messages: list[dict[str, Any]], positions: list[int], results: list[dict[str, Any]]
) -> None:
    """Write guardrail-modified texts back to the messages they came from."""
    for result in results:
        if result.get("decision") == "modify" and result.get("modified_texts"):
            for text_idx, new_text in enumerate(result["modified_texts"]):
                if text_idx < len(positions):
                    messages[positions[text_idx]]["content"] = new_text


async def _cache_hit_rate_limit(
    workspace_id: uuid.UUID, subject: str | None, seed_routes: list[Any]
) -> None:
    """Cache hits still count against the per-user RPM of the alias's first route (G-05)."""
    if not subject or not seed_routes:
        return
    route = seed_routes[0]
    if route.per_user_rpm_limit:
        redis = await get_redis()
        await check_per_user_rpm(redis, workspace_id, subject, route.id, route.per_user_rpm_limit)


async def _check_cost_cap_cached(db: AsyncSession, route: GatewayRoute, workspace_id: Any) -> None:
    """check_cost_cap with a few seconds of reuse per route (review cd:gw-perf).

    Caps are daily / monthly sums, so re-deciding them on every request is ~6 queries
    per route for an answer that changes slowly. A pass or a refusal is reused for
    ``RUNLEDGER_GATEWAY_HOTPATH_TTL_S`` (default 5 s; 0 = always re-check)."""
    if route.daily_cost_limit_usd is None and route.monthly_cost_limit_usd is None:
        return
    key = ("cost_cap", str(route.id))
    cached = ttl_cache.get(key)
    if not is_missing(cached):
        if cached is not None:
            code, detail, headers = cached
            raise HTTPException(code, detail, headers=dict(headers or {}))
        return
    try:
        await check_cost_cap(db, route, workspace_id)
    except HTTPException as exc:
        ttl_cache.put(key, (exc.status_code, exc.detail, dict(exc.headers or {})))
        raise
    ttl_cache.put(key, None)


def _cache_savings_route(seed_routes: list[Any], model: str | None) -> Any:
    """The route whose price a cache hit saved: the seed route serving ``model``."""
    for route in seed_routes:
        if model in (route.target_model, route.alias):
            return route
    return seed_routes[0] if seed_routes else None


async def _cache_hit_savings(
    db: AsyncSession,
    workspace_id: Any,
    seed_routes: list[Any],
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
) -> Decimal | None:
    route = _cache_savings_route(seed_routes, model)
    if route is None:
        return None
    try:
        return await calculate_cost(
            db,
            provider=route.provider,
            model=route.target_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            workspace_id=workspace_id,
        )
    except Exception:  # noqa: BLE001
        return None


async def _enforce_request_budgets(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    end_user_id: str | None,
    feature_tag: str | None,
    principal_user_id: uuid.UUID | None,
    route_alias: str,
    request_tags: list[str],
    preferred_region: str | None,
) -> tuple[str, str | None]:
    """Apply workspace / end-user / feature-tag / API-key / access-group budgets.

    Returns ``(route_alias, decision_note)``. Raises 429 when a ``block`` budget is
    exhausted, when a ``downgrade``/``fallback`` budget names a model with no active
    route, or when a ``throttle`` budget is over its per-minute allowance. Fails open
    if Redis is unavailable.
    """
    redis = await get_redis()
    try:
        check = await check_request_budgets(
            redis,
            db,
            workspace_id=workspace_id,
            api_key_id=api_key_id,
            end_user_id=end_user_id,
            feature_tag=feature_tag,
            principal_user_id=principal_user_id,
        )
    except Exception:
        log.warning("gateway_budget_check_failed", workspace_id=str(workspace_id), exc_info=True)
        return route_alias, None

    if check.allowed and not check.throttled:
        return route_alias, None
    if check.action == "block":
        raise _budget_exceeded(check.budget_id, "Budget limit reached")
    if check.action in {"downgrade", "fallback"}:
        target = check.downgrade_model or check.fallback_model
        alias = (
            await _route_alias_for_model(db, workspace_id, target, request_tags, preferred_region)
            if target
            else None
        )
        if alias is None:
            raise _budget_exceeded(
                check.budget_id,
                f"Budget limit reached and no active route serves the downgrade model '{target}'",
            )
        return alias, f"budget_{check.action}:{check.budget_id}"
    if check.throttled and check.budget_id:
        try:
            over = await check_budget_throttle(redis, check.budget_id, settings.budget_throttle_rpm)
        except Exception:
            over = False
        if over:
            exc = _budget_exceeded(check.budget_id, "Budget limit reached: request throttled")
            exc.headers = {**(exc.headers or {}), "Retry-After": "60"}
            raise exc
        return route_alias, f"budget_throttle:{check.budget_id}"
    return route_alias, None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _record_canonical_gateway_run(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    route: GatewayRoute,
    body: GatewayRuntimeFinalizeRequest,
    input_tokens: int | None,
    output_tokens: int | None,
    blocked_reason: str | None = None,
    shadow_of: str | None = None,
) -> tuple[Decimal | None, uuid.UUID, uuid.UUID, str | None]:
    """Record the gateway call as a run; returns (cost, run_id, provider_call_id, feature_tag).

    ``blocked_reason`` marks a response a post-call guardrail blocked: the provider was
    still paid, so the run is recorded (as failed) with its full cost (review G-10).
    ``shadow_of`` marks a mirrored (shadow) call of that alias: real spend, so it is
    priced and counted, and flagged ``shadow`` so dashboards can separate it (G-12)."""
    ended_at = datetime.now(UTC)
    latency_ms = body.latency_ms if body.latency_ms is not None else body.total_wall_ms
    started_at = ended_at - timedelta(milliseconds=latency_ms or 0)
    metadata = body.request_metadata or {}
    response_id = body.response_json.get("id")
    cost = await calculate_cost(
        db,
        provider=route.provider,
        model=route.target_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        at_time=ended_at,
        workspace_id=workspace_id,
    )
    run_metadata = {
        **metadata,
        "source": "runledger.gateway-rs",
        "model_requested": body.model_requested,
        "model_used": route.target_model,
        "route_id": str(route.id),
        "route_alias": route.alias,
        "provider": route.provider,
        "decision_reason": body.decision_reason,
        "request_tags": body.request_tags,
        "compiler_enabled": body.compiler_enabled,
        "semantic_cache_enabled": body.semantic_cache_enabled,
        "guardrails_enabled": body.guardrails_enabled,
        "ir_decision": body.ir_decision,
        "response_id": response_id,
    }
    if blocked_reason:
        run_metadata["guardrail_blocked"] = blocked_reason
    if shadow_of:
        run_metadata["shadow"] = True
        run_metadata["shadow_of_alias"] = shadow_of
    if body.request_id is not None:
        run_metadata["gateway_request_id"] = str(body.request_id)
    decision = dict(body.decision or {})
    prompt_info = decision.get("prompt") if isinstance(decision.get("prompt"), dict) else None
    if decision:
        # The structured "why this route" record the run-detail panel reads (ENH).
        decision.setdefault("route", {})
        if isinstance(decision["route"], dict):
            decision["route"]["served"] = {
                "route_id": str(route.id),
                "alias": route.alias,
                "provider": route.provider,
                "target_model": route.target_model,
                "region": route.region,
                "reason": body.decision_reason,
                "shadow": bool(shadow_of),
            }
        if blocked_reason:
            decision.setdefault("guardrail", {})
            if isinstance(decision["guardrail"], dict):
                decision["guardrail"]["post_call"] = "block"
                decision["guardrail"]["reason"] = blocked_reason
        run_metadata["gateway_decision"] = decision
    if prompt_info:
        run_metadata.update({k: v for k, v in prompt_info.items() if k.startswith("prompt_")})
    feature_tag = _feature_tag_from(metadata, body.request_tags)

    run = AgentRun(
        workspace_id=workspace_id,
        api_key_id=body.api_key_id,
        end_user_id=body.end_user_id,
        session_id=_metadata_text(metadata, "runledger.session_id", "session_id", "session"),
        feature_tag=feature_tag,
        deployment_version=_metadata_text(
            metadata,
            "runledger.deployment_version",
            "deployment_version",
            "service.version",
            "version",
        )
        # A resolved prompt ref keys the run to its prompt version (review B-23).
        or (
            f"{prompt_info['prompt_name']}:{prompt_info['prompt_version']}"
            if prompt_info and prompt_info.get("prompt_name")
            else None
        ),
        status=RunStatusEnum.failed if blocked_reason else RunStatusEnum.succeeded,
        started_at=started_at,
        ended_at=ended_at,
        total_cost_usd=cost,
        total_input_tokens=input_tokens,
        total_output_tokens=output_tokens,
        run_metadata=run_metadata,
        intent=_metadata_text(metadata, "intent", "task.intent"),
        source_type="gateway-shadow" if shadow_of else "gateway-rs",
    )
    db.add(run)
    await db.flush()

    span = Span(
        run_id=run.id,
        span_type=SpanTypeEnum.llm,
        name=f"{route.provider}:{route.target_model}"[:255],
        started_at=started_at,
        ended_at=ended_at,
        status=SpanStatusEnum.failed if blocked_reason else SpanStatusEnum.succeeded,
        cost_usd=cost,
        span_metadata={
            "source": "runledger.gateway-rs",
            "route_id": str(route.id),
            "route_alias": route.alias,
            "model_requested": body.model_requested,
            "decision_reason": body.decision_reason,
            "response_id": response_id,
        },
    )
    db.add(span)
    await db.flush()

    provider_call_id = uuid.uuid4()
    db.add(
        ProviderCall(
            id=provider_call_id,
            span_id=span.id,
            run_id=run.id,
            workspace_id=workspace_id,
            api_key_id=body.api_key_id,
            end_user_id=body.end_user_id,
            provider=route.provider,
            model=route.target_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=body.latency_ms,
            cost_usd=cost,
            status="success",
            provider_request_id=str(response_id) if response_id else None,
            cost_source="pricing" if cost is not None else None,
            model_provider=route.provider,
            is_billable=True,
        )
    )
    await db.flush()
    return cost, run.id, provider_call_id, feature_tag


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
    needed = None
    if body.required_scope:
        try:
            needed = frozenset(normalize_scopes([body.required_scope]))
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    workspace, api_key, oidc_auth = await _resolve_gateway_bearer_token(body.raw_key, db, needed)
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
    # Route / group lookups run once per request inside the memo (review cd:gw-perf).
    with request_memo():
        return await _preflight(body, db)


async def _preflight(
    body: GatewayRuntimePreflightRequest, db: AsyncSession
) -> GatewayRuntimePreflightResponse:
    request_id = uuid.uuid4()
    trace = DecisionTrace(request_id=request_id, model_requested=body.body.model)
    workspace, api_key, _oidc_auth = await _resolve_gateway_bearer_token(
        body.raw_key, db, GATEWAY_SCOPE
    )

    metadata = body.body.metadata or {}
    # The ACL always runs (no client IP + active rules = 403), works for OIDC callers
    # (no API key) and scopes by access group via the principal user (review G-18).
    principal_user_id = await resolve_principal_user_id(
        db, api_key=api_key, end_user_id=body.end_user_id, workspace=workspace
    )
    await evaluate_ip_acl(
        db,
        workspace_id=workspace.id,
        api_key_id=api_key.id if api_key is not None else None,
        client_ip=body.client_ip,
        principal_user_id=principal_user_id,
    )
    missing_metadata = await enforce_required_metadata(
        db, workspace_id=workspace.id, metadata=metadata
    )

    # Keep every message field (tool_calls, tool_call_id, name, …), not just role/content.
    messages = [m.model_dump(exclude_none=True) for m in body.body.messages]
    request_tags = (
        [str(tag).strip() for tag in metadata.get("tags", [])]
        if isinstance(metadata.get("tags"), list)
        else []
    )
    if body.tags_header:
        request_tags.extend(tag.strip() for tag in body.tags_header.split(",") if tag.strip())
    request_tags = await resolve_request_tags(db, workspace.id, body.body.model, request_tags)
    preferred_region = body.region_header.strip() if body.region_header else None
    api_key_id = api_key.id if api_key is not None else None
    workflow = _feature_tag_from(metadata, request_tags)

    # A managed prompt named by ref is rendered and prepended before guardrails run, so
    # its text is checked like the caller's own messages (review B-23).
    if body.body.prompt:
        resolved_prompt = await resolve_prompt_ref(
            db, workspace.id, body.body.prompt, body.body.prompt_variables
        )
        messages = apply_resolved_prompt(messages, resolved_prompt)
        trace.prompt = {
            **resolved_prompt.as_metadata(),
            "missing_variables": list(resolved_prompt.missing_variables),
        }

    # Guardrails run before either cache is consulted, so a cache hit can't bypass
    # them, and before any sidecar (compiler, router) sees the prompt (G-05, G-09).
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
        # Guardrails see string-content messages only; the positions map each text back to
        # its message so a "modify" result rewrites the right one (review G-08).
        text_positions, pre_texts = _guardrail_texts(messages)
        gr_decision, gr_results, _ = await evaluate_guardrails(
            db,
            workspace.id,
            "pre_call",
            texts=pre_texts,
            structured_messages=messages,
            model=body.body.model,
            end_user_id=body.end_user_id,
            user_id=str(principal_user_id) if principal_user_id else None,
            guardrail_ids=guardrail_ids,
            gateway_request_id=request_id,
            api_key_id=api_key_id,
            workflow=workflow,
        )
        trace.guardrail = {"pre_call": gr_decision, "checked": len(gr_results)}
        if gr_decision == "block":
            blocked_reason = next(
                (r["reason"] for r in gr_results if r["decision"] == "block"),
                "Blocked by guardrail",
            )
            raise HTTPException(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, blocked_reason)
        if gr_decision == "modify":
            _apply_modified_texts(messages, text_positions, gr_results)
    else:
        trace.guardrail = {"pre_call": "off"}

    seed_routes = await select_routes(
        db,
        workspace.id,
        body.body.model,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )
    # PII redaction runs before the caches, the context compiler and the classifier, so
    # none of them (and no cache entry) sees the raw values (review G-09, S-12).
    if seed_routes and seed_routes[0].pii_redaction_enabled:
        messages = redact_messages(messages)
    # One cache key for lookup (here) and store (finalize): model, guardrail-processed
    # messages and every parameter that changes the answer (G-07, G-19).
    cache_params = _cache_params(body.body)
    # Per-user RPM applies to the end user, or the API key when none is named (G-14).
    rpm_key = rpm_subject(body.end_user_id, api_key.id if api_key is not None else None)
    cache_key = make_cache_key(body.body.model, messages, cache_params)
    semantic_scope = _semantic_scope(api_key, body.end_user_id, cache_params)

    cache_entry = None
    cache_profile = await get_cache_profile(db, workspace.id)
    exact_cacheable = (
        body.body.cache and not body.body.stream and cache_profile.allows(body.body.model)
    )
    if exact_cacheable:
        cache_entry = await check_cache(db, workspace.id, cache_key, model=body.body.model)
    trace.cache["exact"] = (
        "hit" if cache_entry is not None else ("miss" if exact_cacheable else "off")
    )
    if cache_entry is not None:
        await _cache_hit_rate_limit(workspace.id, rpm_key, seed_routes)
        await increment_hit_count(db, cache_entry)
        await record_cache_outcome(
            db,
            workspace.id,
            hit=True,
            savings_usd=await _cache_hit_savings(
                db,
                workspace.id,
                seed_routes,
                cache_entry.model,
                cache_entry.prompt_tokens,
                cache_entry.completion_tokens,
            ),
        )
        trace.route = {"alias": body.body.model, "reason": "cache_hit"}
        trace.budget = {"status": "skipped"}
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
            config_fingerprint={"decision": trace.as_dict()},
            request_id=request_id,
            api_key_id=api_key_id,
            workflow=workflow,
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
            cache_key=cache_key,
            prepared_messages=messages,
            effective_tools=body.body.tools,
            effective_reasoning_effort=body.body.reasoning_effort,
            decision_reason="cache_hit",
            execution_steps=[],
            request_id=request_id,
            decision=trace.as_dict(),
            decision_header=trace.header(),
        )
    if exact_cacheable:
        await record_cache_outcome(db, workspace.id, hit=False)

    semantic_enabled = body.body.semantic_cache
    if not semantic_enabled and not body.body.stream:
        semantic_enabled = bool(seed_routes and seed_routes[0].semantic_cache_enabled)
    if semantic_enabled and not body.body.stream:
        sem_hit = await semantic_cache_svc.lookup(
            workspace.id,
            body.body.model,
            messages,
            security_scope=semantic_scope,
            threshold=cache_profile.similarity_threshold,
        )
        trace.cache["semantic"] = "hit" if sem_hit is not None else "miss"
        if sem_hit is not None:
            await _cache_hit_rate_limit(workspace.id, rpm_key, seed_routes)
            usage = sem_hit.get("usage") or {}
            await record_cache_outcome(
                db,
                workspace.id,
                hit=True,
                savings_usd=await _cache_hit_savings(
                    db,
                    workspace.id,
                    seed_routes,
                    body.body.model,
                    _optional_int(usage.get("prompt_tokens")),
                    _optional_int(usage.get("completion_tokens")),
                ),
            )
            trace.route = {"alias": body.body.model, "reason": "semantic_cache_hit"}
            trace.budget = {"status": "skipped"}
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
                config_fingerprint={"decision": trace.as_dict()},
                request_id=request_id,
                api_key_id=api_key_id,
                workflow=workflow,
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
                cache_key=cache_key,
                semantic_scope=semantic_scope,
                prepared_messages=messages,
                effective_tools=body.body.tools,
                effective_reasoning_effort=body.body.reasoning_effort,
                semantic_cache_enabled=True,
                decision_reason="semantic_cache_hit",
                execution_steps=[],
                request_id=request_id,
                decision=trace.as_dict(),
                decision_header=trace.header(),
            )
    elif "semantic" not in trace.cache:
        trace.cache["semantic"] = "off"

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

    alias_before_budget = route_alias
    route_alias, budget_note = await _enforce_request_budgets(
        db,
        workspace_id=workspace.id,
        api_key_id=api_key_id,
        end_user_id=body.end_user_id,
        feature_tag=workflow,
        principal_user_id=principal_user_id,
        route_alias=route_alias,
        request_tags=request_tags,
        preferred_region=preferred_region,
    )

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
    trace.budget = {"status": "ok"}
    if budget_note:
        decision_reason = f"{decision_reason}|{budget_note}"
        action, _, budget_id = budget_note.partition(":")
        trace.budget = {
            "status": action.removeprefix("budget_"),
            "budget_id": budget_id or None,
            "rerouted_from": alias_before_budget if route_alias != alias_before_budget else None,
        }
    if ir_decision:
        trace.intelligent_routing = {
            k: ir_decision.get(k) for k in ("alias", "reason", "task_class", "reasoning_effort")
        }
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
    provider_budget_blocked = False
    # The last cost-cap / RPM refusal; returned (429 + reason headers) when it leaves no
    # runnable route, so a limit isn't reported as a 502 outage (review G-13).
    limit_refusal: HTTPException | None = None

    async def _route_within_provider_budgets(
        db: AsyncSession, workspace_id: uuid.UUID, route: GatewayRoute
    ) -> bool:
        nonlocal provider_budget_blocked
        try:
            result = await check_provider_profile_budgets(
                await get_redis(),
                db,
                workspace_id=workspace_id,
                provider=route.provider,
                model=route.target_model,
            )
        except Exception:
            log.warning("gateway_provider_budget_check_failed", route_id=str(route.id))
            return True
        if result.allowed:
            return True
        provider_budget_blocked = True
        return False

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
                await _check_cost_cap_cached(db, route, workspace.id)
                if not await _route_within_provider_budgets(db, workspace.id, route):
                    continue
                if rpm_key and route.per_user_rpm_limit:
                    redis = await get_redis()
                    # Only the first runnable route (the one expected to serve) takes a
                    # slot; fallbacks are checked without counting (review G-14).
                    await check_per_user_rpm(
                        redis,
                        workspace.id,
                        rpm_key,
                        route.id,
                        route.per_user_rpm_limit,
                        consume=not execution_steps,
                    )
            except HTTPException as exc:
                if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    limit_refusal = exc
                    trace.skipped.append(
                        {
                            "route_id": str(route.id),
                            "alias": alias_to_try,
                            "why": (exc.headers or {}).get("X-Cost-Cap-Reason")
                            or str(exc.detail)[:80],
                        }
                    )
                continue
            step_forward_messages = (
                redact_messages(step_messages) if route.pii_redaction_enabled else step_messages
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
            if body.body.stream and (route.provider or "").lower() in _STREAM_USAGE_PROVIDERS:
                # Ask OpenAI-compatible providers to report token usage in the last
                # stream chunk, so streamed calls are metered (review G-03).
                step_request["stream_options"] = {"include_usage": True}
            direct_provider = _runtime_direct_provider_request(
                route=route,
                request_body=step_request,
                stream=body.body.stream,
            )
            step_entry: dict[str, Any] = {
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
                # gateway-rs samples mirrors itself and fires them in the background.
                "mirror_sample_pct": _mirror_sample_pct(route),
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
            if direct_provider is not None and hasattr(direct_provider, "response_format"):
                if direct_provider.response_format:
                    step_entry["response_format"] = direct_provider.response_format
                if direct_provider.provider_stream_format:
                    step_entry["provider_stream_format"] = direct_provider.provider_stream_format
            execution_steps.append(step_entry)
            trace.candidates.append(
                {
                    "route_id": str(route.id),
                    "alias": alias_to_try,
                    "provider": route.provider,
                    "target_model": route.target_model,
                    "trigger": trigger,
                    "region": route.region,
                }
            )

    if not execution_steps:
        if limit_refusal is not None:
            raise limit_refusal
        if provider_budget_blocked:
            raise _budget_exceeded(
                None, "Provider budget limit reached for every route serving this request"
            )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"No runnable gateway routes remained for alias '{route_alias}'",
        )

    trace.route = {
        "alias": route_alias,
        "requested": body.body.model,
        "reason": decision_reason,
        "primary_route_id": str(primary_route.id),
    }
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
        cache_key=cache_key,
        semantic_scope=semantic_scope,
        request_id=request_id,
        decision=trace.as_dict(),
        decision_header=trace.header(),
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

    # A post-call block still records the run, the request and the spend (the provider
    # was paid) and skips the caches; the 451 is raised at the end (review G-10).
    blocked_reason: str | None = None
    finalize_workflow = _feature_tag_from(body.request_metadata or {}, body.request_tags)
    if body.guardrails_enabled:
        finalize_key = await db.get(ApiKey, body.api_key_id) if body.api_key_id else None
        principal_user_id = await resolve_principal_user_id(
            db, api_key=finalize_key, end_user_id=body.end_user_id, workspace=workspace
        )
        response_content = ""
        response_tool_calls: list[dict[str, Any]] = []
        choices = body.response_json.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            response_content = msg.get("content", "") or ""
            response_tool_calls = [c for c in (msg.get("tool_calls") or []) if isinstance(c, dict)]
        # Tool-call arguments are checked like response text, so a model can't route
        # blocked content through a function call (review G-10).
        tool_arg_texts = [
            str((c.get("function") or {}).get("arguments") or "") for c in response_tool_calls
        ]
        response_texts = [t for t in [response_content, *tool_arg_texts] if t]
        if response_texts:
            post_result = await evaluate_guardrails(
                db,
                workspace.id,
                "post_call",
                texts=response_texts,
                tool_calls=response_tool_calls or None,
                structured_messages=body.prepared_messages,
                model=body.model_requested,
                end_user_id=body.end_user_id,
                user_id=str(principal_user_id) if principal_user_id else None,
                gateway_request_id=body.request_id,
                api_key_id=body.api_key_id,
                workflow=finalize_workflow,
            )
            during_result = await evaluate_guardrails(
                db,
                workspace.id,
                "during_call",
                texts=[
                    str(m.get("content", "")) for m in body.prepared_messages if m.get("content")
                ]
                + response_texts,
                tool_calls=response_tool_calls or None,
                structured_messages=body.prepared_messages,
                model=body.model_requested,
                end_user_id=body.end_user_id,
                user_id=str(principal_user_id) if principal_user_id else None,
                gateway_request_id=body.request_id,
                api_key_id=body.api_key_id,
                workflow=finalize_workflow,
            )
            for phase_decision, phase_results, _ in [post_result, during_result]:
                if phase_decision == "block" and blocked_reason is None:
                    blocked_reason = next(
                        (r["reason"] for r in phase_results if r["decision"] == "block"),
                        "Response blocked by guardrail",
                    )

    usage = body.response_json.get("usage") or {}
    input_tokens = _optional_int(usage.get("prompt_tokens"))
    output_tokens = _optional_int(usage.get("completion_tokens"))
    if body.cache and blocked_reason is None:
        # The key preflight looked up with (falls back for older gateways).
        cache_key = body.cache_key or make_cache_key(body.model_requested, body.prepared_messages)
        await store_cache(
            db=db,
            workspace_id=workspace.id,
            cache_key=cache_key,
            model=route.target_model,
            response_json=body.response_json,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            scope_model=body.model_requested,
        )
    if body.semantic_cache_enabled and blocked_reason is None:
        await semantic_cache_svc.store(
            workspace_id=workspace.id,
            model=body.model_requested,
            messages=body.prepared_messages,
            response_json=body.response_json,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            security_scope=body.semantic_scope
            or f"key:{body.api_key_id or 'oidc'}|user:{body.end_user_id or ''}",
        )
    gateway_overhead_ms = max((body.total_wall_ms or 0) - (body.latency_ms or 0), 0)
    cost, run_id, provider_call_id, feature_tag = await _record_canonical_gateway_run(
        db,
        workspace_id=workspace.id,
        route=route,
        body=body,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        blocked_reason=blocked_reason,
    )
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
        req_status="blocked" if blocked_reason else "success",
        decision_reason=(
            f"guardrail_blocked: {blocked_reason}"[:255] if blocked_reason else body.decision_reason
        ),
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
        request_id=body.request_id,
        run_id=run_id,
        api_key_id=body.api_key_id,
        workflow=feature_tag,
    )
    # Pre- and post-call guardrail events of this request now point at its run (G-19).
    await link_guardrail_events_to_run(
        db, workspace_id=workspace.id, request_id=body.request_id, run_id=run_id
    )
    try:
        async with db.begin_nested():
            await record_budget_spend(
                db,
                await get_redis(),
                workspace_id=workspace.id,
                provider_call_id=provider_call_id,
                cost_usd=cost,
                run_id=run_id,
                api_key_id=body.api_key_id,
                end_user_id=body.end_user_id,
                feature_tag=feature_tag,
                provider=route.provider,
                model=route.target_model,
            )
        await db.commit()
    except Exception:
        log.exception("gateway_budget_spend_failed", provider_call_id=str(provider_call_id))
    if blocked_reason:
        raise HTTPException(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, blocked_reason)
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
        chunks = stream_request(
            route=route,
            messages=messages,
            timeout_override_ms=body.timeout_ms,
            **kwargs,
        ).__aiter__()
        # Read the first chunk before answering, so a provider error or timeout gets a
        # real status code instead of a broken stream.
        try:
            first = await chunks.__anext__()
        except StopAsyncIteration:
            first = b""
        except Exception as exc:  # noqa: BLE001
            return _provider_error_response(exc)

        async def _provider_stream() -> AsyncGenerator[bytes]:
            if first:
                yield first
            async for chunk in chunks:
                yield chunk

        return StreamingResponse(_provider_stream(), media_type="text/event-stream")

    try:
        return await forward_request(
            route=route,
            messages=messages,
            timeout_override_ms=body.timeout_ms,
            **kwargs,
        )
    except Exception as exc:  # noqa: BLE001
        return _provider_error_response(exc)


def _provider_error_response(exc: Exception) -> JSONResponse:
    """Map a provider failure to a response gateway-rs can act on: the provider's own
    status and body (so 400/413 reach the error-triggered fallbacks, review G-11), 504 on
    timeout, 502 when the provider can't be reached. Previously these escaped as a
    dropped connection."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            content: Any = exc.response.json()
        except ValueError:
            content = {"detail": exc.response.text[:4000]}
        return JSONResponse(status_code=exc.response.status_code, content=content)
    if isinstance(exc, httpx.TimeoutException):
        return JSONResponse(status_code=504, content={"detail": "provider request timed out"})
    log.warning("gateway_provider_execute_failed", error=str(exc)[:300])
    return JSONResponse(
        status_code=502, content={"detail": f"provider request failed: {exc}"[:500]}
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


def _mirror_sample_pct(route: GatewayRoute) -> float:
    """The route's mirror sample rate (0–1), or 0 when it has no mirror alias."""
    cfg = route.mirror_config if isinstance(route.mirror_config, dict) else {}
    if not cfg.get("alias"):
        return 0.0
    try:
        return max(0.0, min(1.0, float(cfg.get("sample_pct") or 0)))
    except (TypeError, ValueError):
        return 0.0


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
    if not mirror_alias or mirror_pct <= 0:
        return {"ok": True}
    if not body.sampled and random.random() >= mirror_pct:  # noqa: S311
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
    # The messages already passed pre-call guardrails (and the primary route's
    # redaction); redact again when the shadow route asks for it (review G-12).
    if mirror_route.pii_redaction_enabled:
        messages = redact_messages(messages)

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
        latency_ms = int((time.monotonic() - started) * 1000)
        input_tokens = _optional_int(usage.get("prompt_tokens"))
        output_tokens = _optional_int(usage.get("completion_tokens"))
        decision = f"mirror:{route.alias}->{mirror_alias}|shadow_compare:{similarity:.3f}"
        # Shadow spend is real spend: record it as a priced, shadow-flagged run and count
        # it against budgets, so it isn't invisible to FinOps (review G-12).
        cost, run_id, provider_call_id, feature_tag = await _record_canonical_gateway_run(
            db,
            workspace_id=body.workspace_id,
            route=mirror_route,
            body=GatewayRuntimeFinalizeRequest(
                workspace_id=body.workspace_id,
                route_id=mirror_route.id,
                api_key_id=body.api_key_id,
                model_requested=body.model_requested,
                prepared_messages=messages,
                response_json=mirror_response,
                request_metadata=body.request_metadata,
                request_tags=body.request_tags,
                latency_ms=latency_ms,
                decision_reason=decision,
                end_user_id=body.end_user_id,
                request_id=None,
            ),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            shadow_of=route.alias,
        )
        await record_gateway_request(
            db=db,
            workspace_id=body.workspace_id,
            model_requested=f"mirror:{body.model_requested}",
            route=mirror_route,
            model_used=mirror_route.target_model,
            cache_hit=False,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            req_status="success",
            decision_reason=decision,
            config_fingerprint={
                "shadow": True,
                "cost_usd": str(cost) if cost is not None else None,
                "run_id": str(run_id),
                "shadow_of_request_id": str(body.request_id) if body.request_id else None,
            },
            run_id=run_id,
            api_key_id=body.api_key_id,
            workflow=feature_tag,
        )
        try:
            async with db.begin_nested():
                await record_budget_spend(
                    db,
                    await get_redis(),
                    workspace_id=body.workspace_id,
                    provider_call_id=provider_call_id,
                    cost_usd=cost,
                    run_id=run_id,
                    api_key_id=body.api_key_id,
                    end_user_id=body.end_user_id,
                    feature_tag=feature_tag,
                    provider=mirror_route.provider,
                    model=mirror_route.target_model,
                )
            await db.commit()
        except Exception:
            log.exception("gateway_mirror_budget_spend_failed")
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


# ── Run decision ("why this route") ───────────────────────────────────────────


class GatewayRunGuardrailEvent(BaseModel):
    guardrail_name: str
    mode: str
    decision: str
    reason: str | None = None
    latency_ms: float | None = None
    created_at: datetime


class GatewayRunDecisionResponse(BaseModel):
    """Everything the gateway decided for one run: the decision trace preflight built
    (route, cache, budget, guardrail, prompt, candidates, skipped routes), the request
    row it recorded and the guardrail events linked to it (ENH, review G-19)."""

    run_id: uuid.UUID
    gateway_request_id: uuid.UUID | None = None
    decision: dict[str, Any] | None = None
    decision_header: str | None = None
    status: str | None = None
    latency_ms: int | None = None
    gateway_overhead_ms: int | None = None
    workflow: str | None = None
    api_key_id: uuid.UUID | None = None
    guardrail_events: list[GatewayRunGuardrailEvent] = Field(default_factory=list)


def _header_from_decision(decision: dict[str, Any]) -> str | None:
    """The X-RunLedger-Decision value this run was answered with."""
    served = (decision.get("route") or {}).get("served") or {}
    parts = []
    if served:
        parts.append(
            f"route={served.get('alias')}/{served.get('provider')}:{served.get('target_model')}"
        )
    cache = (decision.get("cache") or {}).get("result")
    if cache:
        parts.append(f"cache={cache}")
    budget = (decision.get("budget") or {}).get("status")
    if budget:
        parts.append(f"budget={budget}")
    guardrail = (decision.get("guardrail") or {}).get("result")
    if guardrail:
        parts.append(f"guardrail={guardrail}")
    return "; ".join(parts) or None


@router.get("/runs/{run_id}/decision", response_model=GatewayRunDecisionResponse)
async def get_gateway_run_decision(
    run_id: uuid.UUID,
    workspace: WorkspaceDep,
    db: DbDep,
) -> GatewayRunDecisionResponse:
    from runledger_api.models.guardrails import GuardrailEvent  # noqa: PLC0415

    run = await db.get(AgentRun, run_id)
    if run is None or run.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    request_row = (
        await db.execute(
            select(GatewayRequest)
            .where(GatewayRequest.workspace_id == workspace.id, GatewayRequest.run_id == run_id)
            .order_by(GatewayRequest.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    metadata = run.run_metadata or {}
    decision = metadata.get("gateway_decision") if isinstance(metadata, dict) else None
    events = list(
        (
            await db.execute(
                select(GuardrailEvent)
                .where(GuardrailEvent.workspace_id == workspace.id, GuardrailEvent.run_id == run_id)
                .order_by(GuardrailEvent.created_at.asc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    fingerprint = (request_row.config_fingerprint or {}) if request_row is not None else {}
    overhead = fingerprint.get("gateway_overhead_ms") if isinstance(fingerprint, dict) else None
    return GatewayRunDecisionResponse(
        run_id=run_id,
        gateway_request_id=request_row.id if request_row is not None else None,
        decision=decision if isinstance(decision, dict) else None,
        decision_header=_header_from_decision(decision) if isinstance(decision, dict) else None,
        status=request_row.status if request_row is not None else None,
        latency_ms=request_row.latency_ms if request_row is not None else None,
        gateway_overhead_ms=_optional_int(overhead),
        workflow=(request_row.workflow if request_row is not None else None) or run.feature_tag,
        api_key_id=(request_row.api_key_id if request_row is not None else None) or run.api_key_id,
        guardrail_events=[
            GatewayRunGuardrailEvent(
                guardrail_name=e.guardrail_name,
                mode=e.mode,
                decision=e.decision,
                reason=e.reason,
                latency_ms=e.latency_ms,
                created_at=e.created_at,
            )
            for e in events
        ],
    )
