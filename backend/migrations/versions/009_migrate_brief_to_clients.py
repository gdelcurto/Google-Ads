"""Data migration: extract client/hotel data from existing brief_json.

For each project that has a brief_json and no client_id yet:
  1. Create a Client from brief.client fields
  2. Create a Hotel from brief.hotel_specifics fields
  3. Set project.client_id and project.hotel_id

Projects without a brief are left unlinked (client_id / hotel_id = NULL).

Revision ID: 009
Revises: 008
Create Date: 2026-02-25 00:00:00.000000
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = datetime.utcnow()


def _new_id() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    conn = op.get_bind()

    projects = conn.execute(
        sa.text(
            "SELECT id, name, owner_id, brief_json, client_id "
            "FROM projects "
            "WHERE brief_json IS NOT NULL AND client_id IS NULL"
        )
    ).fetchall()

    for row in projects:
        project_id = row[0]
        project_name = row[1]
        owner_id = row[2]
        brief_raw = row[3]

        try:
            brief = json.loads(brief_raw)
        except Exception:
            continue

        client_data = brief.get("client") or {}
        hotel_data  = brief.get("hotel_specifics") or {}
        loc         = hotel_data.get("location") or {}

        brand_name = (
            client_data.get("brand_name")
            or hotel_data.get("name")
            or project_name
            or "Cliente senza nome"
        )

        # ── Create Client ─────────────────────────────────────────────────────
        client_id = _new_id()
        conn.execute(
            sa.text(
                "INSERT INTO clients "
                "(id, name, bb_client_id, agency, contact_email, contact_phone, "
                " notes, owner_id, created_at, updated_at) "
                "VALUES (:id, :name, :bb_client_id, :agency, :contact_email, "
                "        :contact_phone, :notes, :owner_id, :created_at, :updated_at)"
            ),
            {
                "id":            client_id,
                "name":          brand_name,
                "bb_client_id":  None,
                "agency":        client_data.get("agency"),
                "contact_email": client_data.get("contact_email"),
                "contact_phone": client_data.get("contact_phone"),
                "notes":         f"Migrato automaticamente dal progetto: {project_name}",
                "owner_id":      owner_id,
                "created_at":    _NOW,
                "updated_at":    _NOW,
            },
        )

        # ── Create Hotel ──────────────────────────────────────────────────────
        hotel_id = _new_id()
        conn.execute(
            sa.text(
                "INSERT INTO hotels "
                "(id, client_id, name, bb_hotel_id, category, stars, "
                " address, city, country, country_code, lat, lng, "
                " website_url, booking_engine, property_type, "
                " adr, seasonality_json, scraped_json, scraped_at, "
                " created_at, updated_at) "
                "VALUES "
                "(:id, :client_id, :name, :bb_hotel_id, :category, :stars, "
                " :address, :city, :country, :country_code, :lat, :lng, "
                " :website_url, :booking_engine, :property_type, "
                " :adr, :seasonality_json, :scraped_json, :scraped_at, "
                " :created_at, :updated_at)"
            ),
            {
                "id":              hotel_id,
                "client_id":       client_id,
                "name":            brand_name,
                "bb_hotel_id":     None,
                "category":        hotel_data.get("category", "city_hotel"),
                "stars":           hotel_data.get("stars", 0),
                "address":         loc.get("address"),
                "city":            loc.get("city"),
                "country":         loc.get("country"),
                "country_code":    loc.get("country_code"),
                "lat":             (loc.get("coordinates") or {}).get("lat"),
                "lng":             (loc.get("coordinates") or {}).get("lng"),
                "website_url":     hotel_data.get("website_url"),
                "booking_engine":  hotel_data.get("booking_engine"),
                "property_type":   hotel_data.get("property_type"),
                "adr":             None,
                "seasonality_json": None,
                "scraped_json":    None,
                "scraped_at":      None,
                "created_at":      _NOW,
                "updated_at":      _NOW,
            },
        )

        # ── Link project ──────────────────────────────────────────────────────
        conn.execute(
            sa.text(
                "UPDATE projects SET client_id = :cid, hotel_id = :hid "
                "WHERE id = :pid"
            ),
            {"cid": client_id, "hid": hotel_id, "pid": project_id},
        )


def downgrade() -> None:
    # Remove auto-migrated clients/hotels (identified by the notes marker)
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE projects SET client_id = NULL, hotel_id = NULL"
    ))
    conn.execute(sa.text("DELETE FROM hotels"))
    conn.execute(sa.text(
        "DELETE FROM clients WHERE notes LIKE 'Migrato automaticamente%'"
    ))
