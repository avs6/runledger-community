"""
Governance preflight for gateway pass-through endpoints (review G-15).

Pass-through used to forward any body to the upstream after only key auth and the IP
ACL. It now runs the same checks the chat path runs, before the upstream is called:

1. **Required metadata** — workspace ``required_metadata_fields`` (reject mode → 400).
   Metadata comes from the ``X-RunLedger-Metadata`` header (JSON object) plus the
   workflow / end-user headers below.
2. **Request budgets** — workspace, API key, end user, workflow (feature tag) and
   access-group budgets. ``block`` and ``throttle`` (over the per-minute allowance)
   refuse with 429; ``downgrade`` / ``fallback`` have no model to switch to on a raw
   upstream, so they refuse too.
3. **Pre-call guardrails** — run on the request body's text (UTF-8, first 64 KiB).
   ``block`` → 451. A ``modify`` result can't be applied to an opaque upstream body, so
   it is recorded (``guardrail_modify_not_applied`` in the decision) and the body is
   forwarded unchanged; use a chat route when you need redaction.

The endpoint's ``cost_per_call_usd`` is then counted against those same budgets on
success, so pass-through spend is visible to FinOps.

Headers: ``X-RunLedger-Workflow`` (or ``X-RunLedger-Feature-Tag``),
``X-RunLedger-End-User-Id``, ``X-RunLedger-Metadata``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.core.redis import get_redis
from runledger_api.services.budgets import (
    check_budget_throttle,
    check_request_budgets,
    record_budget_spend,
)
from runledger_api.services.guardrails import evaluate_guardrails
from runledger_api.services.security import enforce_required_metadata
from runledger_api.services.sessions import resolve_principal_user_id

log = structlog.get_logger()

GUARDRAIL_TEXT_LIMIT = 64 * 1024


@dataclass
class PassthroughGovernance:
    request_id: uuid.UUID
    workflow: str | None
    end_user_id: str | None
    principal_user_id: uuid.UUID | None
    notes: list[str] = field(default_factory=list)

    def decision_suffix(self) -> str:
        return "".join(f"|{note}" for note in self.notes)


def _header_metadata(request: Request) -> dict[str, Any]:
    raw = request.headers.get("x-runledger-metadata")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "X-RunLedger-Metadata must be a JSON object"
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "X-RunLedger-Metadata must be a JSON object"
        )
    return parsed


def _budget_refusal(budget_id: str | None, detail: str, retry_after: str | None = None) -> None:
    headers = {"X-Cost-Cap-Reason": "budget_exceeded"}
    if budget_id:
        headers["X-Budget-Id"] = budget_id
    if retry_after:
        headers["Retry-After"] = retry_after
    raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail, headers=headers)


async def passthrough_preflight(
    db: AsyncSession,
    *,
    workspace: Any,
    api_key: Any,
    slug: str,
    request: Request,
    raw_body: bytes,
) -> PassthroughGovernance:
    metadata = _header_metadata(request)
    workflow = (
        request.headers.get("x-runledger-workflow")
        or request.headers.get("x-runledger-feature-tag")
        or metadata.get("workflow")
        or metadata.get("feature_tag")
    )
    workflow = str(workflow)[:255] if workflow else None
    end_user_id = request.headers.get("x-runledger-end-user-id") or metadata.get("end_user_id")
    end_user_id = str(end_user_id)[:255] if end_user_id else None
    if workflow:
        metadata.setdefault("workflow", workflow)
        metadata.setdefault("feature_tag", workflow)
    if end_user_id:
        metadata.setdefault("end_user_id", end_user_id)

    gov = PassthroughGovernance(
        request_id=uuid.uuid4(),
        workflow=workflow,
        end_user_id=end_user_id,
        principal_user_id=await resolve_principal_user_id(
            db, api_key=api_key, end_user_id=end_user_id, workspace=workspace
        ),
    )

    missing = await enforce_required_metadata(db, workspace_id=workspace.id, metadata=metadata)
    if missing:
        gov.notes.append(f"metadata_warn:{','.join(missing)}")

    redis = await get_redis()
    try:
        check = await check_request_budgets(
            redis,
            db,
            workspace_id=workspace.id,
            api_key_id=api_key.id if api_key is not None else None,
            end_user_id=end_user_id,
            feature_tag=workflow,
            principal_user_id=gov.principal_user_id,
        )
    except Exception:  # noqa: BLE001 — fail open like the chat path
        log.warning("passthrough_budget_check_failed", workspace_id=str(workspace.id))
        check = None
    if check is not None and not (check.allowed and not check.throttled):
        if check.throttled and check.budget_id and check.action not in {"block"}:
            try:
                over = await check_budget_throttle(
                    redis, check.budget_id, settings.budget_throttle_rpm
                )
            except Exception:  # noqa: BLE001
                over = False
            if over:
                _budget_refusal(check.budget_id, "Budget limit reached: request throttled", "60")
            gov.notes.append(f"budget_throttle:{check.budget_id}")
        else:
            _budget_refusal(
                check.budget_id,
                "Budget limit reached"
                if check.action == "block"
                else f"Budget limit reached ({check.action}); a pass-through endpoint has no "
                "model to switch to",
            )

    text = raw_body[:GUARDRAIL_TEXT_LIMIT].decode("utf-8", errors="ignore").strip()
    if text and not getattr(workspace, "guardrail_bypass", False):
        decision, results, _ = await evaluate_guardrails(
            db,
            workspace.id,
            "pre_call",
            texts=[text],
            model=f"passthrough:{slug}",
            end_user_id=end_user_id,
            user_id=str(gov.principal_user_id) if gov.principal_user_id else None,
            metadata=metadata,
            gateway_request_id=gov.request_id,
            api_key_id=api_key.id if api_key is not None else None,
            workflow=workflow,
        )
        if decision == "block":
            await db.commit()  # keep the guardrail events of the refused request
            reason = next(
                (r["reason"] for r in results if r["decision"] == "block"),
                "Blocked by guardrail",
            )
            raise HTTPException(status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, reason)
        if decision == "modify":
            gov.notes.append("guardrail_modify_not_applied")
    return gov


async def record_passthrough_spend(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    gov: PassthroughGovernance,
    api_key_id: uuid.UUID | None,
    cost_usd: Decimal | None,
    slug: str,
) -> None:
    """Count the endpoint's per-call price against budgets (idempotent per request)."""
    if not cost_usd or cost_usd <= 0:
        return
    try:
        async with db.begin_nested():
            await record_budget_spend(
                db,
                await get_redis(),
                workspace_id=workspace_id,
                provider_call_id=gov.request_id,
                cost_usd=cost_usd,
                api_key_id=api_key_id,
                end_user_id=gov.end_user_id,
                feature_tag=gov.workflow,
                provider="passthrough",
                model=slug,
                principal_user_id=gov.principal_user_id,
            )
        await db.commit()
    except Exception:  # noqa: BLE001
        log.exception("passthrough_budget_spend_failed", request_id=str(gov.request_id))
