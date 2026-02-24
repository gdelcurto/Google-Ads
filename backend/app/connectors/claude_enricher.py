"""
Anthropic Claude API enrichment for hotel briefs.

Provides ClaudeEnricher with:
    enrich_brief(scraped, langs)                  -> (data_dict, api_log_entry)
    suggest_sitelinks(common, lang_code, landing) -> (list[sitelink], api_log_entry)
    suggest_type_copy(common, lang_code, usp, ct) -> (dict, api_log_entry)
    suggest_keywords(payload)                     -> (dict, api_log_entry)
    suggest_budget_strategy(payload)              -> BudgetStrategyResponse

Also exports the standalone background-task runner:
    run_autofill_job(job_id, url, langs, content, api_key, update_status)
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_ROME = ZoneInfo("Europe/Rome")
from typing import Callable, Dict, List, Optional

from app.connectors.web_scraper import (
    LANG_IDS, LANG_NAMES, ScrapedSite, scan_entry, _score_sitemap_url,
)
from app.skills import (
    combined_skills, load_skill,
    AD_COPY_VARIANT_GENERATOR, AD_EXTENSION_AUDIT,
    BID_STRATEGY_RECOMMENDATIONS, BUDGET_SCENARIO_PLANNER,
    GOOGLE_ADS_AUDIT, KEYWORD_CANNIBALIZATION,
    QUALITY_SCORE_BREAKDOWN, SEARCH_TERM_MINING,
)

logger = logging.getLogger(__name__)

# ── Model pricing ─────────────────────────────────────────────────────────────

_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80,  4.00),
    "claude-sonnet-4-6":         (3.00, 15.00),
}


def _api_log_entry(agent: str, reason: str, endpoint: str, model: str, usage) -> dict:
    """Build a structured API call log entry from a Claude API call's usage metadata."""
    in_p, out_p = _MODEL_PRICING.get(model, (1.0, 5.0))
    cost_usd = (usage.input_tokens * in_p + usage.output_tokens * out_p) / 1_000_000
    return {
        "ts":            datetime.now(_TZ_ROME).isoformat(),
        "agent":         agent,
        "reason":        reason,
        "endpoint":      endpoint,
        "model":         model,
        "input_tokens":  usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd":      round(cost_usd, 6),
    }


# ── Text helpers ──────────────────────────────────────────────────────────────

def _trim_to_word(text: str, max_chars: int) -> str:
    """Trim sitelink text to max_chars at word boundary (sitelinks only)."""
    text = text.rstrip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    space = cut.rfind(' ')
    return cut[:space] if space > 0 else cut


def _filter_by_limit(items: list, max_chars: int) -> list:
    """Discard items exceeding char limit instead of truncating them."""
    return [s for s in items if isinstance(s, str) and len(s.rstrip()) <= max_chars]


def _truncate_to_limit(items: list, max_chars: int) -> list:
    """Keep items within max_chars, truncating at word boundary instead of discarding.

    Preferred over _filter_by_limit when we need to guarantee at least some
    output even if the LLM generates slightly-over-limit text.
    """
    result = []
    for s in items:
        if not isinstance(s, str) or not s.strip():
            continue
        s = s.strip()
        if len(s) <= max_chars:
            result.append(s)
        else:
            cut = s[:max_chars].rstrip()
            space = cut.rfind(' ')
            if space > max_chars // 2:
                cut = cut[:space]
            result.append(cut)
    return result


def _truncate_assets(data: dict) -> dict:
    """Post-process: discard over-limit headlines/descriptions, trim sitelinks.

    USP principale is informational (not a Google Ads asset) — never discarded.
    """
    for lang in data.get('languages', []):
        lang['headlines']    = _filter_by_limit(lang.get('headlines', []), 30)
        lang['descriptions'] = _filter_by_limit(lang.get('descriptions', []), 90)[:4]
        lang['callouts']     = _filter_by_limit(lang.get('callouts', []), 25)
        # usp_main is informational context, not a Google Ads asset — leave as-is
    return data


def _extract_json_object(raw: str) -> str:
    """
    Extract the outermost {...} block from a Claude response, stripping ```json fences.

    Uses rfind('}') to find the outer closing brace so nested objects are preserved.
    The greedy approach (start + rfind) is more reliable than a non-greedy regex which
    would stop at the first } it finds (e.g. the closing brace of a nested object).
    """
    # Strip ```json ... ``` fences if present, then extract normally
    fence = re.search(r'```(?:json)?\s*(\{.*\})\s*```', raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    start, end = raw.find('{'), raw.rfind('}')
    if start != -1 and end != -1:
        return raw[start:end + 1]
    return raw


def _extract_json_array(raw: str) -> str:
    """Extract the first [...] block from a Claude response."""
    m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
    if m:
        return m.group(1)
    start, end = raw.find('['), raw.rfind(']')
    if start != -1 and end != -1:
        return raw[start:end + 1]
    return raw


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT_HOTEL_CORE = """\
Sei un copywriter Google Ads certificato, specializzato in hotel e hospitality da oltre 10 anni.
Conosci a fondo la psicologia del viaggiatore, le dinamiche del funnel alberghiero e le best
practice RSA per battere le OTA (Booking, Expedia) nelle aste di brand e acquisizione.

═══ PRINCIPI DEL COPY ALBERGHIERO DI QUALITÀ ═══

SPECIFICITÀ PRIMA DI TUTTO
  ✗ "Ottimo hotel con servizi"          → generico, zero conversioni
  ✓ "Rooftop Pool con Vista sul Duomo"  → specifico, evocativo, desiderabile
  ✗ "Hotel di lusso a Roma"             → scontato
  ✓ "5 Min dal Colosseo a Piedi"        → distanza concreta, non km astratti

BENEFICIO, NON CARATTERISTICA
  ✗ "Piscina riscaldata disponibile"    → caratteristica
  ✓ "Piscina Riscaldata Tutto l'Anno"   → beneficio fruibile sempre
  ✗ "Colazione servita ogni mattina"    → ovvio
  ✓ "Colazione Buffet Inclusa nel Prezzo" → beneficio economico esplicito

OFFERTA DIRETTA vs OTA
  ✓ "Miglior Tariffa Garantita"         → promessa forte e verificabile (24 chars)
  ✓ "Prenota Senza Commissioni"         → beneficio economico diretto (24 chars)
  ✓ "Check-in Anticipato Incluso"       → vantaggio esclusivo del diretto (28 chars)
  ✓ "Sconto 10% sul Sito Ufficiale"     → incentivo quantificato (30 chars)

═══ REGOLE ASSOLUTE SUI CARATTERI ═══

Conta OGNI carattere (lettere, spazi, apostrofi, trattini) prima di rispondere.

  HEADLINE   → massimo 30 caratteri
  DESCRIZIONI → massimo 90 caratteri
  CALLOUT     → massimo 25 caratteri
  SITELINK testo       → massimo 25 caratteri
  SITELINK descrizione → massimo 35 caratteri ciascuna

REGOLA FONDAMENTALE: ogni headline, descrizione, callout e sitelink DEVE essere
una FRASE COMPLETA con senso compiuto. Se il testo non sta nel limite di caratteri,
RISCRIVILO più corto. NON troncare MAI una frase a metà.
  ✗ "Resort 4 stelle Bagno di" — VIETATO: troncato, senza senso
  ✓ "Resort 4 Stelle a Bagno" — OK: frase compiuta e comprensibile
  ✗ "Immergiti nel benessere nel cuore del Parco. Camere" — VIETATO
  ✓ "Benessere nel cuore del Parco." — OK: senso compiuto

═══ CONTENUTO AUTENTICO ═══

Genera solo servizi, caratteristiche e USP REALI trovati nel testo fornito.
Non inventare: non aggiungere spa se non è menzionata, non promettere vista mare se non c'è.
Usa i dettagli specifici dell'hotel per differenziarlo dalla concorrenza generica.

Rispondi ESCLUSIVAMENTE con JSON valido, zero testo aggiuntivo prima o dopo.
"""

_USER_PROMPT_TEMPLATE = """\
Analizza il sito web di un hotel e genera un brief strutturato per campagne Google Ads.

URL: {url}
Lingue richieste: {languages}

{lang_url_section}\
--- CONTENUTO DEL SITO ---
{content}
--- FINE CONTENUTO ---

═══ ISTRUZIONI PER IL COPY ═══

USP PRINCIPALE (obbligatoria, per ogni lingua):
- Una frase che sintetizza il vantaggio competitivo principale dell'hotel
- Basata su dati REALI trovati nel sito (posizione, servizi, categoria)
- Esempio: "Resort 4 stelle con spa e piscina a 50m dalla spiaggia di Jesolo"
- NON lasciare vuota: è il campo più importante per la strategia copy

HEADLINES (≤ 30 caratteri ciascuna):
- Genera almeno 10 headline diverse che coprono questi 4 temi:
  1. Brand/identità (es. "[Nome Hotel] Ufficiale", "4 Stelle sul Lago di Como")
  2. Prenotazione diretta (es. "Miglior Tariffa Garantita", "Prenota Senza Commissioni")
  3. Servizi/USP specifici (es. "Spa e Piscina Infinity", "Colazione Buffet Inclusa")
  4. Posizione/accesso (es. "50m dalla Spiaggia", "Centro Storico a Piedi")
- Usa dati REALI dal sito: posizione precisa, servizi effettivi, caratteristiche uniche
- Ogni headline = un argomento di vendita indipendente, non variazioni dello stesso
- VERIFICA: conta i caratteri di ogni headline prima di includerla

DESCRIZIONI (≤ 90 caratteri ciascuna — OBBLIGATORIE, esattamente 4):
- Genera esattamente 4 descrizioni per lingua — né più né meno, questo campo NON deve mai essere vuoto
- Descrizione 1: beneficio principale + CTA (es. "Prenota sul sito ufficiale e risparmia.")
- Descrizione 2: USP diversa + urgency/rassicurazione
- Descrizione 3: servizio/esperienza specifica dell'hotel
- Descrizione 4: vantaggio prenotazione diretta o garanzia
- Sii specifico: cita servizi reali, non generalità
- Conta i caratteri: ogni descrizione DEVE stare entro 90 caratteri

CALLOUT (≤ 25 caratteri ciascuno):
- Fatti concreti, non aggettivi — "Piscina Riscaldata" batte "Servizi Eccellenti"
- Varia i temi: prezzo, flessibilità, servizi, posizione

LANDING PAGE PER LINGUA (CRITICO):
- Usa ESATTAMENTE gli URL forniti nella sezione "URL per lingua" qui sopra.
- Se per una lingua è fornito un URL specifico, usalo come landing_page — NON inventare path.

═══ OUTPUT JSON ═══

{{
  "brand_name": "Nome commerciale dell'hotel",
  "brand_slug": "nome-in-slug",
  "domain": "www.dominio.it",
  "country": "IT",
  "hotel_category": "city_hotel|resort|boutique|business|agriturismo",
  "stars": 4,
  "rooms": null,
  "address": "Via Esempio 1, 00100 Roma",
  "services": ["Piscina", "Spa", "Ristorante", "Navetta Aeroporto"],
  "strengths": ["50m dalla spiaggia", "Vista panoramica sul golfo", "Parcheggio gratuito"],
  "booking_engine_url": "https://www.dominio.it/prenota",
  "target_countries": ["IT", "DE", "GB"],
  "languages": [
    {{
      "code": "IT",
      "name": "Italiano",
      "google_language_id": 1004,
      "landing_page": "https://www.dominio.it/it/",
      "brand_terms": ["Grand Hotel Bellevue", "Hotel Bellevue Roma"],
      "usp_main": "Hotel 4 stelle a 2 min dal Colosseo, colazione inclusa e miglior tariffa garantita.",
      "headlines": ["Grand Hotel Bellevue Roma", "Miglior Tariffa Garantita", "2 Min dal Colosseo", "Prenota Senza Commissioni", "Terrazza Panoramica", "Colazione Buffet Inclusa", "Sito Ufficiale", "Camera Vista Fori", "Check-in Anticipato", "Cancellazione Gratuita"],
      "descriptions": [
        "Hotel 4 stelle nel cuore di Roma, a 2 min dal Colosseo. Prenota diretto.",
        "Colazione inclusa, terrazza panoramica e parcheggio. Cancellazione gratis.",
        "Sito ufficiale: miglior tariffa garantita e vantaggi esclusivi per te.",
        "Camere vista Fori Imperiali, WiFi gratis e concierge dedicato 24/7."
      ],
      "callouts": ["Miglior Prezzo Online", "Colazione Inclusa", "Cancellazione Gratis"]
    }}
  ]
}}

Genera {n_langs} oggetti nella lista "languages", uno per ciascuna lingua: {languages}.
Per ogni lingua scrivi headline, descrizioni e callout NELLA LINGUA CORRETTA.
Adatta le espressioni culturalmente (non tradurre letteralmente).
"""


def _build_lang_url_section(
    lang_landings: Dict[str, str],
    lang_urls: Dict[str, List[str]],
    langs: List[str],
) -> str:
    """Build a text block for the AI prompt describing discovered URLs per language."""
    if not lang_landings and not lang_urls:
        return ""
    lines = ["--- URL PER LINGUA (rilevati dalla sitemap del sito) ---"]
    for lang in langs:
        landing = lang_landings.get(lang)
        lang_name = LANG_NAMES.get(lang, lang)
        if landing:
            lines.append(f"{lang} ({lang_name}) — homepage: {landing}")
        relevant = sorted(
            lang_urls.get(lang, []),
            key=_score_sitemap_url,
            reverse=True,
        )[:5]
        for url in relevant:
            if url != landing:
                lines.append(f"  {url}")
    lines.append("--- FINE URL PER LINGUA ---\n")
    return "\n".join(lines) + "\n"


# ── Per-type copy prompt data ─────────────────────────────────────────────────

_TYPE_COPY_PROMPTS: dict[str, dict] = {
    "brand": {
        "label": "Brand Search",
        "context": (
            "CONTESTO PSICOLOGICO: questi utenti cercano già il nome esatto dell'hotel su Google.\n"
            "Sanno chi sei. Il pericolo reale è che Booking.com o Expedia intercettino la loro ricerca\n"
            "con brand bidding, portandoli a prenotare su OTA (con commissione del 15-25%).\n"
            "Il tuo obiettivo: convincerli a prenotare DIRETTAMENTE dal sito ufficiale,\n"
            "comunicando i vantaggi esclusivi che le OTA non possono offrire."
        ),
        "headline_rules": (
            "- HEADLINE 1 (pinnata): DEVE contenere il nome brand/hotel\n"
            "- HEADLINE 2–4: vantaggi esclusivi prenotazione diretta\n"
            "  ✓ 'Miglior Tariffa Garantita' | 'Prenota Senza Commissioni' | 'Check-in Early Gratis'\n"
            "- HEADLINE 5–8: benefici specifici dell'hotel\n"
            "- NO termini generici di categoria — NO keyword insertion ({KeyWord})"
        ),
        "description_rules": (
            "- Prima descrizione: promessa diretta + CTA\n"
            "- Seconda descrizione: USP hotel + rassicurazione (vantaggi che le OTA non danno)\n"
            "- Menziona il nome brand almeno una volta"
        ),
    },
    "acquisition": {
        "label": "Acquisition Search",
        "context": (
            "CONTESTO PSICOLOGICO: questi utenti NON conoscono l'hotel. Stanno cercando\n"
            "una struttura per una destinazione o tipologia. Competono contro Booking, Expedia\n"
            "e altri hotel. Obiettivo: farsi scegliere mostrando i differenziatori più rilevanti."
        ),
        "headline_rules": (
            "- NESSUN nome brand — questi utenti non lo conoscono ancora\n"
            "- Ogni headline è un argomento di vendita INDIPENDENTE — varia i temi:\n"
            "  → Categoria + stelle + città | Posizione concreta | Servizio desiderabile\n"
            "  → Beneficio incluso | Elemento evocativo | Praticità\n"
            "- Usa aggettivi SPECIFICI e VERIFICABILI, non generici"
        ),
        "description_rules": (
            "- Prima descrizione: identifica la struttura + USP + CTA con incentivo\n"
            "- Seconda descrizione: dipingi l'esperienza + rassicurazione\n"
            "- NO nome brand — CTA con beneficio quantificato dove possibile"
        ),
    },
    "retargeting": {
        "label": "Retargeting",
        "context": (
            "CONTESTO PSICOLOGICO: questi utenti hanno già visitato il sito ma NON hanno prenotato.\n"
            "Conoscono l'hotel, erano interessati, ma qualcosa li ha fermati.\n"
            "Obiettivo: riattivare l'interesse con urgency autentica, rassicurazione e/o incentivo.\n"
            "Tono: premuroso e invitante, mai aggressivo o insistente."
        ),
        "headline_rules": (
            "- Richiama IMPLICITAMENTE la visita precedente\n"
            "  ✓ 'Completa la Prenotazione' | 'Tariffa Riservata per Te' | 'La Tua Camera Ti Aspetta'\n"
            "- Urgency autentica (non inventata): 'Ultime Camere', 'Prenota, Cancelli Gratis'\n"
            "- Incentivo al ritorno: 'Sconto Esclusivo per Oggi' | 'Torna e Risparmia il 10%'\n"
            "- EVITA toni aggressivi o pressanti"
        ),
        "description_rules": (
            "- Prima descrizione: rassicura + incentiva con tono caldo\n"
            "- Seconda descrizione: ricorda benefici + CTA con senso di opportunità\n"
            "- Rimuovi gli ostacoli alla prenotazione (cancellazione gratis, flessibilità)"
        ),
    },
}

# ── Budget strategy helpers ───────────────────────────────────────────────────

_BASE_WEIGHTS: dict[str, float] = {
    "search_brand": 0.12,
    "search_acquisition": 0.28,
    "performance_max": 0.38,
    "retargeting": 0.10,
    "demand_gen": 0.12,
}
_FRONTEND_KEYS: dict[str, str] = {
    "search_brand": "brand",
    "search_acquisition": "acquisition",
    "performance_max": "pmax",
    "retargeting": "retargeting",
    "demand_gen": "demand_gen",
}
_STATIC_RATIONALE: dict[str, str] = {
    "search_brand": "Protegge il traffico branded dalle OTA e intercetta utenti ad altissima intenzione d'acquisto con CPC contenuto e ROAS elevato.",
    "search_acquisition": "Intercetta utenti che cercano attivamente hotel nella tua destinazione. È il motore principale per acquisire nuovi clienti diretti.",
    "performance_max": "Campagna omnicanale (Search, Display, YouTube, Maps) che scala automaticamente su tutti i touchpoint Google.",
    "retargeting": "Re-ingaggia i visitatori che hanno esplorato il sito senza prenotare. Alta probabilità di conversione a basso CPA.",
    "demand_gen": "Campagna awareness su YouTube, Discover e Gmail per raggiungere viaggiatori nella fase di ispirazione.",
}


def _suggest_budget(stars: int, hotel_category: str) -> float:
    base: dict[int, float] = {1: 300, 2: 500, 3: 800, 4: 1500, 5: 3000}
    amount = base.get(min(max(stars, 1), 5), 800)
    cat = hotel_category.lower()
    if any(k in cat for k in ("resort", "luxury", "palazzo")):
        amount *= 1.4
    elif any(k in cat for k in ("boutique", "charme", "design")):
        amount *= 1.15
    return round(amount / 100) * 100


def _select_campaign_types(total_monthly: float) -> tuple[list[str], Optional[str]]:
    warning: Optional[str] = None
    if total_monthly < 300:
        warning = (
            f"Budget €{total_monthly:.0f}/mese è sotto la soglia minima consigliata di €300. "
            "Si consiglia di investire almeno €300/mese per ottenere dati statistici significativi."
        )
        return ["search_brand", "search_acquisition"], warning
    if total_monthly < 600:
        return ["search_brand", "search_acquisition"], None
    if total_monthly < 1500:
        return ["search_brand", "search_acquisition", "retargeting"], None
    if total_monthly < 3000:
        return ["search_brand", "search_acquisition", "performance_max", "retargeting"], None
    return ["search_brand", "search_acquisition", "performance_max", "retargeting", "demand_gen"], None


def _compute_split(recommended: list[str]) -> dict[str, float]:
    raw = {k: _BASE_WEIGHTS[k] for k in recommended}
    total = sum(raw.values())
    return {k: round(v / total, 4) for k, v in raw.items()}


def _compute_daily(
    split: dict[str, float],
    total_monthly: float,
    languages: list[str],
) -> dict[str, dict[str, float]]:
    n_langs = max(len(languages), 1)
    result: dict[str, dict[str, float]] = {}
    for backend_key, pct in split.items():
        fe_key = _FRONTEND_KEYS[backend_key]
        monthly_type = total_monthly * pct
        daily_per_lang = monthly_type / n_langs / 30.44
        result[fe_key] = {lang.upper(): round(daily_per_lang, 2) for lang in languages}
    return result


# ── Main enricher class ───────────────────────────────────────────────────────

class ClaudeEnricher:
    """Orchestrates all Anthropic API calls for the autofill pipeline."""

    def __init__(self, api_key: str) -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=4)
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        sections: list[str] = []
        audit_knowledge = combined_skills(GOOGLE_ADS_AUDIT, QUALITY_SCORE_BREAKDOWN)
        if audit_knowledge:
            sections.append(
                "═══ EXPERTISE: GOOGLE ADS AUDIT & QUALITY SCORE ═══\n\n" + audit_knowledge
            )
        sections.append(_SYSTEM_PROMPT_HOTEL_CORE)
        return "\n\n".join(sections)

    # ── Core brief enrichment ─────────────────────────────────────────────────

    async def enrich_brief(
        self,
        scraped: ScrapedSite,
        langs: List[str],
        url: str = "",
    ) -> tuple[dict, dict]:
        """
        Call Claude Sonnet to generate a complete brief from scraped site content.
        Returns (data_dict, api_log_entry).
        """
        lang_url_section = _build_lang_url_section(
            scraped.lang_landings, scraped.lang_urls, langs
        )
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            url=url,
            languages=", ".join(langs),
            content=scraped.content,
            n_langs=len(langs),
            lang_url_section=lang_url_section,
        )

        message = await self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        data = json.loads(_extract_json_object(raw))

        for lang in data.get('languages', []):
            code = str(lang.get('code', '')).upper()
            lang['code'] = code
            if not lang.get('google_language_id'):
                lang['google_language_id'] = LANG_IDS.get(code, 0)
            if not lang.get('name'):
                lang['name'] = LANG_NAMES.get(code, code)

        data = _truncate_assets(data)

        if scraped.lang_landings:
            scraped.scan_log.append(scan_entry("info", ""))
            scraped.scan_log.append(scan_entry("info", "━━ ASSEGNAZIONE LANDING PAGE ━━"))
            for lang in data.get('languages', []):
                code = lang.get('code', '')
                if code in scraped.lang_landings:
                    old = lang.get('landing_page', '')
                    lang['landing_page'] = scraped.lang_landings[code]
                    if old != scraped.lang_landings[code]:
                        scraped.scan_log.append(scan_entry("info",
                            f"  ✓ {code}: {scraped.lang_landings[code]} (AI suggeriva: {old or 'n/a'})"))
                else:
                    scraped.scan_log.append(scan_entry("warn",
                        f"  · {code}: nessuna landing specifica — mantenuto: {lang.get('landing_page', 'n/a')}"))

        data['_scan_log'] = scraped.scan_log
        log = _api_log_entry(
            agent="BriefCompiler",
            reason="Generazione brief da contenuto sito web",
            endpoint="POST /api/autofill",
            model="claude-sonnet-4-6",
            usage=message.usage,
        )
        return data, log

    # ── Sitelinks ─────────────────────────────────────────────────────────────

    async def suggest_sitelinks(
        self,
        common: dict,
        lang_code: str,
        landing_page: str,
        booking_url: str = "",
        sitemap_urls: Optional[List[str]] = None,
    ) -> tuple[list, dict]:
        """Generate 5 sitelinks for one language. Returns (sitelinks_list, api_log_entry)."""
        lang_name = LANG_NAMES.get(lang_code, lang_code)
        services_txt = ", ".join(common.get("services") or []) or "non specificati"
        strengths_txt = ", ".join(common.get("strengths") or []) or "non specificati"
        bk = booking_url or landing_page

        sitemap_hint = ""
        if sitemap_urls:
            scored = sorted(
                [(url, _score_sitemap_url(url)) for url in sitemap_urls if url != landing_page],
                key=lambda x: x[1], reverse=True,
            )
            top_urls = [url for url, _ in scored[:8]]
            if top_urls:
                sitemap_hint = (
                    "\nURL REALI DEL SITO (usa questi come final_url dove pertinenti):\n"
                    + "\n".join(f"  {u}" for u in top_urls) + "\n"
                )

        prompt = (
            f"Sei un copywriter Google Ads specializzato in hotel. Genera esattamente 5 sitelink.\n\n"
            f"Hotel: {common['brand_name']}\n"
            f"Categoria: {common['hotel_category']} — {common['stars']} stelle\n"
            f"Lingua: {lang_name} ({lang_code})\n"
            f"Landing page: {landing_page}\nBooking engine: {bk}\n"
            f"Servizi: {services_txt}\nPunti di forza: {strengths_txt}\n"
            f"{sitemap_hint}\n"
            "REGOLE CARATTERI:\n"
            "- text: ≤ 25 caratteri\n- description_1: ≤ 35 caratteri\n- description_2: ≤ 35 caratteri\n"
            "NON troncare le parole.\n\n"
            "REGOLE CONTENUTO:\n"
            "- final_url: usa gli URL reali forniti sopra quando disponibili\n"
            f"- Scrivi in {lang_name}\n"
            "- 5 temi diversi: prenotazione diretta, offerte, camere, servizi, location\n\n"
            "Restituisci SOLO array JSON di 5 oggetti:\n"
            '[{"text":"...","description_1":"...","description_2":"...","final_url":"..."}]'
        )

        message = await self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=load_skill(AD_EXTENSION_AUDIT),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        sitelinks = json.loads(_extract_json_array(raw))
        result = [
            {
                "text": _trim_to_word(str(sl.get("text", "")), 25),
                "description_1": _trim_to_word(str(sl.get("description_1", "")), 35),
                "description_2": _trim_to_word(str(sl.get("description_2", "")), 35),
                "final_url": str(sl.get("final_url", landing_page)),
            }
            for sl in sitelinks if isinstance(sl, dict) and sl.get("text")
        ]
        log = _api_log_entry(
            agent="SitelinkAgent",
            reason=f"Generazione sitelink — {lang_name} ({lang_code})",
            endpoint="POST /api/autofill/sitelinks",
            model="claude-haiku-4-5-20251001",
            usage=message.usage,
        )
        return result, log

    # ── Per-type RSA copy ─────────────────────────────────────────────────────

    async def suggest_type_copy(
        self,
        common: dict,
        lang_code: str,
        usp: Optional[str],
        campaign_type: str,
    ) -> tuple[dict, dict]:
        """Generate RSA headlines/descriptions for one campaign type. Returns (copy_dict, log)."""
        if campaign_type not in _TYPE_COPY_PROMPTS:
            return {"headlines": [], "descriptions": []}, {}
        meta = _TYPE_COPY_PROMPTS[campaign_type]
        lang_name = LANG_NAMES.get(lang_code, lang_code)
        services_txt = ", ".join(common.get("services") or []) or "non specificati"
        strengths_txt = ", ".join(common.get("strengths") or []) or "non specificati"
        usp_txt = usp or "non specificata"

        prompt = (
            f"Sei un copywriter Google Ads specializzato in hotel e hospitality.\n"
            f"Genera RSA copy ad alto impatto per campagne {meta['label']} in lingua {lang_name}.\n\n"
            f"═══ CONTESTO CAMPAGNA ═══\n{meta['context']}\n\n"
            f"═══ DATI HOTEL ═══\n"
            f"Hotel: {common['brand_name']}\nCategoria: {common['hotel_category']} — {common['stars']} stelle\n"
            f"USP principale: {usp_txt}\nServizi: {services_txt}\nPunti di forza: {strengths_txt}\n"
            f"Lingua output: {lang_name} ({lang_code})\n\n"
            f"═══ REGOLE HEADLINE (MAX 25 caratteri inclusi spazi) ═══\n{meta['headline_rules']}\n\n"
            f"═══ REGOLE DESCRIZIONI (MAX 75 caratteri inclusi spazi) ═══\n{meta['description_rules']}\n\n"
            f"REGOLE TASSATIVE SUI CARATTERI:\n"
            f"1. Ogni HEADLINE: MASSIMO 25 caratteri spazi inclusi. Conta i caratteri prima di scrivere.\n"
            f"2. Ogni DESCRIZIONE: MASSIMO 75 caratteri spazi inclusi. Conta i caratteri prima di scrivere.\n"
            f"3. Ogni descrizione DEVE essere una frase COMPLETA — mai troncare a metà.\n"
            f"   ✗ 'Piscina riscaldata, centro benessere e rist' — VIETATO: troncato\n"
            f"   ✓ 'Piscina e centro benessere. Prenota online.' — OK: frase completa ≤75 car\n"
            f"Se una frase non entra nel limite, RISCRIVILA più concisa finché non entra.\n\n"
            'Genera ESATTAMENTE questo JSON con 10 headline e 3 descrizioni, zero testo aggiuntivo:\n'
            '{"headlines":["h1","h2","h3","h4","h5","h6","h7","h8","h9","h10"],"descriptions":["d1","d2","d3"]}'
        )

        message = await self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=load_skill(AD_COPY_VARIANT_GENERATOR),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        parsed = json.loads(_extract_json_object(raw))
        result = {
            "headlines": _filter_by_limit(
                [h for h in parsed.get("headlines", []) if isinstance(h, str) and h.strip()], 30
            ),
            # Descriptions: no length filter — return complete sentences as-is.
            # Slightly-over-90-char descriptions are far better than empty output;
            # the brief form validator will highlight any that need manual trimming.
            "descriptions": [
                d.strip() for d in parsed.get("descriptions", [])
                if isinstance(d, str) and d.strip()
            ],
        }

        # ── Brand headline enforcement ────────────────────────────────
        # Validator requires at least one headline containing the brand name.
        # If the LLM didn't include it, inject a branded headline at position 1.
        brand_name = common.get("brand_name", "")
        if campaign_type == "brand" and result["headlines"] and brand_name:
            _norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
            bn = _norm(brand_name)
            has_brand = any(bn in _norm(h) for h in result["headlines"])
            if not has_brand:
                # Build a branded headline that fits 30 chars
                candidate = brand_name if len(brand_name) <= 30 else brand_name[:30].rsplit(" ", 1)[0]
                if candidate:
                    result["headlines"].insert(0, candidate)
                    # Keep max 15 headlines (Google RSA limit)
                    result["headlines"] = result["headlines"][:15]

        # ── Acquisition: strip brand name from headlines ─────────────
        # Acquisition targets users who don't know the brand; validator
        # rejects any headline containing brand_terms.
        # Keep originals if filtering leaves fewer than 3 (RSA minimum).
        if campaign_type == "acquisition" and result["headlines"] and brand_name:
            _norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
            bn = _norm(brand_name)
            brand_words = [w for w in bn.split() if len(w) >= 4]
            filtered = [
                h for h in result["headlines"]
                if not any(bw in _norm(h) for bw in [bn] + brand_words)
            ]
            if len(filtered) >= 3:
                result["headlines"] = filtered

        log = _api_log_entry(
            agent=f"TypeCopyAgent ({campaign_type})",
            reason=f"Generazione copy RSA {meta['label']} — {lang_name}",
            endpoint="POST /api/autofill/type-copy",
            model="claude-haiku-4-5-20251001",
            usage=message.usage,
        )
        return result, log

    # ── Keyword suggestion ────────────────────────────────────────────────────

    async def suggest_keywords(self, payload: dict) -> tuple[dict, dict]:
        """Generate acquisition keyword themes. Returns (result_dict, api_log_entry)."""
        lang_code = payload.get("language_code", "IT").upper()
        lang_name = LANG_NAMES.get(lang_code, lang_code)
        services_txt = ", ".join(payload.get("services") or []) or "non specificati"
        strengths_txt = ", ".join(payload.get("strengths") or []) or "non specificati"

        prompt = f"""Sei un esperto SEA/PPC per hotel. Genera keyword themes di acquisizione per Google Ads.

Hotel: {payload.get('brand_name', '')}
Categoria: {payload.get('hotel_category', '')}
Stelle: {payload.get('stars', 3)}
Dominio: {payload.get('domain') or 'non specificato'}
Servizi: {services_txt}
Punti di forza: {strengths_txt}
Lingua: {lang_name} ({lang_code})

Genera keyword themes per campagne Search Acquisition. Restituisci SOLO testo in questo formato:
prenotazione: kw1, kw2, kw3, kw4
categoria: kw1, kw2, kw3
posizione: kw1, kw2, kw3
servizi: kw1, kw2, kw3
[negatives]: kw_neg1, kw_neg2, kw_neg3, kw_neg4, kw_neg5

Regole:
- 4-6 temi con 4-8 keyword ciascuno
- Keyword REALI che un utente cercherebbe per trovare questo hotel
- Scrivi in {lang_name}
- Ultima riga sempre [negatives]: con 5-8 keyword negative
- Zero testo aggiuntivo, solo le righe richieste"""

        message = await self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=combined_skills(SEARCH_TERM_MINING, KEYWORD_CANNIBALIZATION),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        theme_lines: list[str] = []
        negative_lines: list[str] = []
        for line in lines:
            if line.lower().startswith('[negatives]') or line.lower().startswith('negatives'):
                colon = line.find(':')
                if colon != -1:
                    negative_lines = [k.strip() for k in line[colon + 1:].split(',') if k.strip()]
            else:
                theme_lines.append(line)

        result = {
            "kw_themes_text": "\n".join(theme_lines),
            "kw_negative_text": "\n".join(negative_lines),
        }
        log = _api_log_entry(
            agent="KeywordAgent",
            reason=f"Generazione keyword themes — {lang_name} ({lang_code})",
            endpoint="POST /api/autofill/keywords",
            model="claude-haiku-4-5-20251001",
            usage=message.usage,
        )
        return result, log

    # ── Budget strategy ───────────────────────────────────────────────────────

    async def suggest_budget_strategy(self, payload: dict) -> dict:
        """
        Suggest total budget, campaign types, split and rationale via a single Claude call.

        When the user has already entered a budget, Claude only determines the optimal
        split and rationale for that fixed amount.
        When no budget is provided, Claude also recommends the total monthly spend
        based on hotel profile, replacing the static _suggest_budget() lookup table.
        Falls back to static tables only if the AI call fails.
        """
        user_budget = payload.get("total_monthly_budget_eur", 0) or 0
        budget_provided = user_budget > 0

        # Static fallback total (used only when AI fails)
        static_total = (
            float(user_budget) if budget_provided
            else _suggest_budget(payload.get("stars", 3), payload.get("hotel_category", "city_hotel"))
        )
        static_recommended, warning = _select_campaign_types(static_total)
        static_split = _compute_split(static_recommended)

        langs_str = ", ".join(payload.get("languages", ["IT"]))
        n_langs = len(payload.get("languages", ["IT"]))
        all_types = list(_BASE_WEIGHTS.keys())
        split_example = ", ".join(f'"{t}": 20' for t in all_types[:3])

        # Build the budget section of the prompt differently depending on whether
        # the user has already provided a fixed total or we need AI to recommend one.
        if budget_provided:
            budget_section = f"BUDGET MENSILE TOTALE (fissato dal cliente): €{user_budget:.0f}"
            total_field = ""  # Claude doesn't need to suggest a total
        else:
            static_hint = _suggest_budget(payload.get("stars", 3), payload.get("hotel_category", "city_hotel"))
            budget_section = (
                f"BUDGET MENSILE: non specificato dal cliente.\n"
                f"Suggerisci il budget mensile ottimale (intero, multiplo di 100) per questo profilo.\n"
                f"Riferimento indicativo: €{static_hint:.0f} (valore di partenza, puoi discostartene)."
            )
            total_field = '"suggested_total_eur": 1500,'

        ai_prompt = f"""Sei uno stratega Google Ads specializzato in hotel e hospitality.
Definisci la strategia budget OTTIMALE per questo hotel specifico.

HOTEL: {payload.get('brand_name', '')} — {payload.get('hotel_category', '')} {payload.get('stars', 3)} stelle
PAESE: {payload.get('country', 'IT')} — LINGUE: {langs_str} ({n_langs} mercati target)
{budget_section}

Tipi campagna disponibili (usa ESATTAMENTE questi nomi chiave):
  search_brand, search_acquisition, performance_max, retargeting, demand_gen

LINEE GUIDA:
- Budget <€600: solo search_brand + search_acquisition
- Budget €600-€1499: aggiungi retargeting
- Budget €1500-€2999: aggiungi performance_max
- Budget ≥€3000: valuta demand_gen
Benchmark % per {payload.get('hotel_category', 'city_hotel')} {payload.get('stars', 3)}★:
  search_brand 18-25%, search_acquisition 30-45%, performance_max 20-30%,
  retargeting 8-15%, demand_gen 5-12% (solo se budget >€2500)

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido:
{{
  {total_field}
  "recommended_types": ["search_brand", "search_acquisition", "performance_max"],
  "split": {{{split_example}}},
  "overall": "2-3 frasi sulla strategia per questo hotel specifico",
  "search_brand": "rationale concreto per questo hotel",
  "search_acquisition": "rationale",
  "performance_max": "rationale"
}}

Regole JSON:
- I valori in "split" devono essere interi e sommare esattamente 100
- Includi in "split" SOLO i tipi presenti in "recommended_types", con gli stessi nomi esatti
{"- suggested_total_eur: intero euro, multiplo di 100" if not budget_provided else ""}"""

        rationale: dict[str, str] = {}
        overall_strategy = ""
        api_log: Optional[dict] = None
        recommended = static_recommended
        split = static_split
        total_monthly = static_total

        try:
            message = await self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1600,
                system=combined_skills(BID_STRATEGY_RECOMMENDATIONS, BUDGET_SCENARIO_PLANNER),
                messages=[{"role": "user", "content": ai_prompt}],
            )
            api_log = _api_log_entry(
                agent="BudgetStrategyAgent",
                reason=f"AI total+strategy+split — {payload.get('hotel_category', '')} {payload.get('stars', 3)}★",
                endpoint="POST /api/autofill/budget-strategy",
                model="claude-haiku-4-5-20251001",
                usage=message.usage,
            )
            raw = message.content[0].text.strip()
            logger.debug(f"BudgetStrategy Claude raw: {raw[:600]}")
            parsed = json.loads(_extract_json_object(raw))

            # ── AI-suggested total budget (only when not provided by user) ────
            if not budget_provided:
                ai_total = parsed.get("suggested_total_eur")
                if isinstance(ai_total, (int, float)) and 100 <= ai_total <= 50000:
                    total_monthly = float(ai_total)
                    # Recompute warning threshold with AI total
                    _, warning = _select_campaign_types(total_monthly)
                    logger.info(
                        f"BudgetStrategy AI total: €{static_total:.0f} (static) → "
                        f"€{total_monthly:.0f} (AI) for {payload.get('hotel_category')} {payload.get('stars')}★"
                    )

            # ── Recommended types (validate against known keys) ────────────────
            ai_types = [t for t in parsed.get("recommended_types", []) if t in _BASE_WEIGHTS]
            if ai_types:
                recommended = ai_types

            # ── AI-generated split percentages ────────────────────────────────
            ai_split_raw: dict = parsed.get("split", {})
            ai_split = {
                k: float(v)
                for k, v in ai_split_raw.items()
                if k in recommended and isinstance(v, (int, float)) and v > 0
            }
            if ai_split:
                # Fill any missing types proportionally
                for t in recommended:
                    if t not in ai_split:
                        ai_split[t] = _BASE_WEIGHTS.get(t, 1.0) * 10
                total_pct = sum(ai_split.values())
                split = {k: ai_split[k] / total_pct for k in recommended}
                logger.info(
                    f"BudgetStrategy AI split: "
                    + ", ".join(f"{k}={round(v*100)}%" for k, v in split.items())
                )
            else:
                logger.warning("BudgetStrategy: no valid split from Claude, using static fallback")
                split = _compute_split(recommended)

            # ── Rationale text per type ───────────────────────────────────────
            overall_strategy = parsed.get("overall", "")
            for t in recommended:
                rationale[t] = parsed.get(t, _STATIC_RATIONALE.get(t, ""))

        except Exception as exc:
            logger.warning(f"BudgetStrategy AI failed: {exc}. Using static fallback.")
            total_monthly = static_total
            recommended = static_recommended
            split = static_split
            for t in recommended:
                rationale[t] = _STATIC_RATIONALE.get(t, "")
            overall_strategy = (
                f"Strategia full-funnel con {len(recommended)} campagne — "
                f"€{total_monthly:.0f}/mese."
            )

        daily = _compute_daily(split, total_monthly, payload.get("languages", ["IT"]))

        # Prepend split summary so the user immediately sees AI-generated percentages
        _type_labels = {
            "search_brand": "Brand Search", "search_acquisition": "Acquisition",
            "performance_max": "Performance Max", "retargeting": "Retargeting",
            "demand_gen": "Demand Gen",
        }
        split_summary = " · ".join(
            f"{_type_labels.get(k, k)} {round(v * 100)}%"
            for k, v in split.items()
        )
        full_strategy = (
            f"Distribuzione AI: {split_summary}\n\n{overall_strategy}".strip()
            if overall_strategy else split_summary
        )

        return {
            "recommended_types": recommended,
            "budget_split": {k: round(v * 100, 1) for k, v in split.items()},
            "daily_by_type_lang": daily,
            "rationale": rationale,
            "overall_strategy": full_strategy,
            "suggested_total_monthly_eur": total_monthly,
            "min_budget_warning": warning,
            "api_call_log": api_log,
        }


# ── Background job runner (called from autofill.py via BackgroundTasks) ───────

# Maximum wall-clock time for the entire autofill pipeline (scrape + AI calls).
# Prevents background jobs from hanging forever when a site or API is unreachable.
_JOB_TIMEOUT_SECONDS = 300  # 5 minutes


async def run_autofill_job(
    job_id: str,
    url: str,
    langs: List[str],
    content: Optional[str],
    api_key: str,
    update_status: Callable,
) -> None:
    """
    Background task: orchestrate the complete auto-fill pipeline.
    1. Fetch hotel website (or use manual content).
    2. Call Claude Sonnet for the main brief JSON.
    3. For each language in parallel: sitelinks + RSA copies (brand/acq/ret).
    4. Persist enriched result via update_status callback.

    Wrapped in asyncio.wait_for with a global timeout to avoid hung jobs.
    """
    logger.info(f"AutofillJob {job_id} background task started — url={url} langs={langs}")
    try:
        await update_status(job_id, "running")
        await asyncio.wait_for(
            _run_autofill_pipeline(job_id, url, langs, content, api_key, update_status),
            timeout=_JOB_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.error(f"AutofillJob {job_id} timed out after {_JOB_TIMEOUT_SECONDS}s")
        await update_status(
            job_id, "failed",
            error=f"Job scaduto dopo {_JOB_TIMEOUT_SECONDS // 60} minuti. "
                  "Il sito potrebbe essere lento o irraggiungibile. Riprova più tardi.",
        )
    except Exception as exc:
        logger.error(f"AutofillJob {job_id} failed: {exc}", exc_info=True)
        await update_status(job_id, "failed", error=str(exc))


async def _run_autofill_pipeline(
    job_id: str,
    url: str,
    langs: List[str],
    content: Optional[str],
    api_key: str,
    update_status: Callable,
) -> None:
    """Inner pipeline extracted so run_autofill_job can wrap it with a timeout."""
    from app.connectors.web_scraper import scrape_hotel_site, ScrapedSite

    enricher = ClaudeEnricher(api_key)

    if content and content.strip():
        scraped = ScrapedSite(
            content=content.strip()[:14000],
            lang_urls={},
            lang_landings={},
            scan_log=[scan_entry("info", "📋 Contenuto manuale fornito — scansione sito saltata")],
        )
    else:
        scraped = await scrape_hotel_site(url, langs)

    # Persist the scraped data so the brief can be regenerated later
    # without re-scraping the website or re-calling the AI.
    scraped_payload = {
        "content": scraped.content,
        "lang_urls": scraped.lang_urls,
        "lang_landings": scraped.lang_landings,
    }
    await update_status(job_id, "running", scraped=scraped_payload)

    data, brief_log = await enricher.enrich_brief(scraped, langs, url=url)
    api_log: List[dict] = [brief_log]

    common = {
        "brand_name": data.get("brand_name", ""),
        "hotel_category": data.get("hotel_category", "city_hotel"),
        "stars": data.get("stars", 3),
        "services": data.get("services", []),
        "strengths": data.get("strengths", []),
    }
    booking_url = data.get("booking_engine_url") or f"https://{data.get('domain', '')}"

    async def _enrich_language(lang: dict) -> dict:
        code    = lang.get("code", "IT")
        landing = lang.get("landing_page") or f"https://{data.get('domain', '')}"
        usp     = lang.get("usp_main")
        sitemap_lang_urls = scraped.lang_urls.get(code, [])

        async def _safe_sitelinks():
            try:
                sl, log = await enricher.suggest_sitelinks(
                    common, code, landing, booking_url, sitemap_lang_urls
                )
                api_log.append(log)
                return sl
            except Exception as exc:
                logger.warning(f"Job {job_id}: sitelinks failed for {code}: {exc}")
                return []

        async def _safe_copy(ctype):
            try:
                result, log = await enricher.suggest_type_copy(common, code, usp, ctype)
                api_log.append(log)
                return result
            except Exception as exc:
                logger.warning(f"Job {job_id}: type-copy {ctype} failed for {code}: {exc}")
                return {"headlines": [], "descriptions": []}

        async def _safe_keywords():
            try:
                kw_payload = {
                    **common,
                    "domain": data.get("domain", ""),
                    "language_code": code,
                }
                result, log = await enricher.suggest_keywords(kw_payload)
                api_log.append(log)
                return result
            except Exception as exc:
                logger.warning(f"Job {job_id}: keywords failed for {code}: {exc}")
                return {"kw_themes_text": "", "kw_negative_text": ""}

        sl, brand, acq, ret, kw = await asyncio.gather(
            _safe_sitelinks(),
            _safe_copy("brand"),
            _safe_copy("acquisition"),
            _safe_copy("retargeting"),
            _safe_keywords(),
        )
        return {
            **lang,
            "sitelinks": sl,
            "brand_headlines": brand["headlines"],
            "brand_descriptions": brand["descriptions"],
            "acquisition_headlines": acq["headlines"],
            "acquisition_descriptions": acq["descriptions"],
            "retargeting_headlines": ret["headlines"],
            "retargeting_descriptions": ret["descriptions"],
            "kw_themes_text": kw.get("kw_themes_text", ""),
            "kw_negative_text": kw.get("kw_negative_text", ""),
        }

    enriched = await asyncio.gather(*[_enrich_language(lang) for lang in data.get("languages", [])])
    data["languages"] = list(enriched)
    data["_api_log"] = api_log
    data["_scan_log"] = scraped.scan_log

    await update_status(job_id, "completed", result=data)
    logger.info(f"AutofillJob {job_id} completed — brand: {data.get('brand_name')}")
