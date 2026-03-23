"""Platform admin endpoints. Requires is_platform_admin=True on the session user."""

from __future__ import annotations

import re
import secrets
import uuid
from typing import Annotated

import bcrypt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_platform_admin
from runledger_api.models.tenant import (
    Tenant, TenantRoleEnum, TenantUser, User,
    Workspace, WorkspaceRoleEnum, WorkspaceUser,
)
from runledger_api.schemas.auth import (
    OrgAssignment, TenantCreate, TenantResponse,
    TenantStatusUpdate, TenantUpdate,
    UserCreate, UserOrgMembership, UserResponse, UserUpdate, UserWithOrgsResponse,
    WorkspaceDetailResponse, WorkspaceMemberCreate, WorkspaceOrgAssign,
    WorkspaceResponse, WorkspaceCreateForOrg, WorkspaceStatusUpdate,
)
from runledger_api.services.tenancy import log_audit

log = structlog.get_logger()
router = APIRouter(prefix="/platform", tags=["platform-admin"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _make_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:50]
    return f"{base}-{secrets.token_hex(3)}"


async def _ws_detail(db: AsyncSession, ws: Workspace) -> dict:
    tenant = await db.get(Tenant, ws.tenant_id)
    mc = (await db.execute(
        select(func.count()).select_from(WorkspaceUser).where(WorkspaceUser.workspace_id == ws.id)
    )).scalar() or 0
    return {
        "id": ws.id, "tenant_id": ws.tenant_id,
        "tenant_name": tenant.name if tenant else "",
        "name": ws.name, "status": ws.status,
        "is_restricted": ws.is_restricted,
        "created_at": ws.created_at, "member_count": mc,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_platform_stats(
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    tenant_count = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    workspace_count = (await db.execute(select(func.count()).select_from(Workspace))).scalar() or 0
    return {"tenant_count": tenant_count, "user_count": user_count, "workspace_count": workspace_count}


# ─────────────────────────────────────────────────────────────────────────────
# Orgs  (formerly /platform/tenants)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/orgs", response_model=list[TenantResponse])
async def list_all_orgs(
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> list[dict]:
    query = select(Tenant).order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
    if search:
        query = query.where(Tenant.name.ilike(f"%{search}%"))
    tenants = list((await db.execute(query)).scalars().all())
    out = []
    for t in tenants:
        ws_count = (await db.execute(
            select(func.count()).select_from(Workspace).where(Workspace.tenant_id == t.id)
        )).scalar() or 0
        tu_count = (await db.execute(
            select(func.count()).select_from(TenantUser).where(TenantUser.tenant_id == t.id)
        )).scalar() or 0
        out.append({"id": t.id, "name": t.name, "plan": t.plan, "status": t.status,
                    "is_default": t.is_default, "owner_user_id": t.owner_user_id,
                    "created_at": t.created_at, "workspace_count": ws_count, "member_count": tu_count})
    return out


@router.post("/orgs", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def platform_create_org(
    body: TenantCreate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    existing = await db.execute(select(User).where(User.email == body.admin_email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.admin_email}' already exists")

    slug = _make_slug(body.name)
    tenant = Tenant(slug=slug, name=body.name, plan=body.plan)
    db.add(tenant)
    await db.flush()

    pw_hash = bcrypt.hashpw(body.admin_password.encode(), bcrypt.gensalt()).decode()
    user = User(email=body.admin_email, password_hash=pw_hash,
                full_name=body.admin_full_name or body.admin_email.split("@")[0], is_active=True)
    db.add(user)
    await db.flush()

    tenant.owner_user_id = user.id
    db.add(TenantUser(tenant_id=tenant.id, user_id=user.id, role=TenantRoleEnum.org_admin))
    workspace = Workspace(tenant_id=tenant.id, name=f"{body.name} Workspace")
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceUser(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRoleEnum.workspace_admin))
    await db.commit()
    await db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name, "plan": tenant.plan, "status": tenant.status,
            "is_default": tenant.is_default, "owner_user_id": tenant.owner_user_id,
            "created_at": tenant.created_at, "workspace_count": 1, "member_count": 1}


@router.get("/orgs/{org_id}", response_model=TenantResponse)
async def platform_get_org(
    org_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    ws_count = (await db.execute(
        select(func.count()).select_from(Workspace).where(Workspace.tenant_id == tenant.id)
    )).scalar() or 0
    tu_count = (await db.execute(
        select(func.count()).select_from(TenantUser).where(TenantUser.tenant_id == tenant.id)
    )).scalar() or 0
    return {"id": tenant.id, "name": tenant.name, "plan": tenant.plan, "status": tenant.status,
            "is_default": tenant.is_default, "owner_user_id": tenant.owner_user_id,
            "created_at": tenant.created_at, "workspace_count": ws_count, "member_count": tu_count}


@router.put("/orgs/{org_id}", response_model=TenantResponse)
async def platform_update_org(
    org_id: uuid.UUID, body: TenantUpdate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if body.name is not None:
        tenant.name = body.name
    if body.plan is not None:
        tenant.plan = body.plan
    await db.commit()
    await db.refresh(tenant)
    ws_count = (await db.execute(
        select(func.count()).select_from(Workspace).where(Workspace.tenant_id == tenant.id)
    )).scalar() or 0
    tu_count = (await db.execute(
        select(func.count()).select_from(TenantUser).where(TenantUser.tenant_id == tenant.id)
    )).scalar() or 0
    return {"id": tenant.id, "name": tenant.name, "plan": tenant.plan, "status": tenant.status,
            "is_default": tenant.is_default, "owner_user_id": tenant.owner_user_id,
            "created_at": tenant.created_at, "workspace_count": ws_count, "member_count": tu_count}


@router.put("/orgs/{org_id}/status", response_model=TenantResponse)
async def platform_update_org_status(
    org_id: uuid.UUID, body: TenantStatusUpdate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    _, current_user = auth
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if tenant.is_default and body.status != "active":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot suspend or archive the default organization")
    old_status = tenant.status
    tenant.status = body.status
    log_audit(db, actor_user_id=current_user.id, scope_type="platform",
              scope_id=org_id, action="org.status_changed",
              old_value=str(old_status), new_value=str(body.status))
    await db.commit()
    await db.refresh(tenant)
    ws_count = (await db.execute(
        select(func.count()).select_from(Workspace).where(Workspace.tenant_id == tenant.id)
    )).scalar() or 0
    tu_count = (await db.execute(
        select(func.count()).select_from(TenantUser).where(TenantUser.tenant_id == tenant.id)
    )).scalar() or 0
    return {"id": tenant.id, "name": tenant.name, "plan": tenant.plan, "status": tenant.status,
            "is_default": tenant.is_default, "owner_user_id": tenant.owner_user_id,
            "created_at": tenant.created_at, "workspace_count": ws_count, "member_count": tu_count}


@router.delete("/orgs/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_delete_org(
    org_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> None:
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    if tenant.is_default:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the default organization")

    member_ids = list((await db.execute(
        select(TenantUser.user_id).where(TenantUser.tenant_id == org_id)
    )).scalars().all())
    exclusive_user_ids = []
    for uid in member_ids:
        other = (await db.execute(
            select(TenantUser.tenant_id)
            .where(TenantUser.user_id == uid, TenantUser.tenant_id != org_id)
            .limit(1)
        )).scalar()
        if other is None:
            exclusive_user_ids.append(uid)

    await db.delete(tenant)
    await db.flush()

    for uid in exclusive_user_ids:
        user = await db.get(User, uid)
        if user is not None:
            await db.delete(user)

    await db.commit()


@router.get("/orgs/{org_id}/workspaces", response_model=list[WorkspaceResponse])
async def platform_list_org_workspaces(
    org_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> list[Workspace]:
    result = await db.execute(
        select(Workspace).where(Workspace.tenant_id == org_id).order_by(Workspace.created_at)
    )
    return list(result.scalars().all())


@router.post("/orgs/{org_id}/workspaces", status_code=status.HTTP_201_CREATED, response_model=WorkspaceResponse)
async def platform_create_workspace_for_org(
    org_id: uuid.UUID, body: WorkspaceCreateForOrg,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> Workspace:
    tenant = await db.get(Tenant, org_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    workspace = Workspace(tenant_id=org_id, name=body.name)
    db.add(workspace)
    await db.flush()
    await db.commit()
    await db.refresh(workspace)
    log.info("platform_workspace_created", org_id=str(org_id), workspace_id=str(workspace.id))
    return workspace


@router.get("/orgs/{org_id}/members")
async def platform_list_org_members(
    org_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
    search: str | None = Query(None),
) -> list[dict]:
    query = (
        select(TenantUser, User)
        .join(User, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == org_id)
        .order_by(User.full_name)
    )
    if search:
        query = query.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    rows = (await db.execute(query)).all()
    return [
        {
            "user_id": str(tu.user_id),
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "is_platform_admin": u.is_platform_admin,
            "role": str(tu.role),
            "status": str(tu.status) if tu.status else "active",
        }
        for tu, u in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Workspaces  (full platform management)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/workspaces", response_model=list[WorkspaceDetailResponse])
async def platform_list_workspaces(
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
    search: str | None = Query(None),
    org_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> list[dict]:
    query = (
        select(Workspace, Tenant)
        .join(Tenant, Workspace.tenant_id == Tenant.id)
        .order_by(Workspace.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if search:
        query = query.where(
            Workspace.name.ilike(f"%{search}%") | Tenant.name.ilike(f"%{search}%")
        )
    if org_id is not None:
        query = query.where(Workspace.tenant_id == org_id)

    rows = (await db.execute(query)).all()
    out = []
    for ws, t in rows:
        mc = (await db.execute(
            select(func.count()).select_from(WorkspaceUser).where(WorkspaceUser.workspace_id == ws.id)
        )).scalar() or 0
        out.append({
            "id": ws.id, "tenant_id": ws.tenant_id, "tenant_name": t.name,
            "name": ws.name, "status": ws.status, "is_restricted": ws.is_restricted,
            "created_at": ws.created_at, "member_count": mc,
        })
    return out


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def platform_get_workspace(
    workspace_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return await _ws_detail(db, ws)


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceDetailResponse)
async def platform_update_workspace(
    workspace_id: uuid.UUID, body: WorkspaceCreateForOrg,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    ws.name = body.name
    await db.commit()
    await db.refresh(ws)
    return await _ws_detail(db, ws)


@router.put("/workspaces/{workspace_id}/status", response_model=WorkspaceDetailResponse)
async def platform_update_workspace_status(
    workspace_id: uuid.UUID, body: WorkspaceStatusUpdate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    ws.status = body.status
    await db.commit()
    await db.refresh(ws)
    return await _ws_detail(db, ws)


@router.put("/workspaces/{workspace_id}/org", response_model=WorkspaceDetailResponse)
async def platform_move_workspace_org(
    workspace_id: uuid.UUID, body: WorkspaceOrgAssign,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> dict:
    """Move workspace to a different organization."""
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    ws.tenant_id = body.tenant_id
    await db.commit()
    await db.refresh(ws)
    return await _ws_detail(db, ws)


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_delete_workspace(
    workspace_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> None:
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    await db.delete(ws)
    await db.commit()


@router.get("/workspaces/{workspace_id}/members")
async def platform_list_workspace_members(
    workspace_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> list[dict]:
    query = (
        select(WorkspaceUser, User)
        .join(User, WorkspaceUser.user_id == User.id)
        .where(WorkspaceUser.workspace_id == workspace_id)
        .order_by(User.full_name)
        .offset(skip)
        .limit(limit)
    )
    if search:
        query = query.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    rows = (await db.execute(query)).all()
    return [
        {
            "user_id": str(wu.user_id),
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "role": str(wu.role),
            "status": str(wu.status) if wu.status else "active",
        }
        for wu, u in rows
    ]


@router.post("/workspaces/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def platform_add_workspace_member(
    workspace_id: uuid.UUID, body: WorkspaceMemberCreate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> dict:
    ws = await db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    existing = (await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == body.user_id
        )
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this workspace")
    db.add(WorkspaceUser(workspace_id=workspace_id, user_id=body.user_id, role=body.role))
    await db.commit()
    return {"user_id": str(body.user_id), "email": user.email, "full_name": user.full_name, "role": str(body.role)}


@router.put("/workspaces/{workspace_id}/members/{user_id}")
async def platform_update_workspace_member(
    workspace_id: uuid.UUID, user_id: uuid.UUID,
    body: WorkspaceMemberCreate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> dict:
    wu = (await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == user_id
        )
    )).scalar_one_or_none()
    if wu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found in workspace")
    wu.role = body.role
    await db.commit()
    return {"user_id": str(user_id), "role": str(wu.role)}


@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_remove_workspace_member(
    workspace_id: uuid.UUID, user_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> None:
    wu = (await db.execute(
        select(WorkspaceUser).where(
            WorkspaceUser.workspace_id == workspace_id, WorkspaceUser.user_id == user_id
        )
    )).scalar_one_or_none()
    if wu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found in workspace")
    await db.delete(wu)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def platform_create_user(
    body: UserCreate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> User:
    if (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{body.email}' already exists")
    if body.username and (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Username '{body.username}' already taken")

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = User(
        email=body.email, username=body.username or None,
        password_hash=pw_hash,
        full_name=body.full_name or body.email.split("@")[0],
        is_active=True,
    )
    db.add(user)
    await db.flush()

    for assignment in body.org_assignments:
        tenant = await db.get(Tenant, assignment.tenant_id)
        if tenant is None:
            continue
        existing_tu = (await db.execute(
            select(TenantUser).where(TenantUser.tenant_id == assignment.tenant_id, TenantUser.user_id == user.id)
        )).scalar_one_or_none()
        if existing_tu is None:
            role = TenantRoleEnum.org_admin if assignment.role == "org_admin" else TenantRoleEnum.org_member
            db.add(TenantUser(tenant_id=assignment.tenant_id, user_id=user.id, role=role))
            ws_role = WorkspaceRoleEnum.workspace_admin if assignment.role == "org_admin" else WorkspaceRoleEnum.member
            workspaces = list((await db.execute(
                select(Workspace).where(Workspace.tenant_id == assignment.tenant_id)
            )).scalars().all())
            for ws in workspaces:
                db.add(WorkspaceUser(workspace_id=ws.id, user_id=user.id, role=ws_role))

    await db.commit()
    await db.refresh(user)
    log.info("platform_user_created", user_id=str(user.id), email=user.email)
    return user


@router.get("/users", response_model=list[UserWithOrgsResponse])
async def list_all_users(
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
) -> list[dict]:
    query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%")
            | User.full_name.ilike(f"%{search}%")
            | User.username.ilike(f"%{search}%")
        )
    users = list((await db.execute(query)).scalars().all())

    user_ids = [u.id for u in users]
    memberships_result = await db.execute(
        select(TenantUser, Tenant)
        .join(Tenant, TenantUser.tenant_id == Tenant.id)
        .where(TenantUser.user_id.in_(user_ids))
    )
    orgs_by_user: dict[uuid.UUID, list[UserOrgMembership]] = {}
    for tu, tenant in memberships_result.all():
        orgs_by_user.setdefault(tu.user_id, []).append(
            UserOrgMembership(tenant_id=tenant.id, tenant_name=tenant.name, role=tu.role)
        )

    return [
        {
            "id": u.id, "email": u.email, "username": u.username, "full_name": u.full_name,
            "is_active": u.is_active, "is_platform_admin": u.is_platform_admin,
            "last_login_at": u.last_login_at, "created_at": u.created_at,
            "organizations": orgs_by_user.get(u.id, []),
        }
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserWithOrgsResponse)
async def platform_get_user(
    user_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    memberships = (await db.execute(
        select(TenantUser, Tenant)
        .join(Tenant, TenantUser.tenant_id == Tenant.id)
        .where(TenantUser.user_id == user_id)
    )).all()
    return {
        "id": user.id, "email": user.email, "username": user.username,
        "full_name": user.full_name, "is_active": user.is_active,
        "is_platform_admin": user.is_platform_admin,
        "last_login_at": user.last_login_at, "created_at": user.created_at,
        "organizations": [
            UserOrgMembership(tenant_id=t.id, tenant_name=t.name, role=tu.role)
            for tu, t in memberships
        ],
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def platform_update_user(
    user_id: uuid.UUID, body: UserUpdate,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if body.username is not None:
        if body.username and (await db.execute(
            select(User).where(User.username == body.username, User.id != user_id)
        )).scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Username '{body.username}' already taken")
        user.username = body.username or None
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/org-assignments", status_code=status.HTTP_201_CREATED)
async def platform_add_user_to_org(
    user_id: uuid.UUID, body: OrgAssignment,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> dict:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    tenant = await db.get(Tenant, body.tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    existing = (await db.execute(
        select(TenantUser).where(TenantUser.tenant_id == body.tenant_id, TenantUser.user_id == user_id)
    )).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this organization")
    try:
        role = TenantRoleEnum(body.role)
    except ValueError:
        role = TenantRoleEnum.org_member
    db.add(TenantUser(tenant_id=body.tenant_id, user_id=user_id, role=role))
    ws_role = WorkspaceRoleEnum.workspace_admin if role == TenantRoleEnum.org_admin else WorkspaceRoleEnum.member
    workspaces = list((await db.execute(
        select(Workspace).where(Workspace.tenant_id == body.tenant_id)
    )).scalars().all())
    for ws in workspaces:
        existing_wu = (await db.execute(
            select(WorkspaceUser).where(WorkspaceUser.workspace_id == ws.id, WorkspaceUser.user_id == user_id)
        )).scalar_one_or_none()
        if existing_wu is None:
            db.add(WorkspaceUser(workspace_id=ws.id, user_id=user_id, role=ws_role))
    await db.commit()
    return {"tenant_id": str(body.tenant_id), "tenant_name": tenant.name, "role": str(role)}


@router.put("/users/{user_id}/org-assignments/{org_id}")
async def platform_update_user_org_role(
    user_id: uuid.UUID, org_id: uuid.UUID, body: OrgAssignment,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> dict:
    tu = (await db.execute(
        select(TenantUser).where(TenantUser.tenant_id == org_id, TenantUser.user_id == user_id)
    )).scalar_one_or_none()
    if tu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of this organization")
    try:
        tu.role = TenantRoleEnum(body.role)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid role: {body.role}")
    await db.commit()
    tenant = await db.get(Tenant, org_id)
    return {"tenant_id": str(org_id), "tenant_name": tenant.name if tenant else "", "role": str(tu.role)}


@router.delete("/users/{user_id}/org-assignments/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_remove_user_from_org(
    user_id: uuid.UUID, org_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep,
) -> None:
    tu = (await db.execute(
        select(TenantUser).where(TenantUser.tenant_id == org_id, TenantUser.user_id == user_id)
    )).scalar_one_or_none()
    if tu is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a member of this organization")
    await db.delete(tu)
    ws_ids = list((await db.execute(
        select(Workspace.id).where(Workspace.tenant_id == org_id)
    )).scalars().all())
    for wu in (await db.execute(
        select(WorkspaceUser).where(WorkspaceUser.user_id == user_id, WorkspaceUser.workspace_id.in_(ws_ids))
    )).scalars().all():
        await db.delete(wu)
    await db.commit()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_delete_user(
    user_id: uuid.UUID,
    auth: Annotated[tuple, Depends(require_platform_admin)], db: DbDep
) -> None:
    _, current_user = auth
    if user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await db.delete(user)
    await db.commit()
