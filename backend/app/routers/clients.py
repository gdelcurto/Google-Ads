"""Clients and Hotels CRUD."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user, require_strategist_or_admin
from app.database import get_db
from app.domain.models import Client, Hotel
from app.domain.schemas.clients import (
    ClientCreate, ClientListItem, ClientResponse, ClientUpdate,
    HotelCreate, HotelResponse, HotelUpdate, SeasonalityPeriod,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clients", tags=["clients"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _hotel_to_response(h: Hotel) -> HotelResponse:
    seasonality: list[SeasonalityPeriod] = []
    if h.seasonality_json:
        try:
            raw = json.loads(h.seasonality_json)
            seasonality = [SeasonalityPeriod(**p) for p in raw]
        except Exception:
            pass
    return HotelResponse(
        id=h.id,
        client_id=h.client_id,
        name=h.name,
        bb_hotel_id=h.bb_hotel_id,
        category=h.category,
        stars=h.stars,
        address=h.address,
        city=h.city,
        country=h.country,
        country_code=h.country_code,
        lat=h.lat,
        lng=h.lng,
        website_url=h.website_url,
        booking_engine=h.booking_engine,
        property_type=h.property_type,
        adr=h.adr,
        seasonality=seasonality,
        has_scraped_data=bool(h.scraped_json),
        scraped_at=h.scraped_at.isoformat() if h.scraped_at else None,
        created_at=h.created_at.isoformat(),
        updated_at=h.updated_at.isoformat(),
    )


def _client_to_response(c: Client) -> ClientResponse:
    return ClientResponse(
        id=c.id,
        name=c.name,
        bb_client_id=c.bb_client_id,
        agency=c.agency,
        contact_email=c.contact_email,
        contact_phone=c.contact_phone,
        notes=c.notes,
        owner_id=c.owner_id,
        hotels=[_hotel_to_response(h) for h in c.hotels],
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _client_to_list_item(c: Client) -> ClientListItem:
    return ClientListItem(
        id=c.id,
        name=c.name,
        bb_client_id=c.bb_client_id,
        agency=c.agency,
        contact_email=c.contact_email,
        hotels_count=len(c.hotels),
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


async def _get_client_or_404(client_id: str, db: AsyncSession) -> Client:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.hotels))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    return client


async def _get_hotel_or_404(hotel_id: str, db: AsyncSession) -> Hotel:
    result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
    hotel = result.scalar_one_or_none()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel non trovato")
    return hotel


# ── Clients ───────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ClientListItem])
async def list_clients(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.hotels))
        .order_by(Client.name)
    )
    return [_client_to_list_item(c) for c in result.scalars().all()]


@router.post("", response_model=ClientResponse)
async def create_client(
    payload: ClientCreate,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    client = Client(
        **payload.model_dump(),
        owner_id=current_user.user_id,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    # Initialize empty hotels list for response
    client.hotels = []
    logger.info(f"Client created: {client.id} '{client.name}' by {current_user.email}")
    return _client_to_response(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _client_to_response(await _get_client_or_404(client_id, db))


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    client.updated_at = datetime.utcnow()
    return _client_to_response(client)


@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    client = await _get_client_or_404(client_id, db)
    await db.delete(client)
    return {"detail": "Cliente eliminato"}


# ── Hotels (nested under client) ──────────────────────────────────────────────

@router.get("/{client_id}/hotels", response_model=List[HotelResponse])
async def list_hotels(
    client_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, db)
    result = await db.execute(
        select(Hotel).where(Hotel.client_id == client_id).order_by(Hotel.name)
    )
    return [_hotel_to_response(h) for h in result.scalars().all()]


@router.post("/{client_id}/hotels", response_model=HotelResponse)
async def create_hotel(
    client_id: str,
    payload: HotelCreate,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    await _get_client_or_404(client_id, db)
    data = payload.model_dump(exclude={"seasonality"})
    hotel = Hotel(
        **data,
        client_id=client_id,
        seasonality_json=json.dumps([p.model_dump() for p in payload.seasonality]),
    )
    db.add(hotel)
    await db.flush()
    await db.refresh(hotel)
    logger.info(f"Hotel created: {hotel.id} '{hotel.name}' for client {client_id}")
    return _hotel_to_response(hotel)


@router.get("/hotels/{hotel_id}", response_model=HotelResponse)
async def get_hotel(
    hotel_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _hotel_to_response(await _get_hotel_or_404(hotel_id, db))


@router.put("/hotels/{hotel_id}", response_model=HotelResponse)
async def update_hotel(
    hotel_id: str,
    payload: HotelUpdate,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    hotel = await _get_hotel_or_404(hotel_id, db)
    data = payload.model_dump(exclude_none=True, exclude={"seasonality"})
    for field, value in data.items():
        setattr(hotel, field, value)
    if payload.seasonality is not None:
        hotel.seasonality_json = json.dumps([p.model_dump() for p in payload.seasonality])
    hotel.updated_at = datetime.utcnow()
    return _hotel_to_response(hotel)


@router.delete("/hotels/{hotel_id}")
async def delete_hotel(
    hotel_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    hotel = await _get_hotel_or_404(hotel_id, db)
    await db.delete(hotel)
    return {"detail": "Hotel eliminato"}


@router.get("/hotels/{hotel_id}/scraped")
async def get_hotel_scraped_data(
    hotel_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the cached scraped/enriched data for the hotel."""
    hotel = await _get_hotel_or_404(hotel_id, db)
    if not hotel.scraped_json:
        raise HTTPException(status_code=404, detail="Nessun dato scansionato disponibile")
    return {
        "hotel_id": hotel_id,
        "scraped_at": hotel.scraped_at.isoformat() if hotel.scraped_at else None,
        "data": json.loads(hotel.scraped_json),
    }


@router.delete("/hotels/{hotel_id}/scraped")
async def clear_hotel_scraped_data(
    hotel_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Clear the cached scraped data for the hotel."""
    hotel = await _get_hotel_or_404(hotel_id, db)
    hotel.scraped_json = None
    hotel.scraped_at = None
    hotel.updated_at = datetime.utcnow()
    return {"detail": "Cache scansione rimossa"}
