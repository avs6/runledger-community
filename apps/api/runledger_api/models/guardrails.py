"""ORM models for the guardrails, content safety, and policy engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class GuardrailRule(Base):
    """
    A custom or template guardrail rule.

    mode values: pre_call | post_call | both
    rule_type values: custom | template | builtin_filter | partner
    status values: active | disabled | draft
    """

    __tablename__ = "guardrail_rules"
    __table_args__ = (
        sa.Index("ix_guardrail_rules_workspace", "workspace_id"),
        sa.Index("ix_guardrail_rules_workspace_status", "workspace_id", "status"),
        sa.Index("ix_guardrail_rules_workspace_type", "workspace_id", "rule_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    mode: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pre_call'")
    )
    rule_type: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'custom'")
    )
    logic: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    severity: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'medium'")
    )
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("100"))
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'active'")
    )
    template_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class GuardrailEvent(Base):
    """
    An evaluation event recorded each time a guardrail runs against a request.

    decision values: allow | block | modify
    """

    __tablename__ = "guardrail_events"
    __table_args__ = (
        sa.Index("ix_guardrail_events_workspace", "workspace_id"),
        sa.Index("ix_guardrail_events_workspace_decision", "workspace_id", "decision"),
        sa.Index("ix_guardrail_events_rule", "guardrail_rule_id"),
        sa.Index("ix_guardrail_events_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    guardrail_rule_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    guardrail_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    mode: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision: Mapped[str] = mapped_column(sa.Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(sa.Float, nullable=False, server_default=sa.text("0"))
    request_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    gateway_request_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class PartnerGuardrail(Base):
    """
    Configuration for an external guardrail provider (Presidio, Lakera, etc.).

    provider values: presidio | bedrock | lakera | openai_moderation |
                     google_model_armor | guardrails_ai | prompt_security | lasso
    status values: active | disabled | error
    fallback_action values: allow | block
    """

    __tablename__ = "partner_guardrails"
    __table_args__ = (
        sa.Index("ix_partner_guardrails_workspace", "workspace_id"),
        sa.Index("ix_partner_guardrails_workspace_provider", "workspace_id", "provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(sa.Text, nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    mode: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pre_call'")
    )
    endpoint_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    timeout_ms: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("2000")
    )
    fallback_action: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'allow'")
    )
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("200"))
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'active'")
    )
    last_health_check: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    health_status: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    total_calls: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    total_cost_usd: Mapped[float] = mapped_column(
        sa.Float, nullable=False, server_default=sa.text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class GuardrailTestCase(Base):
    """A saved test case for regression testing guardrails."""

    __tablename__ = "guardrail_test_cases"
    __table_args__ = (
        sa.Index("ix_guardrail_test_cases_workspace", "workspace_id"),
        sa.Index("ix_guardrail_test_cases_rule", "guardrail_rule_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    guardrail_rule_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    input_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    input_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    expected_decision: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
