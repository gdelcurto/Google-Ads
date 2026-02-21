"""
Campaign orchestrator: runs all generators on a brief and returns the AccountPlan.
Also handles idempotency checks against existing campaign records.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from app.agents import AGENTS
from app.domain.schemas.brief import Brief
from app.domain.schemas.campaign_plan import AccountPlan, CampaignPlan, CampaignType
from app.generators.acquisition_search import AcquisitionSearchGenerator
from app.generators.brand_search import BrandSearchGenerator
from app.generators.demand_gen import DemandGenGenerator
from app.generators.performance_max import PerformanceMaxGenerator
from app.generators.retargeting import RetargetingGenerator
from app.validators.brief_validator import BriefValidator
from app.validators.strategy_validator import StrategicValidator


def _campaign_type_key(c: CampaignPlan) -> str:
    """Map a generated CampaignPlan back to its CampaignTypeKey (agent key)."""
    tv = c.campaign_type.value
    if tv == CampaignType.performance_max.value:
        return "performance_max"
    if tv == CampaignType.demand_gen.value:
        return "demand_gen"
    if tv == CampaignType.display.value:
        return "retargeting"
    if tv == CampaignType.search.value:
        return "search_brand" if c.campaign_subtype == "Brand" else "search_acquisition"
    return ""

logger = logging.getLogger(__name__)


class CampaignOrchestrator:
    """
    Runs all generators and assembles the full AccountPlan.
    Supports dry_run mode (no API calls, only plan diff output).
    """

    def __init__(self):
        self.validator = BriefValidator()
        self.strategy_validator = StrategicValidator()
        self.generators = [
            BrandSearchGenerator(),
            AcquisitionSearchGenerator(),
            RetargetingGenerator(),
            PerformanceMaxGenerator(),
            DemandGenGenerator(),
        ]

    def generate_plan(
        self,
        brief: Brief,
        project_id: str,
        dry_run: bool = True,
        existing_campaigns: Optional[List[dict]] = None,
    ) -> AccountPlan:
        """
        Main entry point. Validates brief, then runs all generators.
        Returns a complete AccountPlan ready for export or publish.
        """
        logger.info(
            "Generating plan",
            extra={"project_id": project_id, "client": brief.client.brand_slug, "dry_run": dry_run},
        )

        # Step 1: Validate brief
        validation = self.validator.validate(brief)
        if not validation.is_valid:
            logger.warning(
                "Brief validation failed",
                extra={"errors": validation.error_messages},
            )

        # Step 2: Run all generators
        all_campaigns: List[CampaignPlan] = []
        for generator in self.generators:
            try:
                campaigns = generator.generate(brief)
                logger.info(
                    f"{generator.__class__.__name__} generated {len(campaigns)} campaigns"
                )
                all_campaigns.extend(campaigns)
            except Exception as exc:
                logger.error(f"Generator {generator.__class__.__name__} failed: {exc}", exc_info=True)
                validation.add_error(
                    "GENERATOR_FAILURE",
                    f"Generator {generator.__class__.__name__} fallito: {exc}",
                )

        # Step 3: Idempotency diff (mark what's new vs existing)
        if existing_campaigns:
            all_campaigns = self._apply_idempotency(all_campaigns, existing_campaigns)

        # Step 4: Global negative keywords (across all campaigns)
        global_negatives = self._build_global_negatives(brief)

        # Step 5: Agent copy validation — one check per (language × campaign_type)
        agent_warnings: list[str] = []
        seen_pairs: set[tuple[str, str]] = set()
        for c in all_campaigns:
            tk = _campaign_type_key(c)
            pair = (c.language_code, tk)
            if tk and pair not in seen_pairs:
                seen_pairs.add(pair)
                lang = brief.get_language(c.language_code)
                if lang and tk in AGENTS:
                    agent_warnings.extend(AGENTS[tk].validate_copy(lang))

        # Step 5b: Agent strategy validation — per campaign type (budget, structure, audiences)
        seen_types: set[str] = set()
        for c in all_campaigns:
            tk = _campaign_type_key(c)
            if tk and tk not in seen_types and tk in AGENTS:
                seen_types.add(tk)
                agent_warnings.extend(AGENTS[tk].validate_strategy(brief))

        # Step 5c: Cross-campaign strategic validation (differentiation, budget mix)
        agent_warnings.extend(self.strategy_validator.validate(brief))

        # Step 6: Dry run diff (only set if not already set by idempotency)
        if dry_run:
            for campaign in all_campaigns:
                if campaign.dry_run_diff is None:
                    campaign.dry_run_diff = {
                        "action": "create",
                        "campaign_name": campaign.campaign_name,
                        "ad_groups_count": len(campaign.ad_groups),
                        "budget_daily": campaign.settings.budget_daily_eur,
                        "can_publish": campaign.can_publish,
                        "publish_blockers": campaign.publish_blockers,
                    }

        plan = AccountPlan(
            project_id=project_id,
            client_name=brief.client.brand_name,
            client_slug=brief.client.brand_slug,
            brief_version=brief.version,
            campaigns=all_campaigns,
            global_negative_keywords=global_negatives,
            validation_warnings=validation.warning_messages + agent_warnings,
            validation_errors=validation.error_messages,
            is_valid=validation.is_valid,
            publish_ready=validation.is_valid and all(c.can_publish for c in all_campaigns),
        )

        logger.info(
            "Plan generated",
            extra={
                "campaigns": len(all_campaigns),
                "valid": plan.is_valid,
                "publish_ready": plan.publish_ready,
            },
        )
        return plan

    def _apply_idempotency(
        self,
        campaigns: List[CampaignPlan],
        existing: List[dict],
    ) -> List[CampaignPlan]:
        """
        Compare generated campaigns against existing records by external_key.
        Mark as 'update' instead of 'create' for existing ones.
        """
        existing_keys = {e["external_key"]: e for e in existing}

        for campaign in campaigns:
            if campaign.external_key in existing_keys:
                existing_record = existing_keys[campaign.external_key]
                campaign.dry_run_diff = {
                    "action": "update",
                    "existing_google_ads_id": existing_record.get("google_ads_campaign_id"),
                    "changes": ["budget", "status"],
                }
        return campaigns

    def _build_global_negatives(self, brief: Brief):
        """Build a set of global negative keywords applied to all campaigns."""
        from app.domain.schemas.campaign_plan import Keyword, MatchType
        negatives = []

        # Common hotel spam terms
        spam_terms = ["free", "gratis", "gratuito", "kosten", "cheap", "billig"]
        for term in spam_terms:
            negatives.append(
                Keyword(text=term, match_type=MatchType.broad, is_negative=True)
            )

        return negatives
