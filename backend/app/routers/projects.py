"""Projects CRUD and brief management."""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user, require_strategist_or_admin
from app.database import get_db
from app.domain.models import AuditLog, Project
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
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [_to_response(p) for p in projects]


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


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return project
