"""Pydantic schemas for Client and Hotel."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


# ── Seasonality period ────────────────────────────────────────────────────────

class SeasonalityPeriod(BaseModel):
    name: str = ""                          # es. "Alta stagione"
    date_from: str = ""                     # MM-DD format, es. "06-01"
    date_to: str = ""                       # MM-DD format, es. "08-31"
    avg_occupancy_pct: Optional[float] = None   # 0–100
    target_markets: List[str] = []          # ISO-2 country codes
    booking_channels: List[str] = []        # es. ["booking.com", "direct", "expedia"]
    direct_booking_pct: Optional[float] = None  # 0–100


# ── Hotel ─────────────────────────────────────────────────────────────────────

class HotelCreate(BaseModel):
    name: str
    bb_hotel_id: Optional[str] = None
    category: Optional[str] = "city_hotel"
    stars: Optional[int] = 0
    rooms: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    website_url: Optional[str] = None
    booking_engine: Optional[str] = None
    property_type: Optional[str] = None
    adr: Optional[float] = None
    seasonality: List[SeasonalityPeriod] = []


class HotelUpdate(HotelCreate):
    name: Optional[str] = None  # type: ignore[assignment]


class HotelResponse(BaseModel):
    id: str
    client_id: str
    name: str
    bb_hotel_id: Optional[str]
    category: Optional[str]
    stars: Optional[int]
    rooms: Optional[int]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    website_url: Optional[str]
    booking_engine: Optional[str]
    property_type: Optional[str]
    adr: Optional[float]
    seasonality: List[SeasonalityPeriod]
    has_scraped_data: bool
    scraped_at: Optional[str]
    created_at: str
    updated_at: str


# ── Client ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    bb_client_id: Optional[str] = None
    agency: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class ClientUpdate(ClientCreate):
    name: Optional[str] = None  # type: ignore[assignment]


class ClientResponse(BaseModel):
    id: str
    name: str
    bb_client_id: Optional[str]
    agency: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    notes: Optional[str]
    owner_id: str
    hotels: List[HotelResponse]
    created_at: str
    updated_at: str


class ClientListItem(BaseModel):
    id: str
    name: str
    bb_client_id: Optional[str]
    agency: Optional[str]
    contact_email: Optional[str]
    hotels_count: int
    created_at: str
    updated_at: str
