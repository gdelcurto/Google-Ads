"""
Acquisition (Non-Brand) Search Campaign Agent — Senior Google Ads Strategist: Hospitality.

SKILL: Acquisisci nuova domanda da utenti non ancora consapevoli del brand.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import CampaignAgent
from app.domain.schemas.brief import LanguagePlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


class AcquisitionAgent(CampaignAgent):
    TYPE_KEY = "search_acquisition"

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    ACQUISITION SEARCH STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    OBIETTIVO STRATEGICO
    Acquisire nuova domanda da utenti che NON conoscono ancora il brand.
    Competere contro Booking, Expedia e altri hotel nella SERP mostrando
    i differenziatori più rilevanti per chi cerca una struttura in quella
    destinazione/categoria.

    INTENTO UTENTE
    Ricerca categoria + destinazione. Non conosce l'hotel.
    Cerca: "hotel 4 stelle roma centro", "hotel con spa firenze", "hotel vista mare amalfi".
    ROAS atteso: inferiore al Brand (CPA più alto, audience fredda).

    ── STRUTTURA CORRETTA ──────────────────────────────────────────
    ✅ Campagne o ad group TEMATICI (non un unico generico):
       • City intent: "hotel roma centro", "hotel vatiano"
       • Categoria: "hotel 4 stelle roma", "boutique hotel toscana"
       • Proximity: "hotel vicino stazione", "hotel centro storico"
       • Occasion/intent: "hotel per famiglie", "hotel business roma"
    ✅ Match types:
       • Phrase match → controllo
       • Broad match → discovery con negative list forte
    ❌ NO Exact match in Acquisition → usa la Brand campaign per quello

    ── NEGATIVE LIST (CRITICA) ────────────────────────────────────
    ✅ Brand terms dell'hotel come Exact negative (shared list "Brand Negatives")
       → previene query branded di atterrare in Acquisition (CPC sprecati)
    ✅ Extended negatives: hostel, affitto, gratis, lavoro, airbnb,
       recensioni, tripadvisor, booking, expedia, agoda

    ── MESSAGGIO ──────────────────────────────────────────────────
    ❌ MAI il brand name negli headline Acquisition
       → cannibalization: la Brand campaign perde la query al tuo posto
       → budget spreco: paghi CPC brand-intent nel contesto sbagliato
    ✅ Ogni headline = argomento di vendita INDIPENDENTE. Varia i temi:
       • Categoria + stelle + città: "Hotel 4 Stelle Roma Centro" (24 chars)
       • Posizione concreta: "3 Min dalla Stazione" (20 chars)
       • Servizio desiderabile: "Piscina Infinity sul Tetto" (25 chars)
       • Beneficio incluso: "Colazione Buffet Ogni Giorno" (28 chars)
       • Senso evocativo: "Vista Panoramica sulla Laguna" (29 chars)
       • Praticità: "Parcheggio Gratuito Incluso" (27 chars)
    ✅ Keyword insertion {KeyWord} appropriato per ad group tematici
    ❌ NO "Sito Ufficiale" / "Prenota Direttamente" → messaging da Brand

    COPY RULE: Acquisition copy = "Categoria + USP + Esperienza"
    Parla dell'hotel come se l'utente non lo conoscesse ancora.

    ── BUDGET ─────────────────────────────────────────────────────
    🎯 30–45% del budget totale mensile
    La campagna con maggior peso sull'acquisizione di nuovi clienti.
    ROAS inferiore al Brand — è normale, è il costo dell'acquisizione.

    ── KPI / BID STRATEGY ─────────────────────────────────────────
    • Target CPA (se dati di conversione > 30/mese)
    • Target ROAS (se tracking booking value attivo)
    • Maximize Conversions (avvio campagna, dati limitati)
    • max_cpc_acquisition cap applica se impostato

    ── ERRORI DA BLOCCARE ─────────────────────────────────────────
    ⛔ Brand name in qualsiasi headline → cannibalization immediata
    ⛔ Nessuna segmentazione tematica → ad group unico generico = bassa rilevanza
    ⛔ Stessa copy della Brand campaign → intento utente non allineato
    ⛔ ROAS target identico al Brand → segnale che non si capisce il funnel
    ⛔ Budget < 30% → campagna acquisizione sottopotenziata

    ── DIFFERENZIAZIONE OBBLIGATORIA ──────────────────────────────
    Acquisition ≠ Brand: copy, keyword, match type, bid strategy sono TUTTI diversi.
    Se Acquisition e Brand sembrano simili nella logica strategica → errore.
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
                    "Acquisition usa copy generica (categoria/destinazione/USP). "
                    "Sposta questo headline in 'brand_assets.headlines' o rimuovi il brand name."
                )

        # Warn if no type-specific assets configured
        if not (lang.acquisition_assets and lang.acquisition_assets.headlines):
            warnings.append(
                f"[Acquisition/{lang.code}] Usando headline generici per le campagne Acquisition. "
                "Per copy ottimizzata, configura 'acquisition_assets.headlines' con: "
                "categoria/destinazione/USP senza brand name "
                "(es. 'Hotel Roma Centro', '4 Stelle Colosseo', 'Colazione Inclusa')."
            )

        return warnings

    def validate_strategy(self, brief: "Brief") -> List[str]:
        warnings: List[str] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return warnings

        entry = brief.budgets.by_campaign_type.get("search_acquisition")
        if entry and entry.total > 0:
            pct = entry.total / total * 100
            if pct < 30:
                warnings.append(
                    f"[Acquisition] Budget {pct:.1f}% del totale (consigliato 30–45%). "
                    "Budget Acquisition troppo basso per generare volumi di acquisizione significativi. "
                    "Aumenta ad almeno il 30% del budget totale."
                )
            elif pct > 50:
                warnings.append(
                    f"[Acquisition] Budget {pct:.1f}% del totale (max consigliato 45%). "
                    "Budget Acquisition molto elevato. Valuta se redistribuire verso PMax "
                    "per copertura cross-network e reach incrementale."
                )

        # Warn if no keyword themes configured (using vertical template fallback)
        if not brief.acquisition_keywords:
            warnings.append(
                "[Acquisition] Nessun keyword theme specifico configurato. "
                "L'Acquisition usa template verticali come fallback. "
                "Per massimizzare la rilevanza configura keyword themes specifici per questo hotel: "
                "temi consigliati — city intent, categoria, proximity, occasion/intent."
            )

        return warnings
