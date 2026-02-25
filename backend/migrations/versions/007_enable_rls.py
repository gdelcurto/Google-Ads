"""Enable Row Level Security on all public tables (Supabase / PostgreSQL).

Revision ID: 007
Revises: 006
Create Date: 2026-02-25 00:00:00.000000

WHY
---
Supabase exposes all tables in the `public` schema via PostgREST.
Without RLS a request using the `anon` or `authenticated` role could
read/write every row.  Enabling RLS with no permissive policies
effectively blocks PostgREST access while leaving the backend
unaffected: it connects as `postgres` (superuser) or via the
`service_role` key, both of which bypass RLS automatically in
Supabase / standard PostgreSQL.

TABLES
------
users, projects, campaigns, exports, audit_logs,
project_permissions, autofill_jobs
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "users",
    "projects",
    "campaigns",
    "exports",
    "audit_logs",
    "project_permissions",
    "autofill_jobs",
]


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return  # SQLite (dev) — skip silently

    for table in _TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        # Force RLS even for the table owner (extra safety layer).
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    if not _is_postgres():
        return

    for table in _TABLES:
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
