"""Gateway runtime attribution and a single cache profile per workspace.

* ``gateway_requests`` and ``guardrail_events`` get ``run_id``, ``api_key_id`` and
  ``workflow`` so a gateway call, its guardrail checks and its run are joined by key
  instead of by a time-window heuristic (review G-19, O-12).
* ``response_cache_configs`` becomes one profile per workspace (review G-09): duplicates
  are folded into the oldest row (counters summed), then a unique index is added.

Revision ID: gateway_runtime_attribution
Revises: 095_ip_acl_access_groups
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "gateway_runtime_attribution"
down_revision = "095_ip_acl_access_groups"
branch_labels = None
depends_on = None


def _add_attribution(table: str) -> None:
    op.add_column(table, sa.Column("run_id", PGUUID(as_uuid=True), nullable=True))
    op.add_column(table, sa.Column("api_key_id", PGUUID(as_uuid=True), nullable=True))
    op.add_column(table, sa.Column("workflow", sa.Text, nullable=True))
    op.create_index(f"ix_{table}_run", table, ["run_id"])
    op.create_index(f"ix_{table}_workflow", table, ["workspace_id", "workflow", "created_at"])


def upgrade() -> None:
    _add_attribution("gateway_requests")
    _add_attribution("guardrail_events")
    op.create_index(
        "ix_guardrail_events_gateway_request", "guardrail_events", ["gateway_request_id"]
    )

    # One cache profile per workspace: keep the oldest, fold the others' counters into it.
    op.execute(
        """
        WITH ranked AS (
            SELECT id, workspace_id,
                   row_number() OVER (PARTITION BY workspace_id ORDER BY created_at, id) AS rn
            FROM response_cache_configs
        ),
        totals AS (
            SELECT workspace_id,
                   SUM(COALESCE(total_hits, 0)) AS hits,
                   SUM(COALESCE(total_misses, 0)) AS misses,
                   SUM(COALESCE(total_savings_usd, 0)) AS savings
            FROM response_cache_configs
            GROUP BY workspace_id
            HAVING COUNT(*) > 1
        )
        UPDATE response_cache_configs c
        SET total_hits = t.hits, total_misses = t.misses, total_savings_usd = t.savings
        FROM ranked r JOIN totals t ON t.workspace_id = r.workspace_id
        WHERE c.id = r.id AND r.rn = 1
        """
    )
    op.execute(
        """
        DELETE FROM response_cache_configs c
        USING (
            SELECT id, row_number() OVER (PARTITION BY workspace_id ORDER BY created_at, id) AS rn
            FROM response_cache_configs
        ) r
        WHERE c.id = r.id AND r.rn > 1
        """
    )
    op.create_index(
        "uq_response_cache_configs_workspace",
        "response_cache_configs",
        ["workspace_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_response_cache_configs_workspace", table_name="response_cache_configs")
    op.drop_index("ix_guardrail_events_gateway_request", table_name="guardrail_events")
    for table in ("guardrail_events", "gateway_requests"):
        op.drop_index(f"ix_{table}_workflow", table_name=table)
        op.drop_index(f"ix_{table}_run", table_name=table)
        op.drop_column(table, "workflow")
        op.drop_column(table, "api_key_id")
        op.drop_column(table, "run_id")
