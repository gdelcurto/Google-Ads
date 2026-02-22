"""
Naming Enforcer Agent — TECH Cross-cutting Agent.

Validates campaign and ad group naming conventions against the
NamingConvention configured in the brief. Consistent naming is critical
for reporting, filtering, and account hygiene.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief
    from app.domain.schemas.campaign_plan import CampaignPlan


class NamingEnforcerAgent(CampaignAgent):
    TYPE_KEY = "naming_enforcer"
    LEVEL = AgentLevel.TECHNICAL
    BLOCKS_PUBLISH = False
    BLOCKING_RULES = []

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    NAMING ENFORCER — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Verifica che i nomi di campagna e ad group rispettino la convenzione
    definita in brief.naming_convention.

    FORMATO STANDARD
    {lang} | {type} | {subtype} | {match_type}
    es. "IT | Search | Brand | Exact"
        "EN | PMax | All"
        "DE | Display | Retargeting | 30d"

    REGOLE
    ✅ Separatore coerente (default: " | ")
    ✅ Componenti nell'ordine corretto
    ✅ Lingua in maiuscolo (IT, EN, FR)
    ✅ Tipo campagna leggibile (Search, PMax, Display, DemandGen)
    ✅ Nessun carattere speciale problematico

    IMPATTO
    Naming inconsistente rende difficile:
    - Filtrare report per tipo campagna
    - Applicare script di automazione
    - Fare audit dell'account nel tempo
    """

    def validate_plan(
        self,
        brief: "Brief",
        campaigns: List["CampaignPlan"],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        separator = brief.naming_convention.separator

        for campaign in campaigns:
            name = campaign.campaign_name
            if not name:
                issues.append(ValidationIssue(
                    code="NAMING_EMPTY_CAMPAIGN_NAME",
                    message=(
                        f"[Naming/{campaign.language_code}] Campagna senza nome. "
                        "Ogni campagna deve avere un nome leggibile che segua la convenzione."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="NamingEnforcerAgent",
                    language=campaign.language_code,
                ))
                continue

            # Check separator is present (minimal structure check)
            if separator and separator not in name:
                issues.append(ValidationIssue(
                    code="NAMING_SEPARATOR_MISSING",
                    message=(
                        f"[Naming/{campaign.language_code}] Nome campagna '{name}' "
                        f"non usa il separatore configurato ('{separator}'). "
                        f"Formato atteso: {{lang}}{separator}{{type}}{separator}{{subtype}}. "
                        f"es. 'IT{separator}Search{separator}Brand'."
                    ),
                    level="info",
                    blocks_publish=False,
                    agent="NamingEnforcerAgent",
                    language=campaign.language_code,
                ))

        return issues
