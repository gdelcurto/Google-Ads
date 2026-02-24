"""Add project_permissions table for per-user per-project access control.

Revision ID: 005
Revises: 004
Create Date: 2026-02-24 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "project_permissions" not in insp.get_table_names():
        op.create_table(
            "project_permissions",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("all_projects", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("can_read", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("can_write", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("tab_overview", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_campaigns", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_preview", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_brief", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_action_plan", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_plan_json", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_audit", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_scan_log", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("tab_api_log", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_project_permissions_user_id", "project_permissions", ["user_id"])
        op.create_index("ix_project_permissions_project_id", "project_permissions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_permissions_project_id", table_name="project_permissions")
    op.drop_index("ix_project_permissions_user_id", table_name="project_permissions")
    op.drop_table("project_permissions")
