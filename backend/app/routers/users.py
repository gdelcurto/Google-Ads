"""User management and project permissions routes (admin only)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    TokenData, get_current_user, hash_password, require_admin,
)
from app.database import get_db
from app.domain.models import Project, ProjectPermission, User

router = APIRouter(prefix="/api/users", tags=["users"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "strategist"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class PermissionBase(BaseModel):
    all_projects: bool = False
    project_id: Optional[str] = None
    can_read: bool = True
    can_write: bool = False
    tab_overview: bool = True
    tab_campaigns: bool = True
    tab_preview: bool = True
    tab_brief: bool = True
    tab_action_plan: bool = True
    tab_plan_json: bool = True
    tab_audit: bool = True
    tab_scan_log: bool = True
    tab_api_log: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: str
    user_id: str
    project_name: Optional[str] = None
    created_at: str
    created_by: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_resp(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at.isoformat(),
    )


async def _perm_resp(p: ProjectPermission, db: AsyncSession) -> PermissionResponse:
    project_name: Optional[str] = None
    if p.project_id:
        proj = await db.get(Project, p.project_id)
        project_name = proj.name if proj else None
    return PermissionResponse(
        id=p.id,
        user_id=p.user_id,
        all_projects=p.all_projects,
        project_id=p.project_id,
        project_name=project_name,
        can_read=p.can_read,
        can_write=p.can_write,
        tab_overview=p.tab_overview,
        tab_campaigns=p.tab_campaigns,
        tab_preview=p.tab_preview,
        tab_brief=p.tab_brief,
        tab_action_plan=p.tab_action_plan,
        tab_plan_json=p.tab_plan_json,
        tab_audit=p.tab_audit,
        tab_scan_log=p.tab_scan_log,
        tab_api_log=p.tab_api_log,
        created_at=p.created_at.isoformat(),
        created_by=p.created_by,
    )


# ── User CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at))
    return [_user_resp(u) for u in result.scalars().all()]


@router.post("", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email già registrata")
    if payload.role not in ("admin", "strategist", "operator"):
        raise HTTPException(status_code=400, detail="Ruolo non valido")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    return _user_resp(user)


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def update_user(user_id: str, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        if payload.role not in ("admin", "strategist", "operator"):
            raise HTTPException(status_code=400, detail="Ruolo non valido")
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    await db.flush()
    return _user_resp(user)


@router.delete("/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Non puoi eliminare il tuo stesso account")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    await db.delete(user)
    return {"ok": True}


# ── Permission CRUD ───────────────────────────────────────────────────────────

@router.get("/{user_id}/permissions", response_model=list[PermissionResponse], dependencies=[Depends(require_admin)])
async def list_permissions(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    result = await db.execute(
        select(ProjectPermission)
        .where(ProjectPermission.user_id == user_id)
        .order_by(ProjectPermission.created_at)
    )
    perms = result.scalars().all()
    return [await _perm_resp(p, db) for p in perms]


@router.post("/{user_id}/permissions", response_model=PermissionResponse, dependencies=[Depends(require_admin)])
async def add_permission(
    user_id: str,
    payload: PermissionCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    if not payload.all_projects and not payload.project_id:
        raise HTTPException(status_code=400, detail="Specificare project_id oppure all_projects=true")

    if payload.all_projects and payload.project_id:
        raise HTTPException(status_code=400, detail="Non puoi specificare sia project_id che all_projects")

    # Prevent duplicate
    if payload.all_projects:
        dup = await db.execute(
            select(ProjectPermission).where(
                ProjectPermission.user_id == user_id,
                ProjectPermission.all_projects.is_(True),
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Permesso 'tutti i progetti' già esistente per questo utente")
    else:
        dup = await db.execute(
            select(ProjectPermission).where(
                ProjectPermission.user_id == user_id,
                ProjectPermission.project_id == payload.project_id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Permesso per questo progetto già esistente")

    if payload.project_id:
        proj = await db.get(Project, payload.project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Progetto non trovato")

    perm = ProjectPermission(
        user_id=user_id,
        project_id=payload.project_id if not payload.all_projects else None,
        all_projects=payload.all_projects,
        can_read=payload.can_read,
        can_write=payload.can_write,
        tab_overview=payload.tab_overview,
        tab_campaigns=payload.tab_campaigns,
        tab_preview=payload.tab_preview,
        tab_brief=payload.tab_brief,
        tab_action_plan=payload.tab_action_plan,
        tab_plan_json=payload.tab_plan_json,
        tab_audit=payload.tab_audit,
        tab_scan_log=payload.tab_scan_log,
        tab_api_log=payload.tab_api_log,
        created_by=current_user.user_id,
    )
    db.add(perm)
    await db.flush()
    return await _perm_resp(perm, db)


@router.put("/{user_id}/permissions/{perm_id}", response_model=PermissionResponse, dependencies=[Depends(require_admin)])
async def update_permission(
    user_id: str,
    perm_id: str,
    payload: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
):
    perm = await db.get(ProjectPermission, perm_id)
    if not perm or perm.user_id != user_id:
        raise HTTPException(status_code=404, detail="Permesso non trovato")
    perm.can_read = payload.can_read
    perm.can_write = payload.can_write
    perm.tab_overview = payload.tab_overview
    perm.tab_campaigns = payload.tab_campaigns
    perm.tab_preview = payload.tab_preview
    perm.tab_brief = payload.tab_brief
    perm.tab_action_plan = payload.tab_action_plan
    perm.tab_plan_json = payload.tab_plan_json
    perm.tab_audit = payload.tab_audit
    perm.tab_scan_log = payload.tab_scan_log
    perm.tab_api_log = payload.tab_api_log
    await db.flush()
    return await _perm_resp(perm, db)


@router.delete("/{user_id}/permissions/{perm_id}", dependencies=[Depends(require_admin)])
async def delete_permission(user_id: str, perm_id: str, db: AsyncSession = Depends(get_db)):
    perm = await db.get(ProjectPermission, perm_id)
    if not perm or perm.user_id != user_id:
        raise HTTPException(status_code=404, detail="Permesso non trovato")
    await db.delete(perm)
    return {"ok": True}
