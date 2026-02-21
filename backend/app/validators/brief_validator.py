"""
Brief validator: schema validation (Pydantic) + business rules.
Returns structured ValidationResult with errors, warnings, and checklist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.domain.schemas.brief import Brief, CampaignTypeKey, LanguagePlan


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    field: Optional[str] = None
    language: Optional[str] = None


@dataclass
class ChecklistItem:
    label: str
    ok: bool
    detail: Optional[str] = None


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    infos: List[ValidationIssue] = field(default_factory=list)
    checklist: List[ChecklistItem] = field(default_factory=list)

    @property
    def error_messages(self) -> List[str]:
        return [i.message for i in self.errors]

    @property
    def warning_messages(self) -> List[str]:
        return [i.message for i in self.warnings]

    def add_error(self, code: str, message: str, field: str = None, language: str = None):
        self.errors.append(ValidationIssue(Severity.ERROR, code, message, field, language))
        self.is_valid = False

    def add_warning(self, code: str, message: str, field: str = None, language: str = None):
        self.warnings.append(ValidationIssue(Severity.WARNING, code, message, field, language))

    def add_info(self, code: str, message: str, field: str = None, language: str = None):
        self.infos.append(ValidationIssue(Severity.INFO, code, message, field, language))

    def add_check(self, label: str, ok: bool, detail: str = None):
        self.checklist.append(ChecklistItem(label, ok, detail))


class BriefValidator:
    """
    Multi-layer brief validation:
    1. Schema level (already done by Pydantic at parse time)
    2. Business rules (cross-field, domain-specific)
    3. Google Ads policy checks (basic)
    4. Completeness checklist
    """

    # Minimum required per language for a healthy brief
    MIN_HEADLINES = 3
    MIN_DESCRIPTIONS = 2
    MIN_SITELINKS = 2
    MIN_CALLOUTS = 2
    MIN_BRAND_TERMS = 1
    MAX_HEADLINE_LENGTH = 30
    MAX_DESCRIPTION_LENGTH = 90
    MAX_SITELINK_TEXT = 25
    MAX_SITELINK_DESC = 35

    def validate(self, brief: Brief) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        self._validate_budgets(brief, result)
        self._validate_languages(brief, result)
        self._validate_acquisition_keywords(brief, result)
        self._validate_audiences(brief, result)
        self._validate_conversions(brief, result)
        self._validate_geo(brief, result)
        self._validate_policy(brief, result)
        self._build_completeness_checklist(brief, result)

        return result

    # ── Budget validation ─────────────────────────────────────────────────────

    def _validate_budgets(self, brief: Brief, result: ValidationResult):
        total_allocated = sum(
            b.total for b in brief.budgets.by_campaign_type.values()
        )

        if total_allocated > brief.budgets.total_monthly_eur * 1.05:
            result.add_error(
                "BUDGET_OVER_TOTAL",
                f"Budget allocato ({total_allocated:.0f} EUR) supera il totale mensile "
                f"({brief.budgets.total_monthly_eur:.0f} EUR).",
                field="budgets",
            )
        elif total_allocated < brief.budgets.total_monthly_eur * 0.80:
            result.add_warning(
                "BUDGET_UNDER_ALLOCATED",
                f"Meno dell'80% del budget mensile è allocato a campagne "
                f"({total_allocated:.0f} / {brief.budgets.total_monthly_eur:.0f} EUR).",
                field="budgets",
            )

        required_types = [t.value for t in CampaignTypeKey]
        for camp_type in required_types:
            if camp_type not in brief.budgets.by_campaign_type:
                result.add_warning(
                    "BUDGET_MISSING_TYPE",
                    f"Nessun budget definito per tipo campagna '{camp_type}'. "
                    f"Le campagne di questo tipo non verranno generate.",
                    field=f"budgets.by_campaign_type.{camp_type}",
                )

        for camp_type, budget in brief.budgets.by_campaign_type.items():
            for lang_code, amount in budget.by_language.items():
                if amount < 1.0:
                    result.add_warning(
                        "BUDGET_TOO_LOW",
                        f"Budget giornaliero per {camp_type}/{lang_code} "
                        f"è inferiore a 1 EUR ({amount:.2f}). "
                        f"Campagna potrebbe non avere impression.",
                        field=f"budgets.by_campaign_type.{camp_type}.by_language.{lang_code}",
                        language=lang_code,
                    )

    # ── Language / Asset validation ───────────────────────────────────────────

    def _validate_languages(self, brief: Brief, result: ValidationResult):
        if not brief.languages:
            result.add_error("NO_LANGUAGES", "Nessuna lingua configurata nel brief.", field="languages")
            return

        for lang in brief.languages:
            self._validate_language_plan(lang, brief, result)

    def _validate_language_plan(
        self, lang: LanguagePlan, brief: Brief, result: ValidationResult
    ):
        code = lang.code

        # Headlines
        if len(lang.headlines) < self.MIN_HEADLINES:
            result.add_error(
                "HEADLINES_TOO_FEW",
                f"[{code}] Minimo {self.MIN_HEADLINES} headline richieste, "
                f"trovate {len(lang.headlines)}.",
                field=f"languages[{code}].headlines",
                language=code,
            )
        for h in lang.headlines:
            if len(h) > self.MAX_HEADLINE_LENGTH:
                result.add_error(
                    "HEADLINE_TOO_LONG",
                    f"[{code}] Headline troppo lunga ({len(h)} chars > {self.MAX_HEADLINE_LENGTH}): '{h}'",
                    language=code,
                )

        # Descriptions
        if len(lang.descriptions) < self.MIN_DESCRIPTIONS:
            result.add_error(
                "DESCRIPTIONS_TOO_FEW",
                f"[{code}] Minimo {self.MIN_DESCRIPTIONS} description richieste, "
                f"trovate {len(lang.descriptions)}.",
                field=f"languages[{code}].descriptions",
                language=code,
            )
        for d in lang.descriptions:
            if len(d) > self.MAX_DESCRIPTION_LENGTH:
                result.add_error(
                    "DESCRIPTION_TOO_LONG",
                    f"[{code}] Description troppo lunga ({len(d)} chars > {self.MAX_DESCRIPTION_LENGTH}): '{d[:50]}...'",
                    language=code,
                )

        # Sitelinks
        if len(lang.sitelinks) < self.MIN_SITELINKS:
            result.add_warning(
                "SITELINKS_TOO_FEW",
                f"[{code}] Consigliati almeno {self.MIN_SITELINKS} sitelink, "
                f"trovati {len(lang.sitelinks)}.",
                language=code,
            )
        for sl in lang.sitelinks:
            if len(sl.text) > self.MAX_SITELINK_TEXT:
                result.add_error(
                    "SITELINK_TEXT_TOO_LONG",
                    f"[{code}] Sitelink testo troppo lungo ({len(sl.text)} > {self.MAX_SITELINK_TEXT}): '{sl.text}'",
                    language=code,
                )
            if len(sl.description_1) > self.MAX_SITELINK_DESC:
                result.add_error(
                    "SITELINK_DESC_TOO_LONG",
                    f"[{code}] Sitelink description_1 troppo lunga: '{sl.description_1}'",
                    language=code,
                )
            if len(sl.description_2) > self.MAX_SITELINK_DESC:
                result.add_error(
                    "SITELINK_DESC_TOO_LONG",
                    f"[{code}] Sitelink description_2 troppo lunga: '{sl.description_2}'",
                    language=code,
                )

        # Callouts
        for co in lang.callouts:
            if len(co) > 25:
                result.add_error(
                    "CALLOUT_TOO_LONG",
                    f"[{code}] Callout troppo lungo ({len(co)} > 25): '{co}'",
                    language=code,
                )
        if len(lang.callouts) < self.MIN_CALLOUTS:
            result.add_warning(
                "CALLOUTS_TOO_FEW",
                f"[{code}] Consigliati almeno {self.MIN_CALLOUTS} callout, trovati {len(lang.callouts)}.",
                language=code,
            )

        # Brand terms
        if not lang.brand_terms:
            result.add_error(
                "NO_BRAND_TERMS",
                f"[{code}] Nessun brand term definito. Search Brand non generabile.",
                language=code,
            )

        # Landing page
        if not lang.landing_page:
            result.add_error(
                "NO_LANDING_PAGE",
                f"[{code}] Landing page mancante.",
                language=code,
            )

    # ── Keyword validation ────────────────────────────────────────────────────

    def _validate_acquisition_keywords(self, brief: Brief, result: ValidationResult):
        if not brief.acquisition_keywords:
            result.add_warning(
                "NO_ACQUISITION_KEYWORDS",
                "Nessuna keyword di acquisition nel brief. "
                "Verrà usato il template verticale come fallback.",
                field="acquisition_keywords",
            )
            return

        for lang in brief.languages:
            if lang.code not in brief.acquisition_keywords:
                result.add_warning(
                    "MISSING_ACQUISITION_KW_LANG",
                    f"[{lang.code}] Nessuna keyword di acquisition fornita. "
                    f"Verrà usato il template verticale.",
                    language=lang.code,
                )
                continue

            kw_plan = brief.acquisition_keywords[lang.code]
            total_kws = sum(len(v) for v in kw_plan.themes.values())

            if total_kws < 5:
                result.add_warning(
                    "FEW_ACQUISITION_KEYWORDS",
                    f"[{lang.code}] Solo {total_kws} keyword di acquisition. "
                    f"Consigliato almeno 10-15 per tema.",
                    language=lang.code,
                )

            if not kw_plan.negative_keywords:
                result.add_warning(
                    "NO_NEGATIVE_KEYWORDS",
                    f"[{lang.code}] Nessuna negative keyword definita per acquisition.",
                    language=lang.code,
                )

    # ── Audience validation ───────────────────────────────────────────────────

    def _validate_audiences(self, brief: Brief, result: ValidationResult):
        if not brief.audiences.remarketing_lists:
            result.add_warning(
                "NO_REMARKETING_LISTS",
                "Nessuna remarketing list definita. "
                "Retargeting e audience signal PMax saranno limitati.",
                field="audiences.remarketing_lists",
            )

        for camp_type in ["retargeting", "demand_gen"]:
            if camp_type in brief.budgets.by_campaign_type:
                if not brief.audiences.remarketing_lists:
                    result.add_error(
                        "RETARGETING_NO_AUDIENCE",
                        f"Campagna '{camp_type}' richiede almeno una remarketing list.",
                        field="audiences",
                    )
                    break

        if brief.audiences.customer_match.enabled and not brief.audiences.customer_match.list_name:
            result.add_error(
                "CUSTOMER_MATCH_NO_LIST",
                "Customer Match abilitato ma nessuna lista specificata.",
                field="audiences.customer_match",
            )

    # ── Conversions validation ────────────────────────────────────────────────

    def _validate_conversions(self, brief: Brief, result: ValidationResult):
        if not brief.objectives.conversions.primary_conversion_action:
            result.add_error(
                "NO_CONVERSION_ACTION",
                "Nessuna conversion action primaria definita. "
                "Strategia di bid smart-bidding non funzionerà.",
                field="objectives.conversions",
            )

        kpi = brief.objectives.kpi
        if not kpi.target_cpa_eur and not kpi.target_roas:
            result.add_warning(
                "NO_BID_TARGET",
                "Né tCPA né tROAS definiti. "
                "Le campagne useranno Maximize Conversions senza target.",
                field="objectives.kpi",
            )

    # ── Geo validation ────────────────────────────────────────────────────────

    def _validate_geo(self, brief: Brief, result: ValidationResult):
        geo = brief.geo_targeting
        if not geo.target_countries and not geo.target_regions and not geo.target_cities:
            result.add_error(
                "NO_GEO_TARGET",
                "Nessun geo target definito. Le campagne targetteranno tutto il mondo.",
                field="geo_targeting",
            )

    # ── Policy checks ─────────────────────────────────────────────────────────

    POLICY_FORBIDDEN_PHRASES = [
        "numero uno", "number one", "number 1", "il migliore", "the best",
        "die besten", "garantito al 100%", "100% guaranteed",
    ]

    def _validate_policy(self, brief: Brief, result: ValidationResult):
        for lang in brief.languages:
            all_texts = lang.headlines + lang.descriptions
            for sl in lang.sitelinks:
                all_texts += [sl.text, sl.description_1, sl.description_2]
            all_texts += lang.callouts

            for text in all_texts:
                text_lower = text.lower()
                for phrase in self.POLICY_FORBIDDEN_PHRASES:
                    if phrase in text_lower:
                        result.add_warning(
                            "POLICY_SUPERLATIVE",
                            f"[{lang.code}] Possibile violazione policy Google Ads — "
                            f"superlativo non verificabile: '{phrase}' in '{text[:60]}'",
                            language=lang.code,
                        )

        for constraint in brief.policy_constraints:
            result.add_info(
                "POLICY_NOTE",
                f"Vincolo policy dichiarato: {constraint}",
            )

    # ── Completeness checklist ────────────────────────────────────────────────

    def _build_completeness_checklist(self, brief: Brief, result: ValidationResult):
        result.add_check(
            "Cliente e dominio", bool(brief.client.brand_name and brief.client.domain)
        )
        result.add_check(
            "Google Ads Customer ID", bool(brief.client.google_ads_customer_id)
        )
        result.add_check(
            "Obiettivo primario", bool(brief.objectives.primary)
        )
        result.add_check(
            "Conversion action definita",
            bool(brief.objectives.conversions.primary_conversion_action),
        )
        result.add_check(
            "Budget totale > 0", brief.budgets.total_monthly_eur > 0
        )
        result.add_check(
            "Almeno una lingua", len(brief.languages) >= 1
        )
        result.add_check(
            "Geo targeting definito",
            bool(
                brief.geo_targeting.target_countries
                or brief.geo_targeting.target_cities
            ),
        )
        result.add_check(
            "Remarketing list presente",
            len(brief.audiences.remarketing_lists) > 0,
        )
        result.add_check(
            "Keyword acquisition presenti",
            brief.acquisition_keywords is not None and len(brief.acquisition_keywords) > 0,
        )
        result.add_check(
            "Hotel specifics compilati",
            bool(brief.hotel_specifics.location.address),
        )
        result.add_check(
            "UTM config presente",
            bool(brief.utm_config.source),
        )
        result.add_check(
            "Labels Blastness presenti",
            any("blastness" in l for l in brief.labels),
            detail="Almeno una label 'blastness_*' richiesta per il preset standard",
        )

        for lang in brief.languages:
            result.add_check(
                f"[{lang.code}] Headline RSA (≥3)",
                len(lang.headlines) >= 3,
            )
            result.add_check(
                f"[{lang.code}] Description RSA (≥2)",
                len(lang.descriptions) >= 2,
            )
            result.add_check(
                f"[{lang.code}] Sitelink (≥2)",
                len(lang.sitelinks) >= 2,
            )
            result.add_check(
                f"[{lang.code}] Landing page",
                bool(lang.landing_page),
            )
            result.add_check(
                f"[{lang.code}] Brand terms",
                len(lang.brand_terms) >= 1,
            )
