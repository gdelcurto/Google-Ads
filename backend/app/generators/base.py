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
        headlines: Optional[List[str]] = None,
        descriptions: Optional[List[str]] = None,
        ad_group_index: int = 0,
    ) -> RSAd:
        """
        Build RSA from brief language plan.

        - headlines / descriptions: type-specific copy override (from campaign agent).
          When provided, these replace lang.headlines / lang.descriptions.
          Use CampaignAgent.get_headlines(lang) to resolve the right source.
        - pinned_headlines: list of (text, pin_position) tuples for brand name pinning.
        - ad_group_index: 0-based index of the ad group within the campaign.
          When > 0, the headline pool is rotated deterministically so each ad
          group shows a different creative variation (different subset of headlines).
          The pinned headline (if any) is always kept at position 1.
        """
        h_source = list(headlines if headlines is not None else lang.headlines)

        # If type-specific headlines are too few for a valid RSA (min 3),
        # supplement from the generic language pool.
        if headlines is not None and len(h_source) < 3:
            for h in lang.headlines:
                if h not in h_source:
                    h_source.append(h)
                if len(h_source) >= 3:
                    break

        # Ensure pinned headlines are present in the pool (e.g. brand name).
        # If the headline pool doesn't contain the pinned text, inject it at
        # position 0 so it gets included in the RSA and the pin takes effect.
        if pinned_headlines:
            for text, _pos in pinned_headlines:
                if text and len(text) <= 30 and text not in h_source:
                    h_source.insert(0, text)

        # Rotate the headline pool for each ad group so previews differ.
        # Rotation step = 1/3 of pool size, minimum 1, ensuring meaningful shift.
        if ad_group_index > 0 and len(h_source) > 3:
            n = len(h_source)
            step = max(1, n // 3)
            offset = (ad_group_index * step) % n
            # Keep any pinned headline first to avoid losing it in the rotation.
            pin_map_lookup = {text: pos for text, pos in (pinned_headlines or [])}
            pinned_texts = [t for t in h_source if t in pin_map_lookup]
            unpinned = [t for t in h_source if t not in pin_map_lookup]
            rotated_unpinned = unpinned[offset % len(unpinned):] + unpinned[:offset % len(unpinned)] if unpinned else []
            h_source = pinned_texts + rotated_unpinned
        else:
            pin_map_lookup = {text: pos for text, pos in (pinned_headlines or [])}

        # Merge per-type descriptions with generic pool to always meet RSAd min (2).
        # Rotate descriptions too so each ad group emphasises different selling points.
        if descriptions is not None:
            merged = list(descriptions)
            for d in lang.descriptions:
                if d not in merged:
                    merged.append(d)
            d_source = merged
        else:
            d_source = list(lang.descriptions)

        if ad_group_index > 0 and len(d_source) > 2:
            d_offset = ad_group_index % len(d_source)
            d_source = d_source[d_offset:] + d_source[:d_offset]

        rsa_headlines = []
        for h in h_source[:15]:
            pin = pin_map_lookup.get(h)
            rsa_headlines.append(PinnedHeadline(text=h, pin_position=pin))

        return RSAd(
            headlines=rsa_headlines,
            descriptions=d_source[:4],
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

    def _generate_campaign_skeleton(
        self,
        brief: Brief,
        lang: LanguagePlan,
        camp_type: str,
        subtype: str,
        camp_type_key: str,
        network_types: list,
        bid_strategy,
        target_cpa: Optional[float] = None,
        target_roas: Optional[float] = None,
    ) -> tuple:
        """
        Return (campaign_name, external_key, settings, tracking_template, asset_pack).

        Consolidates the 5 boilerplate lines that every generator repeats at the start
        of _generate_for_language():
            campaign_name = self.build_campaign_name(...)
            external_key  = self.build_external_key(...)
            settings      = self.build_campaign_settings(...)
            tracking_template = self.build_tracking_template(...)
            asset_pack    = self.build_asset_pack(...)
        """
        campaign_name = self.build_campaign_name(brief, lang.code, camp_type, subtype)
        external_key  = self.build_external_key(
            brief, lang.code, camp_type.lower(), subtype.lower()
        )
        settings = self.build_campaign_settings(
            brief=brief,
            lang=lang,
            camp_type_key=camp_type_key,
            network_types=network_types,
            bid_strategy=bid_strategy,
            target_cpa=target_cpa,
            target_roas=target_roas,
        )
        tracking_template = self.build_tracking_template(brief.utm_config)
        asset_pack = self.build_asset_pack(lang)
        return campaign_name, external_key, settings, tracking_template, asset_pack

    def _build_rsa_ad(
        self,
        lang: LanguagePlan,
        asset_key: str,
        final_url: str,
        tracking_template: str,
        pinned_headlines: Optional[List[tuple]] = None,
        ad_group_index: int = 0,
    ) -> RSAd:
        """
        Build an RSAd from lang.{asset_key}_headlines / lang.{asset_key}_descriptions
        when per-type copy overrides are stored in the LanguagePlan under a specific key.

        Falls back to lang.headlines / lang.descriptions when the asset_key attributes
        are absent or empty.
        """
        headlines = (
            getattr(lang, f"{asset_key}_headlines", None)
            or lang.headlines
        )
        descriptions = (
            getattr(lang, f"{asset_key}_descriptions", None)
            or lang.descriptions
        )
        return self.build_rsa(
            lang=lang,
            final_url=final_url,
            tracking_template=tracking_template,
            pinned_headlines=pinned_headlines,
            headlines=headlines or None,
            descriptions=descriptions or None,
            ad_group_index=ad_group_index,
        )


def _slugify(text: str, max_len: int = 15) -> str:
    """Convert text to URL-path-safe slug."""
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len]
