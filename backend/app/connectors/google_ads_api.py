"""
Google Ads API Connector.

Architecture:
- GoogleAdsApiConnector: main class, works in dry_run or live mode
- Live mode: requires google-ads Python client properly configured
- Dry run: validates structure and returns diff without API calls

Setup guide is in README.md (OAuth2 credentials, developer token).

Live publish flow per campaign:
  1. _create_or_update_campaign  — create or update the campaign shell
     ├─ _create_campaign_budget  — shared daily budget
     ├─ _apply_bid_strategy      — Target CPA / ROAS / Maximize …
     ├─ _add_geo_targets         — location criteria (country codes)
     ├─ _add_language_targets    — language criteria (Google lang IDs)
     ├─ if PMax:
     │    _create_pmax_asset_group  (per asset group)
     │      └─ _add_text_asset_to_pmax_group  (per headline/desc)
     └─ if standard:
          _create_ad_group       (per ad group)
            ├─ _create_keywords  (positive only)
            └─ _create_rsa       (per RSA)
          _create_campaign_assets        (sitelinks + callouts)
          _create_campaign_negative_keywords
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.domain.schemas.campaign_plan import (
    AccountPlan, AdGroupPlan, AssetPack, CampaignPlan, CampaignType,
    Keyword, PMaxAssetGroup,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Geo target mapping ────────────────────────────────────────────────────────
# Country code → Google Ads geographic location criterion ID.
# These are stable Google canonical IDs; see:
# https://developers.google.com/google-ads/api/data/geotargets
_GEO_TARGET_IDS: dict[str, int] = {
    "IT": 2380, "DE": 2276, "FR": 2250, "ES": 2724,
    "GB": 2826, "UK": 2826, "US": 2840, "AT": 2040,
    "CH": 2756, "NL": 2528, "BE": 2056, "PT": 2620,
    "PL": 2616, "RU": 2643, "CN": 2156, "JP": 2392,
    "AU": 2036, "CA": 2124, "BR": 2076, "SE": 2752,
    "DK": 2208, "NO": 2578, "FI": 2246, "CZ": 2203,
}


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
                diff = campaign.dry_run_diff or {}
                action = "updated" if diff.get("action") == "update" else "created"
                results["published"].append({
                    "campaign": campaign.campaign_name,
                    "google_ads_id": campaign_id,
                    "action": action,
                })
                logger.info(
                    f"Published campaign: {campaign.campaign_name} "
                    f"(ID: {campaign_id}, action: {action})"
                )
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

    # ── Core campaign create/update ───────────────────────────────────────────

    def _create_or_update_campaign(
        self, client: Any, customer_id: str, campaign: CampaignPlan
    ) -> str:
        """
        Create or update a campaign via Google Ads API.

        If dry_run_diff carries action='update' and an existing_google_ads_id,
        updates the campaign budget and tracking template instead of creating.
        Returns the Google Ads campaign resource ID.
        """
        from google.ads.googleads.errors import GoogleAdsException

        # Route to update path when an existing Google Ads ID is known.
        diff = campaign.dry_run_diff or {}
        if diff.get("action") == "update" and diff.get("existing_google_ads_id"):
            existing_id = str(diff["existing_google_ads_id"])
            return self._update_existing_campaign(client, customer_id, campaign, existing_id)

        # ── Create path ───────────────────────────────────────────────────────
        campaign_service = client.get_service("CampaignService")
        campaign_op = client.get_type("CampaignOperation")

        gads_campaign = campaign_op.create
        gads_campaign.name = campaign.campaign_name
        gads_campaign.status = client.enums.CampaignStatusEnum.PAUSED
        gads_campaign.advertising_channel_type = self._map_campaign_type(
            client, campaign.campaign_type.value
        )

        if campaign.settings.tracking_template:
            gads_campaign.tracking_url_template = campaign.settings.tracking_template

        budget_id = self._create_campaign_budget(client, customer_id, campaign)
        gads_campaign.campaign_budget = f"customers/{customer_id}/campaignBudgets/{budget_id}"

        self._apply_bid_strategy(client, gads_campaign, campaign)

        if campaign.settings.labels:
            gads_campaign.labels.extend(campaign.settings.labels)

        try:
            response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_op],
            )
            resource_name = response.results[0].resource_name
            campaign_id = resource_name.split("/")[-1]

            # ── Targeting ─────────────────────────────────────────────────────
            if campaign.settings.geo_targets:
                self._add_geo_targets(
                    client, customer_id, resource_name, campaign.settings.geo_targets
                )

            if campaign.settings.language_ids:
                self._add_language_targets(
                    client, customer_id, resource_name, campaign.settings.language_ids
                )

            # ── Campaign body ─────────────────────────────────────────────────
            if campaign.campaign_type == CampaignType.performance_max:
                # PMax has no ad groups — create asset groups instead.
                for ag in campaign.pmax_asset_groups:
                    if ag.has_missing_assets:
                        logger.warning(
                            f"Skipping PMax asset group '{ag.name}': "
                            f"missing required assets: {ag.missing_asset_notes}"
                        )
                        continue
                    try:
                        self._create_pmax_asset_group(client, customer_id, resource_name, ag)
                    except Exception as exc:
                        logger.error(
                            f"Failed to create PMax asset group '{ag.name}': {exc}",
                            exc_info=True,
                        )
            else:
                # Standard campaign: ad groups first, then campaign-level assets.
                for ag in campaign.ad_groups:
                    try:
                        self._create_ad_group(client, customer_id, resource_name, campaign, ag)
                    except Exception as exc:
                        logger.error(
                            f"Failed to create ad group '{ag.name}': {exc}", exc_info=True
                        )

                # Campaign-level sitelinks + callouts from the first ad group's asset pack.
                if campaign.ad_groups and campaign.ad_groups[0].assets:
                    try:
                        self._create_campaign_assets(
                            client, customer_id, resource_name,
                            campaign.ad_groups[0].assets,
                        )
                    except Exception as exc:
                        logger.warning(f"Failed to create campaign-level assets: {exc}")

            # ── Campaign-level negative keywords ──────────────────────────────
            # Negatives are skipped in _create_keywords (ad-group level)
            # and collected here for campaign-level application.
            neg_kws = [
                kw for ag in campaign.ad_groups
                for kw in ag.keywords if kw.is_negative
            ]
            if neg_kws:
                try:
                    self._create_campaign_negative_keywords(
                        client, customer_id, resource_name, neg_kws
                    )
                except Exception as exc:
                    logger.warning(f"Failed to create campaign negative keywords: {exc}")

            return campaign_id

        except GoogleAdsException as exc:
            errors = [e.message for e in exc.failure.errors]
            raise GoogleAdsApiError(f"Google Ads API error: {'; '.join(errors)}")

    def _update_existing_campaign(
        self, client: Any, customer_id: str,
        campaign: CampaignPlan, existing_id: str,
    ) -> str:
        """
        Update budget and tracking template of an existing campaign.

        A new shared budget is always created (Google Ads shared budgets
        are immutable once attached; attaching a new one is the correct pattern).
        Ad groups, keywords and ads are not touched — use the Campaign Manager
        UI or a separate diff-based sync for granular ad-group updates.
        """
        from google.ads.googleads.errors import GoogleAdsException

        resource_name = f"customers/{customer_id}/campaigns/{existing_id}"

        try:
            new_budget_id = self._create_campaign_budget(client, customer_id, campaign)

            campaign_service = client.get_service("CampaignService")
            campaign_op = client.get_type("CampaignOperation")
            gads_campaign = campaign_op.update
            gads_campaign.resource_name = resource_name
            gads_campaign.campaign_budget = (
                f"customers/{customer_id}/campaignBudgets/{new_budget_id}"
            )
            paths = ["campaign_budget"]
            if campaign.settings.tracking_template:
                gads_campaign.tracking_url_template = campaign.settings.tracking_template
                paths.append("tracking_url_template")

            campaign_op.update_mask.paths.extend(paths)
            campaign_service.mutate_campaigns(
                customer_id=customer_id, operations=[campaign_op]
            )
            logger.info(f"Updated campaign {existing_id} ({campaign.campaign_name})")

        except GoogleAdsException as exc:
            errors = [e.message for e in exc.failure.errors]
            raise GoogleAdsApiError(f"Campaign update error: {'; '.join(errors)}")

        return existing_id

    # ── Budget ────────────────────────────────────────────────────────────────

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

    # ── Targeting ─────────────────────────────────────────────────────────────

    def _add_geo_targets(
        self, client: Any, customer_id: str,
        campaign_resource: str, geo_targets: List[str],
    ) -> None:
        """
        Add location targeting criteria to a campaign.

        geo_targets are country codes (e.g. "IT", "DE"). Unknown codes are
        logged and skipped rather than failing the entire publish.
        """
        criterion_service = client.get_service("CampaignCriterionService")
        geo_service = client.get_service("GeoTargetConstantService")
        operations = []

        for geo in geo_targets:
            location_id = _GEO_TARGET_IDS.get(geo.upper().strip())
            if location_id is None:
                logger.warning(f"Unknown geo target '{geo}' — skipping (add to _GEO_TARGET_IDS)")
                continue
            op = client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = campaign_resource
            criterion.location.geo_target_constant = (
                geo_service.geo_target_constant_path(location_id)
            )
            operations.append(op)

        if operations:
            criterion_service.mutate_campaign_criteria(
                customer_id=customer_id, operations=operations
            )

    def _add_language_targets(
        self, client: Any, customer_id: str,
        campaign_resource: str, language_ids: List[int],
    ) -> None:
        """
        Add language targeting criteria to a campaign.

        language_ids are Google Language IDs (e.g. 1004 for Italian).
        These come from CampaignSettings.language_ids, populated by the Brief.
        """
        criterion_service = client.get_service("CampaignCriterionService")
        lang_service = client.get_service("LanguageConstantService")
        operations = []

        for lang_id in language_ids:
            op = client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = campaign_resource
            criterion.language.language_constant = (
                lang_service.language_constant_path(lang_id)
            )
            operations.append(op)

        if operations:
            criterion_service.mutate_campaign_criteria(
                customer_id=customer_id, operations=operations
            )

    # ── Ad groups (standard campaigns) ───────────────────────────────────────

    def _create_ad_group(
        self, client: Any, customer_id: str,
        campaign_resource: str, campaign: CampaignPlan, ag: AdGroupPlan,
    ):
        """Creates an ad group with its positive keywords and RSA ads."""
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

        if ag.keywords:
            self._create_keywords(client, customer_id, ag_resource, ag.keywords)

        for rsa in ag.ads:
            self._create_rsa(client, customer_id, ag_resource, rsa)

    def _create_keywords(
        self, client: Any, customer_id: str, ag_resource: str, keywords,
    ):
        """
        Creates positive keywords in an ad group.

        Negative keywords are intentionally skipped here — they are collected
        from all ad groups and applied at campaign level by
        _create_campaign_negative_keywords.
        """
        kw_service = client.get_service("AdGroupCriterionService")
        operations = []

        for kw in keywords:
            if kw.is_negative:
                continue
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

    # ── Campaign-level assets (sitelinks + callouts) ──────────────────────────

    def _create_campaign_assets(
        self, client: Any, customer_id: str,
        campaign_resource: str, assets: AssetPack,
    ) -> None:
        """
        Create sitelink and callout assets and link them to the campaign.

        Assets are created in a single batch call; links are created in a
        second batch call. Both use the CampaignAssetService.
        """
        asset_service = client.get_service("AssetService")
        cam_asset_service = client.get_service("CampaignAssetService")
        FieldType = client.enums.AssetFieldTypeEnum

        # Build (type_label, AssetOperation) pairs
        typed_ops: list[tuple[str, Any]] = []

        for sl in assets.sitelinks:
            asset_op = client.get_type("AssetOperation")
            a = asset_op.create
            a.sitelink_asset.link_text = sl.text
            a.sitelink_asset.description1 = sl.description_1
            a.sitelink_asset.description2 = sl.description_2
            a.final_urls.append(sl.final_url)
            typed_ops.append(("sitelink", asset_op))

        for co in assets.callouts:
            asset_op = client.get_type("AssetOperation")
            asset_op.create.callout_asset.callout_text = co.text
            typed_ops.append(("callout", asset_op))

        if not typed_ops:
            return

        resp = asset_service.mutate_assets(
            customer_id=customer_id,
            operations=[op for _, op in typed_ops],
        )

        link_ops = []
        for (asset_type, _), result in zip(typed_ops, resp.results):
            cam_op = client.get_type("CampaignAssetOperation")
            link = cam_op.create
            link.campaign = campaign_resource
            link.asset = result.resource_name
            link.field_type = (
                FieldType.SITELINK if asset_type == "sitelink" else FieldType.CALLOUT
            )
            link_ops.append(cam_op)

        cam_asset_service.mutate_campaign_assets(
            customer_id=customer_id, operations=link_ops
        )

    # ── Campaign-level negative keywords ─────────────────────────────────────

    def _create_campaign_negative_keywords(
        self, client: Any, customer_id: str,
        campaign_resource: str, neg_kws: List[Keyword],
    ) -> None:
        """Add negative keywords at campaign level via CampaignCriterionService."""
        criterion_service = client.get_service("CampaignCriterionService")
        operations = []

        for kw in neg_kws:
            op = client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = campaign_resource
            criterion.negative = True
            criterion.keyword.text = kw.text
            criterion.keyword.match_type = self._map_match_type(client, kw.match_type.value)
            operations.append(op)

        if operations:
            criterion_service.mutate_campaign_criteria(
                customer_id=customer_id, operations=operations
            )

    # ── Performance Max asset groups ──────────────────────────────────────────

    def _create_pmax_asset_group(
        self, client: Any, customer_id: str,
        campaign_resource: str, ag: PMaxAssetGroup,
    ) -> None:
        """
        Create a Performance Max asset group with text assets.

        Text assets (headlines, long headlines, descriptions) are created
        individually via AssetService and linked to the group via
        AssetGroupAssetService.

        Image/logo/video assets require binary upload and are not handled
        here — they should be added manually via Google Ads UI or a
        dedicated image-upload flow after the initial publish.
        """
        from google.ads.googleads.errors import GoogleAdsException

        # ── Create the asset group shell ──────────────────────────────────────
        ag_service = client.get_service("AssetGroupService")
        ag_op = client.get_type("AssetGroupOperation")
        asset_group = ag_op.create
        asset_group.name = ag.name
        asset_group.campaign = campaign_resource
        asset_group.final_urls.append(ag.final_url)
        asset_group.final_url_expansion_opt_out = not ag.final_url_expansion
        asset_group.status = client.enums.AssetGroupStatusEnum.ENABLED

        try:
            response = ag_service.mutate_asset_groups(
                customer_id=customer_id, operations=[ag_op]
            )
            ag_resource = response.results[0].resource_name
        except GoogleAdsException as exc:
            errors = [e.message for e in exc.failure.errors]
            raise GoogleAdsApiError(f"PMax asset group creation error: {'; '.join(errors)}")

        # ── Add text assets ───────────────────────────────────────────────────
        FieldType = client.enums.AssetFieldTypeEnum
        text_assets: list[tuple[str, Any]] = (
            [(h, FieldType.HEADLINE) for h in ag.headlines[:15]]
            + [(lh, FieldType.LONG_HEADLINE) for lh in ag.long_headlines[:5]]
            + [(d, FieldType.DESCRIPTION) for d in ag.descriptions[:5]]
        )

        for text, field_type in text_assets:
            try:
                self._add_text_asset_to_pmax_group(
                    client, customer_id, ag_resource, text, field_type
                )
            except Exception as exc:
                logger.warning(
                    f"Failed to add text asset '{text[:40]}' to PMax group '{ag.name}': {exc}"
                )

        logger.info(
            f"Created PMax asset group '{ag.name}' "
            f"({len(text_assets)} text assets; images require manual upload)"
        )

    def _add_text_asset_to_pmax_group(
        self, client: Any, customer_id: str,
        ag_resource: str, text: str, field_type: Any,
    ) -> None:
        """
        Create a text Asset via AssetService, then link it to a PMax
        asset group via AssetGroupAssetService.

        Each text is a separate mutate call; Google Ads does not allow
        batching asset creation and asset-group linking in one request.
        """
        asset_service = client.get_service("AssetService")
        ag_asset_service = client.get_service("AssetGroupAssetService")

        asset_op = client.get_type("AssetOperation")
        asset_op.create.text_asset.text = text
        resp = asset_service.mutate_assets(customer_id=customer_id, operations=[asset_op])
        asset_resource = resp.results[0].resource_name

        ag_asset_op = client.get_type("AssetGroupAssetOperation")
        link = ag_asset_op.create
        link.asset_group = ag_resource
        link.asset = asset_resource
        link.field_type = field_type
        ag_asset_service.mutate_asset_group_assets(
            customer_id=customer_id, operations=[ag_asset_op]
        )

    # ── Enum mappers ──────────────────────────────────────────────────────────

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

    def _apply_bid_strategy(
        self, client: Any, gads_campaign: Any, campaign: CampaignPlan
    ):
        """Apply bid strategy settings to the campaign resource."""
        bid = campaign.settings.bid_strategy.value
        s = campaign.settings  # avoid shadowing module-level `settings`

        if bid == "Target CPA" and s.target_cpa:
            gads_campaign.target_cpa.target_cpa_micros = int(s.target_cpa * 1_000_000)
        elif bid == "Target ROAS" and s.target_roas:
            gads_campaign.target_roas.target_roas = s.target_roas / 100
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
            gads_campaign.target_impression_share.location_fraction_micros = 1_000_000
            gads_campaign.target_impression_share.cpc_bid_ceiling_micros = 0
        elif bid == "Manual CPC":
            gads_campaign.manual_cpc.enhanced_cpc_enabled = False
        elif bid == "Enhanced CPC":
            gads_campaign.manual_cpc.enhanced_cpc_enabled = True
