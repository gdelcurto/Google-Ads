"""
Brand Search campaign generator.
- Exact + Phrase match on brand terms
- Negative: non-brand exclusions
- RSA with brand-pinned headline
- Per language
"""
from __future__ import annotations

from typing import List

from app.agents.brand import BrandAgent
from app.domain.schemas.brief import Brief, LanguagePlan
from app.domain.schemas.campaign_plan import (
    AdGroupPlan, CampaignPlan, CampaignStatus, CampaignType,
    Keyword, MatchType, NetworkType,
)
from app.generators.base import BaseGenerator

_agent = BrandAgent()


class BrandSearchGenerator(BaseGenerator):
    """Generates Search Brand campaigns for each language in the brief."""

    CAMPAIGN_TYPE_KEY = "search_brand"

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
                subtype="Brand",
                camp_type_key=self.CAMPAIGN_TYPE_KEY,
                network_types=[NetworkType.search],
                bid_strategy=bid_strategy,
            )
        )

        ad_groups = [
            self._build_brand_exact_group(brief, lang, tracking_template, asset_pack),
            self._build_brand_phrase_group(brief, lang, tracking_template, asset_pack),
        ]

        # Negative non-brand at campaign level
        negative_keywords = [
            Keyword(
                text=kw,
                match_type=MatchType.broad,
                is_negative=True,
            )
            for kw in lang.brand_exclusions
        ]

        return CampaignPlan(
            external_key=external_key,
            campaign_name=campaign_name,
            campaign_type=CampaignType.search,
            campaign_subtype="Brand",
            language_code=lang.code,
            status=CampaignStatus.paused,
            settings=settings,
            ad_groups=ad_groups,
            shared_negative_keyword_lists=["Non-Brand Negatives"],
            can_publish=True,
        )

    def _build_brand_exact_group(
        self, brief: Brief, lang: LanguagePlan, tracking_template: str, asset_pack
    ) -> AdGroupPlan:
        group_name = self.build_campaign_name(brief, lang.code, "Brand", "Exact", "")
        group_name = f"{lang.code} | Brand | Exact"

        keywords = [
            Keyword(text=term, match_type=MatchType.exact)
            for term in lang.brand_terms
        ] + [
            Keyword(text=term, match_type=MatchType.exact)
            for term in lang.brand_variants
        ]

        rsa = self.build_rsa(
            lang=lang,
            final_url=lang.landing_page,
            tracking_template=tracking_template,
            pinned_headlines=[(lang.brand_terms[0], 1)] if lang.brand_terms else None,
            headlines=_agent.get_headlines(lang),
            descriptions=_agent.get_descriptions(lang),
            ad_group_index=0,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.enabled,
            default_max_cpc=brief.objectives.kpi.max_cpc_brand,
            keywords=keywords,
            ads=[rsa],
            assets=asset_pack,
        )

    def _build_brand_phrase_group(
        self, brief: Brief, lang: LanguagePlan, tracking_template: str, asset_pack
    ) -> AdGroupPlan:
        group_name = f"{lang.code} | Brand | Phrase"

        keywords = [
            Keyword(text=term, match_type=MatchType.phrase)
            for term in lang.brand_terms
        ] + [
            Keyword(text=term, match_type=MatchType.phrase)
            for term in lang.brand_variants
        ]

        rsa = self.build_rsa(
            lang=lang,
            final_url=lang.landing_page,
            tracking_template=tracking_template,
            headlines=_agent.get_headlines(lang),
            descriptions=_agent.get_descriptions(lang),
            ad_group_index=1,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.enabled,
            default_max_cpc=brief.objectives.kpi.max_cpc_brand,
            keywords=keywords,
            ads=[rsa],
            assets=asset_pack,
        )
