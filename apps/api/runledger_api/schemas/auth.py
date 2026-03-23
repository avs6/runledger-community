from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime

from pydantic import BaseModel

from runledger_api.models.tenant import (
    EnvironmentEnum,
    MemberStatusEnum,
    PlanEnum,
    TenantRoleEnum,
    TenantStatusEnum,
    WorkspaceRoleEnum,
    WorkspaceStatusEnum,
)


def _auto_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]
    suffix = secrets.token_hex(3)
    return f"{base}-{suffix}"


# ── Tenant ────────────────────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    name: str
    plan: PlanEnum = PlanEnum.free
    # Admin user for this org
    admin_email: str
    admin_password: str
    admin_full_name: str | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: PlanEnum
    status: TenantStatusEnum = TenantStatusEnum.active
    is_default: bool
    owner_user_id: uuid.UUID | None
    created_at: datetime
    workspace_count: int = 0
    member_count: int = 0

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: PlanEnum | None = None


# ── Workspace ─────────────────────────────────────────────────────────────────


class WorkspaceCreate(BaseModel):
    tenant_id: uuid.UUID
    name: str


class WorkspaceCreateForOrg(BaseModel):
    """Used by org admins — tenant_id comes from auth context."""

    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: WorkspaceStatusEnum = WorkspaceStatusEnum.active
    is_restricted: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Application ───────────────────────────────────────────────────────────────


class ApplicationCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str
    environment: EnvironmentEnum = EnvironmentEnum.dev


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    environment: EnvironmentEnum
    created_at: datetime

    model_config = {"from_attributes": True}


# ── API Key ───────────────────────────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    name: str | None = None
    environment: EnvironmentEnum = EnvironmentEnum.dev
    scopes: list[str] = []
    created_by: str | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    key_prefix: str
    name: str | None
    scopes: list[str]
    created_at: datetime
    created_by: str | None
    is_session: bool = False

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned only on creation — contains the raw key (shown once)."""

    key: str


# ── User ──────────────────────────────────────────────────────────────────────


class OrgAssignment(BaseModel):
    tenant_id: uuid.UUID
    role: str = "org_member"  # org_admin | org_member


class UserCreate(BaseModel):
    email: str
    password: str
    username: str | None = None
    full_name: str | None = None
    org_assignments: list[OrgAssignment] = []


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserOrgMembership(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    role: str


class UserWithOrgsResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str | None
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    last_login_at: datetime | None
    created_at: datetime
    organizations: list[UserOrgMembership]


class UserUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    password: str | None = None


# ── TenantUser / WorkspaceUser ─────────────────────────────────────────────────


class TenantMemberResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: TenantRoleEnum
    status: MemberStatusEnum = MemberStatusEnum.active
    email: str
    full_name: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: WorkspaceRoleEnum
    status: MemberStatusEnum = MemberStatusEnum.active
    email: str
    full_name: str | None
    is_active: bool
    last_login_at: datetime | None
    joined_at: datetime

    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    email: str
    full_name: str | None = None
    role: WorkspaceRoleEnum = WorkspaceRoleEnum.member
    # Temporary password; in production this would trigger an invite email
    temporary_password: str = "ChangeMe123!"


class InviteOrgMemberRequest(BaseModel):
    email: str
    full_name: str | None = None
    role: TenantRoleEnum = TenantRoleEnum.org_member
    temporary_password: str = "ChangeMe123!"


class RoleUpdateRequest(BaseModel):
    role: WorkspaceRoleEnum


class OrgRoleUpdateRequest(BaseModel):
    role: TenantRoleEnum


# ── Org Profile ───────────────────────────────────────────────────────────────


class OrgProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    plan: PlanEnum
    status: TenantStatusEnum = TenantStatusEnum.active
    is_default: bool
    owner_user_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgProfileUpdate(BaseModel):
    name: str | None = None
    plan: PlanEnum | None = None


class AddWorkspaceMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: WorkspaceRoleEnum = WorkspaceRoleEnum.member


# ── Status updates ─────────────────────────────────────────────────────────────


class TenantStatusUpdate(BaseModel):
    status: TenantStatusEnum
    reason: str | None = None


class WorkspaceStatusUpdate(BaseModel):
    status: WorkspaceStatusEnum
    reason: str | None = None


class MemberStatusUpdate(BaseModel):
    status: MemberStatusEnum
    reason: str | None = None


# ── Workspace (rich / platform) ───────────────────────────────────────────────


class WorkspaceDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    name: str
    status: WorkspaceStatusEnum = WorkspaceStatusEnum.active
    is_restricted: bool = False
    created_at: datetime
    member_count: int = 0


class WorkspaceMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: WorkspaceRoleEnum = WorkspaceRoleEnum.member


class WorkspaceOrgAssign(BaseModel):
    """Move workspace to a different org (or same — idempotent)."""

    tenant_id: uuid.UUID


# ── Audit log ──────────────────────────────────────────────────────────────────


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    target_user_id: uuid.UUID | None
    scope_type: str
    scope_id: uuid.UUID
    action: str
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
