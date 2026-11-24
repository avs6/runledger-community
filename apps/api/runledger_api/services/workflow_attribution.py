"""Workflow and agent attribution for runs (review top#4, B-11, B-14, B-17).

Every ingest path (SDK / ``/ingest/v1``, OTLP, Claude Code logs, gateway-rs) calls
:func:`resolve_run_attribution` once per run so ``agent_runs.workflow_id`` and
``agent_runs.agent_id`` are set the same way everywhere.

Resolution order for the workflow (first match wins, always inside the run's workspace,
archived workflows never match):

1. an explicit workflow reference: ``workflow_id`` (UUID) or ``workflow`` (a workflow id,
   its ``feature_tag`` or its name), from the SDK, the ``X-RunLedger-Workflow`` header or
   the OTLP ``runledger.workflow.id`` / ``runledger.workflow`` attributes;
2. the run's ``feature_tag``;
3. the gateway alias the request used (``workflow_definitions.gateway_alias``).

An id that belongs to another workspace resolves to nothing (B-17): attribution never
crosses tenants. When the workflow has a ``feature_tag`` and the run has none, the run
inherits it, so feature-tag budgets, chargeback and analytics see the traffic too.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.agents import Agent, WorkflowDefinition
from runledger_api.models.events import AgentRun

# Keys read from run metadata / OTLP attributes / gateway request metadata.
WORKFLOW_ID_KEYS = ("runledger.workflow.id", "runledger.workflow_id", "workflow_id")
WORKFLOW_REF_KEYS = (
    "runledger.workflow",
    "runledger.workflow.name",
    "workflow.name",
    "workflow",
)
AGENT_ID_KEYS = ("runledger.agent.id", "runledger.agent_id", "agent_id")
AGENT_NAME_KEYS = ("runledger.agent", "runledger.agent.name", "gen_ai.agent.name", "agent_name")


@dataclass(frozen=True)
class RunAttribution:
    workflow_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    # The workflow's feature_tag, to fill a run that arrived without one.
    feature_tag: str | None = None


def _as_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def first_value(attrs: dict[str, Any] | None, keys: tuple[str, ...]) -> str | None:
    """The first non-empty string value among ``keys`` in ``attrs``."""
    if not attrs:
        return None
    for key in keys:
        val = attrs.get(key)
        if val not in (None, ""):
            return str(val)[:255]
    return None


def _active(workspace_id: uuid.UUID) -> tuple[Any, ...]:
    return (
        WorkflowDefinition.workspace_id == workspace_id,
        WorkflowDefinition.status != "archived",
    )


async def resolve_workflow(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    workflow_id: Any = None,
    workflow: str | None = None,
    feature_tag: str | None = None,
    route_alias: str | None = None,
) -> WorkflowDefinition | None:
    """Find the workflow a run belongs to (see module docstring for the order)."""
    explicit_id = _as_uuid(workflow_id) or _as_uuid(workflow)
    if explicit_id is not None:
        wf = (
            await session.execute(
                select(WorkflowDefinition).where(
                    WorkflowDefinition.id == explicit_id, *_active(workspace_id)
                )
            )
        ).scalar_one_or_none()
        if wf is not None:
            return wf
    if workflow:
        ref = workflow.strip()
        wf = (
            (
                await session.execute(
                    select(WorkflowDefinition)
                    .where(
                        *_active(workspace_id),
                        or_(
                            WorkflowDefinition.feature_tag == ref,
                            func.lower(WorkflowDefinition.name) == ref.lower(),
                        ),
                    )
                    # A tag match beats a name match; then the oldest workflow.
                    .order_by(
                        (WorkflowDefinition.feature_tag == ref).desc(),
                        WorkflowDefinition.created_at,
                    )
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if wf is not None:
            return wf
    if feature_tag:
        wf = (
            (
                await session.execute(
                    select(WorkflowDefinition)
                    .where(*_active(workspace_id), WorkflowDefinition.feature_tag == feature_tag)
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if wf is not None:
            return wf
    if route_alias:
        return (
            (
                await session.execute(
                    select(WorkflowDefinition)
                    .where(*_active(workspace_id), WorkflowDefinition.gateway_alias == route_alias)
                    .order_by(WorkflowDefinition.created_at)
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
    return None


async def resolve_agent_id(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    agent_id: Any = None,
    agent_name: str | None = None,
) -> uuid.UUID | None:
    """Registered agent for a run: by id (same workspace only), else by exact name."""
    explicit = _as_uuid(agent_id) or _as_uuid(agent_name)
    if explicit is not None:
        found = (
            await session.execute(
                select(Agent.id).where(Agent.id == explicit, Agent.workspace_id == workspace_id)
            )
        ).scalar_one_or_none()
        if found is not None:
            return found
    if agent_name:
        return (
            (
                await session.execute(
                    select(Agent.id)
                    .where(
                        Agent.workspace_id == workspace_id,
                        Agent.name == agent_name.strip(),
                        Agent.status != "retired",
                    )
                    .order_by(Agent.created_at)
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
    return None


async def resolve_run_attribution(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    workflow_id: Any = None,
    workflow: str | None = None,
    feature_tag: str | None = None,
    route_alias: str | None = None,
    agent_id: Any = None,
    agent_name: str | None = None,
) -> RunAttribution:
    """Workflow + agent for one run. Never raises on bad references; returns None ids."""
    wf = await resolve_workflow(
        session,
        workspace_id,
        workflow_id=workflow_id,
        workflow=workflow,
        feature_tag=feature_tag,
        route_alias=route_alias,
    )
    agent = None
    if agent_id or agent_name:
        agent = await resolve_agent_id(
            session, workspace_id, agent_id=agent_id, agent_name=agent_name
        )
    return RunAttribution(
        workflow_id=wf.id if wf else None,
        agent_id=agent,
        feature_tag=wf.feature_tag if wf else None,
    )


async def attribution_from_event(
    session: AsyncSession, workspace_id: uuid.UUID, event: dict[str, Any]
) -> RunAttribution:
    """Attribution for a canonical ``run_start`` event (top-level keys, then metadata)."""
    meta = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    workflow_id = event.get("workflow_id") or first_value(meta, WORKFLOW_ID_KEYS)
    workflow = event.get("workflow") or first_value(meta, WORKFLOW_REF_KEYS)
    if workflow_id and _as_uuid(workflow_id) is None and not workflow:
        # e.g. OTLP runledger.workflow.id="support-triage": treat it as a reference.
        workflow, workflow_id = str(workflow_id), None
    return await resolve_run_attribution(
        session,
        workspace_id,
        workflow_id=workflow_id,
        workflow=workflow,
        feature_tag=event.get("feature_tag"),
        route_alias=first_value(meta, ("route_alias", "runledger.route_alias")),
        agent_id=event.get("agent_id") or first_value(meta, AGENT_ID_KEYS),
        agent_name=event.get("agent_name") or first_value(meta, AGENT_NAME_KEYS),
    )


async def link_existing_runs(session: AsyncSession, wf: WorkflowDefinition) -> int:
    """Attach unattributed runs that match a workflow's tag or alias (on create/link).

    Only runs with no workflow yet are touched, so explicit attribution is never
    overwritten. Returns the number of runs linked.
    """
    if wf.status == "archived" or not (wf.feature_tag or wf.gateway_alias):
        return 0
    conds = []
    if wf.feature_tag:
        conds.append(AgentRun.feature_tag == wf.feature_tag)
    if wf.gateway_alias:
        conds.append(AgentRun.run_metadata["route_alias"].astext == wf.gateway_alias)
    result = await session.execute(
        update(AgentRun)
        .where(
            AgentRun.workspace_id == wf.workspace_id,
            AgentRun.workflow_id.is_(None),
            or_(*conds),
        )
        .values(workflow_id=wf.id)
        .execution_options(synchronize_session=False)
    )
    return int(getattr(result, "rowcount", 0) or 0)
