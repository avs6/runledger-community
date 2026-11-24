"""W1-G Build: prompt production governance, one experiment system, Playground run link.

- prompts.default_environment / prompt_versions.environment default to 'dev';
  prompts gain a promotion score gate (promotion_min_score, promotion_score_name);
  prompt_versions.approval_id (unique) records the approval behind each production
  version, so an approval authorises exactly one (review B-02, B-03, ENH).
- eval_experiments.mode ('eval' | 'replay'). Replay Lab datasets and experiments are
  copied into eval_datasets / eval_experiments (replay items carry the run's captured
  messages) and the replay_* tables are dropped (review B-07). Migrated experiments
  start 'pending': their old results were cost projections, not runs.
- playground_requests.run_id links a Playground call to the run gateway-rs recorded
  (review B-10).

Revision ID: build_experiments_prompt_gov
Revises: observe_outcomes_views
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "build_experiments_prompt_gov"
down_revision = "observe_outcomes_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Prompts ──────────────────────────────────────────────────────────────
    op.alter_column("prompts", "default_environment", server_default="dev")
    op.add_column("prompts", sa.Column("promotion_min_score", sa.Float, nullable=True))
    op.add_column("prompts", sa.Column("promotion_score_name", sa.Text, nullable=True))
    op.alter_column("prompt_versions", "environment", server_default="dev")
    op.add_column("prompt_versions", sa.Column("approval_id", PGUUID(as_uuid=True), nullable=True))
    op.create_unique_constraint(
        "uq_prompt_versions_approval_id", "prompt_versions", ["approval_id"]
    )

    # ── Experiments ──────────────────────────────────────────────────────────
    op.add_column(
        "eval_experiments",
        sa.Column("mode", sa.String(16), nullable=False, server_default="eval"),
    )

    # Replay Lab → experiments (mode=replay). Each run id becomes an item with the
    # run's first captured messages, so the dataset can be replayed for real.
    op.execute(
        """
        INSERT INTO eval_datasets
            (id, workspace_id, name, description, source, items, item_count,
             created_at, updated_at)
        SELECT
            d.id,
            d.workspace_id,
            d.name,
            'Migrated from Replay Lab',
            'runs',
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_strip_nulls(jsonb_build_object(
                            'run_id', r.rid,
                            'messages', (
                                SELECT s.metadata -> 'messages'
                                FROM spans s
                                WHERE s.run_id::text = r.rid
                                  AND s.metadata ? 'messages'
                                ORDER BY s.started_at
                                LIMIT 1
                            ),
                            'metadata', '{}'::jsonb
                        ))
                    )
                    FROM jsonb_array_elements_text(d.run_ids) AS r(rid)
                ),
                '[]'::jsonb
            ),
            jsonb_array_length(d.run_ids),
            d.created_at,
            d.created_at
        FROM replay_datasets d
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO eval_experiments
            (id, workspace_id, dataset_id, name, description, mode, evaluator_ids,
             models, status, run_count, scores_created, created_at)
        SELECT
            e.id,
            e.workspace_id,
            CASE WHEN EXISTS (SELECT 1 FROM eval_datasets ds WHERE ds.id = e.dataset_id)
                 THEN e.dataset_id END,
            e.name,
            'Migrated from Replay Lab (cost projection only). Run it to replay through the gateway.',
            'replay',
            '[]'::jsonb,
            COALESCE(
                (
                    SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
                        'model', c ->> 'model', 'label', c ->> 'label'
                    )))
                    FROM jsonb_array_elements(e.configs) AS c
                ),
                '[]'::jsonb
            ),
            'pending',
            0,
            0,
            e.created_at
        FROM replay_experiments e
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.drop_table("replay_experiments")
    op.drop_table("replay_datasets")

    # ── Playground ───────────────────────────────────────────────────────────
    op.add_column("playground_requests", sa.Column("run_id", PGUUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("playground_requests", "run_id")

    op.create_table(
        "replay_datasets",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default="live_runs"),
        sa.Column("run_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_replay_datasets_workspace", "replay_datasets", ["workspace_id", "created_at"]
    )
    op.create_table(
        "replay_experiments",
        sa.Column(
            "id",
            PGUUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dataset_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("configs", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("results", JSONB, nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(14, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_replay_experiments_workspace",
        "replay_experiments",
        ["workspace_id", "created_at"],
    )
    # Replay-mode experiments stay in eval_experiments (data is not split back).
    op.drop_column("eval_experiments", "mode")

    op.drop_constraint("uq_prompt_versions_approval_id", "prompt_versions", type_="unique")
    op.drop_column("prompt_versions", "approval_id")
    op.alter_column("prompt_versions", "environment", server_default="production")
    op.drop_column("prompts", "promotion_score_name")
    op.drop_column("prompts", "promotion_min_score")
    op.alter_column("prompts", "default_environment", server_default="production")
