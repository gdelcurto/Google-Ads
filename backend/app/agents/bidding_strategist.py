"""
Bidding Strategist Agent — L1 Strategic Agent.

Validates bid strategy selection and KPI target configuration before generation.
Checks consistency between bid strategies, objectives, and available conversion data.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.skills import CORE_PPC_FRAMEWORK

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


class BiddingStrategistAgent(CampaignAgent):
    TYPE_KEY = "bidding_strategist"
    LEVEL = AgentLevel.STRATEGIC
    BLOCKS_PUBLISH = False
    BLOCKING_RULES = []
    SKILL_FILES = (CORE_PPC_FRAMEWORK,)

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    BIDDING STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Valida la configurazione delle bid strategy e dei target KPI.
    Assicura che le strategie siano appropriate per l'obiettivo e i dati disponibili.

    REGOLE DI SELEZIONE BID STRATEGY
    ───────────────────────────────────────────────────────────────
    Target CPA:    richiede ≥30 conversioni/mese — altrimenti Maximize Conversions
    Target ROAS:   richiede ≥50 conversioni/mese + tracking valore — altrimenti Max Conv Value
    Manual CPC:    appropriato per avvio campagna, scarse conversioni, brand protection
    Max Conversions: default per nuove campagne senza dati storici

    TARGET KPI COERENZA
    ───────────────────────────────────────────────────────────────
    target_cpa_eur:   deve essere > 0 se usato come bid strategy
    target_roas:      1.0 = breakeven; <1.0 = perdita; >3.0 = aggressivo
    max_cpc_brand:    cap per Brand Search (evita CPC troppo alti su query branded)
    max_cpc_acquisition: cap per Acquisition (controllo costi su query generiche)
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        kpi = brief.objectives.kpi

        # Warn if both target_cpa_eur and target_roas are set (conflicting strategies)
        if kpi.target_cpa_eur and kpi.target_roas:
            issues.append(ValidationIssue(
                code="BIDDING_CONFLICTING_TARGETS",
                message=(
                    "Sia target_cpa_eur che target_roas sono configurati. "
                    "Queste sono strategie di bid mutuamente esclusive. "
                    "Usa Target CPA per obiettivi lead/prenotazione, "
                    "Target ROAS per massimizzare il valore di conversione. Scegli una."
                ),
                level="warning",
                blocks_publish=False,
                agent="BiddingStrategistAgent",
            ))

        # Warn if target_roas is suspiciously high (>10x) or very low (<1.5x)
        if kpi.target_roas:
            if kpi.target_roas > 10.0:
                issues.append(ValidationIssue(
                    code="BIDDING_ROAS_TOO_HIGH",
                    message=(
                        f"Target ROAS {kpi.target_roas:.1f}x è molto aggressivo. "
                        "Con target ROAS >10x Google ridurrà drasticamente il volume di impression "
                        "per cercare solo le conversioni ad alto valore. "
                        "Considera un ROAS più realistico (3–8x per hotel) per mantenere volume."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BiddingStrategistAgent",
                ))
            elif kpi.target_roas < 1.5:
                issues.append(ValidationIssue(
                    code="BIDDING_ROAS_TOO_LOW",
                    message=(
                        f"Target ROAS {kpi.target_roas:.1f}x è molto basso (quasi breakeven o in perdita). "
                        "Un ROAS target < 1.5x significa che stai pagando quasi quanto guadagni. "
                        "Verifica il tracking del valore di conversione o alza il target ROAS."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BiddingStrategistAgent",
                ))

        # Warn if target_cpa_eur is extremely low
        if kpi.target_cpa_eur and kpi.target_cpa_eur < 5.0:
            issues.append(ValidationIssue(
                code="BIDDING_CPA_TOO_LOW",
                message=(
                    f"Target CPA {kpi.target_cpa_eur:.2f}€ è molto basso per il settore hospitality. "
                    "CPA target troppo basso causerà volume di impression molto ridotto. "
                    "CPA tipico per hotel: 15–80€ a seconda del mercato e del tipo di campagna."
                ),
                level="warning",
                blocks_publish=False,
                agent="BiddingStrategistAgent",
            ))

        return issues
