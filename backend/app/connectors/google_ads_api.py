"""
Google Ads API Connector.

Architecture:
- GoogleAdsApiConnector: main class, works in dry_run or live mode
- Live mode: requires google-ads Python client properly configured
- Dry run: validates structure and returns diff without API calls

Setup guide is in README.md (OAuth2 credentials, developer token).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.domain.schemas.campaign_plan import AccountPlan, CampaignPlan

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleAdsApiError(Exception):
    """Raised when the Google Ads API returns an error."""
    pass


class GoogleAdsApiNotConfiguredError(Exception):
    """Raised when credentials are missing."""
    pass


class DryRunResult:
    """Result of a dry-run publish operation."""

    def __init__(self):
        self.would_create: List[Dict] = []
        self.would_update: List[Dict] = []
        self.blocked: List[Dict] = []
        self.errors: List[str] = []

    def add_create(self, campaign_name: str, details: Dict):
        self.would_create.append({"campaign": campaign_name, **details})

    def add_update(self, campaign_name: str, details: Dict):
        self.would_update.append({"campaign": campaign_name, **details})

    def add_blocked(self, campaign_name: str, blockers: List[str]):
        self.blocked.append({"campaign": campaign_name, "blockers": blockers})

    def to_dict(self) -> Dict:
        return {
            "dry_run": True,
            "would_create": self.would_create,
            "would_update": self.would_update,
            "blocked": self.blocked,
            "errors": self.errors,
            "summary": {
                "create_count": len(self.would_create),
                "update_count": len(self.would_update),
                "blocked_count": len(self.blocked),
            },
        }


class GoogleAdsApiConnector:
    """
    Connector for Google Ads API.

    Usage:
        connector = GoogleAdsApiConnector()
        result = connector.publish(plan, customer_id="123-456-7890", dry_run=True)

    To use live mode:
        1. Set all GOOGLE_ADS_* env vars in .env
        2. Pass dry_run=False
        3. Ensure campaign.can_publish=True before calling
    """

    def __init__(self):
        self._client = None
        self._configured = settings.is_google_ads_configured

    def _get_client(self):
        """Lazily initialize the Google Ads client."""
        if self._client is not None:
            return self._client

        if not self._configured:
            raise GoogleAdsApiNotConfiguredError(
                "Google Ads API credentials non configurate. "
                "Imposta le variabili d'ambiente: GOOGLE_ADS_DEVELOPER_TOKEN, "
                "GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN. "
                "Vedi README.md per la guida completa."
            )

        try:
            from google.ads.googleads.client import GoogleAdsClient
            self._client = GoogleAdsClient.load_from_dict({
                "developer_token": settings.google_ads_developer_token,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "refresh_token": settings.google_ads_refresh_token,
                "login_customer_id": settings.google_ads_login_customer_id.replace("-", ""),
                "use_proto_plus": True,
            })
            logger.info("Google Ads client initialized")
            return self._client
        except ImportError:
            raise GoogleAdsApiNotConfiguredError(
                "google-ads package non installato. Esegui: pip install google-ads"
            )
        except Exception as exc:
            raise GoogleAdsApiNotConfiguredError(
                f"Errore inizializzazione Google Ads client: {exc}"
            )

    def publish(
        self,
        plan: AccountPlan,
        customer_id: str,
        dry_run: bool = True,
    ) -> Dict:
        """
        Publish all publishable campaigns in the plan.

        Args:
            plan: The AccountPlan to publish
            customer_id: Google Ads customer ID (format: XXX-XXX-XXXX)
            dry_run: If True, only validates and returns diff without API calls

        Returns:
            Dictionary with results (dry_run diff or actual API responses)
        """
        customer_id_clean = customer_id.replace("-", "")

        if dry_run:
            return self._dry_run(plan)

        if not plan.is_valid:
            raise GoogleAdsApiError(
                f"Piano non valido — risolvi prima gli errori: {plan.validation_errors}"
            )

        client = self._get_client()
        results = {"published": [], "errors": [], "skipped": []}

        for campaign in plan.campaigns:
            if not campaign.can_publish:
                results["skipped"].append({
                    "campaign": campaign.campaign_name,
                    "blockers": campaign.publish_blockers,
                })
                continue

            try:
                campaign_id = self._create_or_update_campaign(
                    client, customer_id_clean, campaign
                )
                results["published"].append({
                    "campaign": campaign.campaign_name,
                    "google_ads_id": campaign_id,
                    "action": "created",
                })
                logger.info(f"Published campaign: {campaign.campaign_name} (ID: {campaign_id})")
            except Exception as exc:
                error_msg = f"Errore pubblicazione '{campaign.campaign_name}': {exc}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append({"campaign": campaign.campaign_name, "error": str(exc)})

        return results

    def _dry_run(self, plan: AccountPlan) -> Dict:
        """Simulate publish and return what would happen."""
        result = DryRunResult()

        for campaign in plan.campaigns:
            if not campaign.can_publish:
                result.add_blocked(campaign.campaign_name, campaign.publish_blockers)
                continue

            diff = campaign.dry_run_diff or {}
            action = diff.get("action", "create")

            if action == "update":
                result.add_update(campaign.campaign_name, {
                    "existing_id": diff.get("existing_google_ads_id"),
                    "budget_daily": campaign.settings.budget_daily_eur,
                    "ad_groups": len(campaign.ad_groups),
                })
            else:
                result.add_create(campaign.campaign_name, {
                    "campaign_type": campaign.campaign_type.value,
                    "language": campaign.language_code,
                    "budget_daily": campaign.settings.budget_daily_eur,
                    "ad_groups": len(campaign.ad_groups),
                    "pmax_asset_groups": len(campaign.pmax_asset_groups),
                })

        return result.to_dict()

    # ── Live API methods (stubs with full implementation) ─────────────────────

    def _create_or_update_campaign(
        self, client: Any, customer_id: str, campaign: CampaignPlan
    ) -> str:
        """
        Create or update a campaign via Google Ads API.
        Returns the Google Ads campaign resource ID.
        """
        from google.ads.googleads.errors import GoogleAdsException

        campaign_service = client.get_service("CampaignService")
        campaign_op = client.get_type("CampaignOperation")

        # Build the campaign resource
        gads_campaign = campaign_op.create
        gads_campaign.name = campaign.campaign_name
        gads_campaign.status = client.enums.CampaignStatusEnum.PAUSED
        gads_campaign.advertising_channel_type = self._map_campaign_type(
            client, campaign.campaign_type.value
        )

        # Budget
        budget_id = self._create_campaign_budget(
            client, customer_id, campaign
        )
        gads_campaign.campaign_budget = f"customers/{customer_id}/campaignBudgets/{budget_id}"

        # Bid strategy
        self._apply_bid_strategy(client, gads_campaign, campaign)

        # Labels
        gads_campaign.labels.extend(campaign.settings.labels)

        try:
            response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_op],
            )
            resource_name = response.results[0].resource_name
            campaign_id = resource_name.split("/")[-1]

            # Create ad groups and ads
            for ag in campaign.ad_groups:
                self._create_ad_group(client, customer_id, resource_name, campaign, ag)

            return campaign_id

        except GoogleAdsException as exc:
            errors = [e.message for e in exc.failure.errors]
            raise GoogleAdsApiError(f"Google Ads API error: {'; '.join(errors)}")

    def _create_campaign_budget(
        self, client: Any, customer_id: str, campaign: CampaignPlan
    ) -> str:
        """Creates a campaign budget and returns its ID."""
        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.get_type("CampaignBudgetOperation")

        budget = budget_op.create
        budget.name = f"{campaign.campaign_name} Budget"
        budget.amount_micros = int(campaign.settings.budget_daily_eur * 1_000_000)
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD

        response = budget_service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[budget_op],
        )
        budget_resource = response.results[0].resource_name
        return budget_resource.split("/")[-1]

    def _create_ad_group(
        self, client: Any, customer_id: str,
        campaign_resource: str, campaign: CampaignPlan, ag: AdGroupPlan
    ):
        """Creates an ad group with its keywords and ads."""
        ag_service = client.get_service("AdGroupService")
        ag_op = client.get_type("AdGroupOperation")

        gads_ag = ag_op.create
        gads_ag.name = ag.name
        gads_ag.campaign = campaign_resource
        gads_ag.status = client.enums.AdGroupStatusEnum.ENABLED
        if ag.default_max_cpc:
            gads_ag.cpc_bid_micros = int(ag.default_max_cpc * 1_000_000)

        response = ag_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[ag_op],
        )
        ag_resource = response.results[0].resource_name

        # Keywords
        if ag.keywords:
            self._create_keywords(client, customer_id, ag_resource, ag.keywords)

        # Ads (RSA)
        for rsa in ag.ads:
            self._create_rsa(client, customer_id, ag_resource, rsa)

    def _create_keywords(self, client: Any, customer_id: str, ag_resource: str, keywords):
        """Creates keywords in the given ad group."""
        from app.domain.schemas.campaign_plan import Keyword
        kw_service = client.get_service("AdGroupCriterionService")
        operations = []

        for kw in keywords:
            if kw.is_negative:
                continue  # Negative handled separately
            op = client.get_type("AdGroupCriterionOperation")
            criterion = op.create
            criterion.ad_group = ag_resource
            criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            criterion.keyword.text = kw.text
            criterion.keyword.match_type = self._map_match_type(client, kw.match_type.value)
            operations.append(op)

        if operations:
            kw_service.mutate_ad_group_criteria(
                customer_id=customer_id,
                operations=operations,
            )

    def _create_rsa(self, client: Any, customer_id: str, ag_resource: str, rsa):
        """Creates an RSA ad."""
        ad_service = client.get_service("AdGroupAdService")
        op = client.get_type("AdGroupAdOperation")

        ag_ad = op.create
        ag_ad.ad_group = ag_resource
        ag_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED

        ad = ag_ad.ad
        ad.final_urls.append(rsa.final_url)
        if rsa.tracking_template:
            ad.tracking_url_template = rsa.tracking_template

        rsa_info = ad.responsive_search_ad
        for h in rsa.headlines[:15]:
            headline = client.get_type("AdTextAsset")
            headline.text = h.text
            if h.pin_position:
                headline.pinned_field = self._map_pin_position(client, h.pin_position)
            rsa_info.headlines.append(headline)

        for d in rsa.descriptions[:4]:
            desc = client.get_type("AdTextAsset")
            desc.text = d
            rsa_info.descriptions.append(desc)

        ad_service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[op],
        )

    def _map_campaign_type(self, client: Any, campaign_type: str) -> Any:
        type_map = {
            "Search": client.enums.AdvertisingChannelTypeEnum.SEARCH,
            "Display": client.enums.AdvertisingChannelTypeEnum.DISPLAY,
            "Performance Max": client.enums.AdvertisingChannelTypeEnum.PERFORMANCE_MAX,
            "Video": client.enums.AdvertisingChannelTypeEnum.VIDEO,
            "Demand Gen": client.enums.AdvertisingChannelTypeEnum.DEMAND_GEN,
        }
        return type_map.get(campaign_type, client.enums.AdvertisingChannelTypeEnum.SEARCH)

    def _map_match_type(self, client: Any, match_type: str) -> Any:
        type_map = {
            "Exact": client.enums.KeywordMatchTypeEnum.EXACT,
            "Phrase": client.enums.KeywordMatchTypeEnum.PHRASE,
            "Broad": client.enums.KeywordMatchTypeEnum.BROAD,
        }
        return type_map.get(match_type, client.enums.KeywordMatchTypeEnum.BROAD)

    def _map_pin_position(self, client: Any, position: int) -> Any:
        pos_map = {
            1: client.enums.ServedAssetFieldTypeEnum.HEADLINE_1,
            2: client.enums.ServedAssetFieldTypeEnum.HEADLINE_2,
            3: client.enums.ServedAssetFieldTypeEnum.HEADLINE_3,
        }
        return pos_map.get(position, client.enums.ServedAssetFieldTypeEnum.HEADLINE_1)

    def _apply_bid_strategy(self, client: Any, gads_campaign: Any, campaign: CampaignPlan):
        """Apply bid strategy settings to the campaign resource."""
        bid = campaign.settings.bid_strategy.value
        settings = campaign.settings

        if bid == "Target CPA" and settings.target_cpa:
            gads_campaign.target_cpa.target_cpa_micros = int(settings.target_cpa * 1_000_000)
        elif bid == "Target ROAS" and settings.target_roas:
            gads_campaign.target_roas.target_roas = settings.target_roas / 100
        elif bid == "Maximize conversions":
            gads_campaign.maximize_conversions.target_cpa_micros = 0
        elif bid == "Maximize conversion value":
            gads_campaign.maximize_conversion_value.target_roas = 0
        elif bid == "Maximize clicks":
            # target_spend with no cpc_bid_ceiling = uncapped maximize clicks
            gads_campaign.target_spend.cpc_bid_ceiling_micros = 0
        elif bid == "Target impression share":
            # Aim for top of page, 100% impression share, no CPC cap
            gads_campaign.target_impression_share.location = (
                client.enums.TargetImpressionShareLocationEnum.TOP_OF_PAGE
            )
            gads_campaign.target_impression_share.location_fraction_micros = 1_000_000  # 100%
            gads_campaign.target_impression_share.cpc_bid_ceiling_micros = 0
