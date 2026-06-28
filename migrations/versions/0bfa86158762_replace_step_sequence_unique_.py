"""replace step sequence unique constraint with partial index

Revision ID: 0bfa86158762
Revises: 20260628_03
Create Date: 2026-06-28 20:23:19.073599
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0bfa86158762'
down_revision: str | None = '20260628_03'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("steps_plan_id_sequence_key", "steps", type_="unique")

    op.create_index(
        "uq_steps_plan_id_sequence_active",
        "steps",
        ["plan_id", "sequence"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_steps_plan_id_sequence_active", table_name="steps")

    # The old constraint also covers soft-deleted rows. Move those rows beyond
    # the active range so the historical data is preserved during downgrade.
    op.execute(
        sa.text(
            """
            WITH active_max AS (
                SELECT
                    plan_id,
                    COALESCE(MAX(sequence) FILTER (WHERE deleted_at IS NULL), 0)
                        AS max_sequence
                FROM steps
                GROUP BY plan_id
            ),
            deleted_steps AS (
                SELECT
                    id,
                    plan_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY plan_id
                        ORDER BY deleted_at, id
                    ) AS position
                FROM steps
                WHERE deleted_at IS NOT NULL
            )
            UPDATE steps
            SET sequence = active_max.max_sequence + deleted_steps.position
            FROM active_max, deleted_steps
            WHERE steps.id = deleted_steps.id
              AND active_max.plan_id = deleted_steps.plan_id
            """
        )
    )

    op.create_unique_constraint(
        "steps_plan_id_sequence_key",
        "steps",
        ["plan_id", "sequence"],
    )
