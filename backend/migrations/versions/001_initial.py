"""Initial schema migration.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("client_slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("preset", sa.String(50), nullable=True),
        sa.Column("vertical", sa.String(50), nullable=True),
        sa.Column("brief_json", sa.Text(), nullable=True),
        sa.Column("plan_json", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("external_key", sa.String(300), nullable=False),
        sa.Column("campaign_name", sa.String(300), nullable=False),
        sa.Column("campaign_type", sa.String(50), nullable=False),
        sa.Column("language_code", sa.String(10), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("budget_daily", sa.Float(), nullable=True),
        sa.Column("can_publish", sa.Boolean(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("google_ads_campaign_id", sa.String(50), nullable=True),
        sa.Column("plan_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "exports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("export_type", sa.String(50), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("is_dry_run", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("exports")
    op.drop_table("campaigns")
    op.drop_table("projects")
    op.drop_table("users")
