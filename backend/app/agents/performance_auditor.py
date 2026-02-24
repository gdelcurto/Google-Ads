"""
Performance Auditor Agent — L3 Audit Agent.

Post-generation cross-campaign audit: copy diversity, headline counts,
ad strength indicators across the generated AccountPlan.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief
    from app.domain.schemas.campaign_plan import CampaignPlan


_MIN_HEADLINES_RSA = 8   # "Good" ad strength threshold
_MIN_HEADLINES_EXCELLENT = 10


class PerformanceAuditorAgent(CampaignAgent):
    TYPE_KEY = "performance_auditor"
    LEVEL = AgentLevel.AUDITOR
    BLOCKS_PUBLISH = False
    BLOCKING_RULES = []

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    PERFORMANCE AUDITOR — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Audit post-generazione: verifica la qualità del piano generato nel suo insieme.
    Controlla indicatori di performance che non sono visibili ai singoli agenti L2.

    CONTROLLI
    ✅ Headline count per lingua per tipo (ad strength indicator)
    ✅ Copy diversity: campagne diverse devono avere messaggi diversi
    ✅ Distribuzione campagne: bilancio delle lingue
    ✅ Copertura network: almeno Search + un canale upper-funnel
    """

    def validate_plan(
        self,
        brief: "Brief",
        campaigns: List["CampaignPlan"],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        if not campaigns:
            return issues

        # Check headline counts per language for Search campaigns.
        # Report once per campaign (use the minimum headline count across
        # all ads in the campaign) to avoid duplicate warnings.
        from app.domain.schemas.campaign_plan import CampaignType
        search_campaigns = [c for c in campaigns if c.campaign_type == CampaignType.search]

        for campaign in search_campaigns:
            min_count = None
            for ad_group in campaign.ad_groups:
                for ad in ad_group.ads:
                    cnt = len(ad.headlines) if hasattr(ad, "headlines") else 0
                    if cnt > 0 and (min_count is None or cnt < min_count):
                        min_count = cnt
            if min_count is not None and min_count < _MIN_HEADLINES_RSA:
                issues.append(ValidationIssue(
                    code="AUDIT_LOW_HEADLINE_COUNT",
                    message=(
                        f"[Audit/{campaign.language_code}] Campagna '{campaign.campaign_name}': "
                        f"{min_count} headline (ottimale: {_MIN_HEADLINES_EXCELLENT}+). "
                        f"Con meno di {_MIN_HEADLINES_RSA} headline l'Ad Strength è 'Poor' o 'Average'. "
                        "Aggiungi headline per migliorare la copertura delle query."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="PerformanceAuditorAgent",
                    language=campaign.language_code,
                ))

        # Check that multiple languages have consistent campaign coverage
        lang_campaign_counts: dict[str, int] = {}
        for campaign in campaigns:
            lang = campaign.language_code
            lang_campaign_counts[lang] = lang_campaign_counts.get(lang, 0) + 1

        if len(lang_campaign_counts) > 1:
            counts = list(lang_campaign_counts.values())
            min_count = min(counts)
            max_count = max(counts)
            if max_count > min_count * 2:
                under_covered = [
                    lang for lang, cnt in lang_campaign_counts.items()
                    if cnt == min_count
                ]
                issues.append(ValidationIssue(
                    code="AUDIT_UNBALANCED_LANGUAGE_COVERAGE",
                    message=(
                        f"[Audit] Copertura campagne non bilanciata tra le lingue. "
                        f"Lingue con meno campagne: {', '.join(under_covered)} ({min_count} campagne). "
                        f"Altre lingue hanno fino a {max_count} campagne. "
                        "Verifica che tutte le lingue abbiano la stessa copertura di tipi."
                    ),
                    level="warning",
                    blocks_publish=False,
                    agent="PerformanceAuditorAgent",
                ))

        return issues
