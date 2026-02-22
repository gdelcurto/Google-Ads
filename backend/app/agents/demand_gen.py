"""
Demand Gen Campaign Agent — Senior Google Ads Strategist: Hospitality.

SKILL: Genera nuova domanda e lavora su intento latente (upper/mid funnel).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.domain.schemas.brief import LanguagePlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


# Transactional copy that doesn't belong in Demand Gen (upper-funnel)
_TRANSACTIONAL_SIGNALS = [
    "prenota", "book now", "reserv",
    "miglior prezzo", "miglior tariff", "best price",
    "sito ufficiale", "official site",
    "offerta", "sconto", "promo",
    "4 stelle", "3 stelle", "5 stelle", "4 star", "3 star",
]

# Travel/hotel audience signals that indicate correct Demand Gen targeting
_TRAVEL_SIGNALS = [
    "travel", "hotel", "accommodation", "trip", "vacation",
    "viaggio", "viaggi", "turismo", "albergo", "soggiorno",
]


class DemandGenAgent(CampaignAgent):
    TYPE_KEY = "demand_gen"
    LEVEL = AgentLevel.SPECIALIST
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "DG_NO_IN_MARKET_SEGMENTS",
    ]

    # Demand Gen = creative fatigue detection + ad copy variants for upper-funnel audiences
    SKILL_FILES = (
        "04-meta-creative-fatigue-detection.md",
        "09-google-and-meta-ad-copy-variant-generator.md",
        "15-google-and-meta-channel-mix-optimizer.md",
    )

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    DEMAND GEN STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    OBIETTIVO STRATEGICO
    Generare nuova domanda e lavorare su intento latente.
    Raggiungere utenti PRIMA che inizino a cercare attivamente.
    Costruire desiderio e ispirazione nelle fasi upper/mid funnel
    su YouTube, Gmail e Google Discover.

    ⚠ CONCETTO CHIAVE: Demand Gen ≠ Search.
    Non si basa su keyword. Si basa su audience.
    Non si misura con ROAS diretto ma con conversioni assistite,
    CTR e reach incrementale.

    INTENTO UTENTE
    Upper/mid funnel: inspirazione, scoperta, comparazione iniziale.
    L'utente non sta cercando attivamente — sta esplorando contenuti.
    Copy promozionale/transazionale è fuori luogo e distruttivo.

    ── STRUTTURA ──────────────────────────────────────────────────
    ✅ Una campagna per mercato
    ✅ Asset group per lingua o segmento (non copiare da Search)
    ❌ NESSUNA logica keyword-based — è puramente audience-driven

    ── AUDIENCE OBBLIGATORIE ──────────────────────────────────────
    🎯 In-market: Travel
    🎯 In-market: Hotel & Accommodation
    🎯 In-market: Trips to [destinazione]
    🎯 Custom segment competitor (URL dei competitor diretti)
    🎯 Lookalike visitatori sito (seed remarketing list)
    → Senza queste audience il targeting è troppo ampio e inefficiente

    ── ASSET OBBLIGATORI ──────────────────────────────────────────
    ✅ Minimo 3 immagini per lingua:
       • Landscape 1200×628 (hotel facade, location, destination)
       • Square 1200×1200 (camera, piscina, experience)
       • Portrait 960×1200 (lifestyle, persone, atmosfera)
    ✅ Headline (≤30 chars): brevi, evocativi, aspirazionali
    ✅ Descriptions: esperienziali, emozionali
    ◐ Video: fortemente consigliato (16:9 YouTube) → aumenta reach

    ── MESSAGGIO ──────────────────────────────────────────────────
    ✅ Copy aspirazionale ed emozionale:
       • "Il Tuo Rifugio a Due Passi dal Mare" (35 chars — per long headline)
       • "Vivi Roma Come un Local"              (22 chars)
       • "Un'Oasi di Pace tra le Dolomiti"      (31 chars — long headline)
       • "Scopri il Lusso Discreto"             (24 chars)
       • "Vista Oceano dalla Tua Suite"          (29 chars)
    ✅ CTA softi: "Scopri di più", "Lasciati ispirare", "Esplora"
    ❌ NON usare (copy transazionale — sbagliato per questo funnel stage):
       × "Prenota ora"
       × "Miglior prezzo garantito"
       × "4 stelle Roma centro"
       × "Offerta speciale"
       × Copy promozionale aggressivo

    COPY RULE: Demand Gen copy = "Esperienza + Emozione + Lifestyle + Location"
    L'utente deve desiderare il soggiorno, non essere spinto a prenotare.

    ── BUDGET ─────────────────────────────────────────────────────
    🎯 5–15% del budget totale mensile
    CPA più alto rispetto alla Search nel breve periodo (è normale).
    ROAS inferiore alla Search — si misura su conversioni assistite.
    Con budget < 5% non raggiunge massa critica per l'apprendimento.

    ── KPI ────────────────────────────────────────────────────────
    ✅ KPI primari: CTR, video completion rate, view-through conversions
    ✅ KPI secondari: conversioni assistite (DemandGen → Search → conversion)
    ❌ NON giudicare con ROAS diretto — questo è top-of-funnel

    ── ERRORI DA BLOCCARE ─────────────────────────────────────────
    ⛔ Stessa struttura della Search → logica totalmente diversa
    ⛔ Nessuna immagine → campagna non può girare
    ⛔ Nessuna audience → targeting generico, efficienza minima
    ⛔ Copy transazionale → tono sbagliato per fase di ispirazione
    ⛔ Budget < 5% → nessun apprendimento, risultati non significativi
    ⛔ Valutare con ROAS diretto → indicatore sbagliato per upper funnel

    ── DIFFERENZIAZIONE OBBLIGATORIA ──────────────────────────────
    Demand Gen ≠ Retargeting prospecting, ≠ Search, ≠ PMax.
    Asset, audience, copy, KPI e logica strategica sono completamente diversi.
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        headlines = self.get_headlines(lang)

        # Detect transactional copy in Demand Gen (wrong tone for upper funnel)
        transactional_found = []
        for h in headlines:
            h_lower = h.lower()
            if any(sig in h_lower for sig in _TRANSACTIONAL_SIGNALS):
                transactional_found.append(h)

        if transactional_found:
            examples = '", "'.join(transactional_found[:2])
            issues.append(ValidationIssue(
                code="DG_TRANSACTIONAL_COPY",
                message=(
                    f'[DemandGen/{lang.code}] Copy transazionale/promozionale rilevata: "{examples}". '
                    "Demand Gen è upper-funnel (inspirazione, non prenotazione). "
                    "Usa copy aspirazionale: 'Il tuo rifugio nel cuore di Roma', 'Vivi Roma come un local'. "
                    "Evita: 'Prenota ora', 'Miglior prezzo', '4 stelle Roma centro'."
                ),
                level="warning",
                blocks_publish=False,
                agent="DemandGenAgent",
                language=lang.code,
            ))

        return issues

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return issues

        entry = brief.budgets.by_campaign_type.get("demand_gen")
        if entry and entry.total > 0:
            pct = entry.total / total * 100
            if pct < 5:
                issues.append(ValidationIssue(
                    code="DG_BUDGET_TOO_LOW",
                    message=(
                        f"[Demand Gen] Budget {pct:.1f}% del totale (consigliato 5–15%). "
                        "Con budget < 5% Demand Gen non raggiunge massa critica per l'apprendimento "
                        "e le performance non sono statisticamente significative."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="DemandGenAgent",
                ))
            elif pct > 20:
                issues.append(ValidationIssue(
                    code="DG_BUDGET_TOO_HIGH",
                    message=(
                        f"[Demand Gen] Budget {pct:.1f}% del totale (max consigliato 15%). "
                        "Budget Demand Gen elevato: in questa fase il CPA è alto e il ROAS basso. "
                        "Valuta di redistribuire verso PMax o Acquisition per conversioni dirette."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="DemandGenAgent",
                ))

        # In-market audience check — OBBLIGATORIA per Demand Gen — hard blocker
        in_market = brief.audiences.in_market_segments
        if not in_market:
            issues.append(ValidationIssue(
                code="DG_NO_IN_MARKET_SEGMENTS",
                message=(
                    "[Demand Gen] Nessun segmento in-market configurato. "
                    "Demand Gen RICHIEDE audience per funzionare correttamente. "
                    "Aggiungi: 'In-market: Travel', 'In-market: Hotel & Accommodation', "
                    "'In-market: Trips to [destinazione]', 'Custom segment competitor'."
                ),
                level="error",
                blocks_publish=True,
                agent="DemandGenAgent",
            ))
        else:
            has_travel = any(
                any(sig in seg.lower() for sig in _TRAVEL_SIGNALS)
                for seg in in_market
            )
            if not has_travel:
                issues.append(ValidationIssue(
                    code="DG_NO_TRAVEL_SEGMENTS",
                    message=(
                        "[Demand Gen] Nessun segmento in-market correlato al travel o hospitality. "
                        "Aggiungi segmenti specifici: 'In-market: Hotel & Accommodation', "
                        "'In-market: Travel', 'In-market: City Breaks'."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="DemandGenAgent",
                ))

        # Lookalike/remarketing audience check
        if not brief.audiences.remarketing_lists:
            issues.append(ValidationIssue(
                code="DG_NO_REMARKETING_SEED",
                message=(
                    "[Demand Gen] Nessuna lista remarketing/lookalike configurata. "
                    "Demand Gen performa significativamente meglio con lookalike dei visitatori del sito. "
                    "Configura almeno una lista remarketing (30–90 giorni) come seed per il lookalike."
                ),
                level="warning",
                blocks_publish=False,
                agent="DemandGenAgent",
            ))

        return issues
