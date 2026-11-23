"""Agent runtime policy (review B-14): one evaluator for the gateway and the SDK.

An agent's controls are enforced wherever its traffic starts:

- ``status``: paused and retired agents are refused;
- ``budget_envelope``: a monthly USD limit on the spend attributed to the agent
  (``agent_runs.agent_id``); refused once reached;
- ``allowed_aliases``: the gateway route aliases the agent may call (empty = any).

The gateway preflight calls :func:`evaluate_agent_policy` for every request whose
metadata names a registered agent (``runledger.agent`` / ``agent_name`` /
``runledger.agent.id``). The SDK calls ``GET /agents/{id}/preflight`` before starting
an agent's run. Both get the same answer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.agents import Agent
from runledger_api.models.events import AgentRun

# Why a request was refused → HTTP status the gateway returns.
REASON_STATUS = {"agent_inactive": 403, "alias_not_allowed": 403, "envelope_exhausted": 429}


@dataclass(frozen=True)
class AgentPolicyDecision:
    agent_id: uuid.UUID
    allowed: bool
    reason_code: str | None
    reason: str | None
    envelope_usd: Decimal | None
    spent_usd: Decimal
    remaining_usd: Decimal | None
    period_start: datetime
    allowed_aliases: list[str]

    @property
    def http_status(self) -> int:
        return REASON_STATUS.get(self.reason_code or "", 403)


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def agent_month_spend(db: AsyncSession, agent: Agent) -> Decimal:
    value = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.total_cost_usd), 0)).where(
                AgentRun.workspace_id == agent.workspace_id,
                AgentRun.agent_id == agent.id,
                AgentRun.started_at >= month_start(),
            )
        )
    ).scalar()
    return Decimal(str(value or 0))


async def evaluate_agent_policy(
    db: AsyncSession, agent: Agent, *, route_alias: str | None = None
) -> AgentPolicyDecision:
    """Status, then alias allow-list, then envelope (cheapest checks first)."""
    allowed_aliases = [str(a) for a in (agent.allowed_aliases or [])]
    envelope = agent.budget_envelope
    code: str | None = None
    reason: str | None = None
    spent = Decimal("0")
    if agent.status != "active":
        code, reason = "agent_inactive", f"agent '{agent.name}' is {agent.status}"
    elif route_alias and allowed_aliases and route_alias not in allowed_aliases:
        code = "alias_not_allowed"
        reason = f"agent '{agent.name}' may not call alias '{route_alias}'"
    if code is None or envelope is not None:
        spent = await agent_month_spend(db, agent)
    if code is None and envelope is not None and spent >= envelope:
        code, reason = "envelope_exhausted", "monthly budget envelope exhausted"
    return AgentPolicyDecision(
        agent_id=agent.id,
        allowed=code is None,
        reason_code=code,
        reason=reason,
        envelope_usd=envelope,
        spent_usd=spent,
        remaining_usd=max(envelope - spent, Decimal("0")) if envelope is not None else None,
        period_start=month_start(),
        allowed_aliases=allowed_aliases,
    )


async def find_agent_for_request(
    db: AsyncSession, workspace_id: uuid.UUID, metadata: dict[str, object] | None
) -> Agent | None:
    """The registered agent a gateway request names, in this workspace only.

    By id (``runledger.agent.id`` / ``agent_id``) or exact name (``runledger.agent`` /
    ``gen_ai.agent.name`` / ``agent_name``). A name prefers an active agent but also finds a
    paused or retired one, so those are refused rather than silently let through.
    """
    from runledger_api.services.workflow_attribution import (  # noqa: PLC0415
        AGENT_ID_KEYS,
        AGENT_NAME_KEYS,
        first_value,
    )

    meta = dict(metadata or {})
    ref_id = first_value(meta, AGENT_ID_KEYS)
    name = first_value(meta, AGENT_NAME_KEYS)
    if ref_id:
        try:
            agent_uuid = uuid.UUID(ref_id)
        except ValueError:
            name = name or ref_id
        else:
            found = (
                await db.execute(
                    select(Agent).where(Agent.id == agent_uuid, Agent.workspace_id == workspace_id)
                )
            ).scalar_one_or_none()
            if found is not None:
                return found
    if not name:
        return None
    return (
        (
            await db.execute(
                select(Agent)
                .where(Agent.workspace_id == workspace_id, Agent.name == name.strip())
                .order_by((Agent.status == "active").desc(), Agent.created_at)
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def enforce_agent_policy_for_request(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    metadata: dict[str, object] | None,
    route_alias: str | None,
) -> str | None:
    """Gateway preflight hook: refuse the request when its agent's policy says no.

    Returns a decision note (``agent:<id>``) for allowed agent traffic, ``None`` when the
    request names no registered agent. Raises 403 (inactive agent, alias not allowed) or
    429 (envelope exhausted) with ``X-Agent-Policy-Reason``.
    """
    from fastapi import HTTPException  # noqa: PLC0415

    agent = await find_agent_for_request(db, workspace_id, metadata)
    if agent is None:
        return None
    decision = await evaluate_agent_policy(db, agent, route_alias=route_alias)
    if not decision.allowed:
        headers = {"X-Agent-Policy-Reason": decision.reason_code or "denied"}
        if decision.reason_code == "envelope_exhausted":
            headers["X-Cost-Cap-Reason"] = "agent_envelope"
        raise HTTPException(
            decision.http_status, f"Agent policy: {decision.reason}", headers=headers
        )
    return f"agent:{agent.id}"
