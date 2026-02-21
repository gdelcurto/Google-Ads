"""
Base generator: common utilities shared by all campaign type generators.
"""
from __future__ import annotations

from typing import List, Optional

from app.domain.schemas.brief import Brief, LanguagePlan, UtmConfig
from app.domain.schemas.campaign_plan import (
    AssetPack, CalloutAsset, CampaignSettings, CampaignStatus, CampaignType,
    RSAd, PinnedHeadline, SitelinkAsset, StructuredSnippetAsset,
)


class BaseGenerator:
    """Shared utilities for all campaign generators."""

    def build_campaign_name(
        self,
        brief: Brief,
        lang: str,
        camp_type: str,
        subtype: str,
        match_type: str = "",
    ) -> str:
        sep = brief.naming_convention.separator
        parts = [lang, camp_type, subtype]
        if match_type:
            parts.append(match_type)
        return sep.join(parts)

    def build_external_key(
        self,
        brief: Brief,
        lang: str,
        camp_type: str,
        subtype: str,
    ) -> str:
        preset = brief.meta.preset.value
        slug = brief.client.brand_slug
        return f"{preset}_{slug}_{lang.lower()}_{camp_type}_{subtype}".replace(" ", "_").lower()

    def build_tracking_template(self, utm: UtmConfig) -> str:
        params = [
            f"utm_source={utm.source}",
            f"utm_medium={utm.medium}",
            f"utm_campaign={utm.campaign}",
            f"utm_content={utm.content}",
            f"utm_term={utm.term}",
        ]
        for k, v in utm.custom_params.items():
            params.append(f"{k}={v}")
        if utm.preset_tag:
            params.append(f"utm_preset={utm.preset_tag}")

        return "{lpurl}?" + "&".join(params)

    def build_asset_pack(self, lang: LanguagePlan) -> AssetPack:
        sitelinks = [
            SitelinkAsset(
                text=sl.text,
                description_1=sl.description_1,
                description_2=sl.description_2,
                final_url=sl.final_url,
            )
            for sl in lang.sitelinks
        ]
        callouts = [CalloutAsset(text=co) for co in lang.callouts]
        snippets = [
            StructuredSnippetAsset(header=s.header, values=s.values)
            for s in lang.structured_snippets
        ]
        return AssetPack(
            sitelinks=sitelinks,
            callouts=callouts,
            structured_snippets=snippets,
        )

    def build_rsa(
        self,
        lang: LanguagePlan,
        final_url: str,
        tracking_template: str,
        pinned_headlines: Optional[List[tuple]] = None,
    ) -> RSAd:
        """
        Build RSA from brief language plan.
        pinned_headlines: list of (text, pin_position) tuples for brand name pinning.
        """
        pin_map = {text: pos for text, pos in (pinned_headlines or [])}

        headlines = []
        for h in lang.headlines[:15]:
            pin = pin_map.get(h)
            headlines.append(PinnedHeadline(text=h, pin_position=pin))

        return RSAd(
            headlines=headlines,
            descriptions=lang.descriptions[:4],
            final_url=final_url,
            tracking_template=tracking_template,
            path_1=_slugify(lang.code, max_len=15),
            path_2=None,
            status=CampaignStatus.enabled,
        )

    def build_campaign_settings(
        self,
        brief: Brief,
        lang: LanguagePlan,
        camp_type_key: str,
        network_types: list,
        bid_strategy,
        target_cpa: Optional[float] = None,
        target_roas: Optional[float] = None,
    ) -> CampaignSettings:
        monthly_budget = brief.get_budget_for(camp_type_key, lang.code)
        daily_budget = round(monthly_budget / 30.44, 2) if monthly_budget else 1.0

        return CampaignSettings(
            bid_strategy=bid_strategy,
            target_cpa=target_cpa,
            target_roas=target_roas,
            budget_daily_eur=daily_budget,
            networks=network_types,
            language_codes=[lang.code],
            language_ids=[lang.google_language_id],
            geo_targets=brief.geo_targeting.target_countries,
            tracking_template=self.build_tracking_template(brief.utm_config),
            labels=brief.labels.copy(),
        )

    def get_labels(self, brief: Brief) -> List[str]:
        return brief.labels.copy()


def _slugify(text: str, max_len: int = 15) -> str:
    """Convert text to URL-path-safe slug."""
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len]
