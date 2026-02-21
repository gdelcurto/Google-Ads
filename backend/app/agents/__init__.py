"""
Campaign type agents — one per campaign type, each encapsulating:
- GUIDELINES: self-contained rules documentation for that type
- get_headlines / get_descriptions: type-specific copy with fallback
- validate_copy: actionable warnings for copy quality issues

Usage:
    from app.agents import AGENTS
    warnings = AGENTS["search_brand"].validate_copy(lang)
    headlines = AGENTS["search_acquisition"].get_headlines(lang)
"""
from app.agents.acquisition import AcquisitionAgent
from app.agents.base import CampaignAgent
from app.agents.brand import BrandAgent
from app.agents.demand_gen import DemandGenAgent
from app.agents.performance_max import PMaxAgent
from app.agents.retargeting import RetargetingAgent

AGENTS: dict[str, CampaignAgent] = {
    BrandAgent.TYPE_KEY:       BrandAgent(),
    AcquisitionAgent.TYPE_KEY: AcquisitionAgent(),
    RetargetingAgent.TYPE_KEY: RetargetingAgent(),
    PMaxAgent.TYPE_KEY:        PMaxAgent(),
    DemandGenAgent.TYPE_KEY:   DemandGenAgent(),
}

__all__ = ["AGENTS", "CampaignAgent"]
