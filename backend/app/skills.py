"""Skill loader — reads marketing skill documentation from docs/ and exposes it
as system-prompt context for Claude API calls.

Skills are loaded lazily and cached in memory (lru_cache) on first access so
there is zero I/O cost after the first call per skill file.

Usage example in autofill.py::

    from app.skills import load_skill, combined_skills, SEARCH_TERM_MINING

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        system=load_skill(SEARCH_TERM_MINING),
        messages=[{"role": "user", "content": prompt}],
    )
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# docs/ is three directories above this file:
#   backend/app/skills.py  →  backend/app/  →  backend/  →  Google-Ads/  →  docs/
_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"

# ── Skill file name constants ─────────────────────────────────────────────────
# Use these in imports rather than raw filename strings so IDEs can track usage.

BUDGET_SCENARIO_PLANNER      = "03-google-and-meta-budget-scenario-planner.md"
SEARCH_TERM_MINING           = "07-google-search-term-mining.md"
AD_COPY_VARIANT_GENERATOR    = "09-google-and-meta-ad-copy-variant-generator.md"
BID_STRATEGY_RECOMMENDATIONS = "11-google-bid-strategy-recommendations.md"
QUALITY_SCORE_BREAKDOWN      = "14-google-quality-score-breakdown.md"
KEYWORD_CANNIBALIZATION      = "20-google-keyword-cannibalization-check.md"
AD_EXTENSION_AUDIT           = "21-google-ad-extension-audit.md"
GOOGLE_ADS_AUDIT             = "37-google-ads-audit.md"

# Additional skills available (not yet wired to a specific agent)
CPA_DIAGNOSTICS              = "01-google-and-meta-cpa-diagnostics.md"
WASTED_SPEND_FINDER          = "02-google-and-meta-wasted-spend-finder.md"
AD_COPY_NARRATIVES           = "05-google-and-meta-client-report-narratives.md"
ANOMALY_DETECTION            = "06-google-and-meta-anomaly-detection.md"
LANDING_PAGE_AUDIT           = "10-google-and-meta-landing-page-audit.md"
CHANNEL_MIX_OPTIMIZER        = "15-google-and-meta-channel-mix-optimizer.md"
ROAS_FORECASTING             = "19-google-and-meta-roas-forecasting.md"
AB_TEST_ANALYZER             = "31-google-and-meta-ab-test-analyzer.md"
AD_SPEND_ALLOCATOR           = "32-google-and-meta-ad-spend-allocator.md"
UTM_TRACKING_GENERATOR       = "44-google-and-meta-utm-tracking-generator.md"


@lru_cache(maxsize=None)
def load_skill(filename: str) -> str:
    """Load a skill markdown file, strip YAML frontmatter, return body text.

    Returns an empty string if the file does not exist so callers never crash.
    Results are cached in memory after the first load.
    """
    path = _DOCS_DIR / filename
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    # Strip --- frontmatter ---
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].strip()
    return text


def combined_skills(*filenames: str, separator: str = "\n\n---\n\n") -> str:
    """Load and concatenate multiple skills, separated by a divider.

    Skips any skill file that does not exist or is empty.
    """
    parts = [p for f in filenames if (p := load_skill(f))]
    return separator.join(parts)
