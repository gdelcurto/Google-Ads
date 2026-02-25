"""
Pydantic schemas for the strategist brief (source of truth).
All campaign generation is derived from this input.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

# Default budget split across campaign types (weights, not percentages).
# Applied when by_campaign_type is not manually specified.
DEFAULT_BUDGET_SPLIT: Dict[str, float] = {
    "search_brand": 0.20,
    "search_acquisition": 0.35,
    "performance_max": 0.30,
    "retargeting": 0.10,
    "demand_gen": 0.05,
}


# ─── Enums ──────────────────────────────────────────────────────────────────

class HotelVertical(str, Enum):
    city_hotel = "city_hotel"
    resort = "resort"
    boutique = "boutique"
    business = "business"
    agriturismo = "agriturismo"


class Preset(str, Enum):
    blastness = "blastness"
    mentefredda = "mentefredda"
    custom = "custom"


class ObjectiveType(str, Enum):
    direct_bookings = "direct_bookings"
    lead_gen = "lead_gen"
    phone_calls = "phone_calls"
    brand_awareness = "brand_awareness"


class BidStrategyChoice(str, Enum):
    """Bid strategy choices exposed to the user in the brief wizard.
    Maps 1-to-1 onto Google Ads API bidding strategies."""
    maximize_conversions = "maximize_conversions"        # Numero di Conversioni
    maximize_conversion_value = "maximize_conversion_value"  # Valore di Conversione
    maximize_clicks = "maximize_clicks"                  # Massimizza i click
    target_impression_share = "target_impression_share"  # Quota impressioni


# Sensible per-type defaults
_DEFAULT_BID_STRATEGY: dict[str, BidStrategyChoice] = {
    "search_brand": BidStrategyChoice.maximize_clicks,
    "search_acquisition": BidStrategyChoice.maximize_conversions,
    "retargeting": BidStrategyChoice.maximize_conversions,
    "performance_max": BidStrategyChoice.maximize_conversion_value,
    "demand_gen": BidStrategyChoice.maximize_conversions,
}


class CampaignTypeKey(str, Enum):
    search_brand = "search_brand"
    search_acquisition = "search_acquisition"
    retargeting = "retargeting"
    performance_max = "performance_max"
    demand_gen = "demand_gen"


class TranslationProvider(str, Enum):
    noop = "noop"
    google = "google"
    deepl = "deepl"


# ─── Sub-schemas ─────────────────────────────────────────────────────────────

class MetaInfo(BaseModel):
    project_name: str = Field(..., min_length=3, max_length=200)
    created_by: str = Field(..., description="Email of the strategist")
    preset: Preset = Preset.blastness
    vertical: HotelVertical = HotelVertical.city_hotel


class ClientInfo(BaseModel):
    brand_name: str = Field(..., min_length=2)
    brand_slug: str = Field(..., pattern=r"^[a-z0-9\-]+$", description="URL-safe slug")
    domain: str = Field(..., description="Root domain without https://")
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217")
    timezone: str = Field(..., description="e.g. Europe/Rome")
    google_ads_customer_id: Optional[str] = Field(
        None, pattern=r"^\d{3}-\d{3}-\d{4}$", description="XXX-XXX-XXXX"
    )
    google_ads_mcc_id: Optional[str] = Field(None, description="Manager account ID")


class KpiTargets(BaseModel):
    target_cpa_eur: Optional[float] = Field(None, ge=0)
    target_roas: Optional[float] = Field(None, ge=0)
    max_cpc_brand: Optional[float] = Field(None, ge=0)
    max_cpc_acquisition: Optional[float] = Field(None, ge=0)


class ConversionsConfig(BaseModel):
    primary_conversion_action: str
    conversion_action_ids: List[str] = Field(default_factory=list)
    secondary_conversion_actions: List[str] = Field(default_factory=list)
    value_per_conversion: Optional[float] = Field(None, ge=0)


class CampaignTypeObjective(BaseModel):
    """Per-campaign-type objective, conversion action and bid strategy override."""
    primary: ObjectiveType
    primary_conversion_action: str = "purchase"
    bid_strategy: BidStrategyChoice = BidStrategyChoice.maximize_conversions


class ObjectivesInfo(BaseModel):
    primary: ObjectiveType
    secondary: List[ObjectiveType] = Field(default_factory=list)
    kpi: KpiTargets = Field(default_factory=KpiTargets)
    conversions: ConversionsConfig
    # Per-type overrides: keys are CampaignTypeKey values (e.g. "search_brand").
    # When present, these take priority over the global primary / conversions fields.
    per_campaign_type: Dict[str, CampaignTypeObjective] = Field(default_factory=dict)

    def get_objective_for(self, campaign_type_key: str) -> ObjectiveType:
        """Return the objective for a specific campaign type, falling back to global."""
        entry = self.per_campaign_type.get(campaign_type_key)
        return entry.primary if entry else self.primary

    def get_conversion_action_for(self, campaign_type_key: str) -> str:
        """Return the primary conversion action for a specific campaign type."""
        entry = self.per_campaign_type.get(campaign_type_key)
        return entry.primary_conversion_action if entry else self.conversions.primary_conversion_action

    def get_bid_strategy_for(self, campaign_type_key: str) -> BidStrategyChoice:
        """Return the explicit bid strategy for a campaign type, falling back to per-type default."""
        entry = self.per_campaign_type.get(campaign_type_key)
        if entry and entry.bid_strategy:
            return entry.bid_strategy
        return _DEFAULT_BID_STRATEGY.get(campaign_type_key, BidStrategyChoice.maximize_conversions)


class BudgetByLanguage(BaseModel):
    total: float = Field(..., ge=0)
    by_language: Dict[str, float] = Field(default_factory=dict)


class BudgetPlan(BaseModel):
    total_monthly_eur: float = Field(..., ge=0)
    by_campaign_type: Dict[str, BudgetByLanguage] = Field(default_factory=dict)


class Sitelink(BaseModel):
    text: str = Field(..., max_length=25)
    description_1: str = Field(..., max_length=35)
    description_2: str = Field(..., max_length=35)
    final_url: str


class StructuredSnippet(BaseModel):
    header: str
    values: List[str] = Field(..., min_length=3, max_length=10)


class UspInfo(BaseModel):
    main: str = Field(..., max_length=300)
    bullets: List[str] = Field(default_factory=list)


class PerTypeAssets(BaseModel):
    """
    Per-campaign-type RSA copy for a language.

    When configured, these headlines/descriptions override the generic pool
    for the specific campaign type, allowing each type to have tailored messaging:
    - brand_assets      → branded copy ("Hotel XYZ Ufficiale", "Miglior Tariffa")
    - acquisition_assets→ generic/category copy ("Hotel Roma Centro", "4 Stelle")
    - retargeting_assets→ urgency copy ("Completa la prenotazione", "Offerta riservata")
    """
    headlines: List[str] = Field(
        default_factory=list,
        description="RSA headlines for this campaign type (max 30 chars each, up to 15)",
    )
    descriptions: List[str] = Field(
        default_factory=list,
        description="RSA descriptions for this campaign type (max 90 chars each, up to 4)",
    )

    @model_validator(mode="after")
    def validate_char_limits(self) -> "PerTypeAssets":
        for h in self.headlines:
            if len(h) > 30:
                raise ValueError(f"Headline too long (max 30 chars): '{h}'")
        for d in self.descriptions:
            if len(d) > 90:
                raise ValueError(f"Description too long (max 90 chars): '{d}'")
        return self


class LanguagePlan(BaseModel):
    code: str = Field(..., min_length=2, max_length=5, description="e.g. IT, EN, FR-CH")
    name: str
    google_language_id: int
    landing_page: str
    brand_terms: List[str] = Field(..., min_length=1)
    brand_variants: List[str] = Field(default_factory=list)
    brand_exclusions: List[str] = Field(default_factory=list)
    usp: UspInfo
    headlines: List[str] = Field(..., min_length=3, max_length=15, description="RSA headlines")
    descriptions: List[str] = Field(..., min_length=2, description="RSA descriptions (max 4)")
    sitelinks: List[Sitelink] = Field(default_factory=list)
    callouts: List[str] = Field(default_factory=list)
    structured_snippets: List[StructuredSnippet] = Field(default_factory=list)

    @field_validator("descriptions", mode="before")
    @classmethod
    def cap_descriptions(cls, v: list) -> list:
        """Silently truncate to 4 descriptions instead of rejecting.

        Google Ads RSA allows max 4 descriptions; the AI prompt asks for
        exactly 4 but occasionally returns 5.  Truncating is safe because
        the first 4 are always the highest-priority ones.
        """
        if isinstance(v, list) and len(v) > 4:
            return v[:4]
        return v
    # ── Per-type copy overrides ────────────────────────────────────────────
    brand_assets: Optional[PerTypeAssets] = Field(
        None,
        description=(
            "Brand-specific RSA copy (brand name + direct booking messaging). "
            "Overrides generic headlines for Brand Search campaigns."
        ),
    )
    acquisition_assets: Optional[PerTypeAssets] = Field(
        None,
        description=(
            "Acquisition-specific RSA copy (no brand name — category/location/USP). "
            "Overrides generic headlines for Acquisition campaigns."
        ),
    )
    retargeting_assets: Optional[PerTypeAssets] = Field(
        None,
        description=(
            "Retargeting-specific RSA copy (urgency/personalization for returning visitors). "
            "Overrides generic headlines for Retargeting campaigns."
        ),
    )

    @model_validator(mode="after")
    def validate_rsa_limits(self) -> "LanguagePlan":
        for h in self.headlines:
            if len(h) > 30:
                raise ValueError(f"Headline too long (max 30 chars): '{h}'")
        for d in self.descriptions:
            if len(d) > 90:
                raise ValueError(f"Description too long (max 90 chars): '{d}'")
        return self

    @model_validator(mode="after")
    def auto_fill_brand_exclusions(self) -> "LanguagePlan":
        """Auto-populate brand_exclusions from brand_terms when not explicitly set."""
        if self.brand_terms and not self.brand_exclusions:
            self.brand_exclusions = list(self.brand_terms)
        return self


class GeoTargeting(BaseModel):
    target_countries: List[str] = Field(default_factory=list)
    target_regions: List[str] = Field(default_factory=list)
    target_cities: List[str] = Field(default_factory=list)
    exclusions: Dict[str, List[str]] = Field(default_factory=dict)
    radius_targets: List[Dict[str, Any]] = Field(default_factory=list)


class PeakPeriod(BaseModel):
    start: str = Field(..., description="YYYY-MM-DD")
    end: str = Field(..., description="YYYY-MM-DD")
    label: str
    budget_multiplier: float = Field(1.0, ge=0.1, le=5.0)


class SeasonalityInfo(BaseModel):
    enabled: bool = False
    peak_periods: List[PeakPeriod] = Field(default_factory=list)
    low_periods: List[PeakPeriod] = Field(default_factory=list)
    ad_schedule: Dict[str, Any] = Field(default_factory=dict)


class RemarketingList(BaseModel):
    name: str
    type: str = Field(..., description="website_visitors | customer_list | youtube")
    lookback_days: int = Field(..., ge=1, le=540)
    source: str
    url_contains: Optional[str] = None


class CustomerMatch(BaseModel):
    enabled: bool = False
    list_name: Optional[str] = None
    source: Optional[str] = None


class AudienceConfig(BaseModel):
    remarketing_lists: List[RemarketingList] = Field(default_factory=list)
    customer_match: CustomerMatch = Field(default_factory=CustomerMatch)
    in_market_segments: List[str] = Field(default_factory=list)
    custom_intent: List[str] = Field(default_factory=list)


class CreativeAssets(BaseModel):
    """
    Visual assets for PMax, Retargeting Display, and Demand Gen campaigns.
    URLs can point to any publicly accessible image/video hosting.
    """
    logo_url: Optional[str] = Field(
        None, description="Logo PNG trasparente 1200x1200 — richiesto per PMax, Retargeting Display, Demand Gen"
    )
    image_landscape: Optional[str] = Field(
        None, description="Immagine orizzontale 1200x628 — richiesta per PMax e Demand Gen"
    )
    image_square: Optional[str] = Field(
        None, description="Immagine quadrata 1200x1200 — richiesta per PMax e Demand Gen"
    )
    image_portrait: Optional[str] = Field(
        None, description="Immagine verticale 960x1200 — opzionale (PMax)"
    )
    youtube_video_url: Optional[str] = Field(
        None, description="URL video YouTube 16:9 — opzionale (PMax, Demand Gen)"
    )


class HotelLocation(BaseModel):
    address: str
    coordinates: Optional[Dict[str, float]] = None
    landmarks_nearby: List[str] = Field(default_factory=list)
    distance_to_landmarks: Dict[str, str] = Field(default_factory=dict)


class HotelSpecifics(BaseModel):
    category: HotelVertical
    stars: int = Field(..., ge=1, le=5)
    rooms: Optional[int] = Field(None, ge=1)
    adr: Optional[float] = Field(None, ge=0, description="Average Daily Rate €/notte")
    occupancy_rate: Optional[float] = Field(None, ge=0, le=100, description="Tasso di occupazione % (0–100)")
    direct_pct: Optional[float] = Field(None, ge=0, le=100, description="% prenotazioni dirette vs OTA")
    location: HotelLocation
    room_categories: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    booking_engine_url: str
    hotel_id_google: Optional[str] = None


class KeywordThemes(BaseModel):
    themes: Dict[str, List[str]] = Field(default_factory=dict)
    negative_keywords: List[str] = Field(default_factory=list)


class NamingConvention(BaseModel):
    separator: str = " | "
    components: List[str] = Field(
        default=["lang", "type", "subtype", "match_type"]
    )
    example: str = "IT | Search | Brand | Exact"


class UtmConfig(BaseModel):
    source: str = "google"
    medium: str = "{network}"
    campaign: str = "{campaignid}"
    content: str = "{adgroupid}"
    term: str = "{keyword}"
    custom_params: Dict[str, str] = Field(default_factory=dict)
    preset_tag: Optional[str] = None


# ─── Root Brief Schema ────────────────────────────────────────────────────────

class Brief(BaseModel):
    """
    The strategist brief — source of truth for all campaign generation.
    All derived data (naming, assets, UTMs) is computed from this object.
    """
    version: str = "1.0"
    meta: MetaInfo
    client: ClientInfo
    objectives: ObjectivesInfo
    budgets: BudgetPlan
    campaign_types: List[CampaignTypeKey] = Field(
        default_factory=lambda: list(CampaignTypeKey),
        description=(
            "Campaign types to generate. "
            "If budgets.by_campaign_type is empty, the total monthly budget is "
            "automatically distributed across these types using DEFAULT_BUDGET_SPLIT."
        ),
    )
    languages: List[LanguagePlan] = Field(..., min_length=1)
    geo_targeting: GeoTargeting = Field(default_factory=GeoTargeting)
    seasonality: Optional[SeasonalityInfo] = None
    audiences: AudienceConfig = Field(default_factory=AudienceConfig)
    hotel_specifics: HotelSpecifics
    creative_assets: CreativeAssets = Field(
        default_factory=CreativeAssets,
        description="Visual assets (images, logo, video) for PMax/Retargeting/DemandGen",
    )
    policy_constraints: List[str] = Field(default_factory=list)
    acquisition_keywords: Optional[Dict[str, KeywordThemes]] = None
    naming_convention: NamingConvention = Field(default_factory=NamingConvention)
    labels: List[str] = Field(default_factory=list)
    utm_config: UtmConfig = Field(default_factory=UtmConfig)

    # NOTE: audiences (remarketing lists, in-market segments) are configured
    # manually by the strategist — no auto-fill.  Retargeting/PMax/Demand Gen
    # campaigns will only be generated when audiences are explicitly set.

    @model_validator(mode="after")
    def auto_distribute_budget(self) -> "Brief":
        """
        If by_campaign_type is empty, auto-distribute total_monthly_eur across
        campaign_types using DEFAULT_BUDGET_SPLIT weights.
        Retargeting / demand_gen are skipped when no remarketing lists are defined.
        """
        if self.budgets.by_campaign_type:
            return self  # Manual allocation — do not override

        total = self.budgets.total_monthly_eur
        if total <= 0 or not self.languages:
            return self

        lang_codes = [lang.code for lang in self.languages]

        # Determine which types can actually run
        active_types: List[CampaignTypeKey] = []
        for ct in self.campaign_types:
            if ct in (CampaignTypeKey.retargeting, CampaignTypeKey.demand_gen):
                if not self.audiences.remarketing_lists:
                    continue  # Cannot run without audience lists
            active_types.append(ct)

        if not active_types:
            return self

        # Normalize weights to active types only
        raw_weights = {ct: DEFAULT_BUDGET_SPLIT.get(ct.value, 1.0) for ct in active_types}
        total_weight = sum(raw_weights.values())

        for ct in active_types:
            type_total = round(total * raw_weights[ct] / total_weight, 2)
            per_lang = round(type_total / len(lang_codes), 2)
            self.budgets.by_campaign_type[ct.value] = BudgetByLanguage(
                total=type_total,
                by_language={code: per_lang for code in lang_codes},
            )

        return self

    @model_validator(mode="after")
    def validate_budget_languages_match(self) -> "Brief":
        """All language codes in budgets must match languages list."""
        lang_codes = {lang.code for lang in self.languages}
        for campaign_type, budget in self.budgets.by_campaign_type.items():
            for lang_code in budget.by_language:
                if lang_code not in lang_codes:
                    raise ValueError(
                        f"Budget language '{lang_code}' in '{campaign_type}' "
                        f"not found in languages list: {lang_codes}"
                    )
        return self

    def get_language(self, code: str) -> Optional[LanguagePlan]:
        for lang in self.languages:
            if lang.code == code:
                return lang
        return None

    def get_budget_for(self, campaign_type: str, lang_code: str) -> float:
        budget_entry = self.budgets.by_campaign_type.get(campaign_type)
        if not budget_entry:
            return 0.0
        return budget_entry.by_language.get(lang_code, 0.0)
