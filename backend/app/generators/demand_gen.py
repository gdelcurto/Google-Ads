"""
Demand Gen campaign generator (former Discovery).
- Remarketing-first targeting
- Creative assets are REQUIRED — publish is BLOCKED if missing
- Generates TODO placeholders and logs all missing assets
"""
from __future__ import annotations

from typing import List

from app.domain.schemas.brief import Brief, LanguagePlan
from app.domain.schemas.campaign_plan import (
    AdGroupPlan, CampaignPlan, CampaignStatus, CampaignType,
    DemandGenAd, NetworkType,
)
from app.generators.base import BaseGenerator


class DemandGenGenerator(BaseGenerator):
    """Generates Demand Gen campaigns per language."""

    CAMPAIGN_TYPE_KEY = "demand_gen"

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

        campaign_name, external_key, settings, _tracking, _assets = (
            self._generate_campaign_skeleton(
                brief=brief,
                lang=lang,
                camp_type="DemandGen",
                subtype="Remarketing",
                camp_type_key=self.CAMPAIGN_TYPE_KEY,
                network_types=[NetworkType.display],
                bid_strategy=bid_strategy,
            )
        )

        ad_groups = self._build_ad_groups(brief, lang)

        # Demand Gen: ALWAYS blocks publish if creative assets are missing
        blockers = []
        for ag in ad_groups:
            for ad in ag.demand_gen_ads:
                if ad.has_missing_assets:
                    for note in ad.missing_asset_notes:
                        blockers.append(f"Ad Group '{ag.name}': {note}")

        return CampaignPlan(
            external_key=external_key,
            campaign_name=campaign_name,
            campaign_type=CampaignType.demand_gen,
            campaign_subtype="Remarketing",
            language_code=lang.code,
            status=CampaignStatus.paused,
            settings=settings,
            ad_groups=ad_groups,
            can_publish=False,  # Always false until assets uploaded
            publish_blockers=blockers if blockers else [
                "Demand Gen richiede creatività validate prima della pubblicazione."
            ],
        )

    def _build_ad_groups(self, brief: Brief, lang: LanguagePlan) -> List[AdGroupPlan]:
        groups = []

        ag_index = 0

        # Group 1: All visitors remarketing
        if brief.audiences.remarketing_lists:
            all_visitors = [
                rm for rm in brief.audiences.remarketing_lists
                if rm.lookback_days >= 14
            ]
            if all_visitors:
                ag = self._build_remarketing_group(
                    brief, lang,
                    audience_name=all_visitors[0].name,
                    group_label="AllVisitors",
                    ag_index=ag_index,
                )
                groups.append(ag)
                ag_index += 1

        # Group 2: Abandoned intent (shorter lookback)
        abandoned = [
            rm for rm in brief.audiences.remarketing_lists
            if rm.lookback_days <= 7
        ]
        if abandoned:
            ag = self._build_remarketing_group(
                brief, lang,
                audience_name=abandoned[0].name,
                group_label="AbandonedBooking",
                ag_index=ag_index,
            )
            groups.append(ag)
            ag_index += 1

        # Group 3: In-market (prospecting)
        if brief.audiences.in_market_segments:
            ag = self._build_inmarket_group(brief, lang, ag_index=ag_index)
            groups.append(ag)

        if not groups:
            # Generic fallback
            groups.append(self._build_generic_group(brief, lang))

        return groups

    def _build_remarketing_group(
        self, brief: Brief, lang: LanguagePlan,
        audience_name: str, group_label: str, ag_index: int = 0
    ) -> AdGroupPlan:
        group_name = f"{lang.code} | DemandGen | {group_label}"

        h_all = list(lang.headlines)
        if ag_index > 0 and len(h_all) > 3:
            offset = (ag_index * max(1, len(h_all) // 3)) % len(h_all)
            h_all = h_all[offset:] + h_all[:offset]
        d_all = list(lang.descriptions)
        if ag_index > 0 and len(d_all) > 2:
            d_offset = ag_index % len(d_all)
            d_all = d_all[d_offset:] + d_all[:d_offset]

        ca = brief.creative_assets
        dg_images = []
        dg_missing: list[str] = []

        if ca.image_landscape:
            dg_images.append(ca.image_landscape)
        else:
            dg_images.append("TODO: immagine landscape 1200x628 (hotel esterno)")
            dg_missing.append("Immagine landscape 1200x628 (richiesta)")

        if ca.image_square:
            dg_images.append(ca.image_square)
        else:
            dg_images.append("TODO: immagine quadrata 1200x1200 (camera/piscina)")
            dg_missing.append("Immagine quadrata 1200x1200 (richiesta)")

        dg_logo = ca.logo_url or "TODO: logo 1200x1200 PNG trasparente"
        if not ca.logo_url:
            dg_missing.append("Logo 1200x1200 PNG trasparente (richiesto)")
        if not ca.youtube_video_url:
            dg_missing.append("Opzionale: video YouTube 16:9 o 1:1")

        demand_gen_ad = DemandGenAd(
            headlines=h_all[:5],
            descriptions=d_all[:4],
            images=dg_images,
            logo_url=dg_logo,
            final_url=lang.landing_page,
            has_missing_assets=len(dg_missing) > 0,
            missing_asset_notes=dg_missing,
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.paused,
            demand_gen_ads=[demand_gen_ad],
            audience_targeting=[audience_name],
            targeting_setting="targeting",
        )

    def _build_inmarket_group(self, brief: Brief, lang: LanguagePlan, ag_index: int = 0) -> AdGroupPlan:
        group_name = f"{lang.code} | DemandGen | InMarket"
        segment = brief.audiences.in_market_segments[0] if brief.audiences.in_market_segments else "Travel"

        h_all = list(lang.headlines)
        if ag_index > 0 and len(h_all) > 3:
            offset = (ag_index * max(1, len(h_all) // 3)) % len(h_all)
            h_all = h_all[offset:] + h_all[:offset]
        d_all = list(lang.descriptions)
        if ag_index > 0 and len(d_all) > 2:
            d_offset = ag_index % len(d_all)
            d_all = d_all[d_offset:] + d_all[:d_offset]

        demand_gen_ad = DemandGenAd(
            headlines=h_all[:5],
            descriptions=d_all[:4],
            images=["TODO: immagine prospecting 1200x628"],
            final_url=lang.landing_page,
            has_missing_assets=True,
            missing_asset_notes=["Immagine landscape 1200x628 (richiesta per in-market)"],
        )

        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.paused,
            demand_gen_ads=[demand_gen_ad],
            audience_targeting=[segment],
            targeting_setting="observation",
        )

    def _build_generic_group(self, brief: Brief, lang: LanguagePlan) -> AdGroupPlan:
        group_name = f"{lang.code} | DemandGen | General"
        demand_gen_ad = DemandGenAd(
            headlines=lang.headlines[:5],
            descriptions=lang.descriptions[:4],
            images=["TODO: immagine 1200x628"],
            final_url=lang.landing_page,
            has_missing_assets=True,
            missing_asset_notes=["Immagine landscape 1200x628 (richiesta)"],
        )
        return AdGroupPlan(
            name=group_name,
            status=CampaignStatus.paused,
            demand_gen_ads=[demand_gen_ad],
            audience_targeting=[],
            targeting_setting="targeting",
        )
