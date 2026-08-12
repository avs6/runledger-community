"""
AI Hub Model Catalog API.

Prefix: /hub
Auth: Bearer API key (workspace-scoped)

Endpoints
---------
POST   /hub/models                 Add model to catalog
GET    /hub/models                 List catalog models
GET    /hub/models/{id}            Get model card
PUT    /hub/models/{id}            Update model card
DELETE /hub/models/{id}            Remove from catalog
POST   /hub/models/{id}/request-access   Request access to a model
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import get_current_workspace
from runledger_api.core.ratelimit import analytics_rate_limit, management_rate_limit
from runledger_api.models.hub import HubModel
from runledger_api.models.tenant import Workspace
from runledger_api.schemas.hub import (
    HubModelCreate,
    HubModelList,
    HubModelResponse,
    HubModelUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/hub", tags=["hub"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
WorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


def _to_response(m: HubModel) -> HubModelResponse:
    return HubModelResponse(
        id=m.id, workspace_id=m.workspace_id, name=m.name, provider=m.provider,
        description=m.description, capabilities=m.capabilities or [],
        context_window=m.context_window, input_cost_per_1k=m.input_cost_per_1k,
        output_cost_per_1k=m.output_cost_per_1k, tags=m.tags or [],
        is_featured=m.is_featured, is_deprecated=m.is_deprecated,
        deprecation_notice=m.deprecation_notice, is_public=m.is_public,
        access_request_count=m.access_request_count, created_at=m.created_at,
        updated_at=m.updated_at,
    )


@router.post("/models", response_model=HubModelResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(management_rate_limit)])
async def add_model(body: HubModelCreate, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = HubModel(
        id=uuid.uuid4(), workspace_id=ws.id, name=body.name, provider=body.provider,
        description=body.description, capabilities=body.capabilities,
        context_window=body.context_window, input_cost_per_1k=body.input_cost_per_1k,
        output_cost_per_1k=body.output_cost_per_1k, tags=body.tags,
        is_featured=body.is_featured, is_public=body.is_public,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _to_response(m)


@router.get("/models", response_model=HubModelList, dependencies=[Depends(analytics_rate_limit)])
async def list_models(
    ws: WorkspaceDep, db: DbDep,
    featured_only: bool = False,
    provider: str | None = None,
    tag: str | None = None,
) -> HubModelList:
    q = select(HubModel).where(HubModel.workspace_id == ws.id, HubModel.is_public.is_(True))
    if featured_only:
        q = q.where(HubModel.is_featured.is_(True))
    if provider:
        q = q.where(HubModel.provider == provider)
    q = q.order_by(HubModel.is_featured.desc(), HubModel.name)
    rows = (await db.execute(q)).scalars().all()
    items = [_to_response(m) for m in rows]
    if tag:
        items = [i for i in items if tag in (i.tags or [])]
    return HubModelList(items=items)


@router.get("/models/{model_id}", response_model=HubModelResponse,
            dependencies=[Depends(analytics_rate_limit)])
async def get_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    return _to_response(m)


@router.put("/models/{model_id}", response_model=HubModelResponse,
            dependencies=[Depends(management_rate_limit)])
async def update_model(model_id: uuid.UUID, body: HubModelUpdate, ws: WorkspaceDep, db: DbDep) -> HubModelResponse:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    m.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(m)
    return _to_response(m)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(management_rate_limit)])
async def remove_model(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> None:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    await db.delete(m)
    await db.commit()


@router.post("/models/{model_id}/request-access", dependencies=[Depends(management_rate_limit)])
async def request_access(model_id: uuid.UUID, ws: WorkspaceDep, db: DbDep) -> dict:
    m = (await db.execute(
        select(HubModel).where(HubModel.id == model_id, HubModel.workspace_id == ws.id)
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    m.access_request_count = (m.access_request_count or 0) + 1
    await db.commit()
    return {"status": "requested", "model_id": str(model_id), "total_requests": m.access_request_count}


class ProviderSyncRequest(BaseModel):
    provider: str
    token: str | None = None
    endpoint_url: str | None = None


DEFAULT_PROVIDER_MODELS: dict[str, list[dict]] = {
    "huggingface": [
        {"name": "meta-llama/Llama-3.3-70B-Instruct", "description": "State-of-the-art 70B open weight LLM by Meta", "context_window": 128000, "input_cost": 0.0007, "output_cost": 0.0009, "tags": ["huggingface", "open-weights", "llama3"]},
        {"name": "deepseek-ai/DeepSeek-R1", "description": "Reasoning open model by DeepSeek AI", "context_window": 64000, "input_cost": 0.00055, "output_cost": 0.00219, "tags": ["huggingface", "reasoning", "deepseek"]},
        {"name": "mistralai/Mistral-7B-Instruct-v0.3", "description": "High efficiency 7B instruction model", "context_window": 32768, "input_cost": 0.0001, "output_cost": 0.0002, "tags": ["huggingface", "mistral", "fast"]},
        {"name": "Qwen/Qwen2.5-Coder-32B-Instruct", "description": "Specialized coding open model by Alibaba Qwen", "context_window": 131072, "input_cost": 0.0003, "output_cost": 0.0006, "tags": ["huggingface", "code", "qwen"]},
        {"name": "google/gemma-2-27b-it", "description": "Lightweight open model family by Google", "context_window": 8192, "input_cost": 0.00027, "output_cost": 0.00027, "tags": ["huggingface", "gemma", "google"]},
    ],
    "openai": [
        {"name": "gpt-4o", "description": "Flagship multimodal LLM by OpenAI", "context_window": 128000, "input_cost": 0.0025, "output_cost": 0.01, "tags": ["openai", "multimodal", "flagship"]},
        {"name": "gpt-4o-mini", "description": "Fast, affordable small model by OpenAI", "context_window": 128000, "input_cost": 0.00015, "output_cost": 0.0006, "tags": ["openai", "fast", "cheap"]},
        {"name": "o3-mini", "description": "High speed reasoning model by OpenAI", "context_window": 200000, "input_cost": 0.0011, "output_cost": 0.0044, "tags": ["openai", "reasoning"]},
    ],
    "anthropic": [
        {"name": "claude-3-5-sonnet-20241022", "description": "State-of-the-art intelligent model by Anthropic", "context_window": 200000, "input_cost": 0.003, "output_cost": 0.015, "tags": ["anthropic", "sonnet", "flagship"]},
        {"name": "claude-3-5-haiku-20241022", "description": "Blazing fast lightweight model by Anthropic", "context_window": 200000, "input_cost": 0.0008, "output_cost": 0.004, "tags": ["anthropic", "haiku", "fast"]},
    ],
    "ollama": [
        {"name": "ollama/llama3.2", "description": "Local Llama 3.2 instance via Ollama", "context_window": 131072, "input_cost": 0.0, "output_cost": 0.0, "tags": ["ollama", "local"]},
        {"name": "ollama/deepseek-r1:14b", "description": "Local DeepSeek R1 14B instance via Ollama", "context_window": 64000, "input_cost": 0.0, "output_cost": 0.0, "tags": ["ollama", "local", "reasoning"]},
    ],
}


@router.post("/sync-provider", dependencies=[Depends(management_rate_limit)])
async def sync_provider_models(body: ProviderSyncRequest, ws: WorkspaceDep, db: DbDep) -> dict:
    p_key = body.provider.lower().strip()
    model_templates = DEFAULT_PROVIDER_MODELS.get(p_key, [])

    if p_key == "huggingface" and body.token:
        try:
            import httpx  # noqa: PLC0415
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://huggingface.co/api/models",
                    headers={"Authorization": f"Bearer {body.token}"},
                    params={"sort": "downloads", "direction": "-1", "limit": 8, "filter": "text-generation"},
                )
                if res.status_code == 200:
                    hf_items = res.json()
                    live_templates = []
                    for hfm in hf_items:
                        m_id = hfm.get("modelId", "")
                        if m_id:
                            live_templates.append({
                                "name": m_id,
                                "description": f"Hugging Face model {m_id} (downloads: {hfm.get('downloads', 0)})",
                                "context_window": 32768,
                                "input_cost": 0.0005,
                                "output_cost": 0.0005,
                                "tags": ["huggingface", "live-sync"],
                            })
                    if live_templates:
                        model_templates = live_templates
        except Exception as err:
            log.warning("hf_hub_sync_failed", error=str(err))

    added_count = 0
    for tpl in model_templates:
        existing = (await db.execute(
            select(HubModel).where(HubModel.workspace_id == ws.id, HubModel.name == tpl["name"])
        )).scalar_one_or_none()
        if not existing:
            m = HubModel(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                name=tpl["name"],
                provider=p_key,
                description=tpl.get("description"),
                context_window=tpl.get("context_window"),
                input_cost_per_1k=tpl.get("input_cost"),
                output_cost_per_1k=tpl.get("output_cost"),
                tags=tpl.get("tags", []),
                is_featured=True,
                is_public=True,
            )
            db.add(m)
            added_count += 1

    await db.commit()
    return {"status": "synced", "provider": p_key, "models_added": added_count, "total_templates": len(model_templates)}
