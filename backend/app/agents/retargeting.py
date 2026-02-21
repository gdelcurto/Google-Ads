"""
Retargeting Campaign Agent.

Philosophy: Retargeting speaks to your warmest audience — people who have
already visited your hotel website. They considered you. The copy must create
urgency, feel personal, and give them a reason to complete what they started.
Generic brand or acquisition copy is a missed opportunity here.
"""
from __future__ import annotations

from typing import List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan

# Words/phrases that signal urgency or personalization — at least one should appear
_URGENCY_SIGNALS = [
    "ancora", "still", "completa", "complete", "ritorna", "return",
    "speciale", "special", "offerta", "offer", "sconto", "discount",
    "prenota", "riservat", "esclusiv", "limited", "limitat",
    "tornat", "abbiam", "aspettiamo", "non perdere",
]


class RetargetingAgent(CampaignAgent):
    TYPE_KEY = "retargeting"

    GUIDELINES = """
    RETARGETING (DISPLAY / RLSA) — Rules for ad copy and targeting
    ═══════════════════════════════════════════════════════════════

    PURPOSE
    Re-engage users who visited your hotel website but didn't book.
    These are warm prospects — higher intent than cold acquisition traffic.
    They need a nudge, not an introduction.

    COPY RULES
    ✅ Headlines: urgency + personalization signals:
       "Stai ancora cercando?", "Completa la tua prenotazione",
       "Tariffa speciale riservata", "Non perdere questa offerta",
       "Torna e prenota — sconto 10%", "Aspettiamo solo te"
    ✅ Descriptions: remind them why they looked, add reason to act now:
       "Camere disponibili per le tue date — prenota prima che esauriscano"
    ❌ NO generic brand copy — they already know the brand
    ❌ NO generic acquisition copy — they're past the discovery phase

    AD GROUP STRUCTURE (by remarketing list / lookback window)
    - 1–7 days  → HIGHEST urgency (abandoned booking intent):
                  "Completa la prenotazione", "Disponibilità limitata"
    - 8–30 days → MODERATE urgency (still considering):
                  "Stai ancora cercando?", "Offerta speciale per te"
    - 31–90 days→ SOFT re-engagement:
                  "Sei ancora interessato?", "Ritorna e risparmia"
    - Customer match → highest bids, most personalized copy

    BID STRATEGY
    - Target CPA (lower target than Acquisition — warmer audience, cheaper to convert)
    - Bid adjustments: +20–50% for 1-7 day lists vs 30-90 day lists

    CREATIVE (Display)
    - Image assets required: 300×250, 728×90, 160×600, 320×50
    - Use hotel imagery (room, pool, view) — NOT just logo
    - Dynamic remarketing (if Google Merchant Center connected): show specific
      rooms or packages the user viewed

    CONFIGURE IN BRIEF
    Set lang.retargeting_assets.headlines with urgency-driven copy.
    Without retargeting_assets, generic headlines are used — these typically
    lack the urgency signals needed to recover abandoning visitors.

    WARNING SIGNS
    ⚠ No urgency signals in headlines → generic copy wastes warm audience
    ⚠ Same copy as Acquisition → no differentiation for returning users
    ⚠ Missing remarketing lists → campaign cannot run (no audience)
    ⚠ Missing image assets → Display creative will be blank
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        if lang.retargeting_assets and lang.retargeting_assets.headlines:
            return lang.retargeting_assets.headlines
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        if lang.retargeting_assets and lang.retargeting_assets.descriptions:
            return lang.retargeting_assets.descriptions
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[str]:
        warnings: List[str] = []
        headlines = self.get_headlines(lang)

        if headlines:
            urgency_found = any(
                any(signal in h.lower() for signal in _URGENCY_SIGNALS)
                for h in headlines
            )
            if not urgency_found:
                warnings.append(
                    f"[Retargeting/{lang.code}] Nessun headline contiene segnali di urgenza o personalizzazione. "
                    "Le campagne Retargeting devono usare copy con urgenza per recuperare visitatori che non hanno prenotato. "
                    "Configurare 'retargeting_assets.headlines' con testi come: "
                    "'Completa la prenotazione', 'Offerta riservata', 'Stai ancora cercando?'."
                )

        if not (lang.retargeting_assets and lang.retargeting_assets.headlines):
            warnings.append(
                f"[Retargeting/{lang.code}] Usando gli headline generici del brief per le campagne Retargeting. "
                "Per massimizzare il recupero di visitatori, configurare 'retargeting_assets.headlines' "
                "con copy orientata all'urgenza e alla personalizzazione."
            )

        return warnings
