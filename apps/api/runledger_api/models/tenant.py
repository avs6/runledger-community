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


class TenantRoleEnum(StrEnum):
    org_admin = "org_admin"
    org_manager = "org_manager"
    org_member = "org_member"
    org_billing_admin = "org_billing_admin"
    org_auditor = "org_auditor"


class WorkspaceRoleEnum(StrEnum):
    workspace_admin = "workspace_admin"
    workspace_editor = "workspace_editor"
    workspace_contributor = "workspace_contributor"
    member = "member"           # legacy alias for workspace_editor
    viewer = "viewer"


class TenantStatusEnum(StrEnum):
    active = "active"
    suspended = "suspended"
    archived = "archived"


class WorkspaceStatusEnum(StrEnum):
    active = "active"
    suspended = "suspended"
    archived = "archived"


class MemberStatusEnum(StrEnum):
    active = "active"
    invited = "invited"
    suspended = "suspended"


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
    status: Mapped[TenantStatusEnum] = mapped_column(
        sa.String(16), nullable=False, server_default="active"
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="tenant", passive_deletes=True)
    tenant_users: Mapped[list["TenantUser"]] = relationship(back_populates="tenant", passive_deletes=True)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    status: Mapped[WorkspaceStatusEnum] = mapped_column(
        sa.String(16), nullable=False, server_default="active"
    )
    is_restricted: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="workspaces")
    applications: Mapped[list["Application"]] = relationship(back_populates="workspace", passive_deletes=True)
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="workspace", passive_deletes=True)


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
    username: Mapped[str | None] = mapped_column(sa.String(64), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("true"), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    is_platform_admin: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("false"), nullable=False
    )
    email_verified: Mapped[bool] = mapped_column(
        sa.Boolean, server_default=sa.text("false"), nullable=False
    )
    email_verify_token: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    firebase_uid: Mapped[str | None] = mapped_column(sa.String(128), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    workspace_users: Mapped[list["WorkspaceUser"]] = relationship(back_populates="user", passive_deletes=True)
    tenant_users: Mapped[list["TenantUser"]] = relationship(back_populates="user", passive_deletes=True)


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
    role: Mapped[WorkspaceRoleEnum] = mapped_column(
        sa.Enum(WorkspaceRoleEnum, name="workspace_role_enum"),
        server_default="workspace_admin",
        nullable=False,
    )
    status: Mapped[MemberStatusEnum] = mapped_column(
        sa.String(16), nullable=False, server_default="active"
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    user: Mapped["User"] = relationship(back_populates="workspace_users")
    workspace: Mapped["Workspace"] = relationship()


class TenantUser(Base):
    __tablename__ = "tenant_users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[TenantRoleEnum] = mapped_column(
        sa.Enum(TenantRoleEnum, name="tenant_role_enum"),
        server_default="org_member",
        nullable=False,
    )
    status: Mapped[MemberStatusEnum] = mapped_column(
        sa.String(16), nullable=False, server_default="active"
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")
    )

    user: Mapped["User"] = relationship(back_populates="tenant_users")
    tenant: Mapped["Tenant"] = relationship(back_populates="tenant_users")


