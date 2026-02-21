"""Pytest fixtures shared across tests."""
import json
from pathlib import Path

import pytest

from app.domain.schemas.brief import Brief

BRIEF_EXAMPLE_PATH = Path(__file__).parents[2] / "examples" / "brief_complete.json"


@pytest.fixture
def sample_brief() -> Brief:
    """Load the complete example brief."""
    data = json.loads(BRIEF_EXAMPLE_PATH.read_text())
    return Brief(**data)


@pytest.fixture
def minimal_brief() -> Brief:
    """Minimal valid brief for fast tests."""
    return Brief(**{
        "version": "1.0",
        "meta": {
            "project_name": "Test Hotel – Setup Q1",
            "created_by": "test@test.com",
            "preset": "blastness",
            "vertical": "city_hotel",
        },
        "client": {
            "brand_name": "Test Hotel",
            "brand_slug": "test-hotel",
            "domain": "www.testhotel.it",
            "country": "IT",
            "currency": "EUR",
            "timezone": "Europe/Rome",
            "google_ads_customer_id": "123-456-7890",
        },
        "objectives": {
            "primary": "direct_bookings",
            "conversions": {"primary_conversion_action": "Reservation"},
            "kpi": {"target_cpa_eur": 50.0},
        },
        "budgets": {
            "total_monthly_eur": 1000,
            "by_campaign_type": {
                "search_brand": {"total": 300, "by_language": {"IT": 300}},
                "search_acquisition": {"total": 500, "by_language": {"IT": 500}},
                "retargeting": {"total": 200, "by_language": {"IT": 200}},
            },
        },
        "languages": [
            {
                "code": "IT",
                "name": "Italiano",
                "google_language_id": 1004,
                "landing_page": "https://www.testhotel.it/",
                "brand_terms": ["test hotel", "hotel test"],
                "brand_exclusions": ["economico", "ostello"],
                "usp": {"main": "Il tuo hotel nel cuore della città", "bullets": []},
                "headlines": [
                    "Test Hotel Sito Ufficiale",
                    "Hotel 4 Stelle in Centro",
                    "Prenota Diretto e Risparmia",
                    "Miglior Prezzo Garantito",
                    "Wi-Fi Gratuito Incluso",
                ],
                "descriptions": [
                    "Hotel 4 stelle nel centro città. Prenota direttamente per il miglior prezzo.",
                    "Camera superior con colazione inclusa. Prenota ora.",
                ],
                "sitelinks": [
                    {
                        "text": "Offerte Speciali",
                        "description_1": "Sconti fino al 20%",
                        "description_2": "Solo sul sito ufficiale",
                        "final_url": "https://www.testhotel.it/offerte",
                    },
                    {
                        "text": "Ristorante",
                        "description_1": "Cucina locale",
                        "description_2": "Aperto tutti i giorni",
                        "final_url": "https://www.testhotel.it/ristorante",
                    },
                ],
                "callouts": ["Colazione Inclusa", "Wi-Fi Gratuito", "Parcheggio"],
                "structured_snippets": [],
            }
        ],
        "geo_targeting": {"target_countries": ["IT"]},
        "audiences": {
            "remarketing_lists": [
                {"name": "All Visitors 30d", "type": "website_visitors", "lookback_days": 30, "source": "google_tag"}
            ],
        },
        "hotel_specifics": {
            "category": "city_hotel",
            "stars": 4,
            "location": {"address": "Via Roma 1, Milano"},
            "booking_engine_url": "https://www.testhotel.it/prenota",
        },
        "labels": ["blastness_setup", "blastness_test-hotel"],
    })
