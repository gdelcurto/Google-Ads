"""
AI-powered strategic advisor for L1 agents, TECH agents, and acquisition keyword generation.

Provides intelligence beyond hardcoded rules:
  - analyze_budget_strategy_ai   — AI insights on budget distribution
  - analyze_bidding_strategy_ai  — AI insights on bid strategy coherence
  - analyze_negative_keywords_ai — AI-generated negative keyword suggestions
  - generate_acquisition_keywords_ai — AI keyword themes when brief has none
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Dict, List, Optional

from app.agents.base import ValidationIssue
from app.skills import (
    combined_skills,
    BID_STRATEGY_RECOMMENDATIONS, BUDGET_SCENARIO_PLANNER,
    CORE_PPC_FRAMEWORK, KEYWORD_CANNIBALIZATION, SEARCH_TERM_MINING,
)

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief, KeywordThemes
    from app.domain.schemas.campaign_plan import CampaignPlan

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _extract_json_array(raw: str) -> str:
    """Extract the first [...] block from a Claude response."""
    m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
    if m:
        return m.group(1)
    start, end = raw.find('['), raw.rfind(']')
    if start != -1 and end != -1:
        return raw[start:end + 1]
    return "[]"


def _parse_issues(raw: str, agent_name: str) -> List[ValidationIssue]:
    """Parse a JSON array of issue dicts into ValidationIssue objects."""
    try:
        items = json.loads(_extract_json_array(raw))
        return [
            ValidationIssue(
                code=d.get("code", f"{agent_name.upper().replace(' ', '_')}_AI_ISSUE"),
                message=d.get("message", ""),
                level=d.get("level", "warning"),
                blocks_publish=False,
                agent=f"{agent_name} (AI)",
            )
            for d in items
            if isinstance(d, dict) and d.get("message")
        ]
    except Exception as exc:
        logger.warning(f"Failed to parse AI issues from {agent_name}: {exc}")
        return []


def _parse_keyword_themes_text(text: str) -> Dict[str, List[str]]:
    """Parse 'theme: kw1, kw2\\n...' text into a dict of {theme: [keywords]}."""
    themes: Dict[str, List[str]] = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        colon = line.find(':')
        if colon == -1:
            continue
        theme_name = line[:colon].strip()
        keywords = [k.strip() for k in line[colon + 1:].split(',') if k.strip()]
        if theme_name and keywords:
            themes[theme_name] = keywords
    return themes


# ── Budget Strategist AI ──────────────────────────────────────────────────────

async def analyze_budget_strategy_ai(
    brief: "Brief",
    api_key: str,
) -> List[ValidationIssue]:
    """
    AI analysis of budget distribution beyond hardcoded BudgetStrategistAgent rules.
    Detects strategic issues specific to the hotel category and campaign mix.
    Returns up to 3 warning/info ValidationIssue objects.
    """
    import anthropic

    total = brief.budgets.total_monthly_eur
    if total <= 0:
        return []  # Already blocked by hardcoded rule

    by_type = brief.budgets.by_campaign_type
    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    services = brief.hotel_specifics.services
    campaign_types = [ct.value for ct in brief.campaign_types]

    distribution_lines = [
        f"- {ct}: €{b.total:.0f}/mese ({b.total / total * 100:.1f}%)"
        for ct, b in by_type.items()
    ]
    distribution_str = (
        "\n".join(distribution_lines)
        if distribution_lines
        else "Non specificata (distribuzione automatica)"
    )
    services_str = ", ".join(services[:10]) if services else "non specificati"

    prompt = f"""Sei un esperto Google Ads specializzato in hotel e hospitality.
Analizza la configurazione del budget di questo account Google Ads.

PROFILO HOTEL:
- Categoria: {hotel_cat}
- Stelle: {stars}
- Servizi principali: {services_str}
- Budget mensile totale: €{total:.0f}

DISTRIBUZIONE BUDGET PER TIPO:
{distribution_str}

CAMPAGNE CONFIGURATE: {', '.join(campaign_types)}

Identifica problemi strategici avanzati che regole meccaniche non possono rilevare:
- Distribuzione non ottimale per questo tipo di hotel (es. troppo poco a Brand per un resort stagionale)
- Budget insufficiente per il learning period di campagne Smart Bidding (min ~€10/giorno per PMax)
- Rischio di cannibalizzazione Brand ↔ Acquisition per questa distribuzione
- Dipendenze critiche tra tipi di campagna con budget squilibrato

NON segnalare: budget zero, discrepanza totale vs allocato, budget < €500 (già gestiti).

Rispondi SOLO con JSON array ([] se nessun issue rilevante):
[{{"code": "BUDGET_...", "message": "...", "level": "warning"}}]
- level: "warning" o "info"
- max 3 issue ad alto impatto pratico
- messaggi in italiano, concreti e actionable"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=600,
            system=combined_skills(BUDGET_SCENARIO_PLANNER, CORE_PPC_FRAMEWORK),
            messages=[{"role": "user", "content": prompt}],
        )
        issues = _parse_issues(response.content[0].text.strip(), "BudgetStrategistAgent")
        if issues:
            logger.info(f"BudgetStrategistAgent AI: {len(issues)} insight(s)")
        return issues
    except Exception as exc:
        logger.warning(f"Budget strategy AI analysis failed: {exc}")
        return []


# ── Bidding Strategist AI ─────────────────────────────────────────────────────

async def analyze_bidding_strategy_ai(
    brief: "Brief",
    api_key: str,
) -> List[ValidationIssue]:
    """
    AI analysis of bid strategy configuration beyond hardcoded BiddingStrategistAgent rules.
    Checks coherence between objectives, KPI targets, budget, and hotel category.
    Returns up to 3 warning/info ValidationIssue objects.
    """
    import anthropic

    kpi = brief.objectives.kpi
    total = brief.budgets.total_monthly_eur
    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    primary_obj = brief.objectives.primary.value
    campaign_types = [ct.value for ct in brief.campaign_types]

    kpi_lines = []
    if kpi.target_cpa_eur:
        kpi_lines.append(f"- Target CPA: €{kpi.target_cpa_eur:.2f}")
    if kpi.target_roas:
        kpi_lines.append(f"- Target ROAS: {kpi.target_roas:.1f}x")
    if kpi.max_cpc_brand:
        kpi_lines.append(f"- Max CPC Brand: €{kpi.max_cpc_brand:.2f}")
    if kpi.max_cpc_acquisition:
        kpi_lines.append(f"- Max CPC Acquisition: €{kpi.max_cpc_acquisition:.2f}")
    kpi_str = (
        "\n".join(kpi_lines)
        if kpi_lines
        else "- Nessun target KPI configurato (uso Maximize Conversions di default)"
    )

    prompt = f"""Sei un esperto di bid strategy Google Ads per il settore hospitality.
Analizza la configurazione delle bid strategy per questo account.

PROFILO HOTEL:
- Categoria: {hotel_cat}
- Stelle: {stars}
- Budget mensile totale: €{total:.0f}
- Obiettivo primario: {primary_obj}
- Campagne: {', '.join(campaign_types)}

CONFIGURAZIONE KPI / BID STRATEGY:
{kpi_str}

Identifica problemi strategici avanzati:
- Coerenza tra obiettivo ({primary_obj}) e bid strategy configurata
- Adeguatezza del budget €{total:.0f}/mese per raggiungere i KPI target
- Rischi specifici per questa categoria hotel (es. resort stagionale vs city hotel)
- Configurazioni mancanti importanti (es. nessun max_cpc con budget limitato)
- Raccomandazioni su quale strategia adottare se KPI non sono impostati

NON segnalare: target CPA+ROAS contemporanei, ROAS >10x, ROAS <1.5x, CPA <€5 (già gestiti).

Rispondi SOLO con JSON array ([] se nessun issue):
[{{"code": "BIDDING_...", "message": "...", "level": "warning"}}]
- level: "warning" o "info"
- max 3 issue ad alto impatto
- messaggi in italiano, concreti e actionable"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=600,
            system=combined_skills(BID_STRATEGY_RECOMMENDATIONS, CORE_PPC_FRAMEWORK),
            messages=[{"role": "user", "content": prompt}],
        )
        issues = _parse_issues(response.content[0].text.strip(), "BiddingStrategistAgent")
        if issues:
            logger.info(f"BiddingStrategistAgent AI: {len(issues)} insight(s)")
        return issues
    except Exception as exc:
        logger.warning(f"Bidding strategy AI analysis failed: {exc}")
        return []


# ── Negative Keywords AI ──────────────────────────────────────────────────────

async def analyze_negative_keywords_ai(
    brief: "Brief",
    campaigns: List["CampaignPlan"],
    api_key: str,
) -> List[ValidationIssue]:
    """
    AI analysis of the negative keyword strategy.
    Extracts acquisition keywords from generated campaigns, then asks Claude to:
    - Suggest specific negatives missing for this hotel type/category
    - Flag cannibalization risks between keyword themes
    Returns up to 4 warning/info ValidationIssue objects.
    """
    import anthropic

    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    services = brief.hotel_specifics.services

    # Collect positive acquisition keywords from generated campaigns
    acq_keywords: List[str] = []
    for c in campaigns:
        if c.campaign_subtype == "Acquisition":
            for ag in c.ad_groups:
                for kw in ag.keywords:
                    if not kw.is_negative and kw.text not in acq_keywords:
                        acq_keywords.append(kw.text)

    if not acq_keywords:
        return []

    brand_terms: List[str] = []
    for lang in brief.languages:
        brand_terms.extend(lang.brand_terms)

    acq_sample = acq_keywords[:30]
    services_str = ", ".join(services[:8]) if services else "non specificati"
    brand_str = ", ".join(list(dict.fromkeys(brand_terms))[:5]) if brand_terms else "non specificati"

    prompt = f"""Sei un esperto Google Ads specializzato in keyword negative per il settore hotel.
Analizza le keyword di acquisizione di questo account e suggerisci ottimizzazioni.

PROFILO HOTEL:
- Categoria: {hotel_cat}
- Stelle: {stars}
- Servizi: {services_str}
- Brand terms (già in negative list): {brand_str}

KEYWORD ACQUISIZIONE GENERATE:
{chr(10).join(f"- {kw}" for kw in acq_sample)}

Il tuo compito:
1. Identifica keyword negative SPECIFICHE mancanti per questa categoria hotel
   Es. hotel 5 stelle → "ostello", "hostel", "low cost", "economico", "dormitorio"
   Es. resort → "day use" se non pertinente, "monolocale", "affitto"
   Es. boutique → "catena", "franchising", "standard"
2. Rileva rischi di cannibalizzazione tra i temi keyword generati
3. Segnala query ambigue che potrebbero attrarre traffico irrilevante

Rispondi SOLO con JSON array ([] se non hai suggerimenti ad alto impatto):
[{{"code": "NEG_...", "message": "...", "level": "warning"}}]
- code: usa prefisso NEG_AI_
- level: "warning" o "info"
- max 4 issue
- messaggi in italiano con le keyword negative specifiche suggerite"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=700,
            system=combined_skills(KEYWORD_CANNIBALIZATION, SEARCH_TERM_MINING),
            messages=[{"role": "user", "content": prompt}],
        )
        issues = _parse_issues(response.content[0].text.strip(), "NegativeArchitectAgent")
        if issues:
            logger.info(f"NegativeArchitectAgent AI: {len(issues)} insight(s)")
        return issues
    except Exception as exc:
        logger.warning(f"Negative keywords AI analysis failed: {exc}")
        return []


# ── Acquisition Keyword AI Generation ────────────────────────────────────────

async def generate_acquisition_keywords_ai(
    brief: "Brief",
    api_key: str,
) -> Dict[str, "KeywordThemes"]:
    """
    Generate acquisition keyword themes via AI for languages that have none in the brief.
    Uses the existing ClaudeEnricher.suggest_keywords() pipeline.

    Returns a dict {lang_code: KeywordThemes} ready to be merged into the brief
    before passing it to the rule-based generators.  Falls back gracefully to an
    empty dict if the API call fails or if all languages already have themes.
    """
    from app.connectors.claude_enricher import ClaudeEnricher
    from app.domain.schemas.brief import KeywordThemes

    # Find languages that have no acquisition keyword themes
    missing_langs = []
    for lang in brief.languages:
        has_themes = (
            brief.acquisition_keywords
            and lang.code in brief.acquisition_keywords
            and bool(brief.acquisition_keywords[lang.code].themes)
        )
        if not has_themes:
            missing_langs.append(lang)

    if not missing_langs:
        return {}

    enricher = ClaudeEnricher(api_key)
    result: Dict[str, KeywordThemes] = {}

    for lang in missing_langs:
        payload = {
            "brand_name": brief.client.brand_name,
            "hotel_category": brief.hotel_specifics.category.value,
            "stars": brief.hotel_specifics.stars,
            "domain": brief.client.domain,
            "services": brief.hotel_specifics.services,
            "strengths": brief.hotel_specifics.strengths,
            "language_code": lang.code,
        }
        try:
            kw_result, _ = await enricher.suggest_keywords(payload)
            themes = _parse_keyword_themes_text(kw_result.get("kw_themes_text", ""))
            neg_text = kw_result.get("kw_negative_text", "")
            negatives = [k.strip() for k in neg_text.split('\n') if k.strip()]
            if themes:
                result[lang.code] = KeywordThemes(
                    themes=themes,
                    negative_keywords=negatives,
                )
                logger.info(
                    f"AI generated {len(themes)} keyword themes for {lang.code}: "
                    f"{list(themes.keys())}"
                )
            else:
                logger.warning(f"AI keyword generation returned empty themes for {lang.code}")
        except Exception as exc:
            logger.warning(f"AI keyword generation failed for {lang.code}: {exc}")

    return result
