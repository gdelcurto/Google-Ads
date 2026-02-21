"""
SQLAlchemy ORM models for persistence.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="strategist")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="owner")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    # draft | validated | preview | published | archived
    preset: Mapped[str] = mapped_column(String(50), default="blastness")
    vertical: Mapped[str] = mapped_column(String(50), default="city_hotel")
    brief_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    campaigns: Mapped[list["CampaignRecord"]] = relationship(
        "CampaignRecord", back_populates="project", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="project", cascade="all, delete-orphan"
    )
    exports: Mapped[list["ExportRecord"]] = relationship(
        "ExportRecord", back_populates="project", cascade="all, delete-orphan"
    )


class CampaignRecord(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    external_key: Mapped[str] = mapped_column(String(300), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(300), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Paused")
    budget_daily: Mapped[float] = mapped_column(Float, default=0.0)
    can_publish: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    google_ads_campaign_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    plan_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship("Project", back_populates="campaigns")


class ExportRecord(Base):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    export_type: Mapped[str] = mapped_column(String(50), default="csv")  # csv | api
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="exports")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="audit_logs")
