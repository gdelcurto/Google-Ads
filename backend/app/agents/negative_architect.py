"""
Negative Architect Agent — TECH Cross-cutting Agent.

Validates the negative keyword strategy across the brief:
brand negatives in Acquisition, competitor isolation, spam term coverage.
Critical for preventing wasted spend and keyword cannibalization.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief
    from app.domain.schemas.campaign_plan import CampaignPlan


class NegativeArchitectAgent(CampaignAgent):
    TYPE_KEY = "negative_architect"
    LEVEL = AgentLevel.TECHNICAL
    BLOCKS_PUBLISH = False
    BLOCKING_RULES = []

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    NEGATIVE ARCHITECT — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Verifica la strategia delle keyword negative per prevenire:
    - Cannibalization Brand ↔ Acquisition
    - Traffico irrilevante che spreca budget
    - Confusione tra tipi di campagna

    NEGATIVE LIST OBBLIGATORIE
    ───────────────────────────────────────────────────────────────
    1. Brand Negatives List (Acquisition + PMax)
       → Exact match dei brand terms → impedisce query branded in Acquisition
       → Essenziale per separare Brand Search da Acquisition

    2. Spam/Noise Negatives (tutte le campagne)
       → "gratis", "gratuito", "free", "lavoro", "offerte di lavoro"
       → "recensioni", "tripadvisor", "booking", "expedia"
       → Hostel, affitto, appartamento (se non pertinente)

    3. Competitor Negatives (opzionale, campagne Brand)
       → Nomi competitor come negative in Brand per evitare confusione

    CRITICO
    Senza brand negatives in Acquisition, le query branded atterrano
    lì invece che in Brand Search → CPC alto + ROAS basso + confusione.
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Check if brand terms are configured (needed to build brand negative list)
        has_brand_terms = any(bool(lang.brand_terms) for lang in brief.languages)

        if not has_brand_terms:
            issues.append(ValidationIssue(
                code="NEG_NO_BRAND_TERMS_FOR_NEGATIVES",
                message=(
                    "Nessun brand term configurato. "
                    "Senza brand terms non è possibile costruire la 'Brand Negatives List' "
                    "da applicare alle campagne Acquisition e PMax. "
                    "Le query branded atterreranno in Acquisition causando cannibalization e CPC alti."
                ),
                level="warning",
                blocks_publish=False,
                agent="NegativeArchitectAgent",
            ))
        else:
            # Check if brand exclusions are explicitly configured
            langs_without_exclusions = [
                lang.code for lang in brief.languages
                if lang.brand_terms and not lang.brand_exclusions
            ]
            if langs_without_exclusions:
                issues.append(ValidationIssue(
                    code="NEG_BRAND_EXCLUSIONS_NOT_CONFIGURED",
                    message=(
                        f"[{', '.join(langs_without_exclusions)}] Brand terms configurati ma "
                        "'brand_exclusions' non esplicitamente impostati. "
                        "Configura 'brand_exclusions' per ogni lingua con i termini esatti "
                        "da usare come negative in Acquisition e PMax "
                        "(es. nome hotel + varianti ufficiali)."
                    ),
                    level="info",
                    blocks_publish=False,
                    agent="NegativeArchitectAgent",
                ))

        return issues
