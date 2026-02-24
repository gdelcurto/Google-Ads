"""
Acquisition (Non-Brand) Search campaign generator.
- Keywords by theme (location, category, intent, occasion)
- Broad + Phrase match
- Negative brand list
- USP-focused RSA per ad group theme
- Falls back to vertical template if no keywords in brief
"""
from __future__ import annotations

from typing import Dict, List

from app.agents.acquisition import AcquisitionAgent
from app.domain.schemas.brief import Brief, LanguagePlan
from app.domain.schemas.campaign_plan import (
    AdGroupPlan, CampaignPlan, CampaignStatus, CampaignType,
    Keyword, MatchType, NetworkType,
)
from app.generators.base import BaseGenerator

_agent = AcquisitionAgent()


class AcquisitionSearchGenerator(BaseGenerator):
    """Generates Search Acquisition (non-brand) campaigns per language."""

    CAMPAIGN_TYPE_KEY = "search_acquisition"

    def generate(self, brief: Brief) -> List[CampaignPlan]:
        campaigns = []

        for lang in brief.languages:
            budget = brief.get_budget_for(self.CAMPAIGN_TYPE_KEY, lang.code)
            if budget <= 0:
                continue

            plan = self._generate_for_language(brief, lang)
            campaigns.append(plan)

        return campaigns

    def _generate_for_language(self, brief: Brief, lang: LanguagePlan) -> CampaignPlan:
        bid_strategy = self.resolve_bid_strategy(brief, self.CAMPAIGN_TYPE_KEY)

        campaign_name, external_key, settings, tracking_template, asset_pack = (
            self._generate_campaign_skeleton(
                brief=brief,
                lang=lang,
                camp_type="Search",
                subtype="Acquisition",
                camp_type_key=self.CAMPAIGN_TYPE_KEY,
                network_types=[NetworkType.search],
                bid_strategy=bid_strategy,
            )
        )

        # Get keyword themes from brief or vertical template fallback
        themes = self._get_keyword_themes(brief, lang)
        negative_brand_kws = self._build_brand_negatives(lang)

        ad_groups = []
        for ag_index, (theme_name, keywords_raw) in enumerate(themes.items()):
            if not keywords_raw:
                continue
            ag = self._build_theme_ad_group(
                brief, lang, theme_name, keywords_raw,
                tracking_template, asset_pack, ag_index,
            )
            ad_groups.append(ag)

        if not ad_groups:
            ad_groups = [self._build_generic_ad_group(brief, lang, tracking_template, asset_pack)]

        # Campaign-level negatives: brand terms as exact negatives
        campaign_negatives = [
            Keyword(text=term, match_type=MatchType.exact, is_negative=True)
            for term in lang.brand_terms
        ]

        return CampaignPlan(
            external_key=external_key,
            campaign_name=campaign_name,
            campaign_type=CampaignType.search,
            campaign_subtype="Acquisition",
            language_code=lang.code,
            status=CampaignStatus.paused,
            settings=settings,
            ad_groups=ad_groups,
            shared_negative_keyword_lists=["Brand Negatives"],
            can_publish=True,
        )

    def _get_keyword_themes(self, brief: Brief, lang: LanguagePlan) -> Dict[str, List[str]]:
        """Returns keyword themes from brief or falls back to vertical template."""
        if brief.acquisition_keywords and lang.code in brief.acquisition_keywords:
            return brief.acquisition_keywords[lang.code].themes

        # Fallback: vertical template
        from app.templates.vertical_templates import VerticalTemplates
        vertical = brief.hotel_specifics.category
        return VerticalTemplates.get_acquisition_themes(vertical, lang.code)

    def _build_brand_negatives(self, lang: LanguagePlan) -> List[Keyword]:
        return [
            Keyword(text=term, match_type=MatchType.exact, is_negative=True)
            for term in lang.brand_terms
        ]

    def _build_theme_ad_group(
        self,
        brief: Brief,
        lang: LanguagePlan,
        theme_name: str,
        keywords_raw: List[str],
        tracking_template: str,
        asset_pack,
        ag_index: int = 0,
    ) -> AdGroupPlan:
        group_name = f"{lang.code} | Acquisition | {theme_name.title()}"

        # Phrase + Broad match per keyword
        keywords = []
        for kw in keywords_raw:
            keywords.append(Keyword(text=kw, match_type=MatchType.phrase))
            keywords.append(Keyword(text=kw, match_type=MatchType.broad))

        rsa = self.build_rsa(
            lang=lang,
            final_url=lang.landing_page,
            tracking_template=tracking_template,
            headlines=_agent.get_headlines(lang),
            descriptions=_agent.get_descriptions(lang),
            ad_group_index=ag_index,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.enabled,
            default_max_cpc=brief.objectives.kpi.max_cpc_acquisition,
            keywords=keywords,
            ads=[rsa],
            assets=asset_pack,
        )

    def _build_generic_ad_group(
        self, brief: Brief, lang: LanguagePlan, tracking_template: str, asset_pack
    ) -> AdGroupPlan:
        group_name = f"{lang.code} | Acquisition | General"
        rsa = self.build_rsa(
            lang=lang,
            final_url=lang.landing_page,
            tracking_template=tracking_template,
            headlines=_agent.get_headlines(lang),
            descriptions=_agent.get_descriptions(lang),
        )
        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.enabled,
            default_max_cpc=brief.objectives.kpi.max_cpc_acquisition,
            keywords=[],
            ads=[rsa],
            assets=asset_pack,
        )
