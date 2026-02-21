"""
Google Ads Hotel Campaigns — FastAPI application entry point.
"""
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

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from app.config import get_settings
from app.database import get_db
from app.domain.models import User
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


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB migrations then seed admin on startup."""
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied")
    await _seed_admin()
    logger.info(
        f"Google Ads Campaigns API started "
        f"[env={settings.app_env}] [debug={settings.app_debug}]"
    )
    yield
    logger.info("Shutting down")


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
from app.routers import auth, autofill, campaigns, export, projects, templates

app.include_router(auth.router)
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
