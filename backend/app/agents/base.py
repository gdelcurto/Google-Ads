"""
Abstract base class for campaign-type-specific intelligence agents.

Each agent encapsulates:
- GUIDELINES: strategic + copy rules for this campaign type (human-readable + LLM-compatible)
- get_headlines / get_descriptions: return type-appropriate copy with fallback
- validate_copy: warnings when copy violates type-specific rules
- validate_strategy: warnings when brief-level strategy violates type-specific budget/structure rules
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief, LanguagePlan


class CampaignAgent(ABC):
    """Base interface for all campaign-type agents."""

    TYPE_KEY: str    # matches CampaignTypeKey enum value (e.g. "search_brand")
    GUIDELINES: str  # self-contained strategic + copy documentation for this campaign type

    # Ordered tuple of skill file names (from docs/) that provide background expertise
    # for this campaign type.  Used when building Claude system prompts for tasks
    # related to this agent.  Load via: from app.skills import combined_skills
    #   combined_skills(*agent.SKILL_FILES)
    SKILL_FILES: tuple[str, ...] = ()

    @abstractmethod
    def get_headlines(self, lang: "LanguagePlan") -> List[str]:
        """
        Return type-specific headlines for this language plan.
        Falls back to lang.headlines if no type-specific assets are configured.
        """
        ...

    @abstractmethod
    def get_descriptions(self, lang: "LanguagePlan") -> List[str]:
        """
        Return type-specific descriptions for this language plan.
        Falls back to lang.descriptions if no type-specific assets are configured.
        """
        ...

    @abstractmethod
    def validate_copy(self, lang: "LanguagePlan") -> List[str]:
        """
        Validate the copy for this campaign type.
        Returns a list of warning strings (not errors) for copy quality issues.
        An empty list means the copy is compliant with this type's rules.
        """
        ...

    def validate_strategy(self, brief: "Brief") -> List[str]:
        """
        Validate the brief-level strategy for this campaign type.
        Checks: budget allocation %, required structural elements, audience configuration.
        Returns a list of strategic warning strings.
        Subclasses should override this to add type-specific checks.
        """
        return []
