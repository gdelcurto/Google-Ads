"""
Pydantic schemas for the generated campaign plan (derived from Brief).
These represent the complete structure ready for export or API publish.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_ROME = ZoneInfo("Europe/Rome")
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MatchType(str, Enum):
    exact = "Exact"
    phrase = "Phrase"
    broad = "Broad"


class CampaignType(str, Enum):
    search = "Search"
    display = "Display"
    video = "Video"
    performance_max = "Performance Max"
    demand_gen = "Demand Gen"
    shopping = "Shopping"


class CampaignStatus(str, Enum):
    enabled = "Enabled"
    paused = "Paused"
    removed = "Removed"


class BidStrategy(str, Enum):
    target_cpa = "Target CPA"
    target_roas = "Target ROAS"
    maximize_conversions = "Maximize conversions"
    maximize_conversion_value = "Maximize conversion value"
    manual_cpc = "Manual CPC"
    enhanced_cpc = "Enhanced CPC"


class NetworkType(str, Enum):
    search = "Search"
    search_partners = "Search partners"
    display = "Display Network"


# ─── Keywords ────────────────────────────────────────────────────────────────

class Keyword(BaseModel):
    text: str
    match_type: MatchType
    max_cpc: Optional[float] = None
    final_url: Optional[str] = None
    is_negative: bool = False
    label: Optional[str] = None


# ─── Ads ─────────────────────────────────────────────────────────────────────

class PinnedHeadline(BaseModel):
    text: str
    pin_position: Optional[int] = Field(None, ge=1, le=3)


class RSAd(BaseModel):
    """Responsive Search Ad"""
    headlines: List[PinnedHeadline] = Field(..., min_length=3, max_length=15)
    descriptions: List[str] = Field(..., min_length=2, max_length=4)
    final_url: str
    tracking_template: Optional[str] = None
    path_1: Optional[str] = Field(None, max_length=15)
    path_2: Optional[str] = Field(None, max_length=15)
    status: CampaignStatus = CampaignStatus.enabled


class DemandGenAd(BaseModel):
    """Demand Gen (former Discovery) ad — may contain TODO placeholders."""
    headlines: List[str] = Field(..., min_length=1, max_length=5)
    descriptions: List[str] = Field(..., min_length=1, max_length=5)
    images: List[str] = Field(default_factory=list, description="Asset URLs or TODO placeholders")
    logo_url: Optional[str] = None
    final_url: str
    has_missing_assets: bool = False
    missing_asset_notes: List[str] = Field(default_factory=list)


class DisplayAd(BaseModel):
    headlines: List[str] = Field(default_factory=list)
    descriptions: List[str] = Field(default_factory=list)
    image_urls: List[str] = Field(default_factory=list)
    logo_url: Optional[str] = None
    final_url: str
    has_missing_assets: bool = False


# ─── Extensions / Assets ─────────────────────────────────────────────────────

class SitelinkAsset(BaseModel):
    text: str = Field(..., max_length=25)
    description_1: str = Field(..., max_length=35)
    description_2: str = Field(..., max_length=35)
    final_url: str


class CalloutAsset(BaseModel):
    text: str = Field(..., max_length=25)


class StructuredSnippetAsset(BaseModel):
    header: str
    values: List[str]


class CallAsset(BaseModel):
    phone_number: Optional[str] = None
    country_code: str = "IT"


class AssetPack(BaseModel):
    sitelinks: List[SitelinkAsset] = Field(default_factory=list)
    callouts: List[CalloutAsset] = Field(default_factory=list)
    structured_snippets: List[StructuredSnippetAsset] = Field(default_factory=list)
    call: Optional[CallAsset] = None


# ─── PMax Asset Groups ────────────────────────────────────────────────────────

class PMaxAssetGroup(BaseModel):
    name: str
    headlines: List[str] = Field(..., min_length=3, max_length=15)
    long_headlines: List[str] = Field(..., min_length=1, max_length=5)
    descriptions: List[str] = Field(..., min_length=2, max_length=5)
    images: List[str] = Field(default_factory=list)
    logo_url: Optional[str] = None
    youtube_video_url: Optional[str] = None
    final_url: str
    audience_signals: List[str] = Field(default_factory=list)
    final_url_expansion: bool = False
    has_missing_assets: bool = False
    missing_asset_notes: List[str] = Field(default_factory=list)


# ─── Ad Groups ────────────────────────────────────────────────────────────────

class AdGroupPlan(BaseModel):
    name: str
    status: CampaignStatus = CampaignStatus.enabled
    default_max_cpc: Optional[float] = None
    keywords: List[Keyword] = Field(default_factory=list)
    ads: List[RSAd] = Field(default_factory=list)
    display_ads: List[DisplayAd] = Field(default_factory=list)
    demand_gen_ads: List[DemandGenAd] = Field(default_factory=list)
    assets: AssetPack = Field(default_factory=AssetPack)
    audience_targeting: List[str] = Field(default_factory=list)
    targeting_setting: str = "targeting"  # targeting | observation


# ─── Campaign ────────────────────────────────────────────────────────────────

class CampaignSettings(BaseModel):
    bid_strategy: BidStrategy
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    budget_daily_eur: float
    networks: List[NetworkType] = Field(default_factory=list)
    language_codes: List[str] = Field(default_factory=list)
    language_ids: List[int] = Field(default_factory=list)
    geo_targets: List[str] = Field(default_factory=list)
    tracking_template: str
    final_url_suffix: Optional[str] = None
    rotation: str = "Optimize"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    labels: List[str] = Field(default_factory=list)


class CampaignPlan(BaseModel):
    """
    A fully specified campaign plan, ready for export or API publish.
    Derived entirely from a Brief.
    """
    external_key: str = Field(..., description="Unique idempotency key")
    campaign_name: str
    campaign_type: CampaignType
    campaign_subtype: str
    language_code: str
    status: CampaignStatus = CampaignStatus.paused
    settings: CampaignSettings
    ad_groups: List[AdGroupPlan] = Field(default_factory=list)
    pmax_asset_groups: List[PMaxAssetGroup] = Field(default_factory=list)
    shared_negative_keyword_lists: List[str] = Field(default_factory=list)
    can_publish: bool = True
    publish_blockers: List[str] = Field(default_factory=list)
    dry_run_diff: Optional[Dict[str, Any]] = None


# ─── Full Account Plan ────────────────────────────────────────────────────────

class AccountPlan(BaseModel):
    """Complete output plan for a client setup."""
    project_id: str
    client_name: str
    client_slug: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(_TZ_ROME))
    brief_version: str = "1.0"
    campaigns: List[CampaignPlan] = Field(default_factory=list)
    global_negative_keywords: List[Keyword] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    # Structured warnings from AI advisor — each item carries an optional
    # suggested_fix dict {brief_path, value, action, label} for frontend CTAs.
    validation_warnings_structured: List[Dict[str, Any]] = Field(default_factory=list)
    is_valid: bool = True
    publish_ready: bool = False

    @property
    def can_publish(self) -> bool:
        return self.is_valid and all(c.can_publish for c in self.campaigns)

    @property
    def total_campaigns(self) -> int:
        return len(self.campaigns)

    @property
    def campaigns_with_blockers(self) -> List[CampaignPlan]:
        return [c for c in self.campaigns if not c.can_publish]
