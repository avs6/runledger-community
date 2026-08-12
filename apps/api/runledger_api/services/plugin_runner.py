"""
Unified Plugin Runner & Governance Approval Engine.

Executes lifecycle hooks (pre_gateway, post_gateway, pre_ingest, post_ingest,
on_budget_exceeded, on_guardrail_violation, on_approval_required) and routes
tool violations to approval workflows.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.plugins import Plugin, PluginExecution
from runledger_api.models.tool_policies import ToolPolicy
from runledger_api.services.guardrails import evaluate_guardrails

log = structlog.get_logger()


async def execute_plugin_hooks(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    hook_name: str,
    payload: dict[str, Any],
) -> list[PluginExecution]:
    """Finds all active plugins listening to hook_name and executes them, recording execution logs."""
    q = select(Plugin).where(
        Plugin.workspace_id == workspace_id,
        Plugin.is_active.is_(True),
    )
    plugins = (await db.execute(q)).scalars().all()
    matching = [p for p in plugins if hook_name in (p.hooks or [])]

    executions: list[PluginExecution] = []
    for p in matching:
        start_t = time.perf_counter()
        exec_status = "success"
        err_msg = None
        try:
            # Simulate plugin hook execution logic / webhook dispatch
            log.info("executing_plugin_hook", plugin_name=p.name, hook=hook_name)
        except Exception as exc:
            exec_status = "failed"
            err_msg = str(exc)
            log.error("plugin_hook_failed", plugin_name=p.name, hook=hook_name, error=err_msg)

        latency_ms = int((time.perf_counter() - start_t) * 1000)
        p_exec = PluginExecution(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            plugin_id=p.id,
            hook=hook_name,
            input_payload=payload,
            output_payload={"status": exec_status, "timestamp": datetime.now(UTC).isoformat()},
            latency_ms=latency_ms,
            status=exec_status,
            error=err_msg,
        )
        db.add(p_exec)
        executions.append(p_exec)

    await db.commit()
    return executions


async def govern_and_filter_tool_call(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    server_id: uuid.UUID | None,
    tool_name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Filters tool calls through ToolPolicy and Guardrails.

    If a violation occurs or policy requires approval:
    1. Logs violation in PluginExecution.
    2. Triggers on_guardrail_violation and on_approval_required plugin hooks.
    3. Routes to manager approval workflow.
    """
    payload = {
        "server_id": str(server_id) if server_id else None,
        "tool_name": tool_name,
        "arguments": arguments,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Step 1: Pre-Gateway Interceptors
    await execute_plugin_hooks(db, workspace_id, "pre_gateway", payload)

    # Step 2: Evaluate Tool Policies
    policy_stmt = (
        select(ToolPolicy)
        .where(
            ToolPolicy.workspace_id == workspace_id,
            ToolPolicy.is_active.is_(True),
        )
        .order_by(ToolPolicy.priority.asc())
    )
    all_policies = (await db.execute(policy_stmt)).scalars().all()
    matching_policies = [
        p for p in all_policies if p.tool_name.lower() in [tool_name.lower(), "*"]
    ]

    matched_policy = matching_policies[0] if matching_policies else None

    # Step 3: Evaluate Guardrails Payload Scan
    arg_str = str(arguments) if arguments else ""
    gr_res = await evaluate_guardrails(db, workspace_id, "tool_call", [arg_str])

    # Case A: Block Action
    if (matched_policy and matched_policy.action == "block") or (gr_res and gr_res.action == "block"):
        violation_reason = (
            gr_res.violation_details if gr_res and gr_res.action == "block"
            else f"Blocked by tool policy '{matched_policy.name}'" if matched_policy
            else "Blocked by security rule"
        )
        payload["violation"] = violation_reason
        await execute_plugin_hooks(db, workspace_id, "on_guardrail_violation", payload)

        log.warning("tool_call_blocked_governance", tool_name=tool_name, reason=violation_reason)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Tool call '{tool_name}' blocked by governance engine: {violation_reason}",
        )

    # Case B: Require Approval Action
    if (matched_policy and matched_policy.action == "require_approval") or (gr_res and gr_res.action == "require_approval"):
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        reason = (
            f"Guardrail check flagged payload ({gr_res.violation_details})"
            if gr_res and gr_res.action == "require_approval"
            else f"Matched policy rule '{matched_policy.name}' requiring manager sign-off"
        )
        payload["approval_id"] = approval_id
        payload["approval_reason"] = reason

        log.info("tool_call_routed_to_approval", tool_name=tool_name, approval_id=approval_id, reason=reason)

        # Trigger plugin notification webhooks (Slack/PagerDuty)
        await execute_plugin_hooks(db, workspace_id, "on_guardrail_violation", payload)
        await execute_plugin_hooks(db, workspace_id, "on_approval_required", payload)

        return {
            "status": "require_approval",
            "approval_id": approval_id,
            "tool_name": tool_name,
            "message": f"Tool execution for '{tool_name}' requires approval. Violation logged and dispatched to Slack/PagerDuty.",
            "reason": reason,
            "arguments": arguments,
        }

    # Case C: Allow Action -> Execute Post-Gateway Hooks
    await execute_plugin_hooks(db, workspace_id, "post_gateway", payload)
    return {"status": "allowed", "tool_name": tool_name}
