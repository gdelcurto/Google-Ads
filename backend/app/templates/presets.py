"""
Preset configurations for agencies: Blastness and Mentefredda.
Provides standard naming conventions, UTM templates, labels, and defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgencyPreset:
    """Standard agency preset — applied as defaults when creating a new project."""
    name: str
    slug: str
    description: str

    # Naming
    naming_separator: str = " | "
    naming_components: List[str] = field(
        default_factory=lambda: ["lang", "type", "subtype", "match_type"]
    )

    # UTM
    utm_source: str = "google"
    utm_medium: str = "{network}"
    utm_campaign: str = "{campaignid}"
    utm_content: str = "{adgroupid}"
    utm_term: str = "{keyword}"
    utm_custom_params: Dict[str, str] = field(
        default_factory=lambda: {"device": "{device}", "matchtype": "{matchtype}"}
    )
    utm_preset_tag: str = ""

    # Labels
    base_labels: List[str] = field(default_factory=list)

    # Bid defaults
    default_bid_strategy: str = "maximize_conversions"
    default_rotation: str = "Optimize"

    # PMax defaults
    pmax_final_url_expansion: bool = False

    # Quality score targets
    target_quality_score: int = 7

    def build_label_set(self, client_slug: str, quarter: str) -> List[str]:
        """Generate the full label set for a client setup."""
        return self.base_labels + [
            f"{self.slug}_{client_slug}",
            f"{self.slug}_{quarter}",
        ]

    def build_tracking_template(self) -> str:
        params = [
            f"utm_source={self.utm_source}",
            f"utm_medium={self.utm_medium}",
            f"utm_campaign={self.utm_campaign}",
            f"utm_content={self.utm_content}",
            f"utm_term={self.utm_term}",
        ]
        for k, v in self.utm_custom_params.items():
            params.append(f"{k}={v}")
        if self.utm_preset_tag:
            params.append(f"utm_preset={self.utm_preset_tag}")
        return "{lpurl}?" + "&".join(params)


# ─── Blastness Preset ─────────────────────────────────────────────────────────

BLASTNESS_PRESET = AgencyPreset(
    name="Blastness",
    slug="blastness",
    description=(
        "Preset standard Blastness per hotel indipendenti e catene alberghiere. "
        "Nomenclatura, UTM e label standardizzate per il reporting centralizzato."
    ),
    naming_separator=" | ",
    naming_components=["lang", "type", "subtype", "match_type"],
    utm_source="google",
    utm_medium="{network}",
    utm_campaign="{campaignid}",
    utm_content="{adgroupid}",
    utm_term="{keyword}",
    utm_custom_params={
        "device": "{device}",
        "matchtype": "{matchtype}",
    },
    utm_preset_tag="blastness",
    base_labels=["blastness_setup"],
    default_bid_strategy="maximize_conversions",
    default_rotation="Optimize",
    pmax_final_url_expansion=False,
    target_quality_score=7,
)

# ─── Mentefredda Preset ───────────────────────────────────────────────────────

MENTEFREDDA_PRESET = AgencyPreset(
    name="Mentefredda",
    slug="mentefredda",
    description=(
        "Preset Mentefredda per clienti premium. "
        "UTM con tracking esteso e segmentazione granulare per A/B test."
    ),
    naming_separator=" | ",
    naming_components=["lang", "type", "subtype", "match_type"],
    utm_source="google",
    utm_medium="{network}",
    utm_campaign="{campaignid}",
    utm_content="{adgroupid}",
    utm_term="{keyword}",
    utm_custom_params={
        "device": "{device}",
        "matchtype": "{matchtype}",
        "placement": "{placement}",
        "creative": "{creative}",
    },
    utm_preset_tag="mentefredda",
    base_labels=["mentefredda_setup"],
    default_bid_strategy="target_cpa",
    default_rotation="Optimize",
    pmax_final_url_expansion=False,
    target_quality_score=8,
)

# ─── Custom Preset ────────────────────────────────────────────────────────────

CUSTOM_PRESET = AgencyPreset(
    name="Custom",
    slug="custom",
    description="Preset personalizzato — configura naming e UTM manualmente.",
    utm_preset_tag="",
    base_labels=["ads_setup"],
)

# ─── Registry ─────────────────────────────────────────────────────────────────

PRESET_REGISTRY: Dict[str, AgencyPreset] = {
    "blastness": BLASTNESS_PRESET,
    "mentefredda": MENTEFREDDA_PRESET,
    "custom": CUSTOM_PRESET,
}


def get_preset(name: str) -> AgencyPreset:
    preset = PRESET_REGISTRY.get(name)
    if not preset:
        raise ValueError(f"Preset '{name}' not found. Available: {list(PRESET_REGISTRY.keys())}")
    return preset


def list_presets() -> List[Dict]:
    return [
        {"name": p.name, "slug": p.slug, "description": p.description}
        for p in PRESET_REGISTRY.values()
    ]
