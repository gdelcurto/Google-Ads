"""Projects CRUD and brief management."""
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_ROME = ZoneInfo("Europe/Rome")
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user, require_strategist_or_admin
from app.database import get_db
from app.domain.models import AuditLog, Project, ProjectPermission
from app.domain.schemas.brief import Brief
from app.validators.brief_validator import BriefValidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])
validator = BriefValidator()


class ProjectCreate(BaseModel):
    name: str
    client_slug: str
    preset: str = "blastness"
    vertical: str = "city_hotel"


class ProjectResponse(BaseModel):
    id: str
    name: str
    client_slug: str
    status: str
    preset: str
    vertical: str
    has_brief: bool
    has_plan: bool
    owner_id: str
    created_at: str
    updated_at: str


def _to_response(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        name=p.name,
        client_slug=p.client_slug,
        status=p.status,
        preset=p.preset,
        vertical=p.vertical,
        has_brief=p.brief_json is not None,
        has_plan=p.plan_json is not None,
        owner_id=p.owner_id,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_q = select(Project).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc())

    if current_user.role == "admin":
        result = await db.execute(base_q)
        return [_to_response(p) for p in result.scalars().all()]

    # Check if user has an all_projects wildcard
    all_perm = await db.execute(
        select(ProjectPermission).where(
            ProjectPermission.user_id == current_user.user_id,
            ProjectPermission.all_projects.is_(True),
            ProjectPermission.can_read.is_(True),
        )
    )
    if all_perm.scalar_one_or_none():
        result = await db.execute(base_q)
        return [_to_response(p) for p in result.scalars().all()]

    # Otherwise, return only explicitly permitted projects
    perms = await db.execute(
        select(ProjectPermission.project_id).where(
            ProjectPermission.user_id == current_user.user_id,
            ProjectPermission.project_id.is_not(None),
            ProjectPermission.can_read.is_(True),
        )
    )
    allowed_ids = [row[0] for row in perms.fetchall()]
    if not allowed_ids:
        return []

    result = await db.execute(
        base_q.where(Project.id.in_(allowed_ids))
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        name=payload.name,
        client_slug=payload.client_slug,
        preset=payload.preset,
        vertical=payload.vertical,
        owner_id=current_user.user_id,
    )
    db.add(project)
    await db.flush()

    log = AuditLog(
        project_id=project.id,
        user_id=current_user.user_id,
        action="create_project",
        entity_type="project",
        entity_id=project.id,
        details=json.dumps({"name": project.name}),
    )
    db.add(log)

    logger.info(f"Project created: {project.id} by {current_user.email}")
    return _to_response(project)


@router.get("/trash/list", response_model=List[ProjectResponse])
async def list_trash(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all soft-deleted projects."""
    result = await db.execute(
        select(Project)
        .where(Project.deleted_at.is_not(None))
        .order_by(Project.deleted_at.desc())
    )
    projects = result.scalars().all()
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db)
    return _to_response(project)


@router.put("/{project_id}/brief")
async def upload_brief(
    project_id: str,
    brief_data: dict,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace the brief JSON for a project. Runs validation."""
    project = await _get_project_or_404(project_id, db)

    # Parse and validate brief
    try:
        brief = Brief(**brief_data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Brief JSON non valido: {exc}")

    validation = validator.validate(brief)

    project.brief_json = brief.model_dump_json()
    project.status = "validated" if validation.is_valid else "draft"
    project.plan_json = None  # Reset plan on brief change

    log = AuditLog(
        project_id=project.id,
        user_id=current_user.user_id,
        action="upload_brief",
        entity_type="project",
        entity_id=project.id,
        details=json.dumps({
            "is_valid": validation.is_valid,
            "errors": len(validation.errors),
            "warnings": len(validation.warnings),
        }),
    )
    db.add(log)

    return {
        "project_id": project_id,
        "status": project.status,
        "validation": {
            "is_valid": validation.is_valid,
            "errors": [{"code": e.code, "message": e.message, "language": e.language} for e in validation.errors],
            "warnings": [{"code": w.code, "message": w.message, "language": w.language} for w in validation.warnings],
            "checklist": [{"label": c.label, "ok": c.ok, "detail": c.detail} for c in validation.checklist],
        },
    }


@router.get("/{project_id}/brief")
async def get_brief(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_or_404(project_id, db)
    if not project.brief_json:
        raise HTTPException(status_code=404, detail="Brief non ancora caricato")
    return json.loads(project.brief_json)


@router.get("/{project_id}/audit")
async def get_audit_log(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.project_id == project_id)
        .order_by(AuditLog.timestamp.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "details": json.loads(l.details) if l.details else None,
            "timestamp": l.timestamp.isoformat(),
            "user_id": l.user_id,
        }
        for l in logs
    ]


@router.delete("/{project_id}")
async def soft_delete_project(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a project (move to trash)."""
    project = await _get_project_or_404(project_id, db)
    if project.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Progetto già nel cestino")
    project.deleted_at = datetime.now(_TZ_ROME)

    log = AuditLog(
        project_id=project.id,
        user_id=current_user.user_id,
        action="soft_delete_project",
        entity_type="project",
        entity_id=project.id,
        details=json.dumps({"name": project.name}),
    )
    db.add(log)

    logger.info(f"Project soft-deleted: {project.id} by {current_user.email}")
    return {"detail": "Progetto spostato nel cestino"}


@router.post("/{project_id}/restore")
async def restore_project(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted project from trash."""
    project = await _get_project_or_404(project_id, db)
    if project.deleted_at is None:
        raise HTTPException(status_code=400, detail="Progetto non nel cestino")
    project.deleted_at = None

    log = AuditLog(
        project_id=project.id,
        user_id=current_user.user_id,
        action="restore_project",
        entity_type="project",
        entity_id=project.id,
        details=json.dumps({"name": project.name}),
    )
    db.add(log)

    logger.info(f"Project restored: {project.id} by {current_user.email}")
    return {"detail": "Progetto ripristinato"}


@router.delete("/{project_id}/permanent")
async def permanent_delete_project(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a project (must be in trash first)."""
    project = await _get_project_or_404(project_id, db)
    if project.deleted_at is None:
        raise HTTPException(
            status_code=400,
            detail="Il progetto deve essere nel cestino prima di eliminarlo definitivamente",
        )

    log = AuditLog(
        project_id=None,
        user_id=current_user.user_id,
        action="permanent_delete_project",
        entity_type="project",
        entity_id=project.id,
        details=json.dumps({"name": project.name, "project_id": project.id}),
    )
    db.add(log)

    await db.delete(project)

    logger.info(f"Project permanently deleted: {project_id} by {current_user.email}")
    return {"detail": "Progetto eliminato definitivamente"}


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return project


# ── Permission helpers ────────────────────────────────────────────────────────

def _full_tabs() -> dict:
    return {
        "overview": True, "campaigns": True, "preview": True,
        "brief": True, "action_plan": True, "plan_json": True,
        "audit": True, "scan_log": True, "api_log": True,
    }


def _no_tabs() -> dict:
    return {k: False for k in _full_tabs()}


def _perm_to_dict(p: ProjectPermission) -> dict:
    return {
        "can_read": p.can_read,
        "can_write": p.can_write,
        "tabs": {
            "overview": p.tab_overview,
            "campaigns": p.tab_campaigns,
            "preview": p.tab_preview,
            "brief": p.tab_brief,
            "action_plan": p.tab_action_plan,
            "plan_json": p.tab_plan_json,
            "audit": p.tab_audit,
            "scan_log": p.tab_scan_log,
            "api_log": p.tab_api_log,
        },
    }


async def _resolve_permissions(user_id: str, user_role: str, project_id: str, db: AsyncSession) -> dict:
    """Return effective permissions for a user on a project.

    Admin always gets full access. For others, check specific project
    permission first, then fall back to the all_projects wildcard.
    """
    if user_role == "admin":
        return {"can_read": True, "can_write": True, "tabs": _full_tabs()}

    # Specific project permission
    res = await db.execute(
        select(ProjectPermission).where(
            ProjectPermission.user_id == user_id,
            ProjectPermission.project_id == project_id,
        )
    )
    perm = res.scalar_one_or_none()
    if perm:
        return _perm_to_dict(perm)

    # All-projects wildcard
    res = await db.execute(
        select(ProjectPermission).where(
            ProjectPermission.user_id == user_id,
            ProjectPermission.all_projects.is_(True),
        )
    )
    perm = res.scalar_one_or_none()
    if perm:
        return _perm_to_dict(perm)

    return {"can_read": False, "can_write": False, "tabs": _no_tabs()}


@router.get("/{project_id}/my-permissions")
async def get_my_permissions(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's effective permissions for a project."""
    return await _resolve_permissions(current_user.user_id, current_user.role, project_id, db)
