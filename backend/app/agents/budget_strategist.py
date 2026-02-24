"""
Budget Strategist Agent — L1 Strategic Agent.

Validates budget configuration before campaign generation:
total budget presence, allocation coherence, distribution health.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.skills import CORE_PPC_FRAMEWORK

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief


class BudgetStrategistAgent(CampaignAgent):
    TYPE_KEY = "budget_strategist"
    LEVEL = AgentLevel.STRATEGIC
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "BUDGET_ZERO_TOTAL",
    ]
    SKILL_FILES = (CORE_PPC_FRAMEWORK,)

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    BUDGET STRATEGIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Valida la configurazione del budget prima della generazione.
    Verifica che il budget totale sia impostato, che la distribuzione per tipo
    sia coerente, e che non ci siano incongruenze nei valori.

    CONTROLLI CHIAVE
    ✅ Budget mensile totale > 0 (OBBLIGATORIO)
    ✅ Somma allocata ≈ totale (margine ±10%)
    ✅ Nessun tipo ha budget 0 se è nella lista campagne attive
    ✅ Budget minimo per tipo rispetta le soglie di efficienza algoritmica

    ── SOGLIE MINIME PER TIPO ──────────────────────────────────────
    Search Brand:     5–15% del totale
    Search Acq:      30–45% del totale
    PMax:            30–50% del totale
    Retargeting:      5–10% del totale
    Demand Gen:       5–15% del totale

    Nota: le soglie individuali sono verificate dai rispettivi agenti L2.
    Questo agente verifica la salute complessiva del budget.
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        total = brief.budgets.total_monthly_eur

        # Total budget must be > 0 — hard blocker
        if total <= 0:
            issues.append(ValidationIssue(
                code="BUDGET_ZERO_TOTAL",
                message=(
                    "Budget mensile totale non configurato o zero. "
                    "Impostare un budget totale in 'budgets.total_monthly_eur' prima di generare il piano."
                ),
                level="error",
                blocks_publish=True,
                agent="BudgetStrategistAgent",
            ))
            return issues

        # Check allocated sum vs total
        by_type = brief.budgets.by_campaign_type
        if by_type:
            allocated = sum(entry.total for entry in by_type.values() if entry.total > 0)
            if allocated > 0:
                unallocated_pct = abs(total - allocated) / total * 100
                if unallocated_pct > 10:
                    issues.append(ValidationIssue(
                        code="BUDGET_ALLOCATION_MISMATCH",
                        message=(
                            f"Budget allocato per tipo ({allocated:.0f}€) differisce dal totale "
                            f"({total:.0f}€) del {unallocated_pct:.1f}%. "
                            "Ricontrollare la distribuzione: la somma dei budget per tipo "
                            "dovrebbe corrispondere al totale mensile."
                        ),
                        level="warning",
                        blocks_publish=False,
                        agent="BudgetStrategistAgent",
                    ))

        # Warn if budget is very low (algorithm learning threshold)
        if 0 < total < 500:
            issues.append(ValidationIssue(
                code="BUDGET_BELOW_LEARNING_THRESHOLD",
                message=(
                    f"Budget mensile totale ({total:.0f}€) è molto basso. "
                    "Con meno di 500€/mese gli algoritmi di Smart Bidding potrebbero non raccogliere "
                    "abbastanza dati per ottimizzare. Considera un budget minimo di 500–1000€/mese "
                    "per ottenere risultati statisticamente significativi."
                ),
                level="warning",
                blocks_publish=False,
                agent="BudgetStrategistAgent",
            ))

        return issues
