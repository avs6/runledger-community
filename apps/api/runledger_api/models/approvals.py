"""ORM model for policy approval workflow."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class Approval(Base):
    """
    A governance approval request for a sensitive action.

    request_type values:
        budget_increase     — raise a budget's limit_usd
        prompt_promote      — promote a prompt version to production
        tool_allow          — allow a privileged tool
        capture_policy_full — enable FULL payload capture mode
        shadow_routing      — enable shadow routing to an external provider

    status values: pending | approved | denied | cancelled
    """

    __tablename__ = "approvals"
    __table_args__ = (
        sa.Index("ix_approvals_workspace_status", "workspace_id", "status"),
        sa.Index("ix_approvals_workspace_type", "workspace_id", "request_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    request_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    status: Mapped[str] = mapped_column(
        sa.Text, nullable=False, server_default=sa.text("'pending'")
    )
    requested_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class AutoApprovalPolicy(Base):
    """Declarative auto-approval rule for low-risk request patterns."""

    __tablename__ = "auto_approval_policies"
    __table_args__ = (
        sa.Index("ix_auto_approval_policies_workspace_type", "workspace_id", "request_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    request_type: Mapped[str] = mapped_column(sa.Text, nullable=False)
    condition: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
