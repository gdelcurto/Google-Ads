"""Add clients and hotels tables; add client_id / hotel_id to projects.

Revision ID: 008
Revises: 007
Create Date: 2026-02-25 00:00:00.000000

NOTE: idempotent — safe to run even if create_all already created the tables
(e.g. when deploying new code where ORM models loaded before migrations ran).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # ── clients ───────────────────────────────────────────────────────────────
    if "clients" not in existing_tables:
        op.create_table(
            "clients",
            sa.Column("id",            sa.String(),      nullable=False),
            sa.Column("name",          sa.String(200),   nullable=False),
            sa.Column("bb_client_id",  sa.String(100),   nullable=True),
            sa.Column("agency",        sa.String(200),   nullable=True),
            sa.Column("contact_email", sa.String(200),   nullable=True),
            sa.Column("contact_phone", sa.String(100),   nullable=True),
            sa.Column("notes",         sa.Text(),        nullable=True),
            sa.Column("owner_id",      sa.String(),      nullable=False),
            sa.Column("created_at",    sa.DateTime(),    nullable=True),
            sa.Column("updated_at",    sa.DateTime(),    nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── hotels ────────────────────────────────────────────────────────────────
    if "hotels" not in existing_tables:
        op.create_table(
            "hotels",
            sa.Column("id",               sa.String(),      nullable=False),
            sa.Column("client_id",        sa.String(),      nullable=False),
            sa.Column("name",             sa.String(200),   nullable=False),
            sa.Column("bb_hotel_id",      sa.String(100),   nullable=True),
            sa.Column("category",         sa.String(50),    nullable=True),
            sa.Column("stars",            sa.Integer(),     nullable=True),
            sa.Column("address",          sa.String(500),   nullable=True),
            sa.Column("city",             sa.String(200),   nullable=True),
            sa.Column("country",          sa.String(200),   nullable=True),
            sa.Column("country_code",     sa.String(10),    nullable=True),
            sa.Column("lat",              sa.Float(),       nullable=True),
            sa.Column("lng",              sa.Float(),       nullable=True),
            sa.Column("website_url",      sa.String(1000),  nullable=True),
            sa.Column("booking_engine",   sa.String(100),   nullable=True),
            sa.Column("property_type",    sa.String(100),   nullable=True),
            sa.Column("adr",              sa.Float(),       nullable=True),
            sa.Column("seasonality_json", sa.Text(),        nullable=True),
            sa.Column("scraped_json",     sa.Text(),        nullable=True),
            sa.Column("scraped_at",       sa.DateTime(),    nullable=True),
            sa.Column("created_at",       sa.DateTime(),    nullable=True),
            sa.Column("updated_at",       sa.DateTime(),    nullable=True),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # ── FK columns on projects (nullable — existing rows have no link yet) ────
    existing_project_cols = {c["name"] for c in insp.get_columns("projects")}

    if "client_id" not in existing_project_cols:
        op.add_column("projects", sa.Column("client_id", sa.String(), nullable=True))
        with op.batch_alter_table("projects") as batch_op:
            batch_op.create_foreign_key(
                "fk_projects_client_id", "clients", ["client_id"], ["id"]
            )

    if "hotel_id" not in existing_project_cols:
        op.add_column("projects", sa.Column("hotel_id", sa.String(), nullable=True))
        with op.batch_alter_table("projects") as batch_op:
            batch_op.create_foreign_key(
                "fk_projects_hotel_id", "hotels", ["hotel_id"], ["id"]
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "projects" in existing_tables:
        existing_project_cols = {c["name"] for c in insp.get_columns("projects")}
        with op.batch_alter_table("projects") as batch_op:
            if "hotel_id" in existing_project_cols:
                batch_op.drop_constraint("fk_projects_hotel_id", type_="foreignkey")
                batch_op.drop_column("hotel_id")
            if "client_id" in existing_project_cols:
                batch_op.drop_constraint("fk_projects_client_id", type_="foreignkey")
                batch_op.drop_column("client_id")

    if "hotels" in existing_tables:
        op.drop_table("hotels")
    if "clients" in existing_tables:
        op.drop_table("clients")
