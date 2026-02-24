"""Add tab_budget_log column to project_permissions.

Revision ID: 006
Revises: 005
Create Date: 2026-02-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing = {c["name"] for c in insp.get_columns("project_permissions")}
    if "tab_budget_log" not in existing:
        op.add_column(
            "project_permissions",
            sa.Column("tab_budget_log", sa.Boolean(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_column("project_permissions", "tab_budget_log")
