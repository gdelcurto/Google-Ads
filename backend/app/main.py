"""
Google Ads Hotel Campaigns — FastAPI application entry point.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Support explicit frontend path for Docker/Railway deployments
_FRONTEND_DIST_ENV = os.getenv("FRONTEND_DIST_PATH", "")

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine, get_db, Base
from app.domain.models import User, ProjectPermission, Client, Hotel  # noqa: F401 — registers models on Base.metadata
from app.auth import hash_password

settings = get_settings()

# ─── Structured logging ───────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.INFO if not settings.app_debug else logging.DEBUG)
logger = logging.getLogger(__name__)


def _run_alembic_upgrade() -> None:
    """Run Alembic migrations synchronously (called via run_in_executor).

    Handles the case where the DB was bootstrapped via create_all without
    Alembic tracking (no alembic_version table). In that scenario we stamp
    the DB at revision 002 (last migration already covered by create_all)
    so that only new migrations (003+) get applied.
    """
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        from sqlalchemy import create_engine, inspect

        ini_path = Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = AlembicConfig(str(ini_path))

        # Build a sync URL from the async DATABASE_URL env var
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        sync_url = (
            db_url
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("sqlite+aiosqlite:///", "sqlite:///")
        )
        if not sync_url:
            # Fall back to the value in alembic.ini
            from configparser import ConfigParser
            cp = ConfigParser()
            cp.read(str(ini_path))
            sync_url = cp.get("alembic", "sqlalchemy.url", fallback="")

        if not sync_url:
            logger.warning("No DATABASE_URL found — skipping Alembic upgrade")
            return

        sync_engine = create_engine(sync_url)
        insp = inspect(sync_engine)
        if "alembic_version" not in insp.get_table_names():
            # DB was created by create_all without Alembic tracking.
            # Stamp at 002 so only migrations after 002 (i.e. 003+) run.
            logger.info("No alembic_version table found — stamping DB at revision 002")
            alembic_command.stamp(alembic_cfg, "002")
        sync_engine.dispose()

        alembic_command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied (upgrade head)")
    except Exception as exc:
        logger.warning(f"Alembic upgrade failed: {exc} — falling back to create_all")


def _ensure_missing_columns(conn) -> None:
    """Add any columns that exist in ORM models but not in the DB.

    This handles the edge case where Alembic migrations fail (e.g. duplicate
    column from a prior create_all) and create_all can't ALTER existing tables.
    Uses raw DDL so it works on both SQLite and PostgreSQL.

    NOTE: use TRUE/FALSE (not 1/0) for boolean defaults — PostgreSQL does not
    accept integer literals as boolean defaults, while SQLite 3.23+ accepts both.
    Each column is patched independently so a single failure doesn't block the rest.
    """
    from sqlalchemy import inspect, text

    insp = inspect(conn)
    _COLUMN_FIXES = [
        ("projects", "deleted_at", "DATETIME"),
        ("autofill_jobs", "scraped_json", "TEXT"),
        ("project_permissions", "tab_overview", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_campaigns", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_preview", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_brief", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_action_plan", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_plan_json", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_audit", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_scan_log", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_api_log", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("project_permissions", "tab_budget_log", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("projects", "client_id", "TEXT"),
        ("projects", "hotel_id",  "TEXT"),
        ("hotels",   "rooms",     "INTEGER"),
    ]
    for table, column, col_type in _COLUMN_FIXES:
        if table not in insp.get_table_names():
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if column not in existing:
            try:
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                ))
                logger.info(f"Added missing column {table}.{column}")
            except Exception as exc:
                logger.error(f"Failed to add column {table}.{column}: {exc}")


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations then seed admin on startup."""
    # Run Alembic migrations first (handles schema changes on existing DBs)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_alembic_upgrade)
    except Exception as exc:
        logger.error(f"Migration executor failed: {exc}", exc_info=True)

    # create_all as safety net for brand-new DBs not tracked by Alembic
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except asyncio.TimeoutError:
        logger.error("Database connection timed out after 10s — app will start anyway")
    except Exception as exc:
        logger.error(f"Database init failed — app will start anyway: {exc}", exc_info=True)

    # Safety net: add columns that migrations couldn't add (e.g. if Alembic
    # failed because create_all had already created the table with old columns).
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_ensure_missing_columns)
    except Exception as exc:
        logger.warning(f"Schema column safety-net failed: {exc}")

    try:
        await asyncio.wait_for(_seed_admin(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.error("Admin seed timed out — app will start anyway")
    except Exception as exc:
        logger.error(f"Admin seed failed — app will start anyway: {exc}", exc_info=True)

    # Mark any jobs left in "pending"/"running" as failed — they were
    # interrupted by a process restart (Railway deploy, crash, etc.).
    try:
        await asyncio.wait_for(_recover_stale_jobs(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.error("Stale job recovery timed out — app will start anyway")
    except Exception as exc:
        logger.warning(f"Stale job recovery failed: {exc}")

    logger.info(
        f"Google Ads Campaigns API started "
        f"[env={settings.app_env}] [debug={settings.app_debug}]"
    )
    yield
    logger.info("Shutting down")


async def _recover_stale_jobs():
    """Mark any pending/running autofill jobs as failed on startup.

    When Railway redeploys or the process crashes, background tasks are killed
    mid-flight. The job row stays in "pending" or "running" forever because
    nothing updates it. This recovery marks them as failed so the user sees a
    clear error and can retry.
    """
    from datetime import datetime
    from sqlalchemy import select, update
    from app.database import AsyncSessionLocal
    from app.domain.models import AutofillJob

    async with AsyncSessionLocal() as db:
        stale = await db.execute(
            select(AutofillJob.id).where(AutofillJob.status.in_(["pending", "running"]))
        )
        stale_ids = [row[0] for row in stale.fetchall()]
        if not stale_ids:
            return
        await db.execute(
            update(AutofillJob)
            .where(AutofillJob.id.in_(stale_ids))
            .values(
                status="failed",
                error_message=(
                    "Job interrotto da un riavvio del server. "
                    "Rilancia la scansione per riprovare."
                ),
                completed_at=datetime.utcnow(),
            )
        )
        await db.commit()
        logger.info(f"Recovered {len(stale_ids)} stale autofill job(s): {stale_ids}")


async def _seed_admin():
    """Create default admin user if it doesn't exist."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == settings.admin_email)
        )
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.admin_email,
                full_name=settings.admin_full_name,
                hashed_password=hash_password(settings.admin_password),
                role="admin",
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Admin user seeded: {settings.admin_email}")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Google Ads Hotel Campaigns API",
    description=(
        "Automated Google Ads campaign generation for the hotel/tourism sector. "
        "Supports Search Brand, Acquisition, Retargeting, PMax, and Demand Gen."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
from app.routers import auth, autofill, campaigns, clients, export, projects, templates, users

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(campaigns.router)
app.include_router(export.router)
app.include_router(templates.router)
app.include_router(autofill.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "google_ads_configured": settings.is_google_ads_configured,
    }


# ─── Frontend SPA (serve React build if present) ──────────────────────────────
# FRONTEND_DIST_PATH env var is set in Docker/Railway; local dev falls back to repo layout
_FRONTEND_DIST = (
    Path(_FRONTEND_DIST_ENV)
    if _FRONTEND_DIST_ENV
    else Path(__file__).parent.parent.parent / "frontend" / "dist"
)

if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        """Serve the React SPA for all non-API routes."""
        file = _FRONTEND_DIST / full_path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": "Google Ads Hotel Campaigns",
            "version": "1.0.0",
            "docs": "/api/docs",
        }
