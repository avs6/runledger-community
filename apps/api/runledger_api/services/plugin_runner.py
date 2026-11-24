"""Governed tool calls: policy decision, approval holds, security events, plugin hooks.

This is the runtime side of tool governance. The decision itself comes from
:mod:`runledger_api.services.tool_policy_engine` (one evaluator everywhere); this
module turns a decision into effects:

* ``block``            → a ``SecurityEvent`` and :class:`ToolCallBlocked`
* ``require_approval`` → a real ``Approval`` row (``pending``) the caller can
  resume with once it is approved (``X-RunLedger-Approval-Id`` on the gateway,
  ``POST /mcp-registry/tool-calls/{id}/resume`` for MCP)
* ``audit``            → a ``SecurityEvent`` and the call proceeds
* ``allow``            → the call proceeds

Plugin hooks run only where they have a real runtime: ``webhook`` plugins with a
``config.url`` are POSTed to (egress-checked, 3 s timeout). Other plugin types are
recorded as ``skipped``, never as a fabricated success.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.approvals import Approval
from runledger_api.models.ledger import SecurityEvent
from runledger_api.models.plugins import Plugin, PluginExecution
from runledger_api.services import tool_policy_engine as engine
from runledger_api.services.egress import EgressBlocked, check_url

log = structlog.get_logger()

# Approval request types used for holds (both are existing, valid approval types).
GATEWAY_HOLD_TYPE = "tool_allow"
MCP_HOLD_TYPE = "external_mcp_tool"
_PLUGIN_TIMEOUT_S = 3.0


class ToolCallBlocked(Exception):
    def __init__(self, decision: engine.PolicyDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


class ToolCallHeld(Exception):
    """The call needs an approval; ``approval_id`` names the pending Approval."""

    def __init__(self, decision: engine.PolicyDecision, approval_id: uuid.UUID) -> None:
        super().__init__(decision.reason)
        self.decision = decision
        self.approval_id = approval_id


async def execute_plugin_hooks(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    hook_name: str,
    payload: dict[str, Any],
) -> list[PluginExecution]:
    """Run active plugins subscribed to ``hook_name`` and record each execution.

    Only flushes; the caller owns the transaction.
    """
    plugins = (
        (
            await db.execute(
                select(Plugin)
                .where(Plugin.workspace_id == workspace_id, Plugin.is_active.is_(True))
                .order_by(Plugin.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    executions: list[PluginExecution] = []
    for plugin in [p for p in plugins if hook_name in (p.hooks or [])]:
        started = time.perf_counter()
        exec_status, err, output = await _run_plugin(plugin, hook_name, payload)
        execution = PluginExecution(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            plugin_id=plugin.id,
            hook=hook_name,
            input_payload=payload,
            output_payload=output,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status=exec_status,
            error=err,
        )
        db.add(execution)
        executions.append(execution)
    if executions:
        await db.flush()
    return executions


async def _run_plugin(
    plugin: Plugin, hook_name: str, payload: dict[str, Any]
) -> tuple[str, str | None, dict[str, Any]]:
    url = (plugin.config or {}).get("url") if plugin.plugin_type == "webhook" else None
    if not url:
        return (
            "skipped",
            f"plugin type '{plugin.plugin_type}' has no executable runtime"
            if plugin.plugin_type != "webhook"
            else "webhook plugin has no config.url",
            {"hook": hook_name},
        )
    try:
        check_url(str(url))
        async with httpx.AsyncClient(timeout=_PLUGIN_TIMEOUT_S, follow_redirects=False) as client:
            resp = await client.post(
                str(url), json={"hook": hook_name, "plugin": plugin.name, "payload": payload}
            )
        ok = resp.status_code < 400
        return (
            "success" if ok else "failed",
            None if ok else f"webhook returned HTTP {resp.status_code}",
            {"hook": hook_name, "http_status": resp.status_code},
        )
    except EgressBlocked as exc:
        return "failed", f"destination refused: {exc}", {"hook": hook_name}
    except httpx.HTTPError as exc:
        log.warning("plugin_hook_failed", plugin=plugin.name, hook=hook_name, error=str(exc))
        return "failed", str(exc)[:500], {"hook": hook_name}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(v) for v in value]
    if isinstance(value, uuid.UUID | datetime):
        return str(value)
    return value


def record_tool_event(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    decision: engine.PolicyDecision,
    *,
    source: str,
    ctx: engine.ToolCallContext,
    run_id: uuid.UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    event_type = {
        "block": "tool_call_blocked",
        "require_approval": "tool_call_held",
        "audit": "tool_call_audited",
    }.get(decision.action, "tool_call_allowed")
    db.add(
        SecurityEvent(
            workspace_id=workspace_id,
            event_type=event_type,
            tool_name=decision.tool_name[:500],
            end_user_id=ctx.end_user_id,
            run_id=run_id,
            details=_json_safe(
                {
                    **decision.as_dict(),
                    "source": source,
                    "api_key_id": ctx.api_key_id,
                    "server_id": ctx.server_id,
                    **(extra or {}),
                }
            ),
        )
    )


async def approved_hold(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    approval_id: uuid.UUID | str | None,
    tool_name: str,
    *,
    api_key_id: uuid.UUID | None = None,
) -> Approval | None:
    """Return the approval when it is approved for this tool (and key, when bound)."""
    if not approval_id:
        return None
    try:
        appr_uuid = approval_id if isinstance(approval_id, uuid.UUID) else uuid.UUID(approval_id)
    except ValueError:
        return None
    approval = await db.get(Approval, appr_uuid)
    if approval is None or approval.workspace_id != workspace_id:
        return None
    if approval.status != "approved" or approval.request_type not in {
        GATEWAY_HOLD_TYPE,
        MCP_HOLD_TYPE,
    }:
        return None
    request = approval.request or {}
    if str(request.get("tool_name", "")).lower() != tool_name.lower():
        return None
    bound_key = request.get("api_key_id")
    if bound_key and api_key_id is not None and str(api_key_id) != str(bound_key):
        return None
    return approval


async def open_hold(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    decision: engine.PolicyDecision,
    ctx: engine.ToolCallContext,
    *,
    request_type: str,
    requested_by: str | None,
    extra: dict[str, Any] | None = None,
) -> Approval:
    """Create (or reuse) a pending Approval for this caller + tool."""
    existing = (
        (
            await db.execute(
                select(Approval)
                .where(
                    Approval.workspace_id == workspace_id,
                    Approval.request_type == request_type,
                    Approval.status == "pending",
                    Approval.request["tool_name"].astext == ctx.tool_name,
                    Approval.request["api_key_id"].astext
                    == (str(ctx.api_key_id) if ctx.api_key_id else ""),
                )
                .order_by(Approval.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if existing is not None and not extra:
        return existing
    approval = Approval(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        request_type=request_type,
        status="pending",
        requested_by=requested_by,
        request=_json_safe(
            {
                "tool_name": ctx.tool_name,
                "api_key_id": str(ctx.api_key_id) if ctx.api_key_id else "",
                "end_user_id": ctx.end_user_id,
                "server_id": ctx.server_id,
                "policy_id": decision.policy_id,
                "policy_name": decision.policy_name,
                "reason": decision.reason,
                "held_at": datetime.now(UTC).isoformat(),
                **(extra or {}),
            }
        ),
    )
    db.add(approval)
    await db.flush()
    return approval


async def govern_tool_call(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    ctx: engine.ToolCallContext,
    *,
    source: str,
    approval_id: uuid.UUID | str | None = None,
    hold_type: str = MCP_HOLD_TYPE,
    requested_by: str | None = None,
    hold_extra: dict[str, Any] | None = None,
    run_hooks: bool = True,
) -> engine.PolicyDecision:
    """Decide and apply effects for one tool call. Flushes; the caller commits.

    Raises :class:`ToolCallBlocked` or :class:`ToolCallHeld`.
    """
    rules = await engine.load_rules(db, workspace_id)
    decision = engine.evaluate(rules, ctx)
    payload = _json_safe(
        {"tool_name": ctx.tool_name, "arguments": ctx.arguments, "source": source}
        | {"decision": decision.as_dict()}
    )
    if decision.action == "require_approval":
        approved = await approved_hold(
            db, workspace_id, approval_id, ctx.tool_name, api_key_id=ctx.api_key_id
        )
        if approved is not None:
            decision.action = "allow"
            decision.reason = f"approved by approval {approved.id}"
            record_tool_event(
                db,
                workspace_id,
                decision,
                source=source,
                ctx=ctx,
                extra={"approval_id": str(approved.id)},
            )
            await db.flush()
            return decision
        approval = await open_hold(
            db,
            workspace_id,
            decision,
            ctx,
            request_type=hold_type,
            requested_by=requested_by,
            extra=hold_extra,
        )
        record_tool_event(
            db,
            workspace_id,
            decision,
            source=source,
            ctx=ctx,
            extra={"approval_id": str(approval.id)},
        )
        if run_hooks:
            await execute_plugin_hooks(
                db,
                workspace_id,
                "on_approval_required",
                payload | {"approval_id": str(approval.id)},
            )
        await db.flush()
        raise ToolCallHeld(decision, approval.id)
    if decision.action == "block":
        record_tool_event(db, workspace_id, decision, source=source, ctx=ctx)
        if run_hooks:
            await execute_plugin_hooks(db, workspace_id, "on_guardrail_violation", payload)
        await db.flush()
        raise ToolCallBlocked(decision)
    if decision.action == "audit":
        record_tool_event(db, workspace_id, decision, source=source, ctx=ctx)
        await db.flush()
    return decision


async def build_context(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    tool_name: str,
    *,
    api_key: Any | None = None,
    principal_user_id: uuid.UUID | None = None,
    end_user_id: str | None = None,
    server_id: uuid.UUID | None = None,
    arguments: dict[str, Any] | None = None,
    tool_type: str | None = None,
    risk_score: int | None = None,
    feature_tag: str | None = None,
    context: dict[str, Any] | None = None,
) -> engine.ToolCallContext:
    """Context from the authenticated caller (never from body-asserted identity)."""
    return engine.ToolCallContext(
        tool_name=tool_name,
        tool_type=tool_type,
        risk_score=risk_score,
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        api_key_id=getattr(api_key, "id", None),
        access_group_ids=await engine.caller_access_group_ids(db, principal_user_id),
        server_id=server_id,
        search_tool_ids=await engine.search_tool_ids_for(db, workspace_id, tool_name),
        arguments=arguments,
        context=context or {},
    )
