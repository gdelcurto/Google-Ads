"""
Performance Max campaign generator.
- Asset group per lingua/mercato
- Audience signals (remarketing + in-market + customer match)
- Final URL expansion: OFF by default for hotels (maintain landing page control)
- Headlines + long headlines + descriptions + images (placeholder if missing)
"""
from __future__ import annotations

from typing import List

from app.domain.schemas.brief import Brief, LanguagePlan
from app.domain.schemas.campaign_plan import (
    BidStrategy, CampaignPlan, CampaignStatus, CampaignType,
    NetworkType, PMaxAssetGroup,
)
from app.generators.base import BaseGenerator


class PerformanceMaxGenerator(BaseGenerator):
    """Generates one PMax campaign per language with one asset group each."""

    CAMPAIGN_TYPE_KEY = "performance_max"

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
        campaign_name = self.build_campaign_name(brief, lang.code, "PMax", "Hotel")
        external_key = self.build_external_key(brief, lang.code, "pmax", "hotel")

        kpi = brief.objectives.kpi
        if kpi.target_roas:
            bid_strategy = BidStrategy.maximize_conversion_value
        elif kpi.target_cpa_eur:
            bid_strategy = BidStrategy.maximize_conversions
        else:
            bid_strategy = BidStrategy.maximize_conversion_value

        settings = self.build_campaign_settings(
            brief=brief,
            lang=lang,
            camp_type_key=self.CAMPAIGN_TYPE_KEY,
            network_types=[NetworkType.search, NetworkType.display],
            bid_strategy=bid_strategy,
            target_roas=kpi.target_roas,
            target_cpa=kpi.target_cpa_eur,
        )

        asset_group = self._build_asset_group(brief, lang)

        blockers = []
        if asset_group.has_missing_assets:
            blockers = [
                f"Asset group '{asset_group.name}': immagini/video mancanti. "
                "PMax richiede almeno 1 immagine landscape, 1 square, 1 logo."
            ]

        return CampaignPlan(
            external_key=external_key,
            campaign_name=campaign_name,
            campaign_type=CampaignType.performance_max,
            campaign_subtype="Hotel",
            language_code=lang.code,
            status=CampaignStatus.paused,
            settings=settings,
            pmax_asset_groups=[asset_group],
            can_publish=len(blockers) == 0,
            publish_blockers=blockers,
        )

    def _build_asset_group(self, brief: Brief, lang: LanguagePlan) -> PMaxAssetGroup:
        group_name = f"{lang.code} | PMax | {brief.client.brand_name} | Asset Group 1"

        # Long headlines: combine USP bullets
        long_headlines = [lang.usp.main] + lang.usp.bullets[:4]

        # Audience signals: remarketing + in-market
        audience_signals = (
            [rm.name for rm in brief.audiences.remarketing_lists]
            + brief.audiences.in_market_segments
        )
        if brief.audiences.customer_match.enabled and brief.audiences.customer_match.list_name:
            audience_signals.append(brief.audiences.customer_match.list_name)

        # Images: placeholder — hotel must provide actual assets
        images = [
            "TODO: landscape image 1200x628 (hotel facade)",
            "TODO: square image 1200x1200 (hotel room)",
            "TODO: portrait image 960x1200 (hotel pool/spa)",
        ]
        logo_url = "TODO: logo PNG transparent 1200x1200"
        youtube_url = None  # Optional

        has_missing = True  # Always require image upload
        missing_notes = [
            "Carica almeno 1 immagine landscape (1200x628)",
            "Carica almeno 1 immagine quadrata (1200x1200)",
            "Carica il logo (1200x1200 PNG trasparente)",
        ]

        return PMaxAssetGroup(
            name=group_name,
            headlines=lang.headlines[:15],
            long_headlines=long_headlines[:5],
            descriptions=lang.descriptions[:5],
            images=images,
            logo_url=logo_url,
            youtube_video_url=youtube_url,
            final_url=lang.landing_page,
            audience_signals=audience_signals,
            final_url_expansion=False,  # OFF for hotels by default
            has_missing_assets=has_missing,
            missing_asset_notes=missing_notes,
        )
