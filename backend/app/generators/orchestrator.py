"""
Campaign orchestrator: runs all generators on a brief and returns the AccountPlan.
Also handles idempotency checks against existing campaign records.

Execution order (agent levels):
  L1 STRATEGIC  — pre-generation: brief structure + strategy validation
  L2 SPECIALIST — copy + per-campaign validation (during generation step)
  TECH          — cross-cutting: naming, negatives, geo (post-generation)
  L3 AUDITOR    — post-generation: cross-campaign audit
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.agents import AGENTS, AUDIT_AGENTS, STRATEGIC_AGENTS, TECH_AGENTS
from app.agents.base import ValidationIssue
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


def _apply_issues_to_campaigns(
    issues: List[ValidationIssue],
    campaigns: List[CampaignPlan],
) -> tuple[list[str], list[str]]:
    """
    Apply ValidationIssue objects to affected campaigns:
    - issues with blocks_publish=True → set campaign.can_publish=False,
      add blocker message to campaign.publish_blockers
    - all issues → classified into warnings or errors for AccountPlan

    Returns (warning_messages, error_messages).
    """
    warnings: list[str] = []
    errors: list[str] = []

    for issue in issues:
        if issue.level == "error":
            errors.append(issue.message)
        else:
            warnings.append(issue.message)

        if issue.blocks_publish:
            for campaign in campaigns:
                lang_match = (
                    issue.language is None
                    or campaign.language_code == issue.language
                )
                type_match = (
                    issue.campaign_type_key is None
                    or _campaign_type_key(campaign) == issue.campaign_type_key
                )
                if lang_match and type_match:
                    campaign.can_publish = False
                    blocker = f"[{issue.code}] {issue.message}"
                    if blocker not in campaign.publish_blockers:
                        campaign.publish_blockers.append(blocker)

    return warnings, errors


class CampaignOrchestrator:
    """
    Runs all generators and assembles the full AccountPlan.
    Supports dry_run mode (no API calls, only plan diff output).

    Validation flow:
      1. BriefValidator (schema + required fields)
      2. L1 Strategic agents (brief structure + strategy)
      3. Generators (create CampaignPlan objects)
      4. L2 Specialist agents (copy + per-campaign validation)
      5. StrategicValidator (cross-campaign coherence)
      6. TECH agents (naming, negatives, geo)
      7. L3 Audit agents (post-generation cross-campaign audit)
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

        all_warnings: list[str] = []
        all_errors: list[str] = []

        # ── Step 1: Schema validation ──────────────────────────────────────────
        validation = self.validator.validate(brief)
        if not validation.is_valid:
            logger.warning(
                "Brief validation failed",
                extra={"errors": validation.error_messages},
            )

        # ── Step 2: L1 Strategic agents (pre-generation) ──────────────────────
        l1_issues: list[ValidationIssue] = []
        for agent in STRATEGIC_AGENTS:
            try:
                l1_issues.extend(agent.validate_strategy(brief))
            except Exception as exc:
                logger.error(f"L1 agent {agent.__class__.__name__} failed: {exc}", exc_info=True)

        # L1 issues don't affect per-campaign can_publish yet (no campaigns generated)
        # but do contribute to account-level errors/warnings
        for issue in l1_issues:
            if issue.level == "error":
                all_errors.append(issue.message)
            else:
                all_warnings.append(issue.message)

        # ── Step 3: Run all generators ─────────────────────────────────────────
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

        # ── Step 4: Idempotency diff (mark what's new vs existing) ────────────
        if existing_campaigns:
            all_campaigns = self._apply_idempotency(all_campaigns, existing_campaigns)

        # ── Step 5: Global negative keywords (across all campaigns) ───────────
        global_negatives = self._build_global_negatives(brief)

        # ── Step 6: L2 Agent copy validation — one check per (language × campaign_type) ──
        l2_issues: list[ValidationIssue] = []
        seen_pairs: set[tuple[str, str]] = set()
        for c in all_campaigns:
            tk = _campaign_type_key(c)
            pair = (c.language_code, tk)
            if tk and pair not in seen_pairs:
                seen_pairs.add(pair)
                lang = brief.get_language(c.language_code)
                if lang and tk in AGENTS:
                    l2_issues.extend(AGENTS[tk].validate_copy(lang))

        # Step 6b: L2 Agent strategy validation — per campaign type
        seen_types: set[str] = set()
        for c in all_campaigns:
            tk = _campaign_type_key(c)
            if tk and tk not in seen_types and tk in AGENTS:
                seen_types.add(tk)
                l2_issues.extend(AGENTS[tk].validate_strategy(brief))

        # Step 6c: Cross-campaign strategic validation
        l2_issues.extend(self.strategy_validator.validate(brief))

        w, e = _apply_issues_to_campaigns(l2_issues, all_campaigns)
        all_warnings.extend(w)
        all_errors.extend(e)

        # ── Step 7: TECH agents (naming, negatives, geo) ──────────────────────
        tech_issues: list[ValidationIssue] = []
        for agent in TECH_AGENTS:
            try:
                tech_issues.extend(agent.validate_strategy(brief))
                tech_issues.extend(agent.validate_plan(brief, all_campaigns))
            except Exception as exc:
                logger.error(f"TECH agent {agent.__class__.__name__} failed: {exc}", exc_info=True)

        w, e = _apply_issues_to_campaigns(tech_issues, all_campaigns)
        all_warnings.extend(w)
        all_errors.extend(e)

        # ── Step 8: L3 Audit agents (post-generation cross-campaign) ──────────
        l3_issues: list[ValidationIssue] = []
        for agent in AUDIT_AGENTS:
            try:
                l3_issues.extend(agent.validate_plan(brief, all_campaigns))
            except Exception as exc:
                logger.error(f"L3 agent {agent.__class__.__name__} failed: {exc}", exc_info=True)

        w, e = _apply_issues_to_campaigns(l3_issues, all_campaigns)
        all_warnings.extend(w)
        all_errors.extend(e)

        # Also apply L1 blocking issues to all campaigns (account-level blockers)
        blocking_l1 = [i for i in l1_issues if i.blocks_publish]
        if blocking_l1:
            for campaign in all_campaigns:
                for issue in blocking_l1:
                    campaign.can_publish = False
                    blocker = f"[{issue.code}] {issue.message}"
                    if blocker not in campaign.publish_blockers:
                        campaign.publish_blockers.append(blocker)

        # ── Step 9: Dry run diff ───────────────────────────────────────────────
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
            validation_warnings=validation.warning_messages + all_warnings,
            validation_errors=validation.error_messages + all_errors,
            is_valid=validation.is_valid and not all_errors,
            publish_ready=validation.is_valid and not all_errors and all(c.can_publish for c in all_campaigns),
        )

        logger.info(
            "Plan generated",
            extra={
                "campaigns": len(all_campaigns),
                "valid": plan.is_valid,
                "publish_ready": plan.publish_ready,
                "warnings": len(all_warnings),
                "errors": len(all_errors),
            },
        )
        return plan

    async def generate_plan_ai(
        self,
        brief: Brief,
        project_id: str,
        api_key: str,
        dry_run: bool = True,
        existing_campaigns: Optional[List[dict]] = None,
    ) -> AccountPlan:
        """
        AI-enhanced plan generation:
          0. In parallel — AI budget pre-optimization + acquisition keyword pre-generation
             (both modify the brief copy before sync generators run)
          1. Generate campaign structure via sync generate_plan()
          2. Enhance all copy with Claude (parallel per ad group)
          3. Validate enhanced copy with Claude (parallel per campaign type)
          4. Merge AI copy validation issues into plan
          5. Run AI strategic advisor (budget residual, bidding, negative keywords) in parallel
          6. Merge AI strategic insights + build validation_warnings_structured with CTAs
        """
        import asyncio
        from app.connectors.ai_copy_generator import AICopyGenerator
        from app.connectors.ai_validator import AIValidator
        from app.connectors.ai_strategic_advisor import (
            analyze_budget_strategy_ai,
            analyze_bidding_strategy_ai,
            analyze_negative_keywords_ai,
            generate_acquisition_keywords_ai,
            optimize_brief_budget_ai,
            optimize_brief_kpi_ai,
        )

        # ── Step 0: AI brief pre-enrichment (budget + KPI + keywords, parallel) ─
        # All three run BEFORE the sync generators so the rule-based pipeline
        # uses AI-recommended configuration instead of defaults / empty templates.
        budget_was_optimized = False
        kpi_was_optimized = False
        try:
            budget_task = asyncio.ensure_future(optimize_brief_budget_ai(brief, api_key))
            kpi_task    = asyncio.ensure_future(optimize_brief_kpi_ai(brief, api_key))
            kw_task     = asyncio.ensure_future(generate_acquisition_keywords_ai(brief, api_key))
            (optimized_brief, budget_was_optimized), (kpi_brief, kpi_was_optimized), ai_kw = (
                await asyncio.gather(budget_task, kpi_task, kw_task)
            )

            # Apply budget optimisation, then layer KPI optimisation on top
            brief = optimized_brief
            if kpi_was_optimized:
                # merge: keep budget from optimized_brief, KPI from kpi_brief
                brief = brief.model_copy(update={"objectives": kpi_brief.objectives})

            # Merge AI-generated keyword themes
            if ai_kw:
                merged_kw = dict(brief.acquisition_keywords or {})
                merged_kw.update(ai_kw)
                brief = brief.model_copy(update={"acquisition_keywords": merged_kw})
                logger.info(
                    f"AI pre-generated acquisition keywords for project {project_id}: "
                    f"languages={list(ai_kw.keys())}"
                )
        except Exception as exc:
            logger.warning(
                f"AI brief pre-enrichment partially failed for project {project_id}: {exc}"
            )

        # ── Step 1: Rule-based generation ─────────────────────────────────────
        plan = self.generate_plan(
            brief=brief,
            project_id=project_id,
            dry_run=dry_run,
            existing_campaigns=existing_campaigns,
        )

        # ── Step 2: AI copy enhancement (in-place) ────────────────────────────
        copy_gen = AICopyGenerator(api_key=api_key)
        try:
            await copy_gen.enhance_campaigns(plan.campaigns, brief, AGENTS)
            logger.info(f"AI copy enhancement complete for project {project_id}")
        except Exception as exc:
            logger.warning(
                f"AI copy enhancement failed for project {project_id}: {exc}. "
                "Static copy kept."
            )

        # ── Step 3: AI copy validation ─────────────────────────────────────────
        ai_validator = AIValidator(api_key=api_key)
        ai_issues: list[ValidationIssue] = []
        try:
            ai_issues = await ai_validator.validate_all(plan.campaigns, brief, AGENTS)
            logger.info(
                f"AI validation complete for project {project_id}: "
                f"{len(ai_issues)} issue(s) found"
            )
        except Exception as exc:
            logger.warning(
                f"AI validation failed for project {project_id}: {exc}. "
                "Skipping AI validation issues."
            )

        # ── Step 4: Merge AI copy validation issues ────────────────────────────
        if ai_issues:
            ai_warnings, ai_errors = _apply_issues_to_campaigns(ai_issues, plan.campaigns)
            new_warnings = plan.validation_warnings + ai_warnings
            new_errors = plan.validation_errors + ai_errors
            plan = plan.model_copy(update={
                "validation_warnings": new_warnings,
                "validation_errors": new_errors,
                "is_valid": not new_errors,
                "publish_ready": (
                    not new_errors and all(c.can_publish for c in plan.campaigns)
                ),
            })

        # ── Step 5: AI strategic advisor (budget residual, bidding, negatives) ─
        # Skip the budget and/or bidding advisors when those settings were
        # already AI-optimized in Step 0 to avoid retroactive warnings.
        advisor_coroutines = [
            analyze_negative_keywords_ai(brief, plan.campaigns, api_key),
        ]
        if not budget_was_optimized:
            advisor_coroutines.insert(0, analyze_budget_strategy_ai(brief, api_key))
        if not kpi_was_optimized:
            advisor_coroutines.append(analyze_bidding_strategy_ai(brief, api_key))

        advisor_results = await asyncio.gather(*advisor_coroutines, return_exceptions=True)

        advisor_issues: list[ValidationIssue] = []
        for result in advisor_results:
            if isinstance(result, list):
                advisor_issues.extend(result)
            elif isinstance(result, Exception):
                logger.warning(
                    f"AI strategic advisor error for project {project_id}: {result}"
                )

        # ── Step 6: Merge AI strategic insights + build structured warnings ──────
        if advisor_issues:
            adv_warnings, adv_errors = _apply_issues_to_campaigns(
                advisor_issues, plan.campaigns
            )
            # Build structured warning list — carries suggested_fix for frontend CTAs
            structured: list[dict] = [
                {
                    "message": issue.message,
                    "code": issue.code,
                    "level": issue.level,
                    "agent": issue.agent,
                    "suggested_fix": issue.suggested_fix,  # None or {brief_path, value, action, label}
                }
                for issue in advisor_issues
            ]
            plan = plan.model_copy(update={
                "validation_warnings": plan.validation_warnings + adv_warnings,
                "validation_errors": plan.validation_errors + adv_errors,
                "validation_warnings_structured": (
                    plan.validation_warnings_structured + structured
                ),
                "is_valid": not (plan.validation_errors + adv_errors),
                "publish_ready": (
                    not (plan.validation_errors + adv_errors)
                    and all(c.can_publish for c in plan.campaigns)
                ),
            })
            logger.info(
                f"AI strategic advisor complete for project {project_id}: "
                f"{len(advisor_issues)} insight(s), "
                f"{sum(1 for i in advisor_issues if i.suggested_fix)} with fix CTA"
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
