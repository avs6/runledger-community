"""ORM models for the agent registry, workflows and agent memory."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        sa.Index("ix_agents_workspace", "workspace_id"),
        sa.Index("ix_agents_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'autonomous'")
    )
    owner: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    default_model: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    default_tools: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    budget_envelope: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(precision=12, scale=4), nullable=True
    )
    # Gateway route aliases this agent may call; empty = any. Enforced with status and
    # budget_envelope by services/agent_policy.py (gateway preflight + SDK).
    allowed_aliases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'active'"))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class WorkflowDefinition(Base):
    """A workflow: the product's top-level object.

    Runs are attributed to a workflow at ingest (``agent_runs.workflow_id``), resolved
    from an explicit id/name (SDK, ``X-RunLedger-Workflow`` header, OTLP
    ``runledger.workflow*`` attributes), the run's ``feature_tag`` or the gateway alias
    the request used. ``feature_tag`` is also the key budgets, chargeback and analytics
    already scope by, so a workflow's budgets are ``feature_tag`` budgets on that tag.
    """

    __tablename__ = "workflow_definitions"
    __table_args__ = (
        sa.Index("ix_workflow_definitions_workspace", "workspace_id"),
        sa.Index(
            "uq_workflow_definitions_feature_tag",
            "workspace_id",
            "feature_tag",
            unique=True,
            postgresql_where=sa.text("feature_tag IS NOT NULL AND status <> 'archived'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    feature_tag: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    gateway_alias: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    steps_schema: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    status: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default=sa.text("'active'"))
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class WorkflowRun(Base):
    """Read-only view over ``agent_runs`` that carry a ``workflow_id`` (migration
    ``workflows_spine``). Workflow runs are ordinary runs; there is no separate record
    to create or update. Query ``AgentRun`` directly in new code."""

    __tablename__ = "workflow_runs"
    __table_args__ = {"info": {"is_view": True}}

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    workflow_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    access_group_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(sa.Text)
    total_cost: Mapped[Decimal] = mapped_column(sa.Numeric(14, 8))
    total_tokens: Mapped[int] = mapped_column(sa.BigInteger)
    total_duration_ms: Mapped[int | None] = mapped_column(sa.BigInteger)
    trigger: Mapped[str | None] = mapped_column(sa.Text)
    started_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True))


class AgentMemory(Base):
    __tablename__ = "agent_memories"
    __table_args__ = (
        sa.Index("ix_agent_memories_agent", "agent_id"),
        sa.Index("ix_agent_memories_workspace", "workspace_id"),
        sa.UniqueConstraint("agent_id", "key", name="uq_agent_memories_agent_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'long_term'")
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    size_bytes: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    access_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    has_pii: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    retention_days: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class AgentMemoryAudit(Base):
    __tablename__ = "agent_memory_audit"
    __table_args__ = (
        sa.Index("ix_agent_memory_audit_agent", "agent_id"),
        sa.Index("ix_agent_memory_audit_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    memory_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(sa.Text, nullable=False)
    key: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    actor: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
