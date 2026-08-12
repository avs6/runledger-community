"""
Projects and Team Models API.

Prefix: /projects, /team-models
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /projects                          Create project
GET    /projects                          List projects
GET    /projects/{id}                     Get project
PUT    /projects/{id}                     Update project
DELETE /projects/{id}                     Delete (deactivate) project
POST   /projects/{id}/keys               Assign key to project
GET    /projects/{id}/keys               List keys in project
DELETE /projects/{id}/keys/{key_id}      Remove key from project

POST   /team-models                      Add team model
GET    /team-models                      List team models
GET    /team-models/{id}                 Get team model
PUT    /team-models/{id}                 Update team model
DELETE /team-models/{id}                 Remove team model
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace, require_workspace_admin
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.projects import Project, ProjectKey, TeamModel
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.projects import (
    ProjectCreate,
    ProjectKeyAssign,
    ProjectKeyList,
    ProjectKeyResponse,
    ProjectList,
    ProjectResponse,
    ProjectUpdate,
    TeamModelCreate,
    TeamModelList,
    TeamModelResponse,
    TeamModelUpdate,
)

log = structlog.get_logger()

project_router = APIRouter(prefix="/projects", tags=["projects"])
team_model_router = APIRouter(prefix="/team-models", tags=["team-models"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


async def _project_key_count(db: AsyncSession, project_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).where(ProjectKey.project_id == project_id)
    )
    return result.scalar() or 0


def _project_to_response(p: Project, key_count: int = 0) -> ProjectResponse:
    return ProjectResponse(
        id=p.id, workspace_id=p.workspace_id, name=p.name, description=p.description,
        owner=p.owner, budget_usd=p.budget_usd, budget_period=p.budget_period,
        is_active=p.is_active, config=p.config or {}, key_count=key_count,
        created_at=p.created_at, updated_at=p.updated_at,
    )


# ── Projects ─────────────────────────────────────────────────────────────────


@project_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED,
                     dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def create_project(body: ProjectCreate, ws: WorkspaceDep, db: DbDep) -> ProjectResponse:
    p = Project(
        id=uuid.uuid4(), workspace_id=ws.id, name=body.name, description=body.description,
        owner=body.owner, budget_usd=body.budget_usd, budget_period=body.budget_period,
        config=body.config,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _project_to_response(p)


@project_router.get("", response_model=ProjectList, dependencies=[Depends(analytics_rate_limit)])
async def list_projects(ws: WorkspaceDep, db: DbDep, include_inactive: bool = False) -> ProjectList:
    q = select(Project).where(Project.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(Project.is_active.is_(True))
    q = q.order_by(Project.name)
    rows = (await db.execute(q)).scalars().all()
    items = []
    for p in rows:
        kc = await _project_key_count(db, p.id)
        items.append(_project_to_response(p, kc))
    return ProjectList(items=items)


@project_router.get("/{project_id}", response_model=ProjectResponse,
                    dependencies=[Depends(analytics_rate_limit)])
async def get_project(project_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> ProjectResponse:
    p = (await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    kc = await _project_key_count(db, p.id)
    return _project_to_response(p, kc)


@project_router.put("/{project_id}", response_model=ProjectResponse,
                    dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def update_project(project_id: uuid.UUID, body: ProjectUpdate, ws: WorkspaceDep, db: DbDep) -> ProjectResponse:
    p = (await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(p)
    kc = await _project_key_count(db, p.id)
    return _project_to_response(p, kc)


@project_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
                       dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def delete_project(project_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    await db.execute(
        update(Project)
        .where(Project.id == project_id, Project.workspace_id == ws.id)
        .values(is_active=False, updated_at=datetime.now(UTC))
    )
    await db.commit()


@project_router.post("/{project_id}/keys", response_model=ProjectKeyResponse,
                     status_code=status.HTTP_201_CREATED, dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def assign_key(project_id: uuid.UUID, body: ProjectKeyAssign, ws: WorkspaceDep, db: DbDep) -> ProjectKeyResponse:
    p = (await db.execute(
        select(Project).where(Project.id == project_id, Project.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    pk = ProjectKey(id=uuid.uuid4(), project_id=project_id, api_key_id=body.api_key_id)
    db.add(pk)
    await db.commit()
    await db.refresh(pk)
    return ProjectKeyResponse(id=pk.id, project_id=pk.project_id, api_key_id=pk.api_key_id, created_at=pk.created_at)


@project_router.get("/{project_id}/keys", response_model=ProjectKeyList,
                    dependencies=[Depends(analytics_rate_limit)])
async def list_keys(project_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> ProjectKeyList:
    rows = (await db.execute(
        select(ProjectKey).where(ProjectKey.project_id == project_id)
    )).scalars().all()
    return ProjectKeyList(items=[ProjectKeyResponse(
        id=pk.id, project_id=pk.project_id, api_key_id=pk.api_key_id, created_at=pk.created_at,
    ) for pk in rows])


@project_router.delete("/{project_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT,
                       dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def remove_key(project_id: uuid.UUID, key_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    pk = (await db.execute(
        select(ProjectKey).where(ProjectKey.project_id == project_id, ProjectKey.api_key_id == key_id)
    )).scalar_one_or_none()
    if not pk:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not assigned to project")
    await db.delete(pk)
    await db.commit()


# ── Team Models ──────────────────────────────────────────────────────────────


def _team_to_response(m: TeamModel) -> TeamModelResponse:
    return TeamModelResponse(
        id=m.id, workspace_id=m.workspace_id, team_name=m.team_name,
        model_name=m.model_name, provider=m.provider, api_base_url=m.api_base_url,
        description=m.description, budget_usd=m.budget_usd, budget_period=m.budget_period,
        is_active=m.is_active, logging_opt_out=m.logging_opt_out, health_status=m.health_status,
        last_health_check=m.last_health_check, total_calls=m.total_calls,
        total_cost_usd=m.total_cost_usd, config=m.config or {},
        created_at=m.created_at, updated_at=m.updated_at,
    )


@team_model_router.post("", response_model=TeamModelResponse, status_code=status.HTTP_201_CREATED,
                        dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def add_team_model(body: TeamModelCreate, ws: WorkspaceDep, db: DbDep) -> TeamModelResponse:
    m = TeamModel(
        id=uuid.uuid4(), workspace_id=ws.id, team_name=body.team_name,
        model_name=body.model_name, provider=body.provider, api_base_url=body.api_base_url,
        description=body.description, budget_usd=body.budget_usd,
        budget_period=body.budget_period, logging_opt_out=body.logging_opt_out, config=body.config,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _team_to_response(m)


@team_model_router.get("", response_model=TeamModelList, dependencies=[Depends(analytics_rate_limit)])
async def list_team_models(
    ws: WorkspaceDep, db: DbDep,
    team_name: str | None = None,
    include_inactive: bool = False,
) -> TeamModelList:
    q = select(TeamModel).where(TeamModel.workspace_id == ws.id)
    if not include_inactive:
        q = q.where(TeamModel.is_active.is_(True))
    if team_name:
        q = q.where(TeamModel.team_name == team_name)
    q = q.order_by(TeamModel.team_name, TeamModel.model_name)
    rows = (await db.execute(q)).scalars().all()
    return TeamModelList(items=[_team_to_response(m) for m in rows])


@team_model_router.get("/{model_id}", response_model=TeamModelResponse,
                       dependencies=[Depends(analytics_rate_limit)])
async def get_team_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> TeamModelResponse:
    m = (await db.execute(
        select(TeamModel).where(TeamModel.id == model_id, TeamModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team model not found")
    return _team_to_response(m)


@team_model_router.put("/{model_id}", response_model=TeamModelResponse,
                       dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def update_team_model(model_id: uuid.UUID, body: TeamModelUpdate, ws: WorkspaceDep, db: DbDep) -> TeamModelResponse:
    m = (await db.execute(
        select(TeamModel).where(TeamModel.id == model_id, TeamModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team model not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    m.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(m)
    return _team_to_response(m)


@team_model_router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT,
                          dependencies=[Depends(management_rate_limit), Depends(require_workspace_admin)])
async def remove_team_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    await db.execute(
        update(TeamModel)
        .where(TeamModel.id == model_id, TeamModel.workspace_id == ws.id)
        .values(is_active=False, updated_at=datetime.now(UTC))
    )
    await db.commit()
