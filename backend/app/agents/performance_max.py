"""
Performance Max Campaign Agent.

Philosophy: PMax is Google's fully automated, omni-channel campaign type.
You don't control placements or targeting — you provide assets and audience
signals, and Google decides everything else. The most critical risks are:
1) Brand cannibalization (PMax will steal branded queries from brand campaigns)
2) Missing image assets (campaign runs at limited scale without them)
3) URL expansion (Google may send traffic to unintended pages)

Configure these constraints before publishing, or performance will be unpredictable.
"""
from __future__ import annotations

from typing import List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan

# Minimum recommended headline count for "Good" ad strength
_MIN_HEADLINES_GOOD = 5
_MIN_HEADLINES_EXCELLENT = 8


class PMaxAgent(CampaignAgent):
    TYPE_KEY = "performance_max"

    GUIDELINES = """
    PERFORMANCE MAX — Rules for asset groups and configuration
    ══════════════════════════════════════════════════════════

    PURPOSE
    Automated omni-channel campaign across Search, Display, YouTube, Gmail,
    Maps, and Shopping. Google optimises placements and creative combinations.
    Best for reaching new audiences at scale and capturing demand across channels.

    ASSET GROUP REQUIREMENTS
    ✅ Headlines: 3 required, 8+ recommended for "Excellent" ad strength (max 30 chars)
    ✅ Long headlines: 1 required (max 90 chars — used in Display/YouTube)
    ✅ Descriptions: 2 required, 4 recommended (max 90 chars)
    ✅ Images: REQUIRED
       - Landscape 1200×628 (hotel exterior / destination)
       - Square 1200×1200 (room, pool, or signature experience)
    ✅ Logo: 1200×1200 PNG with transparent background
    ◐ Video: optional but strongly recommended (16:9 YouTube hosted)
       → Without video, Google auto-generates one (usually low quality)

    BRAND EXCLUSION — CRITICAL before publishing
    ❌ Without brand exclusion lists, PMax will compete with your Brand campaign
       on branded queries — cannibalization drives up your own CPC costs.
    ✅ Add brand exclusion list (exact match: hotel name + variants)
       before publishing the PMax campaign.

    URL EXPANSION
    - Start with url_expansion = False (disabled)
    - Enable only after validating which landing pages Google is using
    - Disable again if Google sends traffic to irrelevant hotel pages

    AUDIENCE SIGNALS (not targeting — signals only)
    ✅ Add remarketing lists → tells Google "users like these convert"
    ✅ Add in-market segments → Travel, Hotels, Luxury Travel
    ✅ Add custom intent → paste keywords from Acquisition campaign
    → More signals = faster learning period

    BID STRATEGY
    - Target ROAS (preferred if you have 30+ conversions/month)
    - Maximize Conversion Value (if starting fresh)
    - Target CPA (for lead-gen / phone-call objectives)

    CONFIGURE IN BRIEF
    Asset images and videos must be uploaded separately (cannot be in brief JSON).
    The brief tracks what's missing via missing_asset_notes in each asset group.

    WARNING SIGNS
    ⚠ < 5 headlines → low ad strength, limited creative combinations
    ⚠ No images → campaign runs only on text/Search inventory (poor scale)
    ⚠ No brand exclusion → expect brand cannibalization within 2 weeks
    ⚠ No audience signals → longer learning period (3–6 weeks vs 1–2 weeks)
    ⚠ url_expansion enabled too early → irrelevant traffic to blog/careers pages
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        # PMax uses a mix: if brand_assets configured use those, else generic
        if lang.brand_assets and lang.brand_assets.headlines:
            return lang.brand_assets.headlines
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        if lang.brand_assets and lang.brand_assets.descriptions:
            return lang.brand_assets.descriptions
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[str]:
        warnings: List[str] = []
        headlines = self.get_headlines(lang)

        if len(headlines) < _MIN_HEADLINES_GOOD:
            warnings.append(
                f"[PMax/{lang.code}] Solo {len(headlines)} headline configurati (minimo 3, "
                f"raccomandati {_MIN_HEADLINES_EXCELLENT}+ per ad strength 'Excellent'). "
                "Aggiungere più headline per migliorare la copertura creativa."
            )

        return warnings
