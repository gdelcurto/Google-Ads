"""
Google Ads Editor CSV Exporter.

Generates a CSV file compatible with Google Ads Editor bulk upload.

Row layout (based on the official Google Ads Editor example format):

  Campaign row  → Campaign + Campaign Type + Campaign Daily Budget +
                  Campaign Status + Networks + Bid Strategy Type +
                  Languages + Start Date + End Date + Ad Schedule + Location

  Keyword row   → Campaign + Campaign Type + Ad Group + Ad Group Status +
                  Max CPC + Keyword + Type   (Exact/Broad/Phrase/Negative)

  RSA row       → Campaign + Campaign Type + Ad Group +
                  Headline 1..15 + Description 1..4 +
                  Final URL + Path 1 + Path 2 + Status

  Sitelink row  → Campaign + Link Text + Description Line 1/2 + Final URL

  Callout row   → Campaign + Callout text

  Snippet row   → Campaign + Header + Snippet Values

  PMax AG row   → Campaign + Asset Group Name + headlines/descriptions/...
"""
from __future__ import annotations

import csv
import io
import logging
from typing import List, Optional

from app.domain.schemas.campaign_plan import (
    AccountPlan, AdGroupPlan, CampaignPlan, CampaignType,
    Keyword, PMaxAssetGroup, RSAd,
)

logger = logging.getLogger(__name__)

# ── Network label mapping ────────────────────────────────────────────────────
# Maps our NetworkType .value strings → Google Ads Editor display labels
_NETWORK_LABELS = {
    "Search":           "Google Search",
    "Search partners":  "Search Partners",
    "Display Network":  "Display Network",
    "YouTube":          "YouTube",
}

# ── Bid Strategy label mapping ───────────────────────────────────────────────
# Ads Editor expects Title Case; our enum uses sentence case
_BID_STRATEGY_LABELS = {
    "Maximize conversions":       "Maximize Conversions",
    "Maximize conversion value":  "Maximize Conversion Value",
    "Maximize clicks":            "Maximize Clicks",
    "Target impression share":    "Target Impression Share",
    "Target CPA":                 "Target CPA",
    "Target ROAS":                "Target ROAS",
    "Manual CPC":                 "Manual CPC",
    "Enhanced CPC":               "Enhanced CPC",
}

# ── Column order (matches Google Ads Editor import format) ───────────────────
_ORDERED_HEADERS = [
    # Campaign-level
    "Campaign",
    "Campaign Type",
    "Campaign Daily Budget",
    "Campaign Status",
    "Networks",
    "Bid Strategy Type",
    "Target CPA",
    "Target ROAS",
    "Languages",
    "Start Date",
    "End Date",
    "Tracking template",
    "Final URL suffix",
    "Labels",
    # Ad Group-level
    "Ad Group",
    "Ad Group Status",
    "Max CPC",
    # Keyword / match type
    "Keyword",
    "Type",
    # RSA headlines (1-15)
    "Headline 1",  "Headline 2",  "Headline 3",  "Headline 4",  "Headline 5",
    "Headline 6",  "Headline 7",  "Headline 8",  "Headline 9",  "Headline 10",
    "Headline 11", "Headline 12", "Headline 13", "Headline 14", "Headline 15",
    # RSA descriptions (1-4)
    "Description 1", "Description 2", "Description 3", "Description 4",
    # Ad destination
    "Final URL",
    "Path 1",
    "Path 2",
    # Row status
    "Status",
    # Campaign targeting (at end, as in Google example)
    "Ad Schedule",
    "Location",
    # Assets — sitelinks
    "Link Text",
    "Description Line 1",
    "Description Line 2",
    # Assets — structured snippets
    "Header",
    "Snippet Values",
    # Assets — callouts
    "Callout text",
    # PMax Asset Groups (best-effort)
    "Asset Group Name",
    "Long Headline 1", "Long Headline 2", "Long Headline 3",
    "Long Headline 4", "Long Headline 5",
    "Final URL Expansion",
    "Audience Signal",
]


class AdsEditorCsvExporter:
    """Exports an AccountPlan to Google Ads Editor compatible CSV."""

    def export(self, plan: AccountPlan) -> str:
        """Returns the full CSV as a UTF-8 string."""
        rows: List[dict] = []

        for campaign in plan.campaigns:
            rows.extend(self._campaign_row(campaign))
            rows.extend(self._keyword_rows(campaign))
            rows.extend(self._rsa_rows(campaign))
            rows.extend(self._asset_rows(campaign))
            rows.extend(self._pmax_rows(campaign))

        rows.extend(self._global_negative_rows(plan))

        # UTF-8 BOM so that tools like Excel / Ads Editor auto-detect encoding
        output = io.StringIO()
        output.write("\ufeff")
        if rows:
            headers = self._headers(rows)
            # QUOTE_MINIMAL: only quote cells that contain the delimiter, a
            # quote character, or a newline.  Empty cells stay truly empty
            # (not ""), which matches the official Google Ads Editor format.
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row.get(h, "") for h in headers])

        return output.getvalue()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _headers(self, rows: List[dict]) -> List[str]:
        """Ordered headers: predefined order + any extra keys found in rows."""
        seen = set(_ORDERED_HEADERS)
        extra = sorted(k for row in rows for k in row if k not in seen)
        return _ORDERED_HEADERS + extra

    @staticmethod
    def _networks(campaign: CampaignPlan) -> str:
        parts = [
            _NETWORK_LABELS.get(n.value, n.value)
            for n in campaign.settings.networks
        ]
        return ";".join(parts)

    @staticmethod
    def _languages(campaign: CampaignPlan) -> str:
        # Use lowercase language codes (it, en, de …)
        codes = [c.lower() for c in campaign.settings.language_codes if c]
        return ";".join(codes)

    @staticmethod
    def _bid_strategy(campaign: CampaignPlan) -> str:
        raw = campaign.settings.bid_strategy.value
        return _BID_STRATEGY_LABELS.get(raw, raw)

    @staticmethod
    def _location(campaign: CampaignPlan) -> str:
        return ";".join(campaign.settings.geo_targets)

    # ── Campaign row ─────────────────────────────────────────────────────────

    def _campaign_row(self, campaign: CampaignPlan) -> List[dict]:
        s = campaign.settings
        row: dict = {
            "Campaign":              campaign.campaign_name,
            "Campaign Type":         campaign.campaign_type.value,
            "Campaign Daily Budget": s.budget_daily_eur,
            "Campaign Status":       campaign.status.value,
            "Networks":              self._networks(campaign),
            "Bid Strategy Type":     self._bid_strategy(campaign),
            "Languages":             self._languages(campaign),
            "Location":              self._location(campaign),
            "Tracking template":     s.tracking_template,
            "Labels":                ";".join(s.labels),
        }
        if s.target_cpa:
            row["Target CPA"] = s.target_cpa
        if s.target_roas:
            row["Target ROAS"] = s.target_roas
        if s.final_url_suffix:
            row["Final URL suffix"] = s.final_url_suffix
        if s.start_date:
            row["Start Date"] = s.start_date
        if s.end_date:
            row["End Date"] = s.end_date
        return [row]

    # ── Keyword rows ─────────────────────────────────────────────────────────

    def _keyword_rows(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            kws = ag.keywords
            if not kws:
                # Ad group with no keywords (display / retargeting) — emit an
                # explicit ad group definition row so Ads Editor registers it.
                rows.append({
                    "Campaign":        campaign.campaign_name,
                    "Campaign Type":   campaign.campaign_type.value,
                    "Ad Group":        ag.name,
                    "Ad Group Status": ag.status.value,
                    "Max CPC":         ag.default_max_cpc or "",
                })
                continue

            for kw in kws:
                kw_type = "Negative" if kw.is_negative else kw.match_type.value
                row: dict = {
                    "Campaign":        campaign.campaign_name,
                    "Campaign Type":   campaign.campaign_type.value,
                    "Ad Group":        ag.name,
                    "Ad Group Status": ag.status.value,
                    "Max CPC":         ag.default_max_cpc or "",
                    "Keyword":         kw.text,
                    "Type":            kw_type,
                }
                if kw.max_cpc:
                    row["Max CPC"] = kw.max_cpc
                if kw.final_url:
                    row["Final URL"] = kw.final_url
                rows.append(row)
        return rows

    # ── RSA rows ─────────────────────────────────────────────────────────────

    def _rsa_rows(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        for ag in campaign.ad_groups:
            for ad in ag.ads:
                rows.append(self._rsa_to_row(campaign, ag.name, ad))
        return rows

    @staticmethod
    def _rsa_to_row(campaign: CampaignPlan, ag_name: str, ad: RSAd) -> dict:
        row: dict = {
            "Campaign":        campaign.campaign_name,
            "Campaign Type":   campaign.campaign_type.value,
            "Ad Group":        ag_name,
            "Final URL":       ad.final_url,
            "Path 1":          ad.path_1 or "",
            "Path 2":          ad.path_2 or "",
            "Status":          ad.status.value,
        }
        if ad.tracking_template:
            row["Tracking template"] = ad.tracking_template
        for i, h in enumerate(ad.headlines[:15], 1):
            row[f"Headline {i}"] = h.text
        for i, d in enumerate(ad.descriptions[:4], 1):
            row[f"Description {i}"] = d
        return row

    # ── Asset rows (sitelinks, callouts, snippets) ────────────────────────────

    def _asset_rows(self, campaign: CampaignPlan) -> List[dict]:
        rows = []
        seen_sl:  set = set()
        seen_co:  set = set()
        seen_sn:  set = set()

        for ag in campaign.ad_groups:
            pack = ag.assets

            for sl in pack.sitelinks:
                if sl.text not in seen_sl:
                    rows.append({
                        "Campaign":          campaign.campaign_name,
                        "Link Text":         sl.text,
                        "Description Line 1": sl.description_1,
                        "Description Line 2": sl.description_2,
                        "Final URL":         sl.final_url,
                    })
                    seen_sl.add(sl.text)

            for co in pack.callouts:
                if co.text not in seen_co:
                    rows.append({
                        "Campaign":    campaign.campaign_name,
                        "Callout text": co.text,
                    })
                    seen_co.add(co.text)

            for sn in pack.structured_snippets:
                if sn.header not in seen_sn:
                    rows.append({
                        "Campaign":      campaign.campaign_name,
                        "Header":        sn.header,
                        "Snippet Values": ";".join(sn.values),
                    })
                    seen_sn.add(sn.header)

        return rows

    # ── PMax Asset Group rows ─────────────────────────────────────────────────

    def _pmax_rows(self, campaign: CampaignPlan) -> List[dict]:
        return [
            self._pmax_ag_to_row(campaign.campaign_name, ag)
            for ag in campaign.pmax_asset_groups
        ]

    @staticmethod
    def _pmax_ag_to_row(campaign_name: str, ag: PMaxAssetGroup) -> dict:
        row: dict = {
            "Campaign":           campaign_name,
            "Asset Group Name":   ag.name,
            "Final URL":          ag.final_url,
            "Final URL Expansion": "Yes" if ag.final_url_expansion else "No",
            "Audience Signal":    ";".join(ag.audience_signals[:3]),
            "Status":             "Enabled",
        }
        for i, h  in enumerate(ag.headlines[:15], 1):
            row[f"Headline {i}"] = h
        for i, lh in enumerate(ag.long_headlines[:5], 1):
            row[f"Long Headline {i}"] = lh
        for i, d  in enumerate(ag.descriptions[:4], 1):
            row[f"Description {i}"] = d
        if ag.has_missing_assets:
            row["Missing Assets"] = " | ".join(ag.missing_asset_notes)
        return row

    # ── Account-level negative keywords ──────────────────────────────────────

    def _global_negative_rows(self, plan: AccountPlan) -> List[dict]:
        return [
            {
                "Keyword": kw.text,
                "Type":    "Negative",
            }
            for kw in plan.global_negative_keywords
        ]


def export_plan_to_csv(plan: AccountPlan) -> str:
    """Convenience wrapper."""
    return AdsEditorCsvExporter().export(plan)
