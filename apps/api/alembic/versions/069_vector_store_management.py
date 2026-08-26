"""Add vector store management tables.

Revision ID: 069
Revises: 068
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vector_store_collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("qdrant_collection", sa.Text, nullable=False),
        sa.Column("embedding_model", sa.Text, nullable=True),
        sa.Column("dimensions", sa.Integer, nullable=True),
        sa.Column("distance_metric", sa.Text, nullable=False, server_default=sa.text("'cosine'")),
        sa.Column("document_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("size_bytes", sa.BigInteger, nullable=False, server_default=sa.text("0")),
        sa.Column("total_queries", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "total_query_cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
        ),
        sa.Column(
            "total_embed_cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")
        ),
        sa.Column("status", sa.Text, nullable=False, server_default=sa.text("'active'")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_queried_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_vector_collections_workspace", "vector_store_collections", ["workspace_id"])
    op.create_index(
        "ix_vector_collections_workspace_name",
        "vector_store_collections",
        ["workspace_id", "name"],
        unique=True,
    )

    op.create_table(
        "vector_store_queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("top_k", sa.Integer, nullable=False, server_default=sa.text("5")),
        sa.Column("threshold", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("result_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("best_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("embed_cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")),
        sa.Column("query_cost", sa.Numeric(precision=12, scale=6), server_default=sa.text("0")),
        sa.Column("results", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_vector_queries_workspace", "vector_store_queries", ["workspace_id"])
    op.create_index("ix_vector_queries_collection", "vector_store_queries", ["collection_id"])


def downgrade() -> None:
    op.drop_table("vector_store_queries")
    op.drop_table("vector_store_collections")
