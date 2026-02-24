"""
Abstract base class for campaign-type-specific intelligence agents.

Each agent encapsulates:
- GUIDELINES: strategic + copy rules for this campaign type (human-readable + LLM-compatible)
- get_headlines / get_descriptions: return type-appropriate copy with fallback
- validate_copy: ValidationIssue list when copy violates type-specific rules
- validate_strategy: ValidationIssue list when brief-level strategy is problematic
- validate_plan: ValidationIssue list for post-generation audit (L3/TECH agents)

Agent levels define the execution order in the orchestrator:
  L1 (STRATEGIC)  — pre-generation: brief structure + strategy
  L2 (SPECIALIST) — copy generation + per-campaign validation
  TECH            — cross-cutting: naming, negatives, geo
  L3 (AUDITOR)    — post-generation: cross-campaign audit
"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief, LanguagePlan
    from app.domain.schemas.campaign_plan import CampaignPlan


class AgentLevel(str, Enum):
    ORCHESTRATOR = "L0"   # Reserved — not implemented by agents
    STRATEGIC    = "L1"   # Pre-generation: brief structure + strategy
    SPECIALIST   = "L2"   # Copy generation + per-campaign validation
    AUDITOR      = "L3"   # Post-generation: cross-campaign audit
    TECHNICAL    = "TECH" # Cross-cutting: naming, negatives, geo


@dataclass
class ValidationIssue:
    """Structured validation result from any agent."""
    code: str             # machine-readable identifier  (e.g. "BRAND_NO_BRAND_TERMS")
    message: str          # human-readable explanation
    level: str            # "error" | "warning" | "info"
    blocks_publish: bool  # True → prevents publishing until resolved
    agent: str            # agent class name that emitted this issue
    language: Optional[str] = None           # None = account-level, set = language-scoped
    campaign_type_key: Optional[str] = None  # None = all types, set = type-scoped
    suggested_fix: Optional[dict] = None     # Structured CTA for frontend: {brief_path, value, action, label}


class CampaignAgent(ABC):
    """Base interface for all campaign-type agents."""

    TYPE_KEY: str    # matches CampaignTypeKey enum value (e.g. "search_brand")
    GUIDELINES: str  # self-contained strategic + copy documentation for this campaign type
    LEVEL: AgentLevel

    # Whether any rule from this agent can block publishing
    BLOCKS_PUBLISH: bool = False
    # Codes of rules that block publishing (subset of all rules this agent emits)
    BLOCKING_RULES: list[str] = []

    # Ordered tuple of skill file names (from docs/) that provide background expertise
    # for this campaign type.  Used when building Claude system prompts for tasks
    # related to this agent.  Load via: from app.skills import combined_skills
    #   combined_skills(*agent.SKILL_FILES)
    SKILL_FILES: tuple[str, ...] = ()

    def get_headlines(self, lang: "LanguagePlan") -> List[str]:
        """
        Return type-specific headlines for this language plan.
        Falls back to lang.headlines if no type-specific assets are configured.
        L2 specialist agents override this.
        """
        return []

    def get_descriptions(self, lang: "LanguagePlan") -> List[str]:
        """
        Return type-specific descriptions for this language plan.
        Falls back to lang.descriptions if no type-specific assets are configured.
        L2 specialist agents override this.
        """
        return []

    def validate_copy(self, lang: "LanguagePlan") -> List[ValidationIssue]:
        """
        Validate the copy for this campaign type and language.
        L2 specialist agents override this.
        An empty list means the copy is compliant with this type's rules.
        """
        return []

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        """
        Validate the brief-level strategy for this campaign type.
        L1 strategic agents and L2 specialist agents override this.
        Returns a list of ValidationIssue objects.
        """
        return []

    def validate_plan(
        self,
        brief: "Brief",
        campaigns: List["CampaignPlan"],
    ) -> List[ValidationIssue]:
        """
        Validate the generated plan (post-generation audit).
        L3 auditor agents and TECH agents override this.
        Returns a list of ValidationIssue objects.
        """
        return []
