"""
AI-powered strategic advisor for L1 agents, TECH agents, and acquisition keyword generation.

Provides intelligence beyond hardcoded rules:
  - optimize_brief_budget_ai      — apply AI-recommended budget split BEFORE generation
  - analyze_budget_strategy_ai    — residual AI insights on budget distribution
  - analyze_bidding_strategy_ai   — AI insights on bid strategy coherence (with suggested_fix)
  - analyze_negative_keywords_ai  — AI-generated negative keyword suggestions
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
    """Parse a JSON array of issue dicts into ValidationIssue objects.

    Each dict may optionally include a 'suggested_fix' key with:
      {brief_path, value, action, label}
    """
    try:
        items = json.loads(_extract_json_array(raw))
        issues = []
        for d in items:
            if not isinstance(d, dict) or not d.get("message"):
                continue
            fix = d.get("suggested_fix")
            # Validate fix structure — discard malformed fixes
            if fix and not (isinstance(fix, dict) and fix.get("brief_path") and fix.get("label")):
                fix = None
            issues.append(ValidationIssue(
                code=d.get("code", f"{agent_name.upper().replace(' ', '_')}_AI_ISSUE"),
                message=d.get("message", ""),
                level=d.get("level", "warning"),
                blocks_publish=False,
                agent=f"{agent_name} (AI)",
                suggested_fix=fix,
            ))
        return issues
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


# ── Budget Pre-optimization ───────────────────────────────────────────────────

async def optimize_brief_budget_ai(brief: "Brief", api_key: str) -> "tuple[Brief, bool]":
    """
    Apply AI-recommended budget allocation to the brief BEFORE campaign generation.

    Calls Claude directly (not the static _BASE_WEIGHTS path) to get optimal split
    percentages for the active campaign types, then rebuilds budgets.by_campaign_type.

    Returns (modified_brief, True) when the allocation was changed,
    (original_brief, False) on any error or if no valid split was returned.
    This flag lets the orchestrator skip the residual budget advisor step.
    """
    import anthropic
    from app.domain.schemas.brief import BudgetByLanguage

    total = brief.budgets.total_monthly_eur
    if total <= 0:
        return brief, False

    lang_codes = [lang.code for lang in brief.languages]
    n_langs = max(len(lang_codes), 1)
    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars

    # Determine active budget keys from the existing by_campaign_type mapping,
    # or derive them from the campaign_types enum list in the brief.
    if brief.budgets.by_campaign_type:
        active_keys = list(brief.budgets.by_campaign_type.keys())
    else:
        _enum_to_keys: Dict[str, List[str]] = {
            "search": ["search_brand", "search_acquisition"],
            "performance_max": ["performance_max"],
            "display": ["retargeting"],
            "demand_gen": ["demand_gen"],
        }
        active_keys = []
        for ct in brief.campaign_types:
            for k in _enum_to_keys.get(ct.value, []):
                if k not in active_keys:
                    active_keys.append(k)

    if not active_keys:
        return brief, False

    keys_json = "{" + ", ".join(f'"{k}": <intero>' for k in active_keys) + "}"
    existing_pcts = {
        k: round(v.total / total * 100, 1)
        for k, v in brief.budgets.by_campaign_type.items()
    } if brief.budgets.by_campaign_type else {}
    existing_str = (
        ", ".join(f"{k}: {p:.1f}%" for k, p in existing_pcts.items())
        if existing_pcts else "non definita"
    )

    prompt = f"""Sei un esperto Google Ads per l'hospitality. Definisci la distribuzione percentuale ottimale del budget mensile tra i tipi di campagna per questo hotel.

PROFILO: {hotel_cat} {stars}★ — Budget totale €{total:.0f}/mese
TIPI ATTIVI: {', '.join(active_keys)}
DISTRIBUZIONE ATTUALE: {existing_str}

Rispondi SOLO con JSON object (percentuali intere che sommano a 100):
{keys_json}

Linee guida:
- search_brand: difesa branded (min 18-22% per hotel con concorrenza alta)
- search_acquisition: acquisizione nuovi clienti (peso principale)
- performance_max: per hotel con buone immagini/video
- retargeting: solo se traffico esistente sufficiente
- demand_gen: solo con budget >€2000/mese totale

SOLO JSON, nessun testo aggiuntivo."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=200,
            system=combined_skills(BUDGET_SCENARIO_PLANNER),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Extract JSON object from Claude response
        m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if not m:
            logger.warning(f"AI budget optimization: no JSON object in response: {raw[:120]}")
            return brief, False

        split_dict = json.loads(m.group(0))

        # Keep only active keys with numeric values
        validated = {
            k: float(v) for k, v in split_dict.items()
            if k in active_keys and isinstance(v, (int, float)) and v > 0
        }
        if not validated:
            logger.warning("AI budget optimization: no valid active keys in response")
            return brief, False

        # Normalize so percentages sum to exactly 100
        total_pct = sum(validated.values())
        normalized = {k: v / total_pct * 100 for k, v in validated.items()}

        new_by_type: dict = {}
        for type_key, pct in normalized.items():
            monthly_for_type = round(total * pct / 100, 2)
            per_lang = round(monthly_for_type / n_langs, 2)
            new_by_type[type_key] = BudgetByLanguage(
                total=monthly_for_type,
                by_language={lang: per_lang for lang in lang_codes},
            )

        # Merge: AI allocation wins for recommended types
        merged = dict(brief.budgets.by_campaign_type)
        merged.update(new_by_type)

        new_budgets = brief.budgets.model_copy(update={"by_campaign_type": merged})
        optimized = brief.model_copy(update={"budgets": new_budgets})

        changed = [f"{k}: €{v.total:.0f} ({normalized[k]:.0f}%)" for k, v in new_by_type.items()]
        logger.info(
            f"AI budget pre-optimization (direct Claude) applied — "
            f"total €{total:.0f} → {', '.join(changed)}"
        )
        return optimized, True

    except Exception as exc:
        logger.warning(f"AI budget pre-optimization failed (using existing): {exc}")
        return brief, False


# ── Bidding KPI Pre-optimization ─────────────────────────────────────────────

async def optimize_brief_kpi_ai(brief: "Brief", api_key: str) -> "tuple[Brief, bool]":
    """
    Pre-optimize KPI targets (Target CPA / Target ROAS) BEFORE campaign generation.

    Runs in Step 0 alongside the budget optimizer.  It fires only when the
    current CPA is inconsistent with the monthly budget (expected conversions
    budget/CPA < MIN_CONVERSIONS_THRESHOLD), indicating the bid strategy will
    not have enough conversion signal to work properly.

    Returns (modified_brief, True) when KPIs were updated,
    (original_brief, False) otherwise.
    The flag lets the orchestrator skip analyze_bidding_strategy_ai() so no
    retroactive bidding warnings appear after the correction.
    """
    import anthropic

    MIN_CONVERSIONS = 20  # Below this the algorithm under-optimises

    kpi = brief.objectives.kpi
    total = brief.budgets.total_monthly_eur
    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    primary_obj = brief.objectives.primary.value

    # Only act when there is a CPA target and the expected volume is too low
    if not kpi.target_cpa_eur or total <= 0:
        return brief, False

    expected_conversions = total / kpi.target_cpa_eur
    if expected_conversions >= MIN_CONVERSIONS:
        return brief, False  # KPIs already consistent — nothing to pre-fix

    kpi_lines = [f"Target CPA: €{kpi.target_cpa_eur:.2f}"]
    if kpi.target_roas:
        kpi_lines.append(f"Target ROAS: {kpi.target_roas:.1f}x")

    prompt = f"""Sei un esperto di bid strategy Google Ads per l'hospitality.

PROFILO: {hotel_cat} {stars}★ — Budget €{total:.0f}/mese — Obiettivo: {primary_obj}
KPI ATTUALI: {', '.join(kpi_lines)}
PROBLEMA: Con questo budget e Target CPA attuale si stimano solo ~{expected_conversions:.0f} conversioni/mese.
Per ottimizzare Target CPA servono ≥{MIN_CONVERSIONS} conversioni/mese.

Rispondi SOLO con JSON con il valore CPA corretto (intero euro):
{{"target_cpa_eur": <intero>}}

Considera: ADR tipico per {hotel_cat} {stars}★, CPC medio hospitality, CTR atteso.
Il nuovo CPA deve garantire ≥{MIN_CONVERSIONS} conversioni/mese con budget €{total:.0f}.
SOLO JSON, nessun testo aggiuntivo."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=100,
            system=combined_skills(BID_STRATEGY_RECOMMENDATIONS),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if not m:
            logger.warning(f"AI KPI optimization: no JSON in response: {raw[:100]}")
            return brief, False

        kpi_dict = json.loads(m.group(0))
        new_cpa = kpi_dict.get("target_cpa_eur")
        if not isinstance(new_cpa, (int, float)) or new_cpa <= 0:
            return brief, False

        new_cpa_f = float(new_cpa)
        # Sanity cap: new CPA must be higher than current and not absurdly large
        if new_cpa_f <= kpi.target_cpa_eur or new_cpa_f > 500:
            return brief, False

        new_kpi = kpi.model_copy(update={"target_cpa_eur": new_cpa_f})
        new_objectives = brief.objectives.model_copy(update={"kpi": new_kpi})
        optimized = brief.model_copy(update={"objectives": new_objectives})

        logger.info(
            f"AI KPI pre-optimization: Target CPA €{kpi.target_cpa_eur:.0f} → "
            f"€{new_cpa_f:.0f} (budget €{total:.0f}, "
            f"expected {total/new_cpa_f:.0f} conversions/month)"
        )
        return optimized, True

    except Exception as exc:
        logger.warning(f"AI KPI pre-optimization failed: {exc}")
        return brief, False




async def analyze_budget_strategy_ai(
    brief: "Brief",
    api_key: str,
) -> List[ValidationIssue]:
    """
    Residual AI analysis of budget distribution after pre-optimization.
    Catches issues that the split alone cannot fix (e.g. total too low for
    the chosen strategy, missing campaign types for the hotel category).
    Returns up to 2 warning/info ValidationIssue objects.
    """
    import anthropic

    total = brief.budgets.total_monthly_eur
    if total <= 0:
        return []

    by_type = brief.budgets.by_campaign_type
    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    campaign_types = [ct.value for ct in brief.campaign_types]

    distribution_lines = [
        f"- {ct}: €{b.total:.0f}/mese ({b.total / total * 100:.1f}%)"
        for ct, b in by_type.items()
    ]
    distribution_str = (
        "\n".join(distribution_lines)
        if distribution_lines
        else "Non specificata"
    )

    prompt = f"""Sei un esperto Google Ads per hotel. Il budget è già stato ottimizzato automaticamente.
Individua SOLO problemi strutturali residui che la redistribuzione automatica non può risolvere.

PROFILO: {hotel_cat} {stars}★ — Budget €{total:.0f}/mese
DISTRIBUZIONE ATTUALE:
{distribution_str}
CAMPAGNE: {', '.join(campaign_types)}

Esempi di problemi residui rilevanti:
- Budget totale troppo basso per supportare tutte le campagne scelte (<€300)
- Mancanza di una campagna critica per questa categoria hotel
- Combinazione di campagne incompatibile con il profilo

NON segnalare: problemi già gestiti dalla redistribuzione automatica.

Rispondi SOLO con JSON array (preferibilmente [] se non ci sono problemi reali):
[{{"code": "BUDGET_...", "message": "...", "level": "warning"}}]
- Max 2 issue, solo problemi strutturali ad alto impatto"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=400,
            system=combined_skills(BUDGET_SCENARIO_PLANNER, CORE_PPC_FRAMEWORK),
            messages=[{"role": "user", "content": prompt}],
        )
        issues = _parse_issues(response.content[0].text.strip(), "BudgetStrategistAgent")
        if issues:
            logger.info(f"BudgetStrategistAgent AI (residual): {len(issues)} insight(s)")
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
    AI analysis of bid strategy configuration with actionable suggested_fix.

    Each issue may include a suggested_fix dict that the frontend renders
    as a 'Applica' CTA button to patch the brief directly.
    Allowed brief_path values for fixes: objectives.kpi.target_cpa_eur,
    objectives.kpi.target_roas, objectives.kpi.max_cpc_brand,
    objectives.kpi.max_cpc_acquisition.
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
        else "- Nessun target KPI (uso Maximize Conversions di default)"
    )

    prompt = f"""Sei un esperto di bid strategy Google Ads per l'hospitality.
Analizza la configurazione KPI e suggerisci correzioni concrete.

PROFILO: {hotel_cat} {stars}★ — Budget €{total:.0f}/mese
Obiettivo: {primary_obj}
Campagne: {', '.join(campaign_types)}

KPI CONFIGURATI:
{kpi_str}

Identifica problemi di bid strategy e per ciascuno proponi un valore corretto.
Considera: volume di conversioni atteso con questo budget, tipicità per categoria hotel,
coerenza tra obiettivo e strategia.

NON segnalare: target CPA+ROAS contemporanei, ROAS >10x, ROAS <1.5x, CPA <€5 (già gestiti).

Rispondi SOLO con JSON array ([] se tutto è corretto):
[{{
  "code": "BIDDING_...",
  "message": "Spiegazione del problema e del valore consigliato.",
  "level": "warning",
  "suggested_fix": {{
    "brief_path": "objectives.kpi.target_cpa_eur",
    "value": 60,
    "action": "set",
    "label": "Imposta Target CPA a €60"
  }}
}}]

Per suggested_fix usa SOLO questi brief_path:
- "objectives.kpi.target_cpa_eur"   (float, euro)
- "objectives.kpi.target_roas"      (float, es. 5.0)
- "objectives.kpi.max_cpc_brand"    (float, euro)
- "objectives.kpi.max_cpc_acquisition" (float, euro)

Se non c'è un fix applicabile lascia suggested_fix a null.
Max 3 issue ad alto impatto, messaggi in italiano."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=700,
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
    AI analysis of negative keyword gaps based on hotel profile and generated keywords.
    Returns informational issues with a suggested_fix to append specific
    negative keywords to the brief's acquisition_keywords for each language.
    """
    import anthropic

    hotel_cat = brief.hotel_specifics.category.value
    stars = brief.hotel_specifics.stars
    services = brief.hotel_specifics.services

    acq_keywords: List[str] = []
    for c in campaigns:
        if c.campaign_subtype == "Acquisition":
            for ag in c.ad_groups:
                for kw in ag.keywords:
                    if not kw.is_negative and kw.text not in acq_keywords:
                        acq_keywords.append(kw.text)

    if not acq_keywords:
        return []

    # Collect all lang codes that have acquisition campaigns
    acq_lang_codes = list({
        c.language_code for c in campaigns if c.campaign_subtype == "Acquisition"
    })
    primary_lang = acq_lang_codes[0] if acq_lang_codes else "IT"

    brand_terms: List[str] = []
    for lang in brief.languages:
        brand_terms.extend(lang.brand_terms)

    acq_sample = acq_keywords[:25]
    services_str = ", ".join(services[:8]) if services else "non specificati"
    brand_str = ", ".join(list(dict.fromkeys(brand_terms))[:5]) if brand_terms else "n/a"

    prompt = f"""Sei un esperto Google Ads specializzato in keyword negative per hotel.

PROFILO: {hotel_cat} {stars}★
Servizi: {services_str}
Brand terms (già negative): {brand_str}

KEYWORD ACQUISIZIONE (campione):
{chr(10).join(f"- {kw}" for kw in acq_sample)}

Suggerisci keyword negative specifiche mancanti per questa tipologia hotel.
Esempi per categoria:
- {stars}★ resort: "ostello", "hostel", "low cost", "economico", "monolocale"
- Business hotel: "vacanza", "spiaggia", "mare" (se non pertinente)
- Boutique: "catena", "franchising", "standardizzato"
Rileva anche cannibalizzazione tra temi keyword.

Per ogni issue includi suggested_fix con le keyword negative esatte da aggiungere.
Il brief_path deve essere: "acquisition_keywords.{primary_lang}.negative_keywords"

Rispondi SOLO con JSON array ([] se nessun problema):
[{{
  "code": "NEG_AI_...",
  "message": "Descrizione del problema con le keyword specifiche.",
  "level": "info",
  "suggested_fix": {{
    "brief_path": "acquisition_keywords.{primary_lang}.negative_keywords",
    "value": ["kw1", "kw2", "kw3"],
    "action": "append_list",
    "label": "Aggiungi keyword negative"
  }}
}}]
Max 2 issue, messaggi in italiano."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=600,
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
    Uses ClaudeEnricher.suggest_keywords() and returns {lang_code: KeywordThemes}
    ready to merge into the brief before generators run.
    Falls back to empty dict on any error.
    """
    from app.connectors.claude_enricher import ClaudeEnricher
    from app.domain.schemas.brief import KeywordThemes

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
