"""Add scraped_json column to autofill_jobs for website data caching.

Stores the raw scraped content (text + lang_urls + lang_landings) so
briefs can be regenerated from cached data without re-scraping or
re-calling the AI enrichment API.

Revision ID: 004
Revises: 003
Create Date: 2026-02-23 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "autofill_jobs",
        sa.Column("scraped_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("autofill_jobs", "scraped_json")
