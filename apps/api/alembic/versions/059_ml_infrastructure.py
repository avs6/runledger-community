"""Add ML intelligence layer — model registry, feature store, anomalies, forecasts, patterns.

Revision ID: 059
Revises: 058
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ML model registry
    op.create_table(
        "ml_models",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("model_type", sa.String(32), nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("artifact", sa.LargeBinary, nullable=True),
        sa.Column("hyperparams", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metrics", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("trained_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_ml_models_workspace_type", "ml_models", ["workspace_id", "model_type", "dimension", "is_active"])

    # ML feature store (daily aggregates)
    op.create_table(
        "ml_features_daily",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("feature_date", sa.Date, nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=True),
        sa.Column("features", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_ml_features_ws_dim_date", "ml_features_daily", ["workspace_id", "dimension", "feature_date"])
    op.create_unique_constraint("uq_ml_features_daily", "ml_features_daily", ["workspace_id", "feature_date", "dimension", "dimension_key"])

    # ML anomalies
    op.create_table(
        "ml_anomalies",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_type", sa.String(32), nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=True),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("detection_method", sa.String(32), nullable=False),
        sa.Column("current_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("expected_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("deviation_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("context", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_suppressed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("suppressed_reason", sa.String(128), nullable=True),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_ml_anomalies_ws_type_date", "ml_anomalies", ["workspace_id", "anomaly_type", "detected_at"])

    # ML forecasts
    op.create_table(
        "ml_forecasts",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("forecast_type", sa.String(32), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=True),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("horizon_days", sa.Integer, nullable=False),
        sa.Column("forecast_from", sa.Date, nullable=False),
        sa.Column("points", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("accuracy_metrics", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("model_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_ml_forecasts_ws_type", "ml_forecasts", ["workspace_id", "forecast_type", "created_at"])

    # ML patterns
    op.create_table(
        "ml_patterns",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(64), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=True),
        sa.Column("pattern", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("evidence", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_ml_patterns_ws", "ml_patterns", ["workspace_id", "dimension", "detected_at"])

    # Forecast accuracy tracking
    op.create_table(
        "forecast_accuracy_tracking",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("forecast_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("predicted_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("actual_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("absolute_error", sa.Numeric(14, 6), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_forecast_accuracy_ws_date", "forecast_accuracy_tracking", ["workspace_id", "target_date"])


def downgrade() -> None:
    op.drop_table("forecast_accuracy_tracking")
    op.drop_table("ml_patterns")
    op.drop_table("ml_forecasts")
    op.drop_table("ml_anomalies")
    op.drop_table("ml_features_daily")
    op.drop_table("ml_models")
