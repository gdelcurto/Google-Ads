"""
Google Ads Editor CSV Exporter.

Generates a flat CSV file compatible with Google Ads Editor bulk upload.

Google Ads Editor uses a flat format (no "Type" column) where entity type
is inferred from which columns contain data:
  - Campaign row:   "Campaign" + "Campaign Type" + "Budget" + …
  - Ad Group row:   "Campaign" + "Ad Group" + "Max CPC"
  - Keyword row:    "Campaign" + "Ad Group" + "Keyword" + "Account keyword type"
  - RSA row:        "Campaign" + "Ad Group" + "Ad type" + "Headline 1" + …
  - Sitelink row:   "Campaign" + "Link Text" + "Final URL"
  - Callout row:    "Campaign" + "Callout text"
  - Snippet row:    "Campaign" + "Header" + "Snippet Values"
  - Neg-KW row:     "Campaign" + "Keyword" + "Account keyword type" (Negative …)

Column names and casing are taken directly from a real Ads Editor export.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import List

from app.domain.schemas.campaign_plan import (
    AccountPlan, AdGroupPlan, CampaignPlan, CampaignType, DemandGenAd,
    DisplayAd, Keyword, PMaxAssetGroup, RSAd,
)

logger = logging.getLogger(__name__)

# Mapping from our MatchType enum values to Ads Editor keyword type strings
_MATCH_TYPE_POS = {"Exact": "Exact", "Phrase": "Phrase", "Broad": "Broad"}
_MATCH_TYPE_NEG = {
    "Exact": "Negative Exact",
    "Phrase": "Negative Phrase",
    "Broad": "Negative Broad",
}


class AdsEditorCsvExporter:
    """
    Exports an AccountPlan to Google Ads Editor compatible CSV (flat format).
    """

    def export(self, plan: AccountPlan) -> str:
        """Returns the full CSV as a string."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        rows: List[dict] = []

        for campaign in plan.campaigns:
            rows.extend(self._export_campaign(campaign))
            rows.extend(self._export_ad_groups(campaign))
            rows.extend(self._export_keywords(campaign))
            rows.extend(self._export_ads(campaign))
            rows.extend(self._export_assets(campaign))
            rows.extend(self._export_pmax_asset_groups(campaign))

        rows.extend(self._export_global_negatives(plan))

        if rows:
            headers = self._get_all_headers(rows)
            writer.writerow(headers)
            for row_dict in rows:
                writer.writerow([row_dict.get(h, "") for h in headers])

        return output.getvalue()

    def _plan_metadata(self, plan: AccountPlan) -> str:
        """Returns plan metadata as a plain string for logging (not written to CSV)."""
        return (
            f"Client: {plan.client_name} | "
            f"Generated: {plan.generated_at.isoformat()} | "
            f"Campaigns: {plan.total_campaigns} | "
            f"Status: {'VALID' if plan.is_valid else 'HAS ERRORS'}"
        )

    def _get_all_headers(self, rows: List[dict]) -> List[str]:
        """
        Return column headers in the standard Ads Editor ordering.
        Column names and order match a real Google Ads Editor export.
        """
        ordered = [
            # ── Campaign ────────────────────────────────────────────────────
            "Campaign",
            "Labels",
            "Campaign Type",
            "Networks",
            "Budget",
            "Budget type",
            "Bid Strategy Type",
            "Target CPA",
            "Target ROAS",
            "Languages",
            "Location",
            "Ad rotation",
            "Tracking template",
            "Final URL suffix",
            "Start Date",
            "End Date",
            # ── Ad Group ────────────────────────────────────────────────────
            "Ad Group",
            "Max CPC",
            # ── Keyword / Negative keyword ──────────────────────────────────
            "Keyword",
            "Account keyword type",
            # ── Ad (RSA) ────────────────────────────────────────────────────
            "Ad type",
            "Final URL",
            "Path 1",
            "Path 2",
            "Headline 1",  "Headline 1 position",
            "Headline 2",  "Headline 2 position",
            "Headline 3",  "Headline 3 position",
            "Headline 4",  "Headline 4 position",
            "Headline 5",  "Headline 5 position",
            "Headline 6",  "Headline 6 position",
            "Headline 7",  "Headline 7 position",
            "Headline 8",  "Headline 8 position",
            "Headline 9",  "Headline 9 position",
            "Headline 10", "Headline 10 position",
            "Headline 11", "Headline 11 position",
            "Headline 12", "Headline 12 position",
            "Headline 13", "Headline 13 position",
            "Headline 14", "Headline 14 position",
            "Headline 15", "Headline 15 position",
            "Description 1", "Description 1 position",
            "Description 2", "Description 2 position",
            "Description 3", "Description 3 position",
            "Description 4", "Description 4 position",
            # ── Sitelink asset ──────────────────────────────────────────────
            "Link Text",
            "Description Line 1",
            "Description Line 2",
            # ── Structured Snippet asset ────────────────────────────────────
            "Header",
            "Snippet Values",
            # ── Callout asset ───────────────────────────────────────────────
            "Callout text",
            # ── PMax Asset Group (best-effort, not fully supported by Editor)
            "Asset Group Name",
            "Long Headline 1", "Long Headline 2", "Long Headline 3",
            "Long Headline 4", "Long Headline 5",
            "Final URL Expansion",
            "Audience Signal",
            # ── Status columns (must come last, matching Ads Editor order) ──
            "Campaign Status",
            "Ad Group Status",
            "Status",
        ]

        all_keys: set = set()
        for row in rows:
            all_keys.update(row.keys())

        extra = sorted(k for k in all_keys if k not in ordered)
        return ordered + extra

    # ── Campaign ───────────────────────────────────────────────────────────────

    def _export_campaign(self, campaign: CampaignPlan) -> List[dict]:
        settings = campaign.settings
        row: dict = {
            "Campaign":         campaign.campaign_name,
            "Campaign Type":    campaign.campaign_type.value,
            "Budget":           settings.budget_daily_eur,
            "Budget type":      "Daily",
            "Bid Strategy Type": settings.bid_strategy.value,
            "Networks":         "; ".join(n.value for n in settings.networks),
            "Languages":        "; ".join(str(lid) for lid in settings.language_ids),
            "Location":         "; ".join(settings.geo_targets),
            "Ad rotation":      settings.rotation,
            "Tracking template": settings.tracking_template,
            "Labels":           "; ".join(settings.labels),
            "Campaign Status":  campaign.status.value,
        }
        if settings.target_cpa:
            row["Target CPA"] = settings.target_cpa
        if settings.target_roas:
            row["Target ROAS"] = settings.target_roas
        if settings.final_url_suffix:
            row["Final URL suffix"] = settings.final_url_suffix
        if settings.start_date:
            row["Start Date"] = settings.start_date
        if settings.end_date:
            row["End Date"] = settings.end_date
        return [row]

    # ── Ad Group ───────────────────────────────────────────────────────────────

    def _export_ad_groups(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            rows.append({
                "Campaign":        campaign.campaign_name,
                "Ad Group":        ag.name,
                "Max CPC":         ag.default_max_cpc or "",
                "Ad Group Status": ag.status.value,
            })
        return rows

    # ── Keywords ───────────────────────────────────────────────────────────────

    def _export_keywords(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            for kw in ag.keywords:
                if kw.is_negative:
                    kw_type = _MATCH_TYPE_NEG.get(kw.match_type.value, "Negative Exact")
                    ad_group = ""
                else:
                    kw_type = _MATCH_TYPE_POS.get(kw.match_type.value, "Broad")
                    ad_group = ag.name

                row: dict = {
                    "Campaign":             campaign.campaign_name,
                    "Ad Group":             ad_group,
                    "Keyword":              kw.text,
                    "Account keyword type": kw_type,
                    "Status":               "Enabled",
                }
                if kw.max_cpc:
                    row["Max CPC"] = kw.max_cpc
                if kw.final_url:
                    row["Final URL"] = kw.final_url
                rows.append(row)
        return rows

    # ── RSA ────────────────────────────────────────────────────────────────────

    def _export_ads(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            for ad in ag.ads:
                rows.append(self._rsa_to_row(campaign.campaign_name, ag.name, ad))
        return rows

    def _rsa_to_row(self, campaign_name: str, ag_name: str, ad: RSAd) -> dict:
        row: dict = {
            "Campaign":          campaign_name,
            "Ad Group":          ag_name,
            "Ad type":           "Responsive search ad",
            "Final URL":         ad.final_url,
            "Tracking template": ad.tracking_template or "",
            "Path 1":            ad.path_1 or "",
            "Path 2":            ad.path_2 or "",
            "Status":            ad.status.value,
        }
        for i, h in enumerate(ad.headlines[:15], 1):
            row[f"Headline {i}"] = h.text
            if h.pin_position:
                row[f"Headline {i} position"] = h.pin_position
        for i, d in enumerate(ad.descriptions[:4], 1):
            row[f"Description {i}"] = d
        return row

    # ── Assets (Sitelinks, Callouts, Snippets) ─────────────────────────────────

    def _export_assets(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        seen_sitelinks: set = set()
        seen_callouts:  set = set()
        seen_snippets:  set = set()

        for ag in campaign.ad_groups:
            assets = ag.assets

            for sl in assets.sitelinks:
                if sl.text not in seen_sitelinks:
                    rows.append({
                        "Campaign":          campaign.campaign_name,
                        "Link Text":         sl.text,
                        "Description Line 1": sl.description_1,
                        "Description Line 2": sl.description_2,
                        "Final URL":         sl.final_url,
                        "Status":            "Enabled",
                    })
                    seen_sitelinks.add(sl.text)

            for co in assets.callouts:
                if co.text not in seen_callouts:
                    rows.append({
                        "Campaign":     campaign.campaign_name,
                        "Callout text": co.text,
                        "Status":       "Enabled",
                    })
                    seen_callouts.add(co.text)

            for sn in assets.structured_snippets:
                if sn.header not in seen_snippets:
                    rows.append({
                        "Campaign":      campaign.campaign_name,
                        "Header":        sn.header,
                        "Snippet Values": "; ".join(sn.values),
                        "Status":        "Enabled",
                    })
                    seen_snippets.add(sn.header)

        return rows

    # ── PMax Asset Groups ──────────────────────────────────────────────────────

    def _export_pmax_asset_groups(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.pmax_asset_groups:
            rows.append(self._pmax_ag_to_row(campaign.campaign_name, ag))
        return rows

    def _pmax_ag_to_row(self, campaign_name: str, ag: PMaxAssetGroup) -> dict:
        row: dict = {
            "Campaign":          campaign_name,
            "Asset Group Name":  ag.name,
            "Final URL":         ag.final_url,
            "Final URL Expansion": "Yes" if ag.final_url_expansion else "No",
            "Audience Signal":   "; ".join(ag.audience_signals[:3]),
            "Status":            "Enabled",
        }
        for i, h  in enumerate(ag.headlines[:15], 1):
            row[f"Headline {i}"] = h
        for i, lh in enumerate(ag.long_headlines[:5], 1):
            row[f"Long Headline {i}"] = lh
        for i, d  in enumerate(ag.descriptions[:5], 1):
            row[f"Description {i}"] = d
        for i, img in enumerate(ag.images[:3], 1):
            row[f"Image {i}"] = img
        if ag.logo_url:
            row["Logo"] = ag.logo_url
        if ag.youtube_video_url:
            row["YouTube Video URL"] = ag.youtube_video_url
        if ag.has_missing_assets:
            row["Missing Assets"] = " | ".join(ag.missing_asset_notes)
        return row

    # ── Global Negatives ───────────────────────────────────────────────────────

    def _export_global_negatives(self, plan: AccountPlan) -> List[dict]:
        rows = []
        for kw in plan.global_negative_keywords:
            rows.append({
                "Campaign":             "",
                "Keyword":              kw.text,
                "Account keyword type": _MATCH_TYPE_NEG.get(
                    kw.match_type.value, "Negative Broad"
                ),
                "Status": "Enabled",
            })
        return rows


def export_plan_to_csv(plan: AccountPlan) -> str:
    """Convenience function."""
    return AdsEditorCsvExporter().export(plan)
