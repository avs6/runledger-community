"""ORM models for projects and team-managed models."""

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


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (sa.Index("ix_projects_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    budget_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    budget_period: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)


class ProjectKey(Base):
    __tablename__ = "project_keys"
    __table_args__ = (
        sa.Index("ix_project_keys_project", "project_id"),
        sa.Index("ix_project_keys_key", "api_key_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    api_key_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)


class TeamModel(Base):
    __tablename__ = "team_models"
    __table_args__ = (sa.Index("ix_team_models_workspace", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    team_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    budget_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(14, 6), nullable=True)
    budget_period: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    logging_opt_out: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    health_status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default=sa.text("'unknown'"))
    last_health_check: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    total_calls: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    total_cost_usd: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False, server_default=sa.text("0"))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False)
