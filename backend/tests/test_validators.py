"""Tests for BriefValidator — schema rules + business rules."""
import pytest

from app.domain.schemas.brief import Brief
from app.validators.brief_validator import BriefValidator, Severity


@pytest.fixture
def validator():
    return BriefValidator()


class TestBriefValidatorWithSampleBrief:
    """Tests on the complete example brief (should be mostly valid)."""

    def test_valid_brief_passes(self, validator, sample_brief):
        result = validator.validate(sample_brief)
        assert result.is_valid, f"Expected valid, got errors: {result.error_messages}"

    def test_no_critical_errors_on_sample(self, validator, sample_brief):
        result = validator.validate(sample_brief)
        error_codes = [e.code for e in result.errors]
        assert "NO_LANGUAGES" not in error_codes
        assert "NO_BRAND_TERMS" not in error_codes

    def test_checklist_has_items(self, validator, sample_brief):
        result = validator.validate(sample_brief)
        assert len(result.checklist) > 0

    def test_checklist_blastness_label(self, validator, sample_brief):
        result = validator.validate(sample_brief)
        label_checks = [c for c in result.checklist if "Blastness" in c.label or "blastness" in c.label.lower()]
        assert any(c.ok for c in label_checks)


class TestBriefValidatorWithMinimalBrief:
    """Tests on the minimal valid brief."""

    def test_minimal_brief_is_valid(self, validator, minimal_brief):
        result = validator.validate(minimal_brief)
        assert result.is_valid, f"Errors: {result.error_messages}"

    def test_brand_terms_present(self, validator, minimal_brief):
        result = validator.validate(minimal_brief)
        it_errors = [e for e in result.errors if e.language == "IT" and e.code == "NO_BRAND_TERMS"]
        assert len(it_errors) == 0

    def test_warning_no_acquisition_keywords(self, validator, minimal_brief):
        """Minimal brief has no acquisition keywords — should warn."""
        result = validator.validate(minimal_brief)
        warn_codes = [w.code for w in result.warnings]
        assert "NO_ACQUISITION_KEYWORDS" in warn_codes


class TestBudgetValidation:
    def test_error_on_budget_over_total(self, validator, minimal_brief):
        minimal_brief.budgets.total_monthly_eur = 100  # way lower than allocated
        result = validator.validate(minimal_brief)
        assert any(e.code == "BUDGET_OVER_TOTAL" for e in result.errors)

    def test_warning_on_under_allocated_budget(self, validator, minimal_brief):
        minimal_brief.budgets.total_monthly_eur = 5000  # way more than allocated
        result = validator.validate(minimal_brief)
        assert any(w.code == "BUDGET_UNDER_ALLOCATED" for w in result.warnings)

    def test_warning_budget_too_low_daily(self, validator, minimal_brief):
        """Budget < 1 EUR/month should warn."""
        minimal_brief.budgets.by_campaign_type["search_brand"].by_language["IT"] = 0.5
        result = validator.validate(minimal_brief)
        assert any(w.code == "BUDGET_TOO_LOW" for w in result.warnings)


class TestHeadlineValidation:
    def test_error_on_headline_too_long(self, validator, minimal_brief):
        lang = minimal_brief.languages[0]
        lang.headlines[0] = "X" * 31  # exceeds 30 chars
        result = validator.validate(minimal_brief)
        assert any(e.code == "HEADLINE_TOO_LONG" for e in result.errors)

    def test_error_on_too_few_headlines(self, validator, minimal_brief):
        minimal_brief.languages[0].headlines = ["Solo Una"]
        result = validator.validate(minimal_brief)
        assert any(e.code == "HEADLINES_TOO_FEW" for e in result.errors)

    def test_error_on_description_too_long(self, validator, minimal_brief):
        minimal_brief.languages[0].descriptions[0] = "D" * 91
        result = validator.validate(minimal_brief)
        assert any(e.code == "DESCRIPTION_TOO_LONG" for e in result.errors)


class TestGeoValidation:
    def test_error_on_no_geo_target(self, validator, minimal_brief):
        minimal_brief.geo_targeting.target_countries = []
        minimal_brief.geo_targeting.target_cities = []
        result = validator.validate(minimal_brief)
        assert any(e.code == "NO_GEO_TARGET" for e in result.errors)


class TestPolicyValidation:
    def test_warning_on_superlative(self, validator, minimal_brief):
        minimal_brief.languages[0].headlines.append("Il Migliore Hotel")
        result = validator.validate(minimal_brief)
        assert any(w.code == "POLICY_SUPERLATIVE" for w in result.warnings)

    def test_no_false_positive_on_normal_headline(self, validator, minimal_brief):
        result = validator.validate(minimal_brief)
        superlative_warns = [w for w in result.warnings if w.code == "POLICY_SUPERLATIVE"]
        assert len(superlative_warns) == 0, f"False positive: {[w.message for w in superlative_warns]}"


class TestPydanticSchemaValidation:
    """Tests that Pydantic validation catches schema errors before validator runs."""

    def test_brief_rejects_mismatched_budget_language(self, minimal_brief):
        with pytest.raises(Exception):
            Brief(**{
                **minimal_brief.model_dump(),
                "budgets": {
                    "total_monthly_eur": 1000,
                    "by_campaign_type": {
                        "search_brand": {"total": 1000, "by_language": {"XX": 1000}}  # XX not in languages
                    },
                },
            })
