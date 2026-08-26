"""Shared gateway router imports, type aliases, and helpers."""

from __future__ import annotations

import logging
import math  # noqa: F401
import os
import random  # noqa: F401
import time  # noqa: F401
import uuid  # noqa: F401
from collections.abc import AsyncGenerator  # noqa: F401
from datetime import UTC, datetime, timedelta  # noqa: F401
from decimal import Decimal  # noqa: F401
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx  # noqa: F401
import sqlalchemy as sa  # noqa: F401
from fastapi import Depends, Header, HTTPException, Query, Request, status  # noqa: F401
from fastapi.responses import Response, StreamingResponse  # noqa: F401
from sqlalchemy import func, select  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

import runledger_api.services.context_compiler as context_compiler  # noqa: F401
import runledger_api.services.intelligent_router as intelligent_router  # noqa: F401
import runledger_api.services.semantic_cache as semantic_cache_svc  # noqa: F401
from runledger_api.core.db import get_db
from runledger_api.core.deps import (
    get_current_api_key,
    get_current_workspace,
    require_admin,
    require_org_admin,
)
from runledger_api.models.gateway import (
    GatewayPassThroughEndpoint,
    GatewayRequest,  # noqa: F401
    GatewayRoute,
    GatewayRoutingGroup,
    RoutingPolicy,  # noqa: F401
)
from runledger_api.models.tenant import ApiKey, TenantUser, User, Workspace
from runledger_api.schemas.gateway import (  # noqa: F401
    GatewayBenchmarkComparisonItem,
    GatewayBenchmarkComparisonList,
    GatewayCompletionRequest,
    GatewayDeploymentHealthItem,
    GatewayDeploymentHealthList,
    GatewayPassThroughEndpointCreate,
    GatewayPassThroughEndpointList,
    GatewayPassThroughEndpointResponse,
    GatewayPassThroughEndpointStats,
    GatewayPassThroughEndpointStatsList,
    GatewayPassThroughEndpointUpdate,
    GatewayPassThroughTestRequest,
    GatewayPassThroughTestResponse,
    GatewayRateLimitOverview,
    GatewayRateLimitTier,
    GatewayRequestList,
    GatewayRequestResponse,
    GatewayRouteCreate,
    GatewayRouteList,
    GatewayRouteResponse,
    GatewayRouteStats,
    GatewayRouteUpdate,
    GatewayRoutingGroupCreate,
    GatewayRoutingGroupList,
    GatewayRoutingGroupResponse,
    GatewayRoutingGroupRouteSummary,
    GatewayRoutingGroupUpdate,
    GatewayRoutingStrategyComparison,
    GatewayRoutingStrategyComparisonItem,
    GatewayRuntimeApiKeyResolveRequest,
    GatewayRuntimeApiKeyResolveResponse,
    GatewayRuntimeEventBatchRequest,
    GatewayRuntimeEventBatchResponse,
    GatewayRuntimeFinalizeRequest,
    GatewayRuntimeFinalizeResponse,
    GatewayRuntimeMirrorRequest,
    GatewayRuntimePreflightRequest,
    GatewayRuntimePreflightResponse,
    GatewayRuntimeProviderExecuteRequest,
    GatewayRuntimeRouteResultRequest,
    GatewayRuntimeSnapshotResponse,
    GatewayStats,
    RoutingPolicyActionResponse,
    RoutingPolicyAnalysisResponse,
    RoutingPolicyCreate,
    RoutingPolicyList,
    RoutingPolicyPromotionRequest,
    RoutingPolicyResponse,
    RoutingPolicyUpdate,
    RoutingPolicyVariantMetrics,
    RoutingRecommendationModel,
    RoutingRecommendationResponse,
)
from runledger_api.services.auth import verify_api_key
from runledger_api.services.gateway import (  # noqa: F401
    _apply_prompt_overrides,
    _override_value,
    _response_text,
    _shadow_similarity,
    check_cache,
    choose_route_for_alias,
    forward_request,
    increment_hit_count,
    make_cache_key,
    record_gateway_request,
    resolve_request_tags,
    select_routes,
    store_cache,
    stream_request,
)
from runledger_api.services.gateway_controls import (  # noqa: F401
    check_cost_cap,
    check_per_user_rpm,
)
from runledger_api.services.gateway_providers import VertexAdapter
from runledger_api.services.gateway_redact import redact_messages  # noqa: F401
from runledger_api.services.gateway_runtime import (  # noqa: F401
    build_gateway_runtime_snapshot,
    ingest_gateway_runtime_events,
    verify_gateway_runtime_signature,
)
from runledger_api.services.guardrails import evaluate_guardrails  # noqa: F401
from runledger_api.services.routing import analyze_routing_policy  # noqa: F401
from runledger_api.services.security import (
    authenticate_oidc_token,
    enforce_required_metadata,  # noqa: F401
    evaluate_ip_acl,  # noqa: F401
    get_client_ip,  # noqa: F401
)

__all__ = [
    # stdlib re-exports
    "math",
    "random",
    "time",
    "uuid",
    "AsyncGenerator",
    "UTC",
    "datetime",
    "timedelta",
    "Decimal",
    "Any",
    "Annotated",
    # third-party re-exports
    "httpx",
    "sa",
    "Depends",
    "Header",
    "HTTPException",
    "Query",
    "Request",
    "status",
    "Response",
    "StreamingResponse",
    "func",
    "select",
    "AsyncSession",
    # module re-exports
    "context_compiler",
    "intelligent_router",
    "semantic_cache_svc",
    # db / deps
    "get_db",
    "get_current_api_key",
    "get_current_workspace",
    "require_admin",
    "require_org_admin",
    # models
    "GatewayPassThroughEndpoint",
    "GatewayRequest",
    "GatewayRoute",
    "GatewayRoutingGroup",
    "RoutingPolicy",
    "ApiKey",
    "TenantUser",
    "User",
    "Workspace",
    # schemas
    "GatewayBenchmarkComparisonItem",
    "GatewayBenchmarkComparisonList",
    "GatewayCompletionRequest",
    "GatewayDeploymentHealthItem",
    "GatewayDeploymentHealthList",
    "GatewayPassThroughEndpointCreate",
    "GatewayPassThroughEndpointList",
    "GatewayPassThroughEndpointResponse",
    "GatewayPassThroughEndpointStats",
    "GatewayPassThroughEndpointStatsList",
    "GatewayPassThroughEndpointUpdate",
    "GatewayPassThroughTestRequest",
    "GatewayPassThroughTestResponse",
    "GatewayRateLimitOverview",
    "GatewayRateLimitTier",
    "GatewayRequestList",
    "GatewayRequestResponse",
    "GatewayRouteCreate",
    "GatewayRouteList",
    "GatewayRouteResponse",
    "GatewayRouteStats",
    "GatewayRouteUpdate",
    "GatewayRoutingGroupCreate",
    "GatewayRoutingGroupList",
    "GatewayRoutingGroupResponse",
    "GatewayRoutingGroupRouteSummary",
    "GatewayRoutingGroupUpdate",
    "GatewayRoutingStrategyComparison",
    "GatewayRoutingStrategyComparisonItem",
    "GatewayRuntimeApiKeyResolveRequest",
    "GatewayRuntimeApiKeyResolveResponse",
    "GatewayRuntimeEventBatchRequest",
    "GatewayRuntimeEventBatchResponse",
    "GatewayRuntimeFinalizeRequest",
    "GatewayRuntimeFinalizeResponse",
    "GatewayRuntimeMirrorRequest",
    "GatewayRuntimePreflightRequest",
    "GatewayRuntimePreflightResponse",
    "GatewayRuntimeProviderExecuteRequest",
    "GatewayRuntimeRouteResultRequest",
    "GatewayRuntimeSnapshotResponse",
    "GatewayStats",
    "RoutingPolicyActionResponse",
    "RoutingPolicyAnalysisResponse",
    "RoutingPolicyCreate",
    "RoutingPolicyList",
    "RoutingPolicyPromotionRequest",
    "RoutingPolicyResponse",
    "RoutingPolicyUpdate",
    "RoutingPolicyVariantMetrics",
    "RoutingRecommendationModel",
    "RoutingRecommendationResponse",
    # services
    "verify_api_key",
    "_apply_prompt_overrides",
    "_override_value",
    "_response_text",
    "_shadow_similarity",
    "check_cache",
    "choose_route_for_alias",
    "forward_request",
    "increment_hit_count",
    "make_cache_key",
    "record_gateway_request",
    "resolve_request_tags",
    "select_routes",
    "store_cache",
    "stream_request",
    "check_cost_cap",
    "check_per_user_rpm",
    "VertexAdapter",
    "redact_messages",
    "build_gateway_runtime_snapshot",
    "ingest_gateway_runtime_events",
    "verify_gateway_runtime_signature",
    "evaluate_guardrails",
    "analyze_routing_policy",
    "authenticate_oidc_token",
    "enforce_required_metadata",
    "evaluate_ip_acl",
    "get_client_ip",
    # type aliases
    "DbDep",
    "WorkspaceDep",
    "OrgAdminDep",
    "AdminDep",
    "ApiKeyDep",
    # helpers
    "log",
    "urlencode",
    "os",
    "_config_fingerprint",
    "_segment_key",
    "_serialize_gateway_route",
    "_serialize_routing_group",
    "_runtime_request_body",
    "_runtime_direct_provider_request",
    "_PASSTHROUGH_ALLOWED_REQUEST_HEADERS",
    "_PASSTHROUGH_ALLOWED_RESPONSE_HEADERS",
    "_resolve_gateway_workspace",
    "_resolve_gateway_bearer_token",
    "_build_passthrough_headers",
    "_build_passthrough_target_url",
]

log = logging.getLogger(__name__)

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
OrgAdminDep = Annotated[tuple[Workspace, User, TenantUser | None], Depends(require_org_admin)]
AdminDep = Annotated[None, Depends(require_admin)]
ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]


def _config_fingerprint(
    *,
    model_used: str | None,
    semantic_cache: bool,
    compiler_enabled: bool,
    compiler_config: dict[str, Any] | None,
    ir_decision: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    The optimization config a request ran under, captured so the flywheel can group
    traffic by (segment, config) and learn the cheapest config that holds the SLA.
    Only the *tunable* dimensions are recorded — the analyzer treats this as the key.
    """
    fp: dict[str, Any] = {
        "model": model_used,
        "semantic_cache": bool(semantic_cache),
        "context_compiler": bool(compiler_enabled),
        "routing": bool(ir_decision and ir_decision.get("alias")),
    }
    if compiler_enabled and isinstance(compiler_config, dict):
        stages = compiler_config.get("stages") or {}
        if isinstance(stages, dict):
            fp["stages"] = sorted(k for k, v in stages.items() if v)
        rate = compiler_config.get("compression_rate")
        if rate is not None and (stages.get("compress") if isinstance(stages, dict) else False):
            fp["compression_rate"] = rate
    if ir_decision and ir_decision.get("tier"):
        fp["tier"] = ir_decision.get("tier")
    return fp


def _segment_key(model_alias: str, ir_decision: dict[str, Any] | None) -> str:
    """Coarse label stamped at request time; the router's complexity×risk class when
    intelligent routing ran, otherwise the requested alias."""
    if ir_decision and ir_decision.get("complexity") and ir_decision.get("risk"):
        return f"{ir_decision['complexity']}x{ir_decision['risk']}"
    return model_alias


def _serialize_gateway_route(
    route: GatewayRoute,
    *,
    routing_group_name: str | None = None,
) -> GatewayRouteResponse:
    payload = GatewayRouteResponse.model_validate(route).model_dump()
    payload["routing_group_name"] = routing_group_name
    return GatewayRouteResponse(**payload)


def _serialize_routing_group(
    group: GatewayRoutingGroup,
    routes: list[GatewayRoute],
) -> GatewayRoutingGroupResponse:
    payload = GatewayRoutingGroupResponse.model_validate(group).model_dump()
    payload["route_count"] = len(routes)
    payload["routes"] = [
        GatewayRoutingGroupRouteSummary.model_validate(route).model_dump() for route in routes
    ]
    return GatewayRoutingGroupResponse(**payload)


def _runtime_request_body(
    *,
    body: GatewayCompletionRequest,
    route: GatewayRoute,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload["model"] = route.target_model
    payload["messages"] = messages
    payload["tools"] = tools
    payload["reasoning_effort"] = reasoning_effort
    return payload


def _runtime_direct_provider_request(
    *,
    route: GatewayRoute,
    request_body: dict[str, Any],
    stream: bool,
) -> tuple[str, dict[str, str]] | None:
    provider = (route.provider or "").lower()
    if provider in {"openai", "anthropic", "ollama", "vllm", "local", "groq", "mistral", "custom"}:
        api_key_var = route.api_key_env_var or "OPENAI_API_KEY"
        api_key = os.getenv(api_key_var, "none") or "none"
        default_base_url = "https://api.openai.com/v1"
        if provider in {"local", "ollama"}:
            default_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
        elif provider == "vllm":
            default_base_url = os.getenv("VLLM_BASE_URL", "http://host.docker.internal:8001/v1")
        base_url = (route.base_url or default_base_url).rstrip("/")
        return (
            f"{base_url}/chat/completions",
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
    if provider == "azure":
        cfg = route.config or {}
        api_key_var = route.api_key_env_var or "AZURE_OPENAI_API_KEY"
        api_key = os.getenv(api_key_var, "none") or "none"
        resource_endpoint = (route.base_url or "").rstrip("/")
        if not resource_endpoint:
            return None
        deployment = cfg.get("deployment_name") or route.target_model
        api_version = cfg.get("api_version") or "2024-02-01"
        return (
            f"{resource_endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
            {
                "api-key": api_key,
                "Content-Type": "application/json",
            },
        )
    if provider == "vertex":
        if stream:
            return None
        try:
            adapter = VertexAdapter()
            contents, system_text = adapter._messages_to_gemini(request_body["messages"])  # type: ignore[attr-defined]
        except Exception:
            from runledger_api.services.gateway_providers import (
                _messages_to_gemini,  # noqa: PLC0415
            )

            contents, system_text = _messages_to_gemini(request_body["messages"])
        try:
            adapter = VertexAdapter()
            url, token = adapter._resolve(route)  # type: ignore[attr-defined]
            payload = adapter._build_gemini_payload(  # type: ignore[attr-defined]
                contents,
                system_text,
                max_tokens=request_body.get("max_tokens"),
                temperature=request_body.get("temperature"),
                top_p=request_body.get("top_p"),
                stop=request_body.get("stop"),
            )
            request_body.clear()
            request_body.update(payload)
            return (
                url,
                {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        except Exception:
            return None
    return None


# ── Chat completions ────────────────────────────────────────────────────────────


ApiKeyDep = Annotated[ApiKey, Depends(get_current_api_key)]

_PASSTHROUGH_ALLOWED_REQUEST_HEADERS = {
    "accept",
    "accept-encoding",
    "content-type",
    "if-match",
    "if-none-match",
    "user-agent",
    "x-correlation-id",
    "x-request-id",
}
_PASSTHROUGH_ALLOWED_RESPONSE_HEADERS = {
    "cache-control",
    "content-length",
    "content-type",
    "etag",
    "last-modified",
}


async def _resolve_gateway_workspace(
    request: Request,
    db: AsyncSession,
) -> tuple[Workspace, ApiKey | None]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_bearer = auth_header.split(" ", 1)[1].strip()
    api_key = await verify_api_key(raw_bearer, db)
    oidc_auth = None if api_key is not None else await authenticate_oidc_token(raw_bearer, db)
    if api_key is None and oidc_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    workspace = (
        (
            await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))
        ).scalar_one()
        if api_key is not None
        else oidc_auth.workspace
    )
    return workspace, api_key


async def _resolve_gateway_bearer_token(
    raw_bearer: str,
    db: AsyncSession,
) -> tuple[Workspace, ApiKey | None, Any | None]:
    api_key = await verify_api_key(raw_bearer, db)
    oidc_auth = None if api_key is not None else await authenticate_oidc_token(raw_bearer, db)
    if api_key is None and oidc_auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    workspace = (
        (
            await db.execute(select(Workspace).where(Workspace.id == api_key.workspace_id))
        ).scalar_one()
        if api_key is not None
        else oidc_auth.workspace
    )
    return workspace, api_key, oidc_auth


def _build_passthrough_headers(
    endpoint: GatewayPassThroughEndpoint,
    request: Request | None = None,
    source_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if request is not None:
        for key, value in request.headers.items():
            lowered = key.lower()
            if lowered in _PASSTHROUGH_ALLOWED_REQUEST_HEADERS:
                headers[key] = value
    for key, value in (source_headers or {}).items():
        lowered = key.lower()
        if lowered in _PASSTHROUGH_ALLOWED_REQUEST_HEADERS:
            headers[key] = value

    for key, value in (endpoint.header_config or {}).items():
        if value is not None:
            headers[str(key)] = str(value)

    auth_type = (endpoint.auth_type or "").lower()
    auth_config = endpoint.auth_config or {}
    if auth_type == "bearer" and auth_config.get("token"):
        headers["Authorization"] = f"Bearer {auth_config['token']}"
    elif auth_type == "api_key" and auth_config.get("value"):
        header_name = str(auth_config.get("header_name") or "x-api-key")
        headers[header_name] = str(auth_config["value"])

    return headers


def _build_passthrough_target_url(
    endpoint: GatewayPassThroughEndpoint,
    *,
    upstream_path: str = "",
    query_params: dict[str, Any] | None = None,
) -> str:
    upstream_base = endpoint.upstream_base_url.rstrip("/")
    path_prefix = (endpoint.path_prefix or "/").strip("/")
    upstream_suffix = upstream_path.strip("/")
    path_parts = [part for part in (path_prefix, upstream_suffix) if part]
    target_url = upstream_base
    if path_parts:
        target_url = f"{upstream_base}/{'/'.join(path_parts)}"

    merged_query: dict[str, Any] = {}
    for key, value in (endpoint.default_query or {}).items():
        if value is not None:
            merged_query[str(key)] = str(value)
    for key, value in (query_params or {}).items():
        if value is not None:
            merged_query[str(key)] = str(value)
    if merged_query:
        target_url = f"{target_url}?{urlencode(merged_query, doseq=True)}"
    return target_url
