"""
Abstract base class for campaign-type-specific intelligence agents.

Each agent encapsulates:
- GUIDELINES: documented rules for this campaign type (human-readable + LLM-compatible)
- get_headlines / get_descriptions: return type-appropriate copy with fallback
- validate_copy: returns actionable warnings when copy violates type-specific rules
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.domain.schemas.brief import LanguagePlan


class CampaignAgent(ABC):
    """Base interface for all campaign-type agents."""

    TYPE_KEY: str   # matches CampaignTypeKey enum value (e.g. "search_brand")
    GUIDELINES: str  # self-contained documentation for this campaign type

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
