from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class BackupRun(Base):
    __tablename__ = "backup_runs"
    __table_args__ = (
        sa.Index("ix_backup_runs_workspace_created", "workspace_id", "created_at"),
        sa.Index("ix_backup_runs_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_mode: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'manual'")
    )
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'queued'")
    )
    backup_scope: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, server_default=sa.text("'full'")
    )
    target: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    command: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    checksum: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    output_excerpt: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )


class BackupTargetConfig(Base):
    __tablename__ = "backup_target_configs"
    __table_args__ = (
        sa.UniqueConstraint("workspace_id", name="uq_backup_target_configs_workspace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'s3'")
    )
    bucket: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    prefix: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    access_key_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    secret_access_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    force_path_style: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    schedule_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    cadence: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'daily'")
    )
    run_hour_utc: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("2")
    )
    retention_days: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("30")
    )
    include_memory_db: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    include_qdrant: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    include_kuzu: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    include_skills: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    encryption_mode: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'server_side'")
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
        onupdate=datetime.utcnow,
    )


class BackupSnapshot(Base):
    __tablename__ = "backup_snapshots"
    __table_args__ = (
        sa.Index("ix_backup_snapshots_workspace_created", "workspace_id", "created_at"),
        sa.Index("ix_backup_snapshots_run", "backup_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    backup_run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("backup_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'full'")
    )
    bucket: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    prefix: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    manifest_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    checksum: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    total_size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    artifact_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    artifacts: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    integrity_status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'pending'")
    )
    verified_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
    )
