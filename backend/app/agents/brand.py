"""
Brand Search Campaign Agent.

Philosophy: Brand campaigns exist to protect your brand SERP and intercept users
who already know the hotel. The ad copy must reinforce trust and the advantage
of booking directly. Every headline should feel like it belongs to the hotel,
not to a generic destination search.
"""
from __future__ import annotations

from typing import List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan


class BrandAgent(CampaignAgent):
    TYPE_KEY = "search_brand"

    GUIDELINES = """
    BRAND SEARCH — Rules for ad copy and keywords
    ══════════════════════════════════════════════

    PURPOSE
    Capture users who search for the hotel by name. These users already have
    intent. The goal is to win the click over OTAs and competitor bidders, and
    steer them to direct booking.

    COPY RULES
    ✅ Headline 1: MUST contain the brand/hotel name — pin it at position 1
    ✅ Other headlines: reinforce the direct booking advantage:
       "Sito Ufficiale", "Miglior Tariffa Garantita", "Prenota Direttamente",
       "Sconto Esclusivo Online", "Cancellazione Gratuita"
    ❌ NO generic location/category terms (e.g. "Hotel Roma Centro") —
       those belong in Acquisition campaigns
    ❌ NO keyword insertion ({KeyWord}) — brand campaigns have fixed intent

    RSA PINNING
    - Pin brand name headline at position 1 (always visible)
    - Positions 2–3 can rotate from direct-booking benefit headlines

    KEYWORD RULES
    ✅ Exact match + Phrase match ONLY for brand terms and variants
    ✅ Include: misspellings, abbreviations, branded product names
    ❌ Negative: all generic non-brand terms (shared negative list "Non-Brand Negatives")

    BID STRATEGY
    - If max_cpc_brand is set → Manual CPC with that cap
    - Otherwise → Maximize Conversions
    - Rationale: brand terms are cheap; control spend, protect margin

    CONFIGURE IN BRIEF
    Set lang.brand_assets.headlines with branded copy to get type-specific RSA.
    Without brand_assets, the generic brief headlines are used — this works but
    may include non-brand terms in a brand context.

    WARNING SIGNS
    ⚠ Brand name not in any headline → ad won't reinforce brand identity
    ⚠ Generic copy in brand campaign → diluted message, lower CTR
    ⚠ Missing brand_assets → system uses generic pool (suboptimal)
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
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

        if not headlines:
            warnings.append(
                f"[Brand/{lang.code}] Nessun headline configurato. "
                "Aggiungere almeno 3 headline in 'headlines' o in 'brand_assets.headlines'."
            )
            return warnings

        # Brand name must appear in at least one headline
        brand_lower = [t.lower() for t in lang.brand_terms]
        brand_found = any(
            any(bt in h.lower() for bt in brand_lower)
            for h in headlines
        )
        if not brand_found:
            example = lang.brand_terms[0] if lang.brand_terms else "nome hotel"
            warnings.append(
                f"[Brand/{lang.code}] Nessun headline contiene il brand name '{example}'. "
                "Le campagne Brand devono sempre includere il nome dell'hotel "
                "(configurare 'brand_assets.headlines' con copy branded)."
            )

        # Warn if no type-specific assets configured
        if not (lang.brand_assets and lang.brand_assets.headlines):
            warnings.append(
                f"[Brand/{lang.code}] Usando gli headline generici del brief per le campagne Brand. "
                "Per copy ottimizzata, configurare 'brand_assets.headlines' con testi specificamente "
                "branded (es. nome hotel + vantaggi prenotazione diretta)."
            )

        return warnings
