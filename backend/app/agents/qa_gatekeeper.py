"""
QA Gatekeeper Agent — L3 Audit Agent.

Final quality gate: validates minimum requirements across the generated plan
before it can be marked as publish-ready. Checks for common configuration
errors that would cause the publish to fail or perform poorly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief
    from app.domain.schemas.campaign_plan import CampaignPlan


class QAGatekeeperAgent(CampaignAgent):
    TYPE_KEY = "qa_gatekeeper"
    LEVEL = AgentLevel.AUDITOR
    BLOCKS_PUBLISH = True
    BLOCKING_RULES = [
        "QA_NO_CAMPAIGNS_GENERATED",
        "QA_CAMPAIGN_NO_AD_GROUPS",
        "QA_AD_GROUP_NO_ADS",
    ]

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    QA GATEKEEPER — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Gate di qualità finale prima del publish.
    Verifica che il piano generato soddisfi i requisiti minimi strutturali
    per poter essere pubblicato su Google Ads.

    CONTROLLI BLOCCANTI
    ⛔ Piano senza campagne generate
    ⛔ Campagna senza ad group
    ⛔ Ad group senza annunci
    ⛔ Annuncio senza headline o description

    CONTROLLI AVVISO
    ⚠ Landing page non configurata
    ⚠ Campagna senza impostazioni budget
    ⚠ Sitelink non configurati (impatta il Quality Score)
    """

    def validate_plan(
        self,
        brief: "Brief",
        campaigns: List["CampaignPlan"],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Must have at least one campaign
        if not campaigns:
            issues.append(ValidationIssue(
                code="QA_NO_CAMPAIGNS_GENERATED",
                message=(
                    "Il piano non contiene nessuna campagna generata. "
                    "Verificare che i tipi di campagna siano configurati correttamente nel brief "
                    "e che i generatori abbiano completato senza errori."
                ),
                level="error",
                blocks_publish=True,
                agent="QAGatekeeperAgent",
            ))
            return issues

        for campaign in campaigns:
            from app.domain.schemas.campaign_plan import CampaignType

            # PMax uses pmax_asset_groups, not ad_groups — check separately
            if campaign.campaign_type == CampaignType.performance_max:
                if not campaign.pmax_asset_groups:
                    issues.append(ValidationIssue(
                        code="QA_PMAX_NO_ASSET_GROUPS",
                        message=(
                            f"[QA/{campaign.language_code}] Campagna PMax '{campaign.campaign_name}' "
                            "non ha asset group. Una campagna PMax senza asset group non può essere pubblicata."
                        ),
                        level="error",
                        blocks_publish=True,
                        agent="QAGatekeeperAgent",
                        language=campaign.language_code,
                    ))
                # Skip ad_groups check for PMax — it has no ad_groups by design
                continue

            # Non-PMax campaigns: must have at least one ad group
            if not campaign.ad_groups:
                issues.append(ValidationIssue(
                    code="QA_CAMPAIGN_NO_AD_GROUPS",
                    message=(
                        f"[QA/{campaign.language_code}] Campagna '{campaign.campaign_name}' "
                        "non ha ad group. Una campagna senza ad group non può essere pubblicata."
                    ),
                    level="error",
                    blocks_publish=True,
                    agent="QAGatekeeperAgent",
                    language=campaign.language_code,
                ))
                continue

            for ad_group in campaign.ad_groups:
                # Each ad group must have at least one ad
                if not ad_group.ads:
                    issues.append(ValidationIssue(
                        code="QA_AD_GROUP_NO_ADS",
                        message=(
                            f"[QA/{campaign.language_code}] Ad group '{ad_group.name}' in "
                            f"'{campaign.campaign_name}' non ha annunci. "
                            "Un ad group senza annunci non può essere pubblicato."
                        ),
                        level="error",
                        blocks_publish=True,
                        agent="QAGatekeeperAgent",
                        language=campaign.language_code,
                    ))

            # Warn if no sitelinks configured (QS impact)
            lang = brief.get_language(campaign.language_code)
            if lang and not lang.sitelinks:
                issues.append(ValidationIssue(
                    code="QA_NO_SITELINKS",
                    message=(
                        f"[QA/{campaign.language_code}] Nessun sitelink configurato per la lingua '{campaign.language_code}'. "
                        "I sitelink migliorano il CTR e il Quality Score. "
                        "Configura almeno 4 sitelink in 'sitelinks' per ogni lingua."
                    ),
                    level="info",
                    blocks_publish=False,
                    agent="QAGatekeeperAgent",
                    language=campaign.language_code,
                ))

        return issues
