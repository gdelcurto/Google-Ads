"""
Google Ads Editor CSV Exporter.
Generates a multi-section CSV file compatible with Google Ads Editor bulk upload.

Google Ads Editor CSV format:
- One file with sections delimited by "Type" column
- Each row has a "Type" that determines the entity: Campaign, Ad Group, Keyword, etc.
- Required columns vary by entity type
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


class AdsEditorCsvExporter:
    """
    Exports an AccountPlan to Google Ads Editor compatible CSV.

    Row types supported:
    - Campaign
    - Ad Group
    - Expanded Text Ad (legacy, for reference)
    - Responsive Search Ad
    - Keyword
    - Negative Keyword (Campaign Level)
    - Sitelink Asset
    - Callout Asset
    - Structured Snippet Asset
    - Performance Max Campaign (special section)
    - Image Asset (placeholders)
    """

    def export(self, plan: AccountPlan) -> str:
        """Returns the full CSV as a string."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        rows = []

        for campaign in plan.campaigns:
            rows.extend(self._export_campaign(campaign))
            rows.extend(self._export_ad_groups(campaign))
            rows.extend(self._export_keywords(campaign))
            rows.extend(self._export_ads(campaign))
            rows.extend(self._export_assets(campaign))
            rows.extend(self._export_pmax_asset_groups(campaign))
            rows.extend(self._export_negative_keywords(campaign))

        # Global negatives (shared list)
        rows.extend(self._export_global_negatives(plan))

        # Write column header + all rows
        if rows:
            headers = self._get_all_headers(rows)
            writer.writerow(headers)
            for row_dict in rows:
                writer.writerow([row_dict.get(h, "") for h in headers])

        return output.getvalue()

    def _plan_metadata_comment(self, plan: AccountPlan) -> str:
        """Returns plan metadata as a plain string (for logging, not for CSV output)."""
        return (
            f"Client: {plan.client_name} | "
            f"Generated: {plan.generated_at.isoformat()} | "
            f"Campaigns: {plan.total_campaigns} | "
            f"Status: {'VALID' if plan.is_valid else 'HAS ERRORS'}"
        )

    def _get_all_headers(self, rows: List[dict]) -> List[str]:
        """Collect all unique column headers from all rows, in standard order."""
        # Standard Google Ads Editor column ordering
        ordered_headers = [
            "Type",
            "Status",
            "Campaign",
            "Ad Group",
            "Campaign Type",
            "Campaign Subtype",
            "Budget",
            "Budget Type",
            "Bid Strategy Type",
            "Target CPA",
            "Target ROAS",
            "Networks",
            "Languages",
            "Location",
            "Ad Rotation",
            "Tracking Template",
            "Final URL Suffix",
            "Label",
            "Start Date",
            "End Date",
            "Default Max CPC",
            "Keyword",
            "Match Type",
            "Max CPC",
            "Headline 1",
            "Headline 2",
            "Headline 3",
            "Headline 4",
            "Headline 5",
            "Headline 6",
            "Headline 7",
            "Headline 8",
            "Headline 9",
            "Headline 10",
            "Headline 11",
            "Headline 12",
            "Headline 13",
            "Headline 14",
            "Headline 15",
            "Headline 1 Position",
            "Headline 2 Position",
            "Headline 3 Position",
            "Description 1",
            "Description 2",
            "Description 3",
            "Description 4",
            "Description 1 Position",
            "Description 2 Position",
            "Final URL",
            "Path 1",
            "Path 2",
            "Sitelink Text",
            "Sitelink Description Line 1",
            "Sitelink Description Line 2",
            "Sitelink Final URL",
            "Callout Text",
            "Snippet Header",
            "Snippet Values",
            "Asset Group Name",
            "Long Headline 1",
            "Long Headline 2",
            "Long Headline 3",
            "Long Headline 4",
            "Long Headline 5",
            "Final URL Expansion",
            "Audience Signal",
        ]
        # Add any extra headers not in the standard order
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())

        extra = [k for k in all_keys if k not in ordered_headers]
        return ordered_headers + sorted(extra)

    # ── Campaign rows ──────────────────────────────────────────────────────────

    def _export_campaign(self, campaign: CampaignPlan) -> List[dict]:
        settings = campaign.settings

        # Networks string
        networks = "; ".join(n.value for n in settings.networks)

        # Languages string (Google Language IDs)
        lang_ids = "; ".join(str(lid) for lid in settings.language_ids)

        # Geo targets
        locations = "; ".join(settings.geo_targets)

        # Bid strategy
        bid_row: dict = {
            "Type": "Campaign",
            "Status": campaign.status.value,
            "Campaign": campaign.campaign_name,
            "Campaign Type": campaign.campaign_type.value,
            "Campaign Subtype": campaign.campaign_subtype,
            "Budget": settings.budget_daily_eur,
            "Budget Type": "Daily",
            "Bid Strategy Type": settings.bid_strategy.value,
            "Networks": networks,
            "Languages": lang_ids,
            "Location": locations,
            "Ad Rotation": settings.rotation,
            "Tracking Template": settings.tracking_template,
            "Label": "; ".join(settings.labels),
        }

        if settings.target_cpa:
            bid_row["Target CPA"] = settings.target_cpa
        if settings.target_roas:
            bid_row["Target ROAS"] = settings.target_roas
        if settings.start_date:
            bid_row["Start Date"] = settings.start_date
        if settings.end_date:
            bid_row["End Date"] = settings.end_date

        return [bid_row]

    # ── Ad Group rows ──────────────────────────────────────────────────────────

    def _export_ad_groups(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            row = {
                "Type": "Ad Group",
                "Status": ag.status.value,
                "Campaign": campaign.campaign_name,
                "Ad Group": ag.name,
                "Default Max CPC": ag.default_max_cpc or "",
            }
            rows.append(row)
        return rows

    # ── Keyword rows ──────────────────────────────────────────────────────────

    def _export_keywords(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            for kw in ag.keywords:
                if kw.is_negative:
                    row_type = "Negative Keyword"
                    ad_group_val = ""
                else:
                    row_type = "Keyword"
                    ad_group_val = ag.name
                row = {
                    "Type": row_type,
                    "Status": "Enabled",
                    "Campaign": campaign.campaign_name,
                    "Ad Group": ad_group_val,
                    "Keyword": kw.text,
                    "Match Type": kw.match_type.value,
                }
                if kw.max_cpc:
                    row["Max CPC"] = kw.max_cpc
                if kw.final_url:
                    row["Final URL"] = kw.final_url
                rows.append(row)
        return rows

    # ── RSA rows ──────────────────────────────────────────────────────────────

    def _export_ads(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            for ad in ag.ads:
                row = self._rsa_to_row(campaign.campaign_name, ag.name, ad)
                rows.append(row)
        return rows

    def _rsa_to_row(self, campaign_name: str, ag_name: str, ad: RSAd) -> dict:
        row = {
            "Type": "Responsive Search Ad",
            "Status": ad.status.value,
            "Campaign": campaign_name,
            "Ad Group": ag_name,
            "Final URL": ad.final_url,
            "Tracking Template": ad.tracking_template or "",
            "Path 1": ad.path_1 or "",
            "Path 2": ad.path_2 or "",
        }

        # Headlines (up to 15)
        for i, h in enumerate(ad.headlines[:15], 1):
            row[f"Headline {i}"] = h.text
            if h.pin_position:
                row[f"Headline {i} Position"] = h.pin_position

        # Descriptions (up to 4)
        for i, d in enumerate(ad.descriptions[:4], 1):
            row[f"Description {i}"] = d

        return row

    # ── Asset rows (Sitelinks, Callouts, Snippets) ───────────────────────────

    def _export_assets(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        seen_sitelinks = set()
        seen_callouts = set()
        seen_snippets = set()

        for ag in campaign.ad_groups:
            assets = ag.assets

            for sl in assets.sitelinks:
                key = sl.text
                if key not in seen_sitelinks:
                    rows.append({
                        "Type": "Sitelink",
                        "Campaign": campaign.campaign_name,
                        "Sitelink Text": sl.text,
                        "Sitelink Description Line 1": sl.description_1,
                        "Sitelink Description Line 2": sl.description_2,
                        "Sitelink Final URL": sl.final_url,
                    })
                    seen_sitelinks.add(key)

            for co in assets.callouts:
                key = co.text
                if key not in seen_callouts:
                    rows.append({
                        "Type": "Callout",
                        "Campaign": campaign.campaign_name,
                        "Callout Text": co.text,
                    })
                    seen_callouts.add(key)

            for sn in assets.structured_snippets:
                key = sn.header
                if key not in seen_snippets:
                    rows.append({
                        "Type": "Structured Snippet",
                        "Campaign": campaign.campaign_name,
                        "Snippet Header": sn.header,
                        "Snippet Values": "; ".join(sn.values),
                    })
                    seen_snippets.add(key)

        return rows

    # ── PMax Asset Group rows ─────────────────────────────────────────────────

    def _export_pmax_asset_groups(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.pmax_asset_groups:
            row = self._pmax_ag_to_row(campaign.campaign_name, ag)
            rows.append(row)
        return rows

    def _pmax_ag_to_row(self, campaign_name: str, ag: PMaxAssetGroup) -> dict:
        row = {
            "Type": "Asset Group",
            "Campaign": campaign_name,
            "Asset Group Name": ag.name,
            "Final URL": ag.final_url,
            "Final URL Expansion": "Yes" if ag.final_url_expansion else "No",
            "Audience Signal": "; ".join(ag.audience_signals[:3]),
        }

        for i, h in enumerate(ag.headlines[:15], 1):
            row[f"Headline {i}"] = h

        for i, lh in enumerate(ag.long_headlines[:5], 1):
            row[f"Long Headline {i}"] = lh

        for i, d in enumerate(ag.descriptions[:5], 1):
            row[f"Description {i}"] = d

        # Images as notes
        for i, img_url in enumerate(ag.images[:3], 1):
            row[f"Image {i}"] = img_url

        if ag.logo_url:
            row["Logo"] = ag.logo_url
        if ag.youtube_video_url:
            row["YouTube Video URL"] = ag.youtube_video_url

        if ag.has_missing_assets:
            row["Missing Assets"] = " | ".join(ag.missing_asset_notes)

        return row

    # ── Negative keyword rows ─────────────────────────────────────────────────

    def _export_negative_keywords(self, campaign: CampaignPlan) -> List[dict]:
        # Shared negative keyword lists are not importable via CSV bulk upload
        # in Google Ads Editor — they must be managed manually in the UI.
        return []

    # ── Global negatives ──────────────────────────────────────────────────────

    def _export_global_negatives(self, plan: AccountPlan) -> List[dict]:
        rows = []
        for kw in plan.global_negative_keywords:
            rows.append({
                "Type": "Negative Keyword",
                "Campaign": "",  # blank = applies to all campaigns in upload
                "Keyword": kw.text,
                "Match Type": kw.match_type.value,
            })
        return rows


def export_plan_to_csv(plan: AccountPlan) -> str:
    """Convenience function."""
    exporter = AdsEditorCsvExporter()
    return exporter.export(plan)
