from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from runledger_api.core.scopes import normalize_scopes
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
    admin_email: str | None = None
    created_at: datetime
    workspace_count: int = 0
    member_count: int = 0
    # Only returned when the org was created with a generated admin password.
    temporary_password: str | None = None

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: PlanEnum | None = None


# ── Workspace ─────────────────────────────────────────────────────────────────


class PlatformTenantUpdate(BaseModel):
    name: str | None = None
    plan: PlanEnum | None = None
    status: TenantStatusEnum | None = None


class PlatformTenantDelete(BaseModel):
    confirmation: str


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
    # Which workspace the key is minted for. Must belong to the caller's org.
    # Defaults to the caller's current workspace when omitted.
    workspace_id: uuid.UUID | None = None
    # environment is retained internally (drives the key prefix) but is no longer
    # surfaced in the dashboard — keys are organised by workspace, not env.
    environment: EnvironmentEnum = EnvironmentEnum.dev
    # What the key may do: read, write, ingest, gateway, mcp (see core/scopes.py).
    # Empty = full access to the workspace.
    scopes: list[str] = []
    created_by: str | None = None
    ownership_type: str = "user"
    owner_reference: str | None = None
    # Optional expiry. Keys without one never expire (rotate them instead).
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def _valid_scopes(cls, value: list[str]) -> list[str]:
        return normalize_scopes(value)


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    ownership_type: str | None = None
    owner_reference: str | None = None
    # Replace the key's scopes; [] removes all limits (full access).
    scopes: list[str] | None = None

    @field_validator("scopes")
    @classmethod
    def _valid_scopes(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else normalize_scopes(value)


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str | None = None
    budget_tier_id: uuid.UUID | None = None
    key_prefix: str
    name: str | None
    scopes: list[str]
    created_at: datetime
    created_by: str | None
    is_session: bool = False
    ownership_type: str = "user"
    owner_reference: str | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None

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
    email_verified: bool = False
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
    """Self-service profile update (PUT /users/me)."""

    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None  # ignored for self-service; kept for compatibility
    password: str | None = None
    # Required when changing the password of an account that already has one.
    current_password: str | None = None


class AdminUserCreate(BaseModel):
    """Create a user identity (no membership) — org-admin action in the Users page."""

    email: str
    full_name: str | None = None
    # Leave empty to have a random policy-compliant password generated; it is
    # returned once in the response and must be changed at first sign-in.
    temporary_password: str | None = None
    # Mark the address verified without an email round-trip (use when SMTP is not
    # configured). Otherwise a verification email is sent.
    skip_verification: bool = False


class AdminUserUpdate(BaseModel):
    """Admin edit of another user's identity."""

    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    email_verified: bool | None = None


class OrgUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    email_verified: bool
    org_role: str | None = None
    org_status: str | None = None
    last_login_at: datetime | None
    created_at: datetime
    # False when the identity is shared with another org or is a platform admin:
    # this org may manage the membership but not the password/active/verified flags.
    can_manage_identity: bool = True
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class OrgUserCreateResponse(OrgUserResponse):
    """Returned once on creation — includes the generated temporary password."""

    temporary_password: str | None = None


class PlatformOrgCreate(BaseModel):
    """Platform-admin creates a new organization (tenant) + its own org admin."""

    name: str
    admin_email: str
    # Leave empty to generate one; it is returned once and must be changed at first
    # sign-in.
    admin_password: str | None = None
    admin_full_name: str | None = None
    # Mark the seeded admin verified (default true on SMTP-less builds) so they can
    # sign in immediately.
    skip_verification: bool = True


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
    # Only set when the invite created a brand-new account.
    temporary_password: str | None = None

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
    # Only set when the invite created a brand-new account.
    temporary_password: str | None = None

    model_config = {"from_attributes": True}


class InviteUserRequest(BaseModel):
    """Add a person to the current workspace.

    New emails get an account (with a generated temporary password unless one is
    given) and org membership. Existing accounts must already be active members of
    this org — use the org invitation flow for anyone else.
    """

    email: str
    full_name: str | None = None
    role: WorkspaceRoleEnum = WorkspaceRoleEnum.member
    temporary_password: str | None = None
    # New accounts only: mark the address verified without an email round-trip
    # (use when SMTP is not configured). Otherwise a verification email is sent.
    skip_verification: bool = False


class InviteOrgMemberRequest(BaseModel):
    """Invite a person to the org. Existing accounts receive a pending invitation
    they must accept; new emails get an account with a temporary password."""

    email: str
    full_name: str | None = None
    role: TenantRoleEnum = TenantRoleEnum.org_member
    temporary_password: str | None = None
    # New accounts only: see InviteUserRequest.skip_verification.
    skip_verification: bool = False


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


# ── Sessions, invitations, verification, password reset ──────────────────────


class SessionInfoResponse(BaseModel):
    """The caller's current dashboard session, derived server-side (GET /auth/me)."""

    email: str
    full_name: str | None
    user_id: str
    workspace_id: str
    workspace_name: str
    tenant_id: str
    tenant_name: str
    is_platform_admin: bool
    tenant_role: str | None
    workspace_role: str | None
    workspace_ids: list[str]
    must_change_password: bool = False


class SessionKeyResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str | None = None
    key_prefix: str
    name: str | None
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    current: bool = False


class PendingInvitationResponse(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    role: TenantRoleEnum
    invited_by_email: str | None = None
    created_at: datetime


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)


class EmailOnlyRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=1024)
