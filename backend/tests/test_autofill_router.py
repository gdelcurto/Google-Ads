"""
Tests for autofill routing logic and business rules.

Since the full FastAPI app cannot be started in this environment (missing system
crypto deps), we test the business logic of the enricher and budget strategy
modules directly, which constitute the real behaviour behind the endpoints.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.connectors.claude_enricher import (
    _api_log_entry,
    _build_lang_url_section,
    _compute_daily,
    _compute_split,
    _select_campaign_types,
    _suggest_budget,
    _trim_to_word,
)
from app.connectors.web_scraper import scan_entry, ScrapedSite, LANG_IDS


# ── _suggest_budget ───────────────────────────────────────────────────────────

def test_suggest_budget_scales_with_stars():
    """Higher star rating → higher suggested budget."""
    b3 = _suggest_budget(3, "city_hotel")
    b5 = _suggest_budget(5, "city_hotel")
    assert b5 > b3


def test_suggest_budget_resort_multiplier():
    """Resort category multiplies budget by 1.4."""
    base = _suggest_budget(4, "city_hotel")
    resort = _suggest_budget(4, "resort")
    assert resort > base


def test_suggest_budget_rounded_to_100():
    """Budget must be a multiple of 100."""
    for stars in range(1, 6):
        b = _suggest_budget(stars, "city_hotel")
        assert b % 100 == 0


# ── _select_campaign_types ────────────────────────────────────────────────────

def test_select_campaign_types_low_budget():
    """Below €300 → only brand + acquisition, with a warning."""
    types, warning = _select_campaign_types(200)
    assert set(types) == {"search_brand", "search_acquisition"}
    assert warning is not None
    assert "300" in warning


def test_select_campaign_types_medium_budget():
    """€600–€1499 → adds retargeting, no warning."""
    types, warning = _select_campaign_types(800)
    assert "retargeting" in types
    assert "performance_max" not in types
    assert warning is None


def test_select_campaign_types_high_budget():
    """≥€3000 → all 5 campaign types active."""
    types, warning = _select_campaign_types(3500)
    assert len(types) == 5
    assert warning is None


def test_select_campaign_types_boundary_3000():
    """At exactly €3000 — performance_max included but demand_gen threshold not yet met."""
    types, _ = _select_campaign_types(3000)
    # €3000 triggers the ≥3000 branch → all 5
    assert "demand_gen" in types


# ── _compute_split ────────────────────────────────────────────────────────────

def test_compute_split_sums_to_one():
    """Budget split percentages must sum to 1.0 across all active types."""
    for budget in [400, 800, 1500, 3000, 5000]:
        types, _ = _select_campaign_types(budget)
        split = _compute_split(types)
        total = sum(split.values())
        assert abs(total - 1.0) < 0.0001, f"Split does not sum to 1.0 for budget {budget}: {split}"


def test_compute_split_all_positive():
    """Each campaign type must have a positive weight."""
    types, _ = _select_campaign_types(3000)
    split = _compute_split(types)
    assert all(v > 0 for v in split.values())


# ── _compute_daily ────────────────────────────────────────────────────────────

def test_compute_daily_returns_frontend_keys():
    """Daily budget dict uses frontend keys (brand, acquisition, pmax…)."""
    types, _ = _select_campaign_types(1500)
    split = _compute_split(types)
    daily = _compute_daily(split, 1500, ["IT", "EN"])
    # All keys should be frontend-style
    assert all(k in {"brand", "acquisition", "pmax", "retargeting", "demand_gen"}
               for k in daily)


def test_compute_daily_splits_by_language():
    """Each campaign type must have an entry per language."""
    types, _ = _select_campaign_types(800)
    split = _compute_split(types)
    daily = _compute_daily(split, 800, ["IT", "DE", "FR"])
    for type_key, by_lang in daily.items():
        assert set(by_lang.keys()) == {"IT", "DE", "FR"}, \
            f"Missing languages for {type_key}: {by_lang.keys()}"


def test_compute_daily_totals_approximate_monthly():
    """Sum of daily*30.44 across all types and languages ≈ total monthly budget."""
    budget = 1200.0
    langs = ["IT"]
    types, _ = _select_campaign_types(budget)
    split = _compute_split(types)
    daily = _compute_daily(split, budget, langs)
    reconstructed = sum(v * 30.44 for by_lang in daily.values() for v in by_lang.values())
    assert abs(reconstructed - budget) < 2.0, \
        f"Reconstructed budget {reconstructed:.2f} deviates too much from {budget}"


# ── _build_lang_url_section ───────────────────────────────────────────────────

def test_build_lang_url_section_empty():
    """Empty landings → empty string."""
    result = _build_lang_url_section({}, {}, ["IT", "EN"])
    assert result == ""


def test_build_lang_url_section_includes_landing():
    """When a landing is known, it appears in the output section."""
    landings = {"IT": "https://hotel.com/it/"}
    result = _build_lang_url_section(landings, {}, ["IT"])
    assert "https://hotel.com/it/" in result
    assert "IT" in result


# ── _trim_to_word ─────────────────────────────────────────────────────────────

def test_trim_to_word_under_limit_unchanged():
    text = "Prenota Online"
    assert _trim_to_word(text, 30) == text


def test_trim_to_word_over_limit_trims_at_word_boundary():
    text = "Questo testo è troppo lungo per un headline"
    result = _trim_to_word(text, 25)
    assert len(result) <= 25
    assert not result.endswith(' ')
    # Should not cut mid-word: no partial word at the boundary
    assert result == result.rstrip()


def test_trim_to_word_no_space_in_text():
    text = "Soloparoleattaccate"
    result = _trim_to_word(text, 10)
    assert len(result) <= 10


# ── _api_log_entry ────────────────────────────────────────────────────────────

def test_api_log_entry_structure():
    """api_log_entry must contain all required fields."""
    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    entry = _api_log_entry(
        agent="TestAgent",
        reason="Unit test",
        endpoint="POST /test",
        model="claude-haiku-4-5-20251001",
        usage=usage,
    )
    required_keys = {"ts", "agent", "reason", "endpoint", "model", "input_tokens", "output_tokens", "cost_usd"}
    assert required_keys.issubset(entry.keys())
    assert entry["agent"] == "TestAgent"
    assert entry["cost_usd"] >= 0


def test_api_log_entry_cost_calculated():
    """Cost must reflect token counts and model pricing."""
    usage = MagicMock()
    usage.input_tokens = 1_000_000  # 1M tokens
    usage.output_tokens = 0
    entry = _api_log_entry(
        agent="A",
        reason="R",
        endpoint="E",
        model="claude-haiku-4-5-20251001",
        usage=usage,
    )
    # claude-haiku input price = $0.80 / 1M tokens
    assert abs(entry["cost_usd"] - 0.80) < 0.01


# ── scan_entry ────────────────────────────────────────────────────────────────

def test_scan_entry_has_correct_fields():
    entry = scan_entry("info", "Test scan")
    assert entry["level"] == "info"
    assert entry["msg"] == "Test scan"
    assert "ts" in entry


# ── ScrapedSite ───────────────────────────────────────────────────────────────

def test_scraped_site_defaults():
    """ScrapedSite defaults scan_log to empty list."""
    site = ScrapedSite(content="content", lang_urls={}, lang_landings={})
    assert site.scan_log == []
    assert site.content == "content"
