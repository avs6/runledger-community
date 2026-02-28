"""
Settings router — workspace-scoped API key management.

Prefix: /settings
Auth: Bearer API key via get_current_workspace
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.models.tenant import ApiKey, Workspace
from runledger_api.schemas.auth import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from runledger_api.services.auth import generate_api_key

log = structlog.get_logger()

router = APIRouter(prefix="/settings", tags=["settings"])

WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(workspace: WorkspaceDep, db: DbDep) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.workspace_id == workspace.id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreateResponse,
)
async def create_api_key(
    body: ApiKeyCreate, workspace: WorkspaceDep, db: DbDep
) -> dict[str, Any]:
    raw_key, key_hash, key_prefix = generate_api_key(body.environment)
    api_key = ApiKey(
        workspace_id=workspace.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=body.name,
        scopes=body.scopes,
    )
    db.add(api_key)
    await db.flush()
    await db.commit()
    await db.refresh(api_key)
    log.info("api_key_created", key_id=str(api_key.id), workspace_id=str(workspace.id))
    return {
        "id": api_key.id,
        "workspace_id": api_key.workspace_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "created_at": api_key.created_at,
        "key": raw_key,
    }


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: uuid.UUID, workspace: WorkspaceDep, db: DbDep) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    if api_key.workspace_id != workspace.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key belongs to another workspace")
    api_key.revoked_at = datetime.now(UTC)
    await db.commit()
    log.info("api_key_revoked", key_id=str(key_id))
