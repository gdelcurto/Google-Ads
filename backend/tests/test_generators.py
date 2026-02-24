"""Tests for all campaign generators and the orchestrator."""
import pytest

from app.domain.schemas.campaign_plan import CampaignType, MatchType
from app.generators.brand_search import BrandSearchGenerator
from app.generators.acquisition_search import AcquisitionSearchGenerator
from app.generators.retargeting import RetargetingGenerator
from app.generators.performance_max import PerformanceMaxGenerator
from app.generators.demand_gen import DemandGenGenerator
from app.generators.orchestrator import CampaignOrchestrator


# ── Brand Search ──────────────────────────────────────────────────────────────

class TestBrandSearchGenerator:
    @pytest.fixture
    def generator(self):
        return BrandSearchGenerator()

    def test_generates_campaigns_per_language(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        lang_codes = {c.language_code for c in campaigns}
        expected = {"IT", "EN", "DE"}
        assert lang_codes == expected

    def test_campaign_type_is_search(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert c.campaign_type == CampaignType.search

    def test_has_exact_and_phrase_ad_groups(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it_campaign = next(c for c in campaigns if c.language_code == "IT")
        ag_names = [ag.name for ag in it_campaign.ad_groups]
        assert any("Exact" in n for n in ag_names)
        assert any("Phrase" in n for n in ag_names)

    def test_brand_terms_as_exact_keywords(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it_campaign = next(c for c in campaigns if c.language_code == "IT")
        exact_group = next(ag for ag in it_campaign.ad_groups if "Exact" in ag.name)
        exact_kws = [kw for kw in exact_group.keywords if kw.match_type == MatchType.exact]
        assert len(exact_kws) > 0

    def test_no_campaign_for_zero_budget_language(self, generator, sample_brief):
        # Remove budget for EN
        sample_brief.budgets.by_campaign_type["search_brand"].by_language.pop("EN", None)
        campaigns = generator.generate(sample_brief)
        lang_codes = {c.language_code for c in campaigns}
        assert "EN" not in lang_codes

    def test_external_key_is_unique_per_language(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        keys = [c.external_key for c in campaigns]
        assert len(keys) == len(set(keys))

    def test_rsa_has_min_headlines(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for campaign in campaigns:
            for ag in campaign.ad_groups:
                for ad in ag.ads:
                    assert len(ad.headlines) >= 3

    def test_external_key_format(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert "_" in c.external_key
            assert c.external_key.islower()


# ── Acquisition Search ────────────────────────────────────────────────────────

class TestAcquisitionSearchGenerator:
    @pytest.fixture
    def generator(self):
        return AcquisitionSearchGenerator()

    def test_generates_per_language(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        assert len(campaigns) >= 1

    def test_ad_groups_per_keyword_theme(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it = next(c for c in campaigns if c.language_code == "IT")
        # Should have ad groups for location, category, intent, occasion
        assert len(it.ad_groups) >= 2

    def test_keywords_include_phrase_and_broad(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it = next(c for c in campaigns if c.language_code == "IT")
        match_types = set()
        for ag in it.ad_groups:
            for kw in ag.keywords:
                match_types.add(kw.match_type)
        assert MatchType.phrase in match_types
        assert MatchType.broad in match_types

    def test_fallback_to_vertical_template_when_no_keywords(self, generator, minimal_brief):
        """Minimal brief has no acquisition keywords — should use vertical template."""
        minimal_brief.budgets.by_campaign_type["search_acquisition"] = {
            "total": 500,
            "by_language": {"IT": 500}
        }
        from app.domain.schemas.brief import BudgetByLanguage
        minimal_brief.budgets.by_campaign_type["search_acquisition"] = BudgetByLanguage(
            total=500, by_language={"IT": 500}
        )
        campaigns = generator.generate(minimal_brief)
        assert len(campaigns) == 1
        assert len(campaigns[0].ad_groups) > 0


# ── Retargeting ───────────────────────────────────────────────────────────────

class TestRetargetingGenerator:
    @pytest.fixture
    def generator(self):
        return RetargetingGenerator()

    def test_generates_display_campaign(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert c.campaign_type == CampaignType.display

    def test_one_ad_group_per_remarketing_list(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it = next(c for c in campaigns if c.language_code == "IT")
        rm_lists = sample_brief.audiences.remarketing_lists
        # At least as many groups as remarketing lists
        assert len(it.ad_groups) >= len(rm_lists)

    def test_cannot_publish_without_images(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            # Display ads always have placeholder images
            assert len(c.publish_blockers) > 0 or not c.can_publish

    def test_no_campaigns_without_remarketing_lists(self, generator, sample_brief):
        sample_brief.audiences.remarketing_lists = []
        sample_brief.audiences.customer_match.enabled = False
        campaigns = generator.generate(sample_brief)
        assert len(campaigns) == 0


# ── Performance Max ───────────────────────────────────────────────────────────

class TestPerformanceMaxGenerator:
    @pytest.fixture
    def generator(self):
        return PerformanceMaxGenerator()

    def test_generates_pmax_campaigns(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert c.campaign_type == CampaignType.performance_max

    def test_one_asset_group_per_language(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert len(c.pmax_asset_groups) == 1

    def test_asset_group_has_audience_signals(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            ag = c.pmax_asset_groups[0]
            assert len(ag.audience_signals) > 0

    def test_final_url_expansion_is_off(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            for ag in c.pmax_asset_groups:
                assert ag.final_url_expansion is False

    def test_missing_assets_block_publish(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert not c.can_publish  # Images not provided

    def test_headlines_copied_from_brief(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it = next(c for c in campaigns if c.language_code == "IT")
        it_lang = sample_brief.get_language("IT")
        ag = it.pmax_asset_groups[0]
        assert ag.headlines[0] == it_lang.headlines[0]


# ── Demand Gen ────────────────────────────────────────────────────────────────

class TestDemandGenGenerator:
    @pytest.fixture
    def generator(self):
        return DemandGenGenerator()

    def test_generates_demand_gen_campaigns(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert c.campaign_type == CampaignType.demand_gen

    def test_always_blocks_publish_without_images(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        for c in campaigns:
            assert not c.can_publish
            assert len(c.publish_blockers) > 0

    def test_remarketing_groups_created(self, generator, sample_brief):
        campaigns = generator.generate(sample_brief)
        it = next(c for c in campaigns if c.language_code == "IT")
        assert len(it.ad_groups) > 0


# ── Orchestrator ──────────────────────────────────────────────────────────────

class TestCampaignOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return CampaignOrchestrator()

    def test_generates_all_campaign_types(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        types = {c.campaign_type for c in plan.campaigns}
        assert CampaignType.search in types
        assert CampaignType.performance_max in types
        assert CampaignType.demand_gen in types

    def test_plan_has_client_info(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        assert plan.client_name == sample_brief.client.brand_name
        assert plan.client_slug == sample_brief.client.brand_slug

    def test_all_campaigns_have_unique_external_keys(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        keys = [c.external_key for c in plan.campaigns]
        assert len(keys) == len(set(keys)), "Duplicate external_keys found"

    def test_dry_run_adds_diff(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123", dry_run=True)
        for c in plan.campaigns:
            assert c.dry_run_diff is not None
            assert "action" in c.dry_run_diff

    def test_global_negatives_present(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        assert len(plan.global_negative_keywords) > 0

    def test_campaigns_have_tracking_template(self, orchestrator, sample_brief):
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        for c in plan.campaigns:
            assert "utm_source=google" in c.settings.tracking_template

    def test_idempotency_marks_existing_as_update(self, orchestrator, sample_brief):
        # Generate first time
        plan = orchestrator.generate_plan(sample_brief, project_id="test-123")
        first_key = plan.campaigns[0].external_key

        # Simulate existing record
        existing = [{"external_key": first_key, "google_ads_campaign_id": "999"}]
        plan2 = orchestrator.generate_plan(
            sample_brief, project_id="test-123", existing_campaigns=existing
        )
        updated_campaign = next(c for c in plan2.campaigns if c.external_key == first_key)
        assert updated_campaign.dry_run_diff["action"] == "update"


# ── CSV Exporter ──────────────────────────────────────────────────────────────

class TestCsvExporter:
    def test_csv_export_produces_output(self, sample_brief):
        from app.generators.orchestrator import CampaignOrchestrator
        from app.connectors.csv_exporter import export_plan_to_csv

        orchestrator = CampaignOrchestrator()
        plan = orchestrator.generate_plan(sample_brief, "test-csv")
        csv_output = export_plan_to_csv(plan)

        assert isinstance(csv_output, str)
        assert len(csv_output) > 100

    def test_csv_contains_campaign_rows(self, sample_brief):
        from app.generators.orchestrator import CampaignOrchestrator
        from app.connectors.csv_exporter import export_plan_to_csv

        plan = CampaignOrchestrator().generate_plan(sample_brief, "test-csv2")
        csv_output = export_plan_to_csv(plan)

        assert "Campaign" in csv_output

    def test_csv_contains_ad_group_rows(self, sample_brief):
        from app.generators.orchestrator import CampaignOrchestrator
        from app.connectors.csv_exporter import export_plan_to_csv

        plan = CampaignOrchestrator().generate_plan(sample_brief, "test-csv3")
        csv_output = export_plan_to_csv(plan)

        assert "Ad Group" in csv_output

    def test_csv_contains_rsa_rows(self, sample_brief):
        from app.generators.orchestrator import CampaignOrchestrator
        from app.connectors.csv_exporter import export_plan_to_csv

        plan = CampaignOrchestrator().generate_plan(sample_brief, "test-csv4")
        csv_output = export_plan_to_csv(plan)

        # RSA rows identified by Headline 1 being non-empty (no Ad type column in this format)
        assert '"Headline 1"' in csv_output
