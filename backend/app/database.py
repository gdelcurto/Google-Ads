"""Database setup with SQLAlchemy async engine."""
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Ensure data directory exists
Path("data").mkdir(exist_ok=True)

_is_postgres = "postgresql" in settings.database_url or "postgres://" in settings.database_url
_connect_args = (
    {"check_same_thread": False}
    if "sqlite" in settings.database_url
    else ({"ssl": "require", "timeout": 10} if _is_postgres else {})
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """Create all tables (used on startup if not using Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
