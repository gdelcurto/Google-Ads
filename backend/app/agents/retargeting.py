"""
Retargeting Campaign Agent — Senior Google Ads Strategist: Hospitality.

SKILL: Recupera utenti caldi e aumenta il conversion rate.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.domain.schemas.brief import LanguagePlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


# Words/phrases that signal urgency or personalization — at least one should appear
_URGENCY_SIGNALS = [
    "ancora", "still", "completa", "complete", "ritorna", "return",
    "speciale", "special", "offerta", "offer", "sconto", "discount",
    "prenota", "riservat", "esclusiv", "limited", "limitat",
    "tornat", "aspettiamo", "non perdere", "disponibil", "ultima",
]

# Transactional/generic phrases that indicate copy not differentiated from acquisition
_ACQUISITION_SIGNALS = [
    "4 stelle", "3 stelle", "5 stelle", "4 star", "3 star",
    "hotel centro", "hotel roma", "hotel milan", "hotel firenze",
    "vicino a", "min dalla", "posizione",
]


class RetargetingAgent(CampaignAgent):
    TYPE_KEY = "retargeting"
    LEVEL = AgentLevel.SPECIALIST
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "RET_NO_REMARKETING_LISTS",
    ]

    # Retargeting = ad extension/sitelink audit + copy variants for warm audiences
    SKILL_FILES = (
        "21-google-ad-extension-audit.md",
        "09-google-and-meta-ad-copy-variant-generator.md",
        "22-meta-retargeting-window-analysis.md",
    )

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    RETARGETING STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    OBIETTIVO STRATEGICO
    Recuperare utenti caldi che hanno già visitato il sito ma non hanno
    prenotato. Aumentare il conversion rate senza spendere budget su
    audience fredde. Questi utenti ti conoscono già — non hai bisogno
    di presentarti, hai bisogno di convincerli a completare.

    INTENTO UTENTE
    Caldo: considerazione avanzata o abbandono in fase di prenotazione.
    Sa chi sei. Probabilmente sta ancora confrontando opzioni.
    CPA atteso: il PIÙ BASSO dell'account (audience pre-qualificata).

    ── SEGMENTAZIONE OBBLIGATORIA ─────────────────────────────────
    Non usare un'unica lista generica. Segmenta per lookback + intent:

    🔴 7 giorni — aggressivo (abbandono recente, alta intent):
       Copy: "Completa la Prenotazione" | "Disponibilità Limitata"
       Bid: +40–50% rispetto alla lista 30 giorni

    🟡 30 giorni — reminder (ancora in fase di considerazione):
       Copy: "Stai Ancora Cercando?" | "Offerta Riservata per Te"
       Bid: baseline

    🟠 Checkout abandoners — MASSIMA PRIORITÀ:
       Copy: "Completa l'Acquisto" | "La Tua Camera Ti Aspetta"
       Bid: +50–70% (massima bid adjustment)

    ── MESSAGGIO ──────────────────────────────────────────────────
    ✅ Urgenza autentica (non aggressiva):
       • "Completa la Prenotazione"  (24 chars) — diretto, non pressante
       • "Tariffa Riservata per Te"  (24 chars) — personalizzazione percepita
       • "La Tua Camera Ti Aspetta" (24 chars) — calore, attesa
       • "Ultime Camere Disponibili" (25 chars) — scarsità reale
       • "Prenota, Cancelli Gratis"  (24 chars) — rimuovi la paura
       • "Sconto Esclusivo per Oggi" (25 chars) — incentivo temporale
    ✅ Puoi includere il brand name
    ❌ NO copia della Demand Gen prospecting
    ❌ NO copia identica all'Acquisition (sono già oltre quella fase)
    ❌ NO toni aggressivi: "ULTIMA OCCASIONE!!!" è controproducente

    COPY RULE: Retargeting copy = "Urgenza + Rassicurazione + Incentivo"
    Il tono deve essere premuroso e invitante, non insistente.

    ── BUDGET ─────────────────────────────────────────────────────
    🎯 5–10% del budget totale mensile
    Piccolo budget, grande impatto. L'audience è pre-qualificata.
    CPA tipicamente 30–50% più basso rispetto all'Acquisition.

    ── KPI / BID STRATEGY ─────────────────────────────────────────
    • Target CPA con target PIÙ BASSO rispetto all'Acquisition
    • Bid adjustments: +20–50% per lista 7 giorni vs 30–90 giorni
    • Customer match → bid massima, copy più personalizzata

    ── ERRORI DA BLOCCARE ─────────────────────────────────────────
    ⛔ Nessuna lista remarketing → campagna non può girare
    ⛔ Unica lista generica → nessuna segmentazione per urgency
    ⛔ Stessa copy dell'Acquisition → opportunità sprecata su audience calda
    ⛔ Copy senza urgency signals → tasso di recupero bassissimo
    ⛔ Struttura identica alla Search → Display ha logica diversa
    ⛔ Budget > 15% → sovrainvestimento su audience già acquisita

    ── DIFFERENZIAZIONE OBBLIGATORIA ──────────────────────────────
    Retargeting ≠ Prospecting: copy, audience, bid, segmentazione sono diversi.
    Separare fisicamente le campagne prospecting da quelle retargeting.
    """

    def get_headlines(self, lang: LanguagePlan) -> List[str]:
        if lang.retargeting_assets and lang.retargeting_assets.headlines:
            return lang.retargeting_assets.headlines
        return lang.headlines

    def get_descriptions(self, lang: LanguagePlan) -> List[str]:
        if lang.retargeting_assets and lang.retargeting_assets.descriptions:
            return lang.retargeting_assets.descriptions
        return lang.descriptions

    def validate_copy(self, lang: LanguagePlan) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        headlines = self.get_headlines(lang)

        if headlines:
            urgency_found = any(
                any(signal in h.lower() for signal in _URGENCY_SIGNALS)
                for h in headlines
            )
            if not urgency_found:
                issues.append(ValidationIssue(
                    code="RET_NO_URGENCY_SIGNALS",
                    message=(
                        f"[Retargeting/{lang.code}] Nessun headline contiene segnali di urgenza o personalizzazione. "
                        "Retargeting deve usare copy con urgency per recuperare visitatori che non hanno prenotato. "
                        "Configura 'retargeting_assets.headlines' con testi come: "
                        "'Completa la prenotazione', 'Offerta riservata', 'Ultime camere disponibili'."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                    language=lang.code,
                ))

            # Warn if copy looks like acquisition (no differentiation)
            acquisition_like = any(
                any(sig in h.lower() for sig in _ACQUISITION_SIGNALS)
                for h in headlines
            )
            if acquisition_like:
                issues.append(ValidationIssue(
                    code="RET_ACQUISITION_LIKE_COPY",
                    message=(
                        f"[Retargeting/{lang.code}] Alcuni headline sembrano copy da Acquisition "
                        "(categoria/destinazione). Retargeting è per utenti che già conoscono l'hotel: "
                        "usa urgency e personalizzazione, non presentazione della struttura."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                    language=lang.code,
                ))

        if not (lang.retargeting_assets and lang.retargeting_assets.headlines):
            issues.append(ValidationIssue(
                code="RET_GENERIC_HEADLINES",
                message=(
                    f"[Retargeting/{lang.code}] Usando headline generici per le campagne Retargeting. "
                    "Per massimizzare il recupero dei visitatori configura 'retargeting_assets.headlines' "
                    "con copy urgency: 'Completa la prenotazione', 'Tariffa riservata', "
                    "'Ultime camere disponibili', 'Sconto esclusivo per oggi'."
                ),
                level="warning",
                blocks_publish=False,
                agent="RetargetingAgent",
                language=lang.code,
            ))

        return issues

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        total = brief.budgets.total_monthly_eur
        if total <= 0:
            return issues

        entry = brief.budgets.by_campaign_type.get("retargeting")
        if entry and entry.total > 0:
            pct = entry.total / total * 100
            if pct < 5:
                issues.append(ValidationIssue(
                    code="RET_BUDGET_TOO_LOW",
                    message=(
                        f"[Retargeting] Budget {pct:.1f}% del totale (consigliato 5–10%). "
                        "Budget Retargeting troppo basso: audience pre-qualificata con CPA basso, "
                        "è uno dei canali più efficienti — non sottoinvestire."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                ))
            elif pct > 15:
                issues.append(ValidationIssue(
                    code="RET_BUDGET_TOO_HIGH",
                    message=(
                        f"[Retargeting] Budget {pct:.1f}% del totale (max consigliato 10%). "
                        "Budget Retargeting elevato: l'audience è limitata (solo visitatori del sito). "
                        "Con budget troppo alto si satura rapidamente il pubblico disponibile."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                ))

        # Check remarketing lists — hard blocker: campaign cannot run without them
        rm_lists = brief.audiences.remarketing_lists
        if not rm_lists:
            issues.append(ValidationIssue(
                code="RET_NO_REMARKETING_LISTS",
                message=(
                    "[Retargeting] Nessuna lista remarketing configurata. "
                    "La campagna Retargeting NON può girare senza liste audience. "
                    "Configura almeno: '7 giorni' (aggressivo), '30 giorni' (reminder), "
                    "'Checkout Abandoners' (massima priorità)."
                ),
                level="error",
                blocks_publish=True,
                agent="RetargetingAgent",
            ))
        else:
            lookbacks = [rm.lookback_days for rm in rm_lists]
            has_short = any(lb <= 7 for lb in lookbacks)
            has_mid = any(8 <= lb <= 30 for lb in lookbacks)

            if not has_short:
                issues.append(ValidationIssue(
                    code="RET_NO_SHORT_LOOKBACK",
                    message=(
                        "[Retargeting] Manca una lista con lookback ≤7 giorni (intento recente ad alta urgency). "
                        "Aggiungi una lista '7 giorni' o 'Checkout Abandoners' per il targeting aggressivo "
                        "degli utenti con abbandono recente."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                ))
            if not has_mid:
                issues.append(ValidationIssue(
                    code="RET_NO_MID_LOOKBACK",
                    message=(
                        "[Retargeting] Manca una lista con lookback 8–30 giorni (fase reminder). "
                        "Aggiungi una lista '30 giorni' per utenti ancora in fase di consideration "
                        "con tone premuroso e incentivo moderato."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="RetargetingAgent",
                ))

        return issues
