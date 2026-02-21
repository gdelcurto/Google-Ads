"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token, decode_token, get_current_user,
    hash_password, require_admin, verify_password, TokenData,
)
from app.database import get_db
from app.domain.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "strategist"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password errati",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account disabilitato")

    token = create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name},
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
    )


@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_admin)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
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
    return UserResponse(
        id=user.id, email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
    )
