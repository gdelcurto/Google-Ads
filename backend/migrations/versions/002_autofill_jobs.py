"""Add autofill_jobs staging table for background auto-fill jobs.

Revision ID: 002
Revises: 001
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "autofill_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("languages_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autofill_jobs_project_id", "autofill_jobs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_autofill_jobs_project_id", table_name="autofill_jobs")
    op.drop_table("autofill_jobs")
