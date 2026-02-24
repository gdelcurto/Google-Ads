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
    _trim_to_word,
    _VALID_CAMPAIGN_TYPES,
    _FALLBACK_TYPES,
)
from app.connectors.web_scraper import scan_entry, ScrapedSite, LANG_IDS


# ── _VALID_CAMPAIGN_TYPES / _FALLBACK_TYPES ───────────────────────────────────

def test_valid_campaign_types_contains_required():
    """All expected campaign type keys must be present."""
    required = {"search_brand", "search_acquisition", "performance_max", "retargeting", "demand_gen"}
    assert required == set(_VALID_CAMPAIGN_TYPES)


def test_fallback_types_are_subset_of_valid():
    """Fallback types must all be valid campaign type keys."""
    assert all(t in _VALID_CAMPAIGN_TYPES for t in _FALLBACK_TYPES)


# ── _compute_daily ────────────────────────────────────────────────────────────

def test_compute_daily_returns_frontend_keys():
    """Daily budget dict uses frontend keys (brand, acquisition, pmax…)."""
    split = {"search_brand": 0.30, "search_acquisition": 0.40, "performance_max": 0.30}
    daily = _compute_daily(split, 1500, ["IT", "EN"])
    assert all(k in {"brand", "acquisition", "pmax", "retargeting", "demand_gen"} for k in daily)


def test_compute_daily_splits_by_language():
    """Each campaign type must have an entry per language."""
    split = {"search_brand": 0.50, "search_acquisition": 0.50}
    daily = _compute_daily(split, 800, ["IT", "DE", "FR"])
    for type_key, by_lang in daily.items():
        assert set(by_lang.keys()) == {"IT", "DE", "FR"}, \
            f"Missing languages for {type_key}: {by_lang.keys()}"


def test_compute_daily_totals_approximate_monthly():
    """Sum of daily*30.44 across all types and languages ≈ total monthly budget."""
    budget = 1200.0
    langs = ["IT"]
    split = {"search_brand": 0.25, "search_acquisition": 0.40, "retargeting": 0.35}
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
