"""
Demand Gen Campaign Agent.

Philosophy: Demand Gen (formerly Discovery) targets users in the inspiration
and discovery phase. They're not searching — they're browsing YouTube, Gmail,
and Google Discover. The copy and creative must be aspirational and visual-first.
Transactional copy ("Book Now", "Best Price") is out of place here — it matches
the intent of Acquisition campaigns, not Demand Gen.
"""
from __future__ import annotations

from typing import List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan


class DemandGenAgent(CampaignAgent):
    TYPE_KEY = "demand_gen"

    GUIDELINES = """
    DEMAND GEN (formerly Discovery) — Rules for creative and targeting
    ══════════════════════════════════════════════════════════════════

    PURPOSE
    Reach users during the inspiration/discovery phase on YouTube, Gmail,
    and Google Discover. Build desire before they start actively searching.
    This is top-of-funnel awareness — measured in assisted conversions,
    CTR, and video views — NOT direct ROAS.

    COPY RULES
    ✅ Headlines: aspirational and experiential (not transactional):
       "Il Tuo Rifugio nel Cuore di Roma"
       "Vivi Roma Come un Local"
       "Un'Oasi di Lusso a Due Passi dal Colosseo"
    ❌ AVOID transactional copy used in Acquisition/Brand:
       "Prenota Subito", "Miglior Prezzo", "4 Stelle Roma Centro"
       → Wrong tone for discovery stage (user isn't ready to book)
    ✅ Call to action: softer preferred → "Scopri di più", "Lasciati ispirare"
    ✅ Descriptions: evocative, emotional, paint the experience:
       "Camere con vista mozzafiato, colazione gourmet e servizio su misura"

    CREATIVE REQUIREMENTS (blocks publish if missing)
    ✅ Landscape image 1200×628 — hotel exterior or destination beauty shot
    ✅ Square image 1200×1200 — room, pool, or signature experience
    ✅ Logo 1200×1200 PNG transparent
    ◐ Video (optional but strongly recommended): YouTube 16:9
       → Video significantly increases reach and engagement on YouTube

    TARGETING (audience-based, no keywords)
    ✅ In-market segments: Travel, Hotels, Luxury Travel, City Breaks
    ✅ Custom intent: seed with keywords from Acquisition campaign
    ✅ Remarketing lists: 30–90 day lookback (re-inspire past visitors)
    ❌ No keyword targeting — Demand Gen is audience-only

    BID STRATEGY
    - Maximize Clicks (awareness phase, limited conversion data)
    - Maximize Conversions (once you have baseline data)
    - Target CPA (if you track assisted conversions)

    KPI
    - Primary: CTR, video completion rate, view-through conversions
    - Secondary: assisted conversions (Demand Gen → Acquisition → conversion)
    - NOT direct ROAS — this is not a bottom-of-funnel channel

    CONFIGURE IN BRIEF
    Creative assets (images, logo, video) must be uploaded separately.
    The brief tracks missing assets via DemandGenAd.missing_asset_notes.

    WARNING SIGNS
    ⚠ Transactional copy → wrong tone for inspiration-phase users
    ⚠ No images → campaign cannot run (required assets missing)
    ⚠ Same copy as Acquisition → misaligned message for discovery intent
    ⚠ No in-market segments → broad targeting, poor efficiency
    ⚠ Judging by direct ROAS → Demand Gen is measured on assisted value
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        # Demand Gen uses DemandGenAd format (not RSA), generic headlines as fallback
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[str]:
        # Demand Gen doesn't use RSA — creative validation happens in DemandGenGenerator
        # (images are the critical asset, tracked via has_missing_assets)
        return []
