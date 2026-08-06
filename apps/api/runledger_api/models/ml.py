"""ORM models for the ML intelligence layer — model registry, features, anomalies, forecasts, patterns."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class MLModel(Base):
    """Trained ML model artifact stored per workspace."""

    __tablename__ = "ml_models"
    __table_args__ = (
        sa.Index(
            "ix_ml_models_workspace_type", "workspace_id", "model_type", "dimension", "is_active"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    model_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    dimension_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    artifact: Mapped[bytes | None] = mapped_column(sa.LargeBinary, nullable=True)
    hyperparams: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    sample_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    trained_at: Mapped[datetime | None] = mapped_column(sa.TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class MLFeatureDaily(Base):
    """Pre-computed daily feature vector per workspace per dimension."""

    __tablename__ = "ml_features_daily"
    __table_args__ = (
        sa.Index("ix_ml_features_ws_dim_date", "workspace_id", "dimension", "feature_date"),
        sa.UniqueConstraint(
            "workspace_id",
            "feature_date",
            "dimension",
            "dimension_key",
            name="uq_ml_features_daily",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    feature_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    dimension: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    dimension_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class MLAnomaly(Base):
    """Detected anomaly in cost, latency, error rate, or other metrics."""

    __tablename__ = "ml_anomalies"
    __table_args__ = (
        sa.Index("ix_ml_anomalies_ws_type_date", "workspace_id", "anomaly_type", "detected_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    anomaly_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    dimension_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    severity: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'medium'")
    )
    detection_method: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    expected_value: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    deviation_score: Mapped[Decimal] = mapped_column(sa.Numeric(8, 4), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    is_suppressed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    suppressed_reason: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    correlation_group_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        sa.TIMESTAMP(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class MLForecast(Base):
    """Stored forecast result with point predictions and confidence intervals."""

    __tablename__ = "ml_forecasts"
    __table_args__ = (
        sa.Index("ix_ml_forecasts_ws_type", "workspace_id", "forecast_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    forecast_type: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    dimension_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    method: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    horizon_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    forecast_from: Mapped[date] = mapped_column(sa.Date, nullable=False)
    points: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'[]'")
    )
    accuracy_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class MLPattern(Base):
    """Classified usage pattern per dimension (steady, growing, declining, spiky, seasonal, one_shot)."""

    __tablename__ = "ml_patterns"
    __table_args__ = (sa.Index("ix_ml_patterns_ws", "workspace_id", "dimension", "detected_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dimension: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    dimension_key: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    pattern: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(sa.Numeric(4, 3), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'")
    )
    detected_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )


class ForecastAccuracy(Base):
    """Tracks forecast accuracy by comparing predicted vs actual values."""

    __tablename__ = "forecast_accuracy_tracking"
    __table_args__ = (sa.Index("ix_forecast_accuracy_ws_date", "workspace_id", "target_date"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    forecast_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    target_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    predicted_value: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    actual_value: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    absolute_error: Mapped[Decimal] = mapped_column(sa.Numeric(14, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
