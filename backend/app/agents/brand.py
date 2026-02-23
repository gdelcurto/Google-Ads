"""
Brand Search Campaign Agent — Senior Google Ads Strategist: Hospitality.

SKILL: Difendi la domanda esistente e intercetta utenti che già conoscono il brand.
"""
from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.domain.schemas.brief import LanguagePlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


class BrandAgent(CampaignAgent):
    TYPE_KEY = "search_brand"
    LEVEL = AgentLevel.SPECIALIST
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "BRAND_NO_HEADLINES",
        "BRAND_NO_BRAND_IN_HEADLINES",
        "BRAND_NO_BRAND_TERMS",
    ]

    # Brand copy = RSA copy generation + full account audit knowledge (QS, structure, negatives)
    SKILL_FILES = (
        "09-google-and-meta-ad-copy-variant-generator.md",
        "37-google-ads-audit.md",
        "14-google-quality-score-breakdown.md",
    )

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    BRAND SEARCH STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    OBIETTIVO STRATEGICO
    Difendere la domanda esistente. Intercettare utenti che già conoscono
    il brand prima che le OTA (Booking, Expedia) li convertano con brand bidding.
    Questi utenti sono in fase FINALE di prenotazione: la conversione è quasi
    certa — l'unica domanda è dove prenotano (sito diretto vs OTA).

    INTENTO UTENTE
    Consapevole, spesso in fase finale di prenotazione.
    Cerca il nome esatto dell'hotel o varianti conosciute.
    ROAS atteso: il più alto di tutte le campagne dell'account.

    ── STRUTTURA CORRETTA ──────────────────────────────────────────
    ✅ Una campagna per mercato/lingua
    ✅ Un solo ad group "Brand" (o due: Exact + Phrase)
    ✅ Solo keyword brand:
       • Exact match: [nome hotel], [variante 1]
       • Phrase match: "nome hotel", "nome hotel prenota"
    ❌ NO broad match — troppo impreciso per query branded
    ✅ Negative: recensioni, lavoro, informazioni non rilevanti

    ── MESSAGGIO ──────────────────────────────────────────────────
    ✅ Headline 1 (PINNATA): DEVE contenere il nome brand/hotel
       es. "Grand Hotel Bellevue" | "Hotel Roma Ufficiale"
    ✅ Altre headline: vantaggio esclusivo prenotazione diretta
       • "Miglior Tariffa Garantita"     (24 chars)
       • "Prenota sul Sito Ufficiale"    (26 chars)
       • "Senza Commissioni OTA"         (21 chars)
       • "Cancellazione Gratuita"        (22 chars)
       • "Check-in Anticipato Incluso"   (27 chars)
       • "Sconto 10% Solo Online"        (21 chars)
    ❌ NO termini generici di categoria → quelli vanno in Acquisition
    ❌ NO keyword insertion ({KeyWord}) — brand ha intento fisso

    COPY RULE: Brand copy = "Sito ufficiale + miglior tariffa + vantaggi esclusivi"
    NON deve sembrare la stessa campagna dell'Acquisition.

    ── BUDGET ─────────────────────────────────────────────────────
    🎯 5–15% del budget totale mensile
    Rationale: le query brand sono poche e cheap — proteggere il brand
    non richiede molto budget, ma è criticamente importante farlo.
    Brand ha il ROAS PIÙ ALTO dell'account → non sottoinvestire.

    ── KPI / BID STRATEGY ─────────────────────────────────────────
    • Se max_cpc_brand impostato → Manual CPC con quel cap
    • Se target_cpa_eur impostato → Target CPA
    • Altrimenti → Maximize Conversions
    ROAS atteso: più alto rispetto a Acquisition e PMax.

    ── ERRORI DA BLOCCARE ─────────────────────────────────────────
    ⛔ Keyword generiche in campagna Brand → sprechi e confusione
    ⛔ Copy da Acquisition (senza brand name, toni generici)
    ⛔ Stesso ROAS target della Search non-brand → segnale di misconfigurazione
    ⛔ Budget > 20% → sovrainvestimento su traffico già intenzionato
    ⛔ Brand terms mancanti → campagna non genera nulla

    ── DIFFERENZIAZIONE OBBLIGATORIA ──────────────────────────────
    Brand ≠ Acquisition: copy, intento, match type, bid strategy sono TUTTI diversi.
    Se Brand e Acquisition sembrano strategicamente simili → errore da correggere.
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        if lang.brand_assets and lang.brand_assets.headlines:
            return lang.brand_assets.headlines
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        if lang.brand_assets and lang.brand_assets.descriptions:
            return lang.brand_assets.descriptions
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        headlines = self.get_headlines(lang)

        if not headlines:
            issues.append(ValidationIssue(
                code="BRAND_NO_HEADLINES",
                message=(
                    f"[Brand/{lang.code}] Nessun headline configurato. "
                    "Aggiungere almeno 3 headline in 'headlines' o in 'brand_assets.headlines'."
                ),
                level="error",
                blocks_publish=True,
                agent="BrandAgent",
                language=lang.code,
            ))
            return issues

        # Brand name must appear in at least one headline (accent-insensitive)
        def _strip_accents(s: str) -> str:
            return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()

        brand_lower = [_strip_accents(t.lower()) for t in lang.brand_terms]
        brand_found = any(
            any(bt in _strip_accents(h.lower()) for bt in brand_lower)
            for h in headlines
        )
        if not brand_found:
            example = lang.brand_terms[0] if lang.brand_terms else "nome hotel"
            issues.append(ValidationIssue(
                code="BRAND_NO_BRAND_IN_HEADLINES",
                message=(
                    f"[Brand/{lang.code}] Nessun headline contiene il brand name '{example}'. "
                    "Brand campaigns DEVONO includere il nome dell'hotel (pinnato in posizione 1). "
                    "Configura 'brand_assets.headlines' con copy branded."
                ),
                level="error",
                blocks_publish=True,
                agent="BrandAgent",
                language=lang.code,
            ))

        # Warn if no type-specific assets configured
        if not (lang.brand_assets and lang.brand_assets.headlines):
            issues.append(ValidationIssue(
                code="BRAND_GENERIC_HEADLINES",
                message=(
                    f"[Brand/{lang.code}] Usando headline generici per le campagne Brand. "
                    "Per copy ottimizzata, configura 'brand_assets.headlines' con: "
                    "nome hotel + vantaggi prenotazione diretta (sito ufficiale, miglior tariffa, cancellazione gratis)."
                ),
                level="warning",
                blocks_publish=False,
                agent="BrandAgent",
                language=lang.code,
            ))

        return issues

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return issues

        entry = brief.budgets.by_campaign_type.get("search_brand")
        if entry and entry.total > 0:
            pct = entry.total / total * 100
            if pct < 5:
                issues.append(ValidationIssue(
                    code="BRAND_BUDGET_TOO_LOW",
                    message=(
                        f"[Brand] Budget {pct:.1f}% del totale (consigliato 5–15%). "
                        "Budget Brand troppo basso: le OTA possono superarti nell'asta sulle query branded. "
                        "Aumenta ad almeno il 5% per proteggere il tuo brand SERP."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BrandAgent",
                ))
            elif pct > 20:
                issues.append(ValidationIssue(
                    code="BRAND_BUDGET_TOO_HIGH",
                    message=(
                        f"[Brand] Budget {pct:.1f}% del totale (max consigliato 15%). "
                        "Sovrainvestimento su Brand: il traffico brand è già intenzionato e costa poco. "
                        "Redistribuisci verso Acquisition o PMax per crescita."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BrandAgent",
                ))

        # Brand terms must be configured per language
        for lang in brief.languages:
            if not lang.brand_terms:
                issues.append(ValidationIssue(
                    code="BRAND_NO_BRAND_TERMS",
                    message=(
                        f"[Brand/{lang.code}] Nessun brand term configurato. "
                        "Senza brand terms la campagna Brand non può essere strutturata correttamente. "
                        "Aggiungi nome hotel + varianti in 'brand_terms'."
                    ),
                    level="error",
                    blocks_publish=True,
                    agent="BrandAgent",
                    language=lang.code,
                ))

        return issues
