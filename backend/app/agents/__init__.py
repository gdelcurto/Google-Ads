"""
Campaign type agents — one per campaign type, each encapsulating:
- GUIDELINES: self-contained rules documentation for that type
- get_headlines / get_descriptions: type-specific copy with fallback
- validate_copy: ValidationIssue list for copy quality issues
- validate_strategy: ValidationIssue list for brief-level strategic issues
- validate_plan: ValidationIssue list for post-generation audit (L3/TECH)

Agents are organized by level:
  L1 (STRATEGIC)  — STRATEGIC_AGENTS: pre-generation brief validation
  L2 (SPECIALIST) — AGENTS: copy + per-campaign validation (keyed by TYPE_KEY)
  TECH            — TECH_AGENTS: cross-cutting naming, negatives, geo
  L3 (AUDITOR)    — AUDIT_AGENTS: post-generation cross-campaign audit

Usage:
    from app.agents import AGENTS, STRATEGIC_AGENTS, TECH_AGENTS, AUDIT_AGENTS
    issues = AGENTS["search_brand"].validate_copy(lang)
    headlines = AGENTS["search_acquisition"].get_headlines(lang)
    pre_issues = [i for a in STRATEGIC_AGENTS for i in a.validate_strategy(brief)]
"""
# ── L2 Specialist agents ───────────────────────────────────────────────────────
from app.agents.acquisition import AcquisitionAgent
from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue
from app.agents.brand import BrandAgent
from app.agents.demand_gen import DemandGenAgent
from app.agents.performance_max import PMaxAgent
from app.agents.retargeting import RetargetingAgent

# ── L1 Strategic agents ───────────────────────────────────────────────────────
from app.agents.account_architect import AccountArchitectAgent
from app.agents.budget_strategist import BudgetStrategistAgent
from app.agents.bidding_strategist import BiddingStrategistAgent

# ── L3 Audit agents ───────────────────────────────────────────────────────────
from app.agents.performance_auditor import PerformanceAuditorAgent
from app.agents.qa_gatekeeper import QAGatekeeperAgent

# ── TECH cross-cutting agents ─────────────────────────────────────────────────
from app.agents.naming_enforcer import NamingEnforcerAgent
from app.agents.negative_architect import NegativeArchitectAgent
from app.agents.geo_specialist import GeoSpecialistAgent


# L2 Specialist agents — keyed by campaign TYPE_KEY for direct lookup in orchestrator
AGENTS: dict[str, CampaignAgent] = {
    BrandAgent.TYPE_KEY:       BrandAgent(),
    AcquisitionAgent.TYPE_KEY: AcquisitionAgent(),
    RetargetingAgent.TYPE_KEY: RetargetingAgent(),
    PMaxAgent.TYPE_KEY:        PMaxAgent(),
    DemandGenAgent.TYPE_KEY:   DemandGenAgent(),
}

# L1 Strategic agents — run before generation on the brief
STRATEGIC_AGENTS: list[CampaignAgent] = [
    AccountArchitectAgent(),
    BudgetStrategistAgent(),
    BiddingStrategistAgent(),
]

# TECH cross-cutting agents — run on brief + generated plan
TECH_AGENTS: list[CampaignAgent] = [
    NamingEnforcerAgent(),
    NegativeArchitectAgent(),
    GeoSpecialistAgent(),
]

# L3 Audit agents — run after generation on the full plan
AUDIT_AGENTS: list[CampaignAgent] = [
    PerformanceAuditorAgent(),
    QAGatekeeperAgent(),
]


__all__ = [
    "AGENTS",
    "STRATEGIC_AGENTS",
    "TECH_AGENTS",
    "AUDIT_AGENTS",
    "CampaignAgent",
    "AgentLevel",
    "ValidationIssue",
]
