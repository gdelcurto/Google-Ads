"""
Bidding Strategist Agent — L1 Strategic Agent.

Validates per-campaign-type bid strategy configuration before generation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.domain.schemas.brief import BidStrategyChoice
from app.skills import CORE_PPC_FRAMEWORK

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief

# Strategies not compatible with Performance Max campaigns
_PMAX_INCOMPATIBLE = {BidStrategyChoice.maximize_clicks, BidStrategyChoice.target_impression_share}

# Strategies not compatible with Display/Retargeting/DemandGen
_DISPLAY_INCOMPATIBLE = {BidStrategyChoice.target_impression_share}


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
    Valida la strategia di offerta configurata per ogni tipo di campagna.
    Assicura compatibilità tra strategia e tipo di campagna.

    STRATEGIE DISPONIBILI
    ───────────────────────────────────────────────────────────────
    maximize_conversions      → Numero di Conversioni (smart bidding)
    maximize_conversion_value → Valore di Conversione (smart bidding)
    maximize_clicks           → Massimizza i Click (volume puro)
    target_impression_share   → Quota Impressioni (visibilità)

    COMPATIBILITÀ
    ───────────────────────────────────────────────────────────────
    Performance Max: solo maximize_conversions o maximize_conversion_value
    Display/Retargeting/DemandGen: no target_impression_share
    Search Brand: maximize_clicks è efficace per la protezione del brand
    Search Acquisition: maximize_conversions è la scelta standard
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for ct_key in brief.campaign_types:
            choice = brief.objectives.get_bid_strategy_for(ct_key)

            if ct_key == "performance_max" and choice in _PMAX_INCOMPATIBLE:
                issues.append(ValidationIssue(
                    code="BIDDING_PMAX_INCOMPATIBLE",
                    message=(
                        f"Performance Max non supporta '{choice.value}'. "
                        "Usa 'maximize_conversions' o 'maximize_conversion_value'."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BiddingStrategistAgent",
                ))

            if ct_key in ("retargeting", "demand_gen") and choice in _DISPLAY_INCOMPATIBLE:
                issues.append(ValidationIssue(
                    code="BIDDING_DISPLAY_INCOMPATIBLE",
                    message=(
                        f"'{choice.value}' non è supportato per campagne Display/DemandGen. "
                        "Usa 'maximize_conversions' o 'maximize_conversion_value'."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="BiddingStrategistAgent",
                ))

        return issues
