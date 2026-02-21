"""
Acquisition (Non-Brand) Search Campaign Agent.

Philosophy: Acquisition campaigns speak to users who don't yet know the hotel.
They are searching generically for a place to stay. The copy must compete on
the merits of the hotel's location, category and USPs — never on brand name.
Including the brand name in acquisition headlines causes cannibalization with
brand campaigns and confuses intent-based bidding.
"""
from __future__ import annotations

from typing import List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan


class AcquisitionAgent(CampaignAgent):
    TYPE_KEY = "search_acquisition"

    GUIDELINES = """
    ACQUISITION SEARCH — Rules for ad copy and keywords
    ════════════════════════════════════════════════════

    PURPOSE
    Capture users who search generically for a hotel in a destination.
    They don't know the brand yet. Win them on location, amenities, value.

    COPY RULES
    ✅ Headlines: location + category + USPs + amenities:
       "Hotel Roma Centro Storico", "4 Stelle Vicino al Colosseo",
       "Colazione Inclusa", "Piscina Panoramica", "Miglior Vista sul Duomo"
    ✅ Keyword insertion {KeyWord} is appropriate for theme-based ad groups
    ❌ NEVER include brand name in acquisition headlines
       → cannibalization risk (brand campaign loses to your own acquisition)
       → budget waste on brand-intent queries in the wrong campaign
    ❌ No "Sito Ufficiale" / "Prenota Direttamente" → brand-context messaging

    KEYWORD STRUCTURE (by theme / ad group)
    - Location: "hotel roma centro", "hotel piazza navona", "hotel vatiano"
    - Category: "hotel 4 stelle roma", "hotel di lusso roma"
    - Intent: "hotel conveniente roma", "hotel con spa", "hotel per famiglie"
    - Occasion: "hotel per anniversario", "hotel per business roma"

    MATCH TYPES
    ✅ Phrase match + Broad match per keyword
    → Phrase for control, Broad for discovery
    ❌ No Exact match in acquisition (use Brand campaign for that precision)

    NEGATIVE KEYWORDS (campaign level — critical)
    ❌ All brand terms as Exact match negative
    → Prevents brand queries from landing in acquisition (wasted CPCs)
    → Shared list: "Brand Negatives"

    BID STRATEGY
    - Target CPA (if you have conversion data and a CPA target)
    - Target ROAS (if you track booking value)
    - Maximize Conversions (if starting fresh, limited data)
    - max_cpc_acquisition cap applies if set

    CONFIGURE IN BRIEF
    Set lang.acquisition_assets.headlines with category/location/USP copy.
    Without acquisition_assets, the generic brief headlines are used — check
    they don't contain the brand name.

    WARNING SIGNS
    ⚠ Brand name in any headline → cannibalization, reconfigure copy
    ⚠ No theme separation → single generic ad group = low relevance
    ⚠ Missing acquisition_assets → may be using branded copy by mistake
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        if lang.acquisition_assets and lang.acquisition_assets.headlines:
            return lang.acquisition_assets.headlines
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        if lang.acquisition_assets and lang.acquisition_assets.descriptions:
            return lang.acquisition_assets.descriptions
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[str]:
        warnings: List[str] = []
        headlines = self.get_headlines(lang)

        # Brand name must NOT appear in acquisition headlines
        brand_lower = [t.lower() for t in lang.brand_terms]
        for h in headlines:
            if any(bt in h.lower() for bt in brand_lower):
                warnings.append(
                    f"[Acquisition/{lang.code}] L'headline '{h}' contiene il brand name. "
                    "Le campagne Acquisition devono usare copy generica (categoria/destinazione). "
                    "Configurare 'acquisition_assets.headlines' con testi senza brand name, "
                    "oppure spostare questo headline in 'brand_assets.headlines'."
                )

        # Warn if no type-specific assets configured
        if not (lang.acquisition_assets and lang.acquisition_assets.headlines):
            warnings.append(
                f"[Acquisition/{lang.code}] Usando gli headline generici del brief per le campagne Acquisition. "
                "Per copy ottimizzata, configurare 'acquisition_assets.headlines' con testi "
                "orientati a categoria/destinazione/USP (es. 'Hotel Roma Centro', '4 Stelle Colosseo')."
            )

        return warnings
