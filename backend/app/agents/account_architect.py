"""
Account Architect Agent — L1 Strategic Agent.

Validates the overall account structure before campaign generation:
structural coherence, campaign mix, required dependencies between campaign types.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


class AccountArchitectAgent(CampaignAgent):
    TYPE_KEY = "account_architect"
    LEVEL = AgentLevel.STRATEGIC
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "ARCH_NO_LANGUAGES",
        "ARCH_PMAX_WITHOUT_BRAND",
    ]

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    ACCOUNT ARCHITECT — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Valuta la struttura complessiva dell'account prima della generazione.
    Non genera campagne — valida che le precondizioni strutturali siano soddisfatte.

    CONTROLLI CHIAVE
    ✅ Almeno una lingua configurata
    ✅ Tipi di campagna compatibili tra loro
    ✅ PMax richiede Brand Search attivo (brand exclusion list)
    ✅ Retargeting e Demand Gen richiedono audience configurate
    ✅ Mix coerente con la strategia dell'account

    ── DIPENDENZE CRITICHE ─────────────────────────────────────────
    PMax + Brand Search: SEMPRE insieme
    → PMax senza Brand Search = cannibalization garantita sulle query branded
    → Brand Search senza PMax = copertura cross-network mancante

    Retargeting: richiede remarketing lists configurate
    Demand Gen: richiede in-market segments configurati
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Must have at least one language
        if not brief.languages:
            issues.append(ValidationIssue(
                code="ARCH_NO_LANGUAGES",
                message=(
                    "Nessuna lingua configurata nel brief. "
                    "Il piano non può essere generato senza almeno una lingua."
                ),
                level="error",
                blocks_publish=True,
                agent="AccountArchitectAgent",
            ))
            return issues

        # Check PMax + Brand Search dependency
        active_types = set(brief.budgets.by_campaign_type.keys())
        has_pmax = "performance_max" in active_types
        has_brand = "search_brand" in active_types

        if has_pmax and not has_brand:
            issues.append(ValidationIssue(
                code="ARCH_PMAX_WITHOUT_BRAND",
                message=(
                    "Performance Max attivo senza campagna Brand Search. "
                    "PMax senza brand exclusion list cannibalizzerà le query branded entro 2 settimane. "
                    "Aggiungi una campagna Brand Search e configura la brand exclusion list in PMax."
                ),
                level="error",
                blocks_publish=True,
                agent="AccountArchitectAgent",
            ))

        # Warn if retargeting is selected but no remarketing lists
        has_retargeting = "retargeting" in active_types
        if has_retargeting and not brief.audiences.remarketing_lists:
            issues.append(ValidationIssue(
                code="ARCH_RETARGETING_NO_LISTS",
                message=(
                    "Campagna Retargeting selezionata ma nessuna lista remarketing configurata. "
                    "Retargeting non può girare senza audience. "
                    "Configura le liste in 'audiences.remarketing_lists' o rimuovi il tipo Retargeting."
                ),
                level="warning",
                blocks_publish=False,
                agent="AccountArchitectAgent",
            ))

        # Warn if demand_gen is selected but no in-market segments
        has_demand_gen = "demand_gen" in active_types
        if has_demand_gen and not brief.audiences.in_market_segments:
            issues.append(ValidationIssue(
                code="ARCH_DEMAND_GEN_NO_AUDIENCE",
                message=(
                    "Campagna Demand Gen selezionata ma nessun segmento in-market configurato. "
                    "Demand Gen richiede audience per funzionare. "
                    "Configura i segmenti in 'audiences.in_market_segments' o rimuovi il tipo Demand Gen."
                ),
                level="warning",
                blocks_publish=False,
                agent="AccountArchitectAgent",
            ))

        return issues
