import uuid
from datetime import datetime
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from runledger_api.core.db import Base


class PlanEnum(StrEnum):
    free = "free"
    starter = "starter"
    growth = "growth"
    enterprise = "enterprise"


class EnvironmentEnum(StrEnum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(sa.String(64), unique=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    plan: Mapped[PlanEnum] = mapped_column(
        sa.Enum(PlanEnum, name="plan_enum"), default=PlanEnum.free
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="tenant")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="workspaces")
    applications: Mapped[list["Application"]] = relationship(back_populates="workspace")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="workspace")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    environment: Mapped[EnvironmentEnum] = mapped_column(
        sa.Enum(EnvironmentEnum, name="environment_enum"), default=EnvironmentEnum.dev
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="applications")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    key_hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    key_prefix: Mapped[str] = mapped_column(sa.String(24))
    name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String), server_default=sa.text("'{}'::varchar[]")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )
    is_session: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("false"), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="api_keys")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    workspace_users: Mapped[list["WorkspaceUser"]] = relationship(back_populates="user")


class WorkspaceUser(Base):
    __tablename__ = "workspace_users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(sa.String(32), server_default="admin")
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    user: Mapped["User"] = relationship(back_populates="workspace_users")
    workspace: Mapped["Workspace"] = relationship()
