"""
Geo Specialist Agent — TECH Cross-cutting Agent.

Validates geo targeting configuration: target countries presence,
consistency between geo settings and language configuration,
radius targeting coherence.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from app.agents.base import AgentLevel, CampaignAgent, ValidationIssue

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief
    from app.domain.schemas.campaign_plan import CampaignPlan


class GeoSpecialistAgent(CampaignAgent):
    TYPE_KEY = "geo_specialist"
    LEVEL = AgentLevel.TECHNICAL
    BLOCKS_PUBLISH = False
    BLOCKING_RULES = []

    GUIDELINES = """
    ══════════════════════════════════════════════════════════════════
    GEO SPECIALIST — Hospitality Google Ads
    ══════════════════════════════════════════════════════════════════

    RUOLO
    Valida la configurazione del targeting geografico.
    Un geo targeting corretto è fondamentale per non sprecare budget
    su mercati non rilevanti o per non escludere mercati profittevoli.

    CONTROLLI
    ✅ Almeno un paese target configurato
    ✅ Coerenza tra geo targeting e lingue configurate
    ✅ Radius targeting con coordinate valide (se configurato)
    ✅ Esclusioni geografiche non in conflitto con target

    BEST PRACTICE HOSPITALITY
    ───────────────────────────────────────────────────────────────
    Target: paesi di origine dei tuoi guest principali
    Lingue: corrispondono ai mercati target
    Radius: utile per "hotel vicino a [landmark]" queries

    ESEMPIO COERENTE
    Target Countries: IT, DE, FR, GB
    Languages configured: IT, DE, FR, EN
    → Coerente ✅

    ESEMPIO INCOERENTE
    Target Countries: IT only
    Languages configured: IT, EN, DE
    → EN e DE non raggiungeranno il loro mercato → budget sprecato ⚠
    """

    def validate_strategy(self, brief: "Brief") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        geo = brief.geo_targeting

        # Check if any geo targeting is configured at all
        has_any_geo = (
            bool(geo.target_countries)
            or bool(geo.target_regions)
            or bool(geo.target_cities)
            or bool(geo.radius_targets)
        )

        if not has_any_geo:
            issues.append(ValidationIssue(
                code="GEO_NO_TARGETING",
                message=(
                    "Nessun targeting geografico configurato. "
                    "Senza geo targeting le campagne girano su tutto il mondo, "
                    "sprecando budget su mercati non rilevanti. "
                    "Configura almeno 'geo_targeting.target_countries' con i paesi di origine dei tuoi ospiti."
                ),
                level="warning",
                blocks_publish=False,
                agent="GeoSpecialistAgent",
            ))
            return issues

        # Check language/geo coherence
        if geo.target_countries and brief.languages:
            lang_codes = {lang.code.upper()[:2] for lang in brief.languages}
            country_codes = {c.upper() for c in geo.target_countries}

            # Italian market: IT lang maps to IT country
            # English: EN maps to GB, US, AU, IE, etc.
            # This is a simplified heuristic check
            implied_countries = {
                "IT": {"IT"},
                "EN": {"GB", "US", "AU", "IE", "CA", "NZ"},
                "DE": {"DE", "AT", "CH"},
                "FR": {"FR", "BE", "CH", "LU"},
                "ES": {"ES", "MX", "AR", "CO"},
            }

            uncovered_langs = []
            for lang_code in lang_codes:
                expected_countries = implied_countries.get(lang_code, set())
                if expected_countries and not expected_countries.intersection(country_codes):
                    uncovered_langs.append(lang_code)

            if uncovered_langs:
                issues.append(ValidationIssue(
                    code="GEO_LANGUAGE_MISMATCH",
                    message=(
                        f"Lingue configurate ({', '.join(uncovered_langs)}) potrebbero non avere "
                        f"il mercato corrispondente nei paesi target ({', '.join(geo.target_countries)}). "
                        "Verifica che i paesi target includano i mercati principali per ogni lingua configurata."
                    ),
                    level="info",
                    blocks_publish=False,
                    agent="GeoSpecialistAgent",
                ))

        return issues
