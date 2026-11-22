"""OTLP metrics: daily rollups per metric series.

Revision ID: 092_otlp_metric_rollups
Revises: 091_ingestion_hardening
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "092_otlp_metric_rollups"
down_revision = "091_ingestion_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "otlp_metric_rollups",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("series_key", sa.String(40), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("temporality", sa.String(16), nullable=True),
        sa.Column("service_name", sa.String(128), nullable=True),
        sa.Column("attributes", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("points", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total", sa.Float, nullable=True),
        sa.Column("observations", sa.BigInteger, nullable=True),
        sa.Column("min_value", sa.Float, nullable=True),
        sa.Column("max_value", sa.Float, nullable=True),
        sa.Column("last_value", sa.Float, nullable=True),
        sa.Column("cumulative_value", sa.Float, nullable=True),
        sa.Column("cumulative_count", sa.BigInteger, nullable=True),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "series_key", "day", name="uq_otlp_metric_rollups_series_day"
        ),
    )
    op.create_index("ix_otlp_metric_rollups_ws_day", "otlp_metric_rollups", ["workspace_id", "day"])
    op.create_index(
        "ix_otlp_metric_rollups_ws_name", "otlp_metric_rollups", ["workspace_id", "name", "day"]
    )


def downgrade() -> None:
    op.drop_index("ix_otlp_metric_rollups_ws_name", table_name="otlp_metric_rollups")
    op.drop_index("ix_otlp_metric_rollups_ws_day", table_name="otlp_metric_rollups")
    op.drop_table("otlp_metric_rollups")
