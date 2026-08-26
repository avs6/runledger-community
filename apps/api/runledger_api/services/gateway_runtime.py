from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.gateway import (
    GatewayRequest,
    GatewayRoute,
    GatewayRoutingGroup,
    RoutingPolicy,
)
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.services import kafka_export

VALID_GATEWAY_RUNTIME_EVENT_TYPES = {
    "gateway.request.completed",
    "gateway.request.rejected",
    "gateway.enforcement.applied",
    "gateway.route.health",
}


def verify_gateway_runtime_signature(
    *,
    workspace_id: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> None:
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid runtime event timestamp") from exc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    if abs(datetime.now(UTC) - ts) > timedelta(minutes=5):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Runtime event signature expired")
    payload = b".".join([workspace_id.encode(), timestamp.encode(), body])
    expected = hmac.new(
        settings.effective_ingest_signing_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid runtime event signature")


def snapshot_version(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


async def build_gateway_runtime_snapshot(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
) -> dict[str, Any]:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    groups = list(
        (
            await db.execute(
                select(GatewayRoutingGroup)
                .where(
                    GatewayRoutingGroup.workspace_id == workspace_id,
                    GatewayRoutingGroup.is_active.is_(True),
                )
                .order_by(
                    GatewayRoutingGroup.alias.asc(),
                    GatewayRoutingGroup.name.asc(),
                    GatewayRoutingGroup.created_at.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    routes = list(
        (
            await db.execute(
                select(GatewayRoute)
                .where(
                    GatewayRoute.workspace_id == workspace_id,
                    GatewayRoute.is_active.is_(True),
                )
                .order_by(GatewayRoute.alias.asc(), GatewayRoute.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    policies = list(
        (
            await db.execute(
                select(RoutingPolicy)
                .where(
                    RoutingPolicy.workspace_id == workspace_id,
                    RoutingPolicy.is_active.is_(True),
                )
                .order_by(RoutingPolicy.alias.asc(), RoutingPolicy.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    api_keys = list(
        (
            await db.execute(
                select(ApiKey)
                .where(
                    ApiKey.workspace_id == workspace_id,
                    ApiKey.is_session.is_(False),
                )
                .order_by(ApiKey.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    last_config_change_at = max(
        [
            now,
            *[group.updated_at or group.created_at for group in groups],
            *[policy.updated_at or policy.created_at for policy in policies],
            *[route.last_health_check_at or route.created_at for route in routes],
            *[
                key.revoked_at or key.expires_at or key.last_used_at or key.created_at
                for key in api_keys
            ],
        ]
    )

    payload = {
        "workspace": {
            "workspace_id": str(workspace.id),
            "tenant_id": str(workspace.tenant_id),
            "name": workspace.name,
            "status": workspace.status,
            "is_restricted": workspace.is_restricted,
            "guardrail_bypass": workspace.guardrail_bypass,
        },
        "routing_groups": [
            {
                "routing_group_id": str(group.id),
                "workspace_id": str(group.workspace_id),
                "alias": group.alias,
                "name": group.name,
                "description": group.description,
                "match_tags": list(group.match_tags or []),
                "default_tags": list(group.default_tags or []),
                "strategy_type": group.strategy_type,
                "strategy_config": group.strategy_config or {},
                "is_active": group.is_active,
                "created_at": group.created_at,
                "updated_at": group.updated_at,
            }
            for group in groups
        ],
        "routes": [
            {
                "route_id": str(route.id),
                "workspace_id": str(route.workspace_id),
                "routing_group_id": str(route.routing_group_id) if route.routing_group_id else None,
                "alias": route.alias,
                "provider": route.provider,
                "target_model": route.target_model,
                "base_url": route.base_url,
                "api_key_env_var": route.api_key_env_var,
                "priority": route.priority,
                "config": route.config or {},
                "required_tags": list(route.required_tags or []),
                "excluded_tags": list(route.excluded_tags or []),
                "region": route.region,
                "retry_count": route.retry_count,
                "timeout_ms": route.timeout_ms,
                "cooldown_seconds": route.cooldown_seconds,
                "cooldown_until": route.cooldown_until,
                "mirror_config": route.mirror_config or {},
                "fallback_config": route.fallback_config or {},
                "semantic_cache_enabled": route.semantic_cache_enabled,
                "context_compiler_enabled": route.context_compiler_enabled,
                "context_compiler_config": route.context_compiler_config or {},
                "intelligent_routing_enabled": route.intelligent_routing_enabled,
                "routing_config": route.routing_config or {},
                "health_auto_disable": route.health_auto_disable,
                "deployment_status": route.deployment_status,
                "health_summary": route.health_summary,
                "runtime_controls": {
                    "daily_cost_limit_usd": route.daily_cost_limit_usd,
                    "monthly_cost_limit_usd": route.monthly_cost_limit_usd,
                    "per_user_rpm_limit": route.per_user_rpm_limit,
                    "pii_redaction_enabled": route.pii_redaction_enabled,
                },
                "created_at": route.created_at,
                "last_health_check_at": route.last_health_check_at,
            }
            for route in routes
        ],
        "routing_policies": [
            {
                "policy_id": str(policy.id),
                "workspace_id": str(policy.workspace_id),
                "alias": policy.alias,
                "policy_type": policy.policy_type,
                "config": policy.config or {},
                "is_active": policy.is_active,
                "created_at": policy.created_at,
                "updated_at": policy.updated_at,
            }
            for policy in policies
        ],
        "auth": {
            "mode": "workspace_bearer_api_keys",
            "api_keys": [
                {
                    "api_key_id": str(key.id),
                    "workspace_id": str(key.workspace_id),
                    "key_prefix": key.key_prefix,
                    "key_hash": key.key_hash,
                    "name": key.name,
                    "scopes": list(key.scopes or []),
                    "expires_at": key.expires_at,
                    "revoked_at": key.revoked_at,
                    "is_session": key.is_session,
                    "is_active": key.revoked_at is None
                    and (key.expires_at is None or key.expires_at > now),
                    "ownership_type": key.ownership_type,
                    "owner_reference": key.owner_reference,
                    "budget_tier_id": str(key.budget_tier_id) if key.budget_tier_id else None,
                    "guardrail_config": key.guardrail_config or {},
                }
                for key in api_keys
            ],
        },
        "last_config_change_at": last_config_change_at,
        "published_at": now,
    }
    payload["version"] = snapshot_version(payload)
    return payload


async def ingest_gateway_runtime_events(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    source_service: str,
    events: list[dict[str, Any]],
) -> int:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    accepted = 0
    now = datetime.now(UTC)
    for event in events:
        event_type = str(event.get("event_type") or "").strip()
        if event_type not in VALID_GATEWAY_RUNTIME_EVENT_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Unsupported runtime event type '{event_type}'",
            )
        if str(event.get("workspace_id")) != str(workspace_id):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Runtime event workspace_id must match the batch workspace_id",
            )

        if event_type in {"gateway.request.completed", "gateway.request.rejected"}:
            request_id = event.get("request_id")
            if request_id is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "request_id is required for gateway request events"
                )
            existing = await db.get(GatewayRequest, request_id)
            if existing is None:
                created_at = event.get("completed_at") or event.get("started_at") or now
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                route_id = event.get("route_id")
                request_row = GatewayRequest(
                    id=request_id
                    if isinstance(request_id, uuid.UUID)
                    else uuid.UUID(str(request_id)),
                    workspace_id=workspace_id,
                    route_id=uuid.UUID(str(route_id)) if route_id else None,
                    model_requested=str(event.get("model_requested") or "unknown"),
                    model_used=(
                        str(event["model_used"]) if event.get("model_used") is not None else None
                    ),
                    cache_hit=bool(event.get("cache_hit") or False),
                    input_tokens=event.get("input_tokens"),
                    output_tokens=event.get("output_tokens"),
                    latency_ms=event.get("latency_ms"),
                    status=str(
                        event.get("status")
                        or ("error" if event_type == "gateway.request.rejected" else "success")
                    ),
                    decision_reason=(
                        str(event["decision_reason"])
                        if event.get("decision_reason") is not None
                        else None
                    ),
                    config_fingerprint={
                        "provider": event.get("provider"),
                        "cost_usd": str(event["cost_usd"])
                        if event.get("cost_usd") is not None
                        else None,
                        "semantic_cache_hit": bool(event.get("semantic_cache_hit") or False),
                        "stream": bool(event.get("stream") or False),
                        "source_service": source_service,
                    },
                    segment_key=source_service,
                    created_at=created_at,
                )
                db.add(request_row)
            await kafka_export.publish_event(
                db,
                workspace_id=workspace_id,
                event_type=event_type,
                payload={
                    **event,
                    "source": source_service,
                    "run_id": str(request_id),
                    "gateway_request_id": str(request_id),
                    "event_summary": f"Gateway runtime event: {event_type}",
                    "idempotency_key": f"runtime-event:{event_type}:{request_id}",
                },
            )
            accepted += 1
            continue

        if event_type == "gateway.enforcement.applied":
            await kafka_export.publish_event(
                db,
                workspace_id=workspace_id,
                event_type=event_type,
                payload={
                    **event,
                    "source": source_service,
                    "event_summary": "Gateway enforcement applied",
                    "idempotency_key": (
                        f"runtime-event:{event_type}:{event.get('request_id') or accepted}:{event.get('action') or 'unknown'}"
                    ),
                },
            )
            accepted += 1
            continue

        if event_type == "gateway.route.health":
            route_id = event.get("route_id")
            route = await db.get(GatewayRoute, route_id) if route_id else None
            if route is None or route.workspace_id != workspace_id:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "Gateway route not found for health event"
                )
            route.last_health_check_at = now
            if event.get("consecutive_failures") is not None:
                route.consecutive_health_failures = int(event["consecutive_failures"])
            deployment_status = str(event.get("deployment_status") or "").strip().lower()
            if deployment_status == "healthy":
                route.disabled_reason = None
            elif deployment_status in {"degraded", "down"}:
                route.disabled_reason = (
                    str(event["health_summary"])
                    if event.get("health_summary") is not None
                    else route.disabled_reason
                )
            await kafka_export.publish_event(
                db,
                workspace_id=workspace_id,
                event_type=event_type,
                payload={
                    **event,
                    "source": source_service,
                    "event_summary": "Gateway route health updated",
                    "idempotency_key": f"runtime-event:{event_type}:{route.id}:{route.last_health_check_at.isoformat()}",
                },
            )
            accepted += 1

    await db.commit()
    return accepted
