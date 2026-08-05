"""ML model registry — save, load, and list trained model artifacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.ml import MLModel

log = structlog.get_logger()


async def save_model(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    model_type: str,
    dimension: str,
    artifact_bytes: bytes,
    hyperparams: dict[str, Any],
    metrics: dict[str, Any],
    sample_count: int,
    dimension_key: str | None = None,
) -> MLModel:
    """Save a trained model, deactivating any previous version of the same type/dimension."""
    await db.execute(
        update(MLModel)
        .where(
            MLModel.workspace_id == workspace_id,
            MLModel.model_type == model_type,
            MLModel.dimension == dimension,
            MLModel.dimension_key == dimension_key if dimension_key else MLModel.dimension_key.is_(None),
            MLModel.is_active.is_(True),
        )
        .values(is_active=False)
    )

    max_version = await db.scalar(
        select(func.coalesce(func.max(MLModel.version), 0)).where(
            MLModel.workspace_id == workspace_id,
            MLModel.model_type == model_type,
            MLModel.dimension == dimension,
            MLModel.dimension_key == dimension_key if dimension_key else MLModel.dimension_key.is_(None),
        )
    )

    model = MLModel(
        workspace_id=workspace_id,
        model_type=model_type,
        dimension=dimension,
        dimension_key=dimension_key,
        version=(max_version or 0) + 1,
        artifact=artifact_bytes,
        hyperparams=hyperparams,
        metrics=metrics,
        sample_count=sample_count,
        trained_at=datetime.now(UTC),
        is_active=True,
    )
    db.add(model)
    await db.flush()
    log.info("ml_model_saved", model_type=model_type, dimension=dimension, version=model.version)
    return model


async def load_model(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    model_type: str,
    dimension: str,
    dimension_key: str | None = None,
) -> MLModel | None:
    """Load the active model artifact for a given type/dimension."""
    where = [
        MLModel.workspace_id == workspace_id,
        MLModel.model_type == model_type,
        MLModel.dimension == dimension,
        MLModel.is_active.is_(True),
    ]
    if dimension_key is not None:
        where.append(MLModel.dimension_key == dimension_key)
    else:
        where.append(MLModel.dimension_key.is_(None))

    result = await db.execute(select(MLModel).where(and_(*where)).limit(1))
    return result.scalar_one_or_none()


async def list_models(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    active_only: bool = True,
) -> list[MLModel]:
    """List all models for a workspace."""
    where = [MLModel.workspace_id == workspace_id]
    if active_only:
        where.append(MLModel.is_active.is_(True))
    result = await db.execute(
        select(MLModel).where(and_(*where)).order_by(MLModel.model_type, MLModel.dimension)
    )
    return list(result.scalars().all())
