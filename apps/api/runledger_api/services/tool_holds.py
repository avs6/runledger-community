"""Tool policy in the gateway path, and approvals as gateway holds.

Preflight (:func:`govern_request_tools`)
    Each tool in the request's ``tools[]`` goes through the shared evaluator.
    ``block`` → the tool is stripped from ``tools[]`` (and a security event recorded);
    ``require_approval`` → the request is **held**: no provider call is made, a
    pending ``Approval`` is created and the gateway answers ``202`` with
    ``{"status": "held", "approval_id": ...}`` and an ``X-RunLedger-Approval-Id``
    header. Once the approval is approved the client resubmits the same request with
    ``metadata["runledger.approval_id"] = <id>`` and it goes through.

Finalize (:func:`govern_response_tool_calls`)
    Each ``tool_call`` the model returned is evaluated too. A blocked tool call fails
    the response (451, the run is still recorded); a call that needs approval holds
    the response (202 + approval id) so the agent can't act on it until approved.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.services import plugin_runner as governance
from runledger_api.services import tool_policy_engine as engine

APPROVAL_METADATA_KEYS = ("runledger.approval_id", "runledger_approval_id", "approval_id")
HOLD_RETRY_AFTER_S = "30"


def approval_id_from(metadata: dict[str, Any] | None) -> str | None:
    for key in APPROVAL_METADATA_KEYS:
        value = (metadata or {}).get(key)
        if value:
            return str(value)
    return None


def hold_response(tool_name: str, approval_id: uuid.UUID, reason: str) -> HTTPException:
    return HTTPException(
        status.HTTP_202_ACCEPTED,
        detail={
            "status": "held",
            "approval_id": str(approval_id),
            "tool_name": tool_name,
            "reason": reason,
            "resume": "resubmit with metadata['runledger.approval_id'] once approved",
        },
        headers={"X-RunLedger-Approval-Id": str(approval_id), "Retry-After": HOLD_RETRY_AFTER_S},
    )


async def _context(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    tool_name: str,
    *,
    api_key_id: uuid.UUID | None,
    access_group_ids: frozenset[uuid.UUID],
    end_user_id: str | None,
    feature_tag: str | None,
    arguments: dict[str, Any] | None = None,
) -> engine.ToolCallContext:
    return engine.ToolCallContext(
        tool_name=tool_name,
        tool_type="function",
        end_user_id=end_user_id,
        feature_tag=feature_tag,
        api_key_id=api_key_id,
        access_group_ids=access_group_ids,
        search_tool_ids=await engine.search_tool_ids_for(db, workspace_id, tool_name),
        arguments=arguments,
    )


async def govern_request_tools(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    tools: list[dict[str, Any]] | None,
    *,
    api_key_id: uuid.UUID | None,
    principal_user_id: uuid.UUID | None,
    end_user_id: str | None,
    feature_tag: str | None,
    metadata: dict[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Return ``tools[]`` with blocked tools removed; raise a 202 hold when needed."""
    names = engine.tool_names_from_request(tools)
    if not names:
        return tools
    rules = await engine.load_rules(db, workspace_id)
    if not rules:
        return tools
    groups = await engine.caller_access_group_ids(db, principal_user_id)
    approval_id = approval_id_from(metadata)
    stripped: set[str] = set()
    for name in dict.fromkeys(names):
        ctx = await _context(
            db,
            workspace_id,
            name,
            api_key_id=api_key_id,
            access_group_ids=groups,
            end_user_id=end_user_id,
            feature_tag=feature_tag,
        )
        try:
            await governance.govern_tool_call(
                db,
                workspace_id,
                ctx,
                source="gateway_preflight",
                approval_id=approval_id,
                hold_type=governance.GATEWAY_HOLD_TYPE,
                requested_by=str(principal_user_id) if principal_user_id else None,
                run_hooks=False,
            )
        except governance.ToolCallBlocked:
            stripped.add(name.lower())
        except governance.ToolCallHeld as exc:
            await db.commit()
            raise hold_response(name, exc.approval_id, exc.decision.reason) from exc
    await db.commit()
    if not stripped:
        return tools
    kept = [
        t
        for t in tools or []
        if not any(n.lower() in stripped for n in engine.tool_names_from_request([t]))
    ]
    return kept or None


async def govern_response_tool_calls(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    tool_calls: list[dict[str, Any]],
    *,
    api_key_id: uuid.UUID | None,
    principal_user_id: uuid.UUID | None,
    end_user_id: str | None,
    feature_tag: str | None,
    metadata: dict[str, Any] | None,
) -> tuple[str | None, uuid.UUID | None]:
    """Return ``(blocked_reason, held_approval_id)`` for the model's tool calls."""
    if not tool_calls:
        return None, None
    rules = await engine.load_rules(db, workspace_id)
    if not rules:
        return None, None
    groups = await engine.caller_access_group_ids(db, principal_user_id)
    approval_id = approval_id_from(metadata)
    for call in tool_calls:
        name = engine.tool_name_of_call(call)
        if not name:
            continue
        raw_args = (call.get("function") or {}).get("arguments")
        ctx = await _context(
            db,
            workspace_id,
            name,
            api_key_id=api_key_id,
            access_group_ids=groups,
            end_user_id=end_user_id,
            feature_tag=feature_tag,
            arguments={"raw": raw_args} if isinstance(raw_args, str) else raw_args,
        )
        try:
            await governance.govern_tool_call(
                db,
                workspace_id,
                ctx,
                source="gateway_finalize",
                approval_id=approval_id,
                hold_type=governance.GATEWAY_HOLD_TYPE,
                requested_by=str(principal_user_id) if principal_user_id else None,
                run_hooks=False,
            )
        except governance.ToolCallBlocked as exc:
            return f"tool call '{name}' blocked: {exc.decision.reason}", None
        except governance.ToolCallHeld as exc:
            return f"tool call '{name}' requires approval {exc.approval_id}", exc.approval_id
    return None, None
