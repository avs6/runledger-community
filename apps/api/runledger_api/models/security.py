from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class WorkspaceSecuritySettings(Base):
    __tablename__ = "workspace_security_settings"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", name="uq_workspace_security_settings_workspace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_metadata_fields: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    required_metadata_mode: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'warn'")
    )
    data_residency_regions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    callback_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    brand_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    oidc_session_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class OIDCProvider(Base):
    __tablename__ = "oidc_providers"
    __table_args__ = (
        sa.Index("ix_oidc_providers_workspace_active", "workspace_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    issuer_url: Mapped[str] = mapped_column(sa.Text, nullable=False)
    audience: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    discovery_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    jwks_uri: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    claim_mappings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class IpAclRule(Base):
    __tablename__ = "ip_acl_rules"
    __table_args__ = (
        sa.Index("ix_ip_acl_rules_workspace_scope", "workspace_id", "scope_type", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default=sa.text("'workspace'"))
    team_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    cidr: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    action: Mapped[str] = mapped_column(sa.String(8), nullable=False, server_default=sa.text("'allow'"))
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="100")
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class KeyRotationEvent(Base):
    __tablename__ = "key_rotation_events"
    __table_args__ = (
        sa.Index("ix_key_rotation_events_api_key", "api_key_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rotated_from_prefix: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    rotated_to_prefix: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    triggered_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    grace_expires_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )

