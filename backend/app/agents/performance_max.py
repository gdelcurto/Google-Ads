"""
Performance Max Campaign Agent — Senior Google Ads Strategist: Hospitality.

SKILL: Scala performance full-funnel e massimizza conversion value cross-network.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


_MIN_HEADLINES_GOOD = 5
_MIN_HEADLINES_EXCELLENT = 8


class PMaxAgent(CampaignAgent):
    TYPE_KEY = "performance_max"

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    PERFORMANCE MAX STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    OBIETTIVO STRATEGICO
    Scalare le performance full-funnel e massimizzare conversion value.
    PMax non è una Search estesa: è cross-network (Search, Display,
    YouTube, Gmail, Maps). Google decide placement e combinazioni creative.
    Fornisci asset + audience signals di qualità e lascia che l'algoritmo
    ottimizzi.

    ⚠ CONCETTO CHIAVE: PMax ≠ Search estesa.
    PMax si basa su asset e audience signals, non su keyword.
    Un PMax con asset scadenti e senza audience signals è denaro sprecato.

    INTENTO UTENTE
    Mid/bottom funnel: Google ottimizza per catturare l'intent rilevante
    attraverso tutti i canali. Reach più ampio della Search pura.
    tROAS o Max Conversion Value come strategia di bid raccomandata.

    ── STRUTTURA CORRETTA ──────────────────────────────────────────
    ✅ Una campagna per mercato/lingua
    ✅ Asset group per lingua (o per segmento: Luxury, Family, Business)
       → Final URL corretto per lingua in ogni asset group
       → Asset NON identici tra asset group: temi diversi
    ✅ Audience signals OBBLIGATORI in ogni asset group:
       • Remarketing lists (visitatori sito, checkout abandoners)
       • In-market: Travel, Hotel & Accommodation, Luxury Travel
       • Customer match (se disponibile)
       → Più signals = periodo apprendimento 1–2 settimane (vs 3–6 senza)
    ✅ Una sola conversione primaria chiara per campagna

    ── ASSET GROUP REQUIREMENTS ────────────────────────────────────
    ✅ Headlines: min 3, consigliati 8+ per "Excellent" ad strength (≤30 chars)
    ✅ Long headlines: min 1 (≤90 chars — usato su Display/YouTube)
    ✅ Descriptions: min 2, consigliati 4 (≤90 chars)
    ✅ Immagini OBBLIGATORIE:
       • Landscape 1200×628 (hotel facade/destination)
       • Square 1200×1200 (camera, piscina, esperienza signature)
    ✅ Logo 1200×1200 PNG trasparente
    ◐ Video: opzionale ma fortemente consigliato (16:9 YouTube)
       → Senza video Google ne genera uno automatico (bassa qualità)

    ── BRAND EXCLUSION — CRITICO PRIMA DEL PUBLISH ────────────────
    ❌ SENZA brand exclusion list, PMax competiterà con la Brand Search
       sulle query branded → cannibalization → costi CPC più alti.
    ✅ Aggiungere brand exclusion list (exact match: nome hotel + varianti)
       PRIMA di pubblicare la campagna PMax.
    ✅ URL expansion = OFF per default negli hotel (mantenere controllo LP)

    ── MESSAGGIO ──────────────────────────────────────────────────
    Mix tra performance e storytelling. NON è la stessa cosa della Search:
    ✅ Headlines mix: alcuni orientati conversion, altri aspirazionali
       • "Prenota Diretto e Risparmia"    (30 chars)
       • "Suite Vista Mare con Terrazza"  (30 chars)
       • "Miglior Tariffa Garantita"      (25 chars)
       • "Colazione Inclusa Ogni Giorno"  (29 chars)
    ✅ Long headlines: evocativi, usati su Display/YouTube
    ❌ NON copiare asset identici dalla Search — PMax ha reach diverso

    ── BUDGET ─────────────────────────────────────────────────────
    🎯 30–50% del budget totale mensile
    PMax è la campagna con il maggior potenziale di scala nell'account.
    tROAS o Max Conversion Value come bid strategy raccomandata.

    ── KPI / BID STRATEGY ─────────────────────────────────────────
    • Target ROAS (se 30+ conversioni/mese) → maximize_conversion_value
    • Target CPA (per lead-gen/telefonate)
    • Maximize Conversion Value (avvio, dati limitati)

    ── ERRORI DA BLOCCARE ─────────────────────────────────────────
    ⛔ Nessun audience signal → apprendimento lentissimo (3–6 settimane)
    ⛔ Nessuna differenziazione asset per lingua → copy sbagliata per mercato
    ⛔ Asset identici alla Search → perdi l'opportunità cross-channel
    ⛔ Nessuna brand exclusion → cannibalization Brand Search garantita
    ⛔ URL expansion abilitata subito → traffico su pagine irrilevanti
    ⛔ < 5 headlines → ad strength "Poor", reach limitatissimo

    ── DIFFERENZIAZIONE OBBLIGATORIA ──────────────────────────────
    PMax ≠ Search Brand, ≠ Search Acquisition.
    Struttura, asset, obiettivo e reach sono completamente diversi.
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        # PMax: prefer brand_assets if configured, else generic
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
                f"[PMax/{lang.code}] Solo {len(headlines)} headline configurati "
                f"(min 3, consigliati {_MIN_HEADLINES_EXCELLENT}+ per ad strength 'Excellent'). "
                "Con pochi headline Google ha combinazioni creative limitate e performance ridotte."
            )

        return warnings

    def validate_strategy(self, brief: "Brief") -> List[str]:
        warnings: List[str] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return warnings

        entry = brief.budgets.by_campaign_type.get("performance_max")
        if entry and entry.total > 0:
            pct = entry.total / total * 100
            if pct < 30:
                warnings.append(
                    f"[PMax] Budget {pct:.1f}% del totale (consigliato 30–50%). "
                    "Performance Max richiede volume sufficiente per l'algoritmo di ottimizzazione. "
                    "Con budget basso il periodo di apprendimento si allunga e le performance soffrono."
                )
            elif pct > 60:
                warnings.append(
                    f"[PMax] Budget {pct:.1f}% del totale (max consigliato 50%). "
                    "PMax dominante: rischio che cannibaliz le campagne Brand e Acquisition. "
                    "Mantieni Brand Search attivo con budget dedicato per proteggere le query branded."
                )

        # Audience signals check
        has_signals = (
            bool(brief.audiences.remarketing_lists)
            or bool(brief.audiences.in_market_segments)
            or brief.audiences.customer_match.enabled
        )
        if not has_signals:
            warnings.append(
                "[PMax] ⚠ Nessun audience signal configurato. "
                "Senza segnali (remarketing lists, in-market segments, customer match), "
                "il periodo di apprendimento sarà 3–6 settimane invece di 1–2. "
                "Configura almeno: remarketing list sito (30 giorni), in-market Travel."
            )

        # Brand exclusion — warn if no brand terms (can't build exclusion list)
        brand_configured = any(bool(l.brand_terms) for l in brief.languages)
        if not brand_configured:
            warnings.append(
                "[PMax] ⛔ Nessun brand term configurato. "
                "Senza brand terms non è possibile impostare la brand exclusion list in PMax. "
                "PMax senza brand exclusion cannibalizzerà le campagne Brand Search "
                "e farà aumentare i CPC delle query branded."
            )

        return warnings
