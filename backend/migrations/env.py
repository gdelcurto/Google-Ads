"""Alembic environment configuration for async SQLAlchemy."""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database import Base
from app.domain import models  # noqa: F401 — import models to register them

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Resolve DATABASE_URL ───────────────────────────────────────────────────────
# Priority: DATABASE_URL env var > alembic.ini fallback.
# Normalizes protocol → async driver (postgresql+asyncpg, sqlite+aiosqlite).
_db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("sqlite:///") and "+aiosqlite" not in _db_url:
    _db_url = _db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    _url = config.get_main_option("sqlalchemy.url", "")
    _is_pg = "postgresql" in _url or _url.startswith("postgres")
    _connect_args = {"ssl": "require", "timeout": 10} if _is_pg else {}
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
