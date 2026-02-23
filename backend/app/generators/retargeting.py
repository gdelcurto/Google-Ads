"""
Retargeting campaign generator.
Supports: Display, Video, Demand Gen inventory.
Uses remarketing lists from brief audiences.
"""
from __future__ import annotations

from typing import List

from app.domain.schemas.brief import Brief, LanguagePlan, RemarketingList
from app.domain.schemas.campaign_plan import (
    AdGroupPlan, BidStrategy, CampaignPlan, CampaignStatus, CampaignType,
    DisplayAd, NetworkType,
)
from app.generators.base import BaseGenerator


class RetargetingGenerator(BaseGenerator):
    """
    Generates Display retargeting campaigns.
    Each remarketing list becomes its own ad group for granular bidding.
    """

    CAMPAIGN_TYPE_KEY = "retargeting"

    def generate(self, brief: Brief) -> List[CampaignPlan]:
        campaigns = []

        if not brief.audiences.remarketing_lists:
            return campaigns

        for lang in brief.languages:
            budget = brief.get_budget_for(self.CAMPAIGN_TYPE_KEY, lang.code)
            if budget <= 0:
                continue

            plan = self._generate_for_language(brief, lang)
            campaigns.append(plan)

        return campaigns

    def _generate_for_language(self, brief: Brief, lang: LanguagePlan) -> CampaignPlan:
        kpi = brief.objectives.kpi
        bid_strategy = BidStrategy.target_cpa if kpi.target_cpa_eur else BidStrategy.maximize_conversions

        campaign_name, external_key, settings, _tracking, _assets = (
            self._generate_campaign_skeleton(
                brief=brief,
                lang=lang,
                camp_type="Retargeting",
                subtype="Display",
                camp_type_key=self.CAMPAIGN_TYPE_KEY,
                network_types=[NetworkType.display],
                bid_strategy=bid_strategy,
                target_cpa=kpi.target_cpa_eur,
            )
        )

        ad_groups = []
        for ag_index, rm_list in enumerate(brief.audiences.remarketing_lists):
            ag = self._build_remarketing_ad_group(brief, lang, rm_list, ag_index)
            ad_groups.append(ag)

        # Add customer match ad group if configured
        if brief.audiences.customer_match.enabled:
            ag = self._build_customer_match_group(brief, lang, len(ad_groups))
            ad_groups.append(ag)

        blockers = []
        for ag in ad_groups:
            for ad in ag.display_ads:
                if ad.has_missing_assets:
                    blockers.append(
                        f"Ad group '{ag.name}': asset immagine mancanti. "
                        "Carica le creatività prima di pubblicare."
                    )

        return CampaignPlan(
            external_key=external_key,
            campaign_name=campaign_name,
            campaign_type=CampaignType.display,
            campaign_subtype="Remarketing",
            language_code=lang.code,
            status=CampaignStatus.paused,
            settings=settings,
            ad_groups=ad_groups,
            can_publish=len(blockers) == 0,
            publish_blockers=blockers,
        )

    def _build_remarketing_ad_group(
        self, brief: Brief, lang: LanguagePlan, rm_list: RemarketingList, ag_index: int = 0
    ) -> AdGroupPlan:
        group_name = f"{lang.code} | Retargeting | {rm_list.name}"

        # Rotate headline pool so each ad group shows a different creative variation.
        h_all = list(lang.headlines)
        if ag_index > 0 and len(h_all) > 3:
            offset = (ag_index * max(1, len(h_all) // 3)) % len(h_all)
            h_all = h_all[offset:] + h_all[:offset]
        d_all = list(lang.descriptions)
        if ag_index > 0 and len(d_all) > 2:
            d_offset = ag_index % len(d_all)
            d_all = d_all[d_offset:] + d_all[:d_offset]

        # Display ads: use provided URLs or mark as missing
        ca = brief.creative_assets
        image_urls = []
        if ca.image_landscape:
            image_urls.append(ca.image_landscape)
        if ca.image_square:
            image_urls.append(ca.image_square)
        if not image_urls:
            image_urls = ["TODO: upload display ad images (300x250, 728x90, 160x600)"]
        logo_url = ca.logo_url or None
        has_missing_display = not ca.image_landscape or not ca.image_square

        display_ad = DisplayAd(
            headlines=h_all[:5],
            descriptions=d_all[:5],
            image_urls=image_urls,
            logo_url=logo_url,
            final_url=lang.landing_page,
            has_missing_assets=has_missing_display,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.paused,
            display_ads=[display_ad],
            audience_targeting=[rm_list.name],
            targeting_setting="targeting",
        )

    def _build_customer_match_group(
        self, brief: Brief, lang: LanguagePlan, ag_index: int = 0
    ) -> AdGroupPlan:
        list_name = brief.audiences.customer_match.list_name or "CRM List"
        group_name = f"{lang.code} | Retargeting | {list_name}"

        h_all = list(lang.headlines)
        if ag_index > 0 and len(h_all) > 3:
            offset = (ag_index * max(1, len(h_all) // 3)) % len(h_all)
            h_all = h_all[offset:] + h_all[:offset]
        d_all = list(lang.descriptions)
        if ag_index > 0 and len(d_all) > 2:
            d_offset = ag_index % len(d_all)
            d_all = d_all[d_offset:] + d_all[:d_offset]

        display_ad = DisplayAd(
            headlines=h_all[:5],
            descriptions=d_all[:5],
            image_urls=["TODO: upload display ad images"],
            final_url=lang.landing_page,
            has_missing_assets=True,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.paused,
            display_ads=[display_ad],
            audience_targeting=[list_name],
            targeting_setting="targeting",
        )
