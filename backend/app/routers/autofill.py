"""Auto-fill brief from hotel website using AI (Claude)."""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import TokenData, require_strategist_or_admin
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autofill", tags=["autofill"])

LANG_IDS: dict[str, int] = {
    "IT": 1004, "EN": 1000, "DE": 1001, "FR": 1002, "ES": 1003,
    "NL": 1010, "PT": 1014, "RU": 1031, "ZH": 1017, "JA": 1005,
    "PL": 1030, "SV": 1040, "NO": 1013, "DA": 1009,
}
LANG_NAMES: dict[str, str] = {
    "IT": "Italiano", "EN": "English", "DE": "Deutsch",
    "FR": "Français", "ES": "Español", "NL": "Nederlands",
    "PT": "Português", "RU": "Русский", "ZH": "中文",
    "JA": "日本語", "PL": "Polski", "SV": "Svenska",
    "NO": "Norsk", "DA": "Dansk",
}

SYSTEM_PROMPT = """\
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
NON troncare le parole: se una parola non entra per intero entro il limite, NON includerla.

  HEADLINE   → massimo 30 caratteri  ("Hotel 4 Stelle Roma" = 20 ✓)
  DESCRIZIONI → massimo 90 caratteri
  CALLOUT     → massimo 25 caratteri  ("Cancellazione Gratis" = 20 ✓)
  SITELINK testo       → massimo 25 caratteri
  SITELINK descrizione → massimo 35 caratteri ciascuna

Come verificare (esempio):
  "Prenota Diretto Online" → P-r-e-n-o-t-a(7) SPACE(8) D-i-r-e-t-t-o(15) SPACE(16) O-n-l-i-n-e(22) = 22 ✓
  "Prenota sul Sito Ufficiale e Risparmia" = 39 caratteri ✗ — troppo lungo

═══ CONTENUTO AUTENTICO ═══

Genera solo servizi, caratteristiche e USP REALI trovati nel testo fornito.
Non inventare: non aggiungere spa se non è menzionata, non promettere vista mare se non c'è.
Usa i dettagli specifici dell'hotel per differenziarlo dalla concorrenza generica.

Rispondi ESCLUSIVAMENTE con JSON valido, zero testo aggiuntivo prima o dopo.
"""

USER_PROMPT_TEMPLATE = """\
Analizza il sito web di un hotel e genera un brief strutturato per campagne Google Ads.

URL: {url}
Lingue richieste: {languages}

--- CONTENUTO DEL SITO ---
{content}
--- FINE CONTENUTO ---

═══ ISTRUZIONI PER IL COPY ═══

HEADLINES (≤ 30 caratteri ciascuna):
- Genera almeno 8 headline diverse che coprono questi 4 temi:
  1. Brand/identità (es. "[Nome Hotel] Ufficiale", "4 Stelle sul Lago di Como")
  2. Prenotazione diretta (es. "Miglior Tariffa Garantita", "Prenota Senza Commissioni")
  3. Servizi/USP specifici (es. "Spa e Piscina Infinity", "Colazione Buffet Inclusa")
  4. Posizione/accesso (es. "50m dalla Spiaggia", "Centro Storico a Piedi")
- Usa dati REALI dal sito: posizione precisa, servizi effettivi, caratteristiche uniche
- Ogni headline = un argomento di vendita indipendente, non variazioni dello stesso
- VERIFICA: conta i caratteri di ogni headline prima di includerla

DESCRIZIONI (≤ 90 caratteri ciascuna):
- Prima descrizione: beneficio principale + CTA (es. "Prenota ora e goditi la vista mozzafiato. Tariffa migliore sul sito ufficiale.")
- Seconda descrizione: USP diversa + urgency/rassicurazione (es. "Camera con terrazza e colazione inclusa. Cancellazione gratuita fino a 24h prima.")
- Sii specifico: cita servizi reali, non generalità

CALLOUT (≤ 25 caratteri ciascuno):
- Fatti concreti, non aggettivi — "Piscina Riscaldata" batte "Servizi Eccellenti"
- Varia i temi: prezzo, flessibilità, servizi, posizione

USP_MAIN (≤ 90 caratteri):
- La proposta di valore unica che distingue questo hotel dalla concorrenza
- Deve rispondere a: "Perché scegliere questo hotel rispetto a tutti gli altri?"

BRAND TERMS:
- Esattamente come gli utenti cercano su Google (nome ufficiale, abbreviazioni comuni, varianti)

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
      "landing_page": "https://www.dominio.it/",
      "brand_terms": ["Grand Hotel Bellevue", "Hotel Bellevue Roma", "Bellevue Hotel"],
      "usp_main": "Hotel 4 stelle a 2 min dal Colosseo, colazione inclusa e miglior tariffa garantita.",
      "headlines": [
        "Grand Hotel Bellevue Roma",
        "Miglior Tariffa Garantita",
        "2 Min dal Colosseo",
        "Colazione Buffet Inclusa",
        "Prenota Senza Commissioni",
        "Suite con Vista Panoramica",
        "Cancellazione Gratuita",
        "Check-in Early Incluso"
      ],
      "descriptions": [
        "Hotel 4 stelle nel cuore di Roma, a 2 minuti dal Colosseo. Prenota diretto e risparmia.",
        "Colazione inclusa ogni mattina, terrazza panoramica e parcheggio. Cancellazione gratis."
      ],
      "callouts": [
        "Miglior Prezzo Online",
        "Colazione Inclusa",
        "Cancellazione Gratis",
        "Parcheggio Gratuito",
        "Check-in Anticipato"
      ]
    }}
  ]
}}

Genera {n_langs} oggetti nella lista "languages", uno per ciascuna lingua: {languages}.
Per ogni lingua scrivi headline, descrizioni e callout NELLA LINGUA CORRETTA.
Adatta le espressioni culturalmente (non tradurre letteralmente: "Miglior Tariffa Garantita"
in tedesco diventa "Bestpreisgarantie", non "Beste Preis Garantiert").
"""


def _strip_html(html: str) -> str:
    """Remove HTML tags, scripts, styles. Return plain text max 10000 chars."""
    html = re.sub(r'<(script|style|noscript)[^>]*>.*?</(script|style|noscript)>', ' ', html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&[a-z]+;', '', html)
    html = re.sub(r'\s+', ' ', html).strip()
    return html[:10000]


async def _fetch_pages(base_url: str) -> str:
    """Fetch homepage and one subpage. Return combined plain text."""
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8,de;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    base = base_url.rstrip('/')
    candidates = [base_url, f"{base}/camere", f"{base}/rooms", f"{base}/servizi", f"{base}/about"]
    collected: list[str] = []
    errors: list[str] = []

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        verify=False,
        headers=headers,
    ) as client:
        for url in candidates[:3]:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and 'text/html' in resp.headers.get('content-type', ''):
                    text = _strip_html(resp.text)
                    if len(text) > 200:
                        collected.append(f"[{url}]\n{text}")
                        if len('\n\n'.join(collected)) > 14000:
                            break
                else:
                    errors.append(f"{url} → HTTP {resp.status_code}")
            except Exception as exc:
                errors.append(f"{url} → {type(exc).__name__}: {exc}")
                continue

    if not collected:
        detail = "Impossibile recuperare il sito web dal server. "
        if errors:
            detail += "Dettagli: " + " | ".join(errors)
        detail += " Usa la modalità manuale: incolla il testo del sito nell'apposita area."
        logger.warning(f"_fetch_pages failed for {base_url}: {errors}")
        raise HTTPException(status_code=422, detail=detail)
    return '\n\n'.join(collected)[:14000]


def _trim_to_word(text: str, max_chars: int) -> str:
    """Ensure text fits within max_chars without cutting words mid-way.

    Handles two cases:
    A) text is LONGER than max_chars: trim to last complete word before limit.
    B) text is EXACTLY max_chars and ends with a letter: the LLM counted to the
       hard limit and stopped mid-word (e.g. "termale" → "termal" at char 90).
       We backtrack to the last complete word to be safe.

    A text that is strictly SHORTER than max_chars is returned unchanged.
    A very long single word with no spaces is hard-trimmed as last resort.
    """
    text = text.rstrip()
    cut = text[:max_chars]

    if len(text) > max_chars:
        # Case A: text overshoots the limit
        if text[max_chars] != ' ':
            space = cut.rfind(' ')
            if space > 0:
                return cut[:space]
            return cut  # single overlong token — unavoidable hard trim
        return cut

    if len(text) == max_chars and max_chars >= 40 and cut and cut[-1].isalpha():
        # Case B: text is exactly at the limit and ends with a letter.
        # Only apply for long fields (descriptions/USP ≥ 40 chars) — headlines (30)
        # and callouts (25) legitimately end at their limit without mid-word risk.
        # The LLM counted to the hard limit and may have stopped mid-word.
        # Backtrack to the previous word boundary to guarantee completeness.
        space = cut.rfind(' ')
        if space > 0:
            return cut[:space]
        return cut  # single token filling entire limit — return as-is

    # Text is under the limit — return unchanged
    return cut


def _truncate_assets(data: dict) -> dict:
    """Post-process: trim headlines/descriptions/callouts to Google Ads limits (word-safe)."""
    for lang in data.get('languages', []):
        lang['headlines'] = [_trim_to_word(h, 30) for h in lang.get('headlines', [])]
        lang['descriptions'] = [_trim_to_word(d, 90) for d in lang.get('descriptions', [])]
        lang['callouts'] = [_trim_to_word(c, 25) for c in lang.get('callouts', [])]
        if lang.get('usp_main'):
            lang['usp_main'] = _trim_to_word(lang['usp_main'], 90)
    return data


class AutofillRequest(BaseModel):
    url: str
    languages: List[str] = ["IT", "EN"]
    content: Optional[str] = None  # manual fallback: paste website text directly


class KeywordsRequest(BaseModel):
    brand_name: str
    hotel_category: str
    stars: int
    language_code: str
    domain: Optional[str] = None
    services: Optional[List[str]] = None
    strengths: Optional[List[str]] = None


class SitelinksRequest(BaseModel):
    brand_name: str
    hotel_category: str
    stars: int
    language_code: str
    landing_page: str
    domain: Optional[str] = None
    services: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    booking_engine_url: Optional[str] = None


class TypeCopyRequest(BaseModel):
    campaign_type: str          # "brand" | "acquisition" | "retargeting"
    brand_name: str
    hotel_category: str
    stars: int
    language_code: str
    domain: Optional[str] = None
    usp_main: Optional[str] = None
    services: Optional[List[str]] = None
    strengths: Optional[List[str]] = None


@router.post("/keywords")
async def suggest_keywords(
    payload: KeywordsRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """
    Generate acquisition keyword themes for a hotel using AI.
    Returns kw_themes_text and kw_negative_text ready to paste into the brief form.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chiave API Anthropic non configurata.",
        )

    lang_code = payload.language_code.upper()
    lang_name = LANG_NAMES.get(lang_code, lang_code)

    services_txt = ", ".join(payload.services or []) or "non specificati"
    strengths_txt = ", ".join(payload.strengths or []) or "non specificati"

    prompt = f"""Sei un esperto SEA/PPC per hotel. Genera keyword themes di acquisizione per Google Ads.

Hotel: {payload.brand_name}
Categoria: {payload.hotel_category}
Stelle: {payload.stars}
Dominio: {payload.domain or 'non specificato'}
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
- Ultima riga sempre [negatives]: con 5-8 keyword negative (es. gratis, recensioni, immagini)
- Zero testo aggiuntivo, solo le righe richieste"""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.error(f"Keywords suggestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")

    # Split negatives from themes
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    theme_lines = []
    negative_lines = []
    for line in lines:
        if line.lower().startswith('[negatives]') or line.lower().startswith('negatives'):
            colon = line.find(':')
            if colon != -1:
                negative_lines = [k.strip() for k in line[colon + 1:].split(',') if k.strip()]
        else:
            theme_lines.append(line)

    return {
        "kw_themes_text": "\n".join(theme_lines),
        "kw_negative_text": "\n".join(negative_lines),
    }


@router.post("/sitelinks")
async def suggest_sitelinks(
    payload: SitelinksRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """
    Generate 4–6 Google Ads sitelinks for a hotel using AI.
    Returns a list of sitelink objects ready to populate the brief form.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chiave API Anthropic non configurata.",
        )

    lang_code = payload.language_code.upper()
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    services_txt = ", ".join(payload.services or []) or "non specificati"
    strengths_txt = ", ".join(payload.strengths or []) or "non specificati"
    booking_url = payload.booking_engine_url or payload.landing_page

    prompt = f"""Sei un copywriter Google Ads specializzato in hotel. Genera esattamente 5 sitelink.

I sitelink appaiono sotto l'annuncio principale e portano l'utente direttamente alle sezioni
più rilevanti del sito. Devono essere specifici, utili e cliccabili.

Hotel: {payload.brand_name}
Categoria: {payload.hotel_category} — {payload.stars} stelle
Lingua: {lang_name} ({lang_code})
Landing page: {payload.landing_page}
Booking engine: {booking_url}
Servizi: {services_txt}
Punti di forza: {strengths_txt}

REGOLE CARATTERI (verifica ogni campo prima di rispondere):
- text: ≤ 25 caratteri, spazi inclusi
- description_1: ≤ 35 caratteri, spazi inclusi
- description_2: ≤ 35 caratteri, spazi inclusi
NON troncare le parole: se non entra per intero, elimina l'ultima parola.

REGOLE CONTENUTO:
- final_url: URL reale basata sulla landing page (modifica solo il path, non inventare domini)
- Scrivi text, description_1, description_2 in {lang_name}
- Ogni sitelink copre un tema DIVERSO — non ripetere variazioni dello stesso:
  1. Prenotazione diretta (booking engine) → vantaggi tariffa/cancellazione
  2. Offerte/pacchetti → risparmio o esperienza inclusa
  3. Camere/suite → caratteristiche specifiche basate sui servizi reali
  4. Servizi hotel → SPA, piscina, ristorante (usa quelli effettivi)
  5. Location/come arrivare → posizione, distanze, navetta
- Le descrizioni devono essere argomenti di vendita, non semplici descrizioni della pagina
  ✗ "Pagina camere del nostro hotel" → ✓ "Camere con vista lago e terrazza privata"

Restituisci SOLO questo JSON (array di 5 oggetti), zero testo aggiuntivo:
[
  {{"text": "Prenota Direttamente", "description_1": "Miglior tariffa garantita", "description_2": "Cancellazione gratuita inclusa", "final_url": "{booking_url}"}},
  {{"text": "Offerte e Pacchetti", "description_1": "Soggiorni con colazione inclusa", "description_2": "Risparmia prenotando sul sito", "final_url": "{payload.landing_page}/offerte"}},
  {{"text": "Le Nostre Camere", "description_1": "Suite con vista panoramica", "description_2": "Arredi di design e comfort top", "final_url": "{payload.landing_page}/camere"}},
  {{"text": "Spa e Piscina", "description_1": "Relax con trattamenti esclusivi", "description_2": "Piscina riscaldata tutto l'anno", "final_url": "{payload.landing_page}/spa"}},
  {{"text": "Come Raggiungerci", "description_1": "Centro città, 3 min dalla stazione", "description_2": "Navetta aeroporto disponibile", "final_url": "{payload.landing_page}/contatti"}}
]"""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.error(f"Sitelinks suggestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")

    # Parse JSON array from response
    try:
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        else:
            start = raw.find('[')
            end = raw.rfind(']')
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        sitelinks = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Sitelinks JSON parse error: {exc}\nRaw: {raw[:500]}")
        raise HTTPException(status_code=500, detail="Risposta AI non parsabile. Riprova.")

    # Enforce character limits (word-safe — never cut mid-word)
    result = []
    for sl in sitelinks:
        if not isinstance(sl, dict) or not sl.get("text"):
            continue
        result.append({
            "text": _trim_to_word(str(sl.get("text", "")), 25),
            "description_1": _trim_to_word(str(sl.get("description_1", "")), 35),
            "description_2": _trim_to_word(str(sl.get("description_2", "")), 35),
            "final_url": str(sl.get("final_url", payload.landing_page)),
        })

    return {"sitelinks": result}


@router.post("")
async def autofill_from_url(
    payload: AutofillRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """
    Fetch a hotel website and use Claude to generate a complete brief draft.
    Returns structured data ready to pre-populate the brief form.
    If `content` is provided, the HTTP fetch is skipped and that text is used directly.
    """
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chiave API Anthropic non configurata. Imposta ANTHROPIC_API_KEY nel file .env",
        )

    langs = [l.upper() for l in payload.languages if l.strip()]
    if not langs:
        raise HTTPException(status_code=422, detail="Almeno una lingua richiesta")

    # 1. Fetch the website (or use manually provided content)
    if payload.content and payload.content.strip():
        logger.info(f"Autofill: using manual content for {payload.url}, langs={langs}")
        content = payload.content.strip()[:14000]
    else:
        logger.info(f"Autofill: fetching {payload.url} for languages {langs}")
        content = await _fetch_pages(payload.url)

    # 2. Call Claude
    user_prompt = USER_PROMPT_TEMPLATE.format(
        url=payload.url,
        languages=", ".join(langs),
        content=content,
        n_langs=len(langs),
    )

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.error(f"Anthropic call failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore chiamata AI: {exc}")

    # 3. Parse JSON from response
    try:
        # Claude sometimes wraps in ```json ... ```
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        else:
            # Find first { ... } block
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"JSON parse error: {exc}\nRaw: {raw[:500]}")
        raise HTTPException(
            status_code=500,
            detail="Il modello AI ha restituito una risposta non parsabile. Riprova.",
        )

    # 4. Enrich language metadata and truncate to Google Ads limits
    for lang in data.get('languages', []):
        code = str(lang.get('code', '')).upper()
        lang['code'] = code
        if not lang.get('google_language_id'):
            lang['google_language_id'] = LANG_IDS.get(code, 0)
        if not lang.get('name'):
            lang['name'] = LANG_NAMES.get(code, code)

    data = _truncate_assets(data)

    logger.info(f"Autofill OK: {data.get('brand_name')} — {len(data.get('languages', []))} langs")
    return data


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
            "  ✓ 'Hotel Bellevue Ufficiale' | '[Brand] Sito Ufficiale' | 'Grand Hotel [Nome]'\n"
            "- HEADLINE 2–4: vantaggi esclusivi prenotazione diretta\n"
            "  ✓ 'Miglior Tariffa Garantita'  (24 chars)\n"
            "  ✓ 'Prenota Senza Commissioni'  (24 chars)\n"
            "  ✓ 'Check-in Anticipato Gratis' (26 chars)\n"
            "  ✓ 'Cancellazione Flessibile'   (24 chars)\n"
            "  ✓ 'Sconto 10% Solo Online'     (21 chars)\n"
            "- HEADLINE 5–8: benefici specifici dell'hotel (non generici)\n"
            "  ✓ 'Colazione Buffet Inclusa' | 'Suite con Vista Mare' | 'Parcheggio Gratuito'\n"
            "- NO termini generici di categoria (quelli vanno in Acquisition)\n"
            "- NO keyword insertion ({KeyWord})\n"
            "- Varia i temi: credenziale ufficiale → risparmio → flessibilità → USP hotel"
        ),
        "description_rules": (
            "- Prima descrizione: promessa diretta + CTA\n"
            "  ✓ 'Prenota sul sito ufficiale: miglior tariffa e vantaggi esclusivi garantiti.'\n"
            "- Seconda descrizione: USP hotel + rassicurazione (benefici che le OTA non danno)\n"
            "  ✓ '[Brand]: colazione inclusa, early check-in e cancellazione gratuita. Prenota ora.'\n"
            "- Menziona il nome brand almeno una volta\n"
            "- Comunica urgency morbida: 'Prenota ora', 'Disponibilità limitata'"
        ),
    },
    "acquisition": {
        "label": "Acquisition Search",
        "context": (
            "CONTESTO PSICOLOGICO: questi utenti NON conoscono l'hotel. Stanno cercando\n"
            "una struttura per una destinazione o tipologia (es. 'hotel 4 stelle Roma centro',\n"
            "'resort con spa toscana'). Compaiono nella SERP insieme a decine di altri hotel\n"
            "e alle OTA. Il tuo obiettivo: farsi scegliere tra tutti, mostrando i differenziatori\n"
            "più rilevanti per chi cerca quella tipologia di hotel in quella destinazione."
        ),
        "headline_rules": (
            "- NESSUN nome brand — questi utenti non lo conoscono ancora\n"
            "- Ogni headline è un argomento di vendita INDIPENDENTE — varia i temi:\n"
            "  → Categoria + stelle + città: 'Hotel 4 Stelle Roma Centro' (24 chars)\n"
            "  → Posizione concreta in tempo: '3 Min dalla Stazione' (20 chars)\n"
            "  → Servizio visibile/desiderabile: 'Piscina Infinity sul Tetto' (25 chars)\n"
            "  → Beneficio incluso: 'Colazione Buffet Ogni Giorno' (28 chars)\n"
            "  → Elemento sensoriale/evocativo: 'Vista Panoramica sulla Laguna' (29 chars)\n"
            "  → Praticità: 'Parcheggio Gratuito Incluso' (27 chars)\n"
            "  → Flessibilità: 'Cancellazione Gratuita' (22 chars)\n"
            "- Usa aggettivi SPECIFICI e VERIFICABILI, non generici\n"
            "  ✗ 'Hotel di Qualità' → ✓ 'Hotel 4 Stelle Fronte Mare'\n"
            "  ✗ 'Servizi Eccellenti' → ✓ 'Spa, Piscina e Ristorante'\n"
            "- Parla dei BENEFICI per l'ospite, non delle caratteristiche dell'hotel"
        ),
        "description_rules": (
            "- Prima descrizione: identifica la struttura + USP principale + CTA con incentivo\n"
            "  ✓ 'Hotel 4 stelle nel cuore di Firenze, a 5 min dal Duomo. Prenota online e risparmia.'\n"
            "- Seconda descrizione: dipingi l'esperienza + rassicurazione prenotazione\n"
            "  ✓ 'Spa, piscina riscaldata e terrazza con vista sulle colline. Tariffa migliore online.'\n"
            "- NO nome brand\n"
            "- CTA con beneficio quantificato dove possibile: 'risparmia fino al 20%', 'dal sito ufficiale'"
        ),
    },
    "retargeting": {
        "label": "Retargeting",
        "context": (
            "CONTESTO PSICOLOGICO: questi utenti hanno già visitato il sito ma NON hanno prenotato.\n"
            "Conoscono l'hotel, erano interessati, ma qualcosa li ha fermati: prezzo, incertezza,\n"
            "distrazione, confronto con altre strutture. Non sono 'freddi' — sono 'tiepidi'.\n"
            "Il tuo obiettivo: riattivare l'interesse con urgency autentica, rassicurazione\n"
            "e/o un incentivo al ritorno. Tono: premuroso e invitante, mai aggressivo o insistente."
        ),
        "headline_rules": (
            "- Richiama IMPLICITAMENTE la visita precedente (senza dirlo esplicitamente)\n"
            "  ✓ 'Completa la Prenotazione' (24 chars) — diretto, non aggressivo\n"
            "  ✓ 'Tariffa Riservata per Te' (24 chars) — personalizzazione percepita\n"
            "  ✓ 'La Tua Camera Ti Aspetta' (24 chars) — calore, senso di attesa\n"
            "- Urgency autentica (non inventata, non allarmista)\n"
            "  ✓ 'Ultime Camere Disponibili' (25 chars) — scarsità reale\n"
            "  ✓ 'Offerta Valida Ancora Oggi' (26 chars — usa 25 chars: 'Offerta Valida per Oggi')\n"
            "  ✓ 'Prenota, Cancelli Gratis'  (24 chars) — rimuovi l'ostacolo della paura\n"
            "- Incentivo al ritorno\n"
            "  ✓ 'Sconto Esclusivo per Oggi' (25 chars)\n"
            "  ✓ 'Torna e Risparmia il 10%'  (24 chars)\n"
            "- Puoi includere il nome brand per rafforzare il riconoscimento\n"
            "- EVITA toni aggressivi o pressanti: 'ULTIMA OCCASIONE!!!' è controproducente"
        ),
        "description_rules": (
            "- Prima descrizione: rassicura + incentiva con tono caldo\n"
            "  ✓ 'Le date che cercavi sono ancora disponibili. Prenota ora con cancellazione gratuita.'\n"
            "- Seconda descrizione: ricorda i benefici + CTA con senso di opportunità\n"
            "  ✓ '[Brand]: colazione inclusa e miglior tariffa garantita. Non aspettare, prenota oggi.'\n"
            "- Rimuovi gli ostacoli alla prenotazione: menziona cancellazione gratis, flessibilità\n"
            "- Senso di opportunità (non di minaccia): 'ancora disponibile', 'prenota oggi'"
        ),
    },
}


# ─── Budget Strategy ──────────────────────────────────────────────────────────

class BudgetStrategyRequest(BaseModel):
    brand_name: str
    hotel_category: str
    stars: int
    total_monthly_budget_eur: float
    languages: List[str]
    vertical: str = "hotel"
    country: str = "IT"


class BudgetStrategyResponse(BaseModel):
    recommended_types: List[str]
    budget_split: dict
    daily_by_type_lang: dict
    rationale: dict
    overall_strategy: str
    min_budget_warning: Optional[str] = None


# Weights when all 5 types are active (sum = 1.0)
_BASE_WEIGHTS: dict[str, float] = {
    "search_brand": 0.12,
    "search_acquisition": 0.28,
    "performance_max": 0.38,
    "retargeting": 0.10,
    "demand_gen": 0.12,
}

# Frontend key → backend key (for daily_by_type_lang output)
_FRONTEND_KEYS: dict[str, str] = {
    "search_brand": "brand",
    "search_acquisition": "acquisition",
    "performance_max": "pmax",
    "retargeting": "retargeting",
    "demand_gen": "demand_gen",
}


def _select_campaign_types(total_monthly: float) -> tuple[list[str], Optional[str]]:
    """Return recommended campaign types + optional budget warning based on total monthly budget."""
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
    """Normalize base weights to active campaign types only."""
    raw = {k: _BASE_WEIGHTS[k] for k in recommended}
    total = sum(raw.values())
    return {k: round(v / total, 4) for k, v in raw.items()}


def _compute_daily(
    split: dict[str, float],
    total_monthly: float,
    languages: list[str],
) -> dict[str, dict[str, float]]:
    """Return daily budget per campaign type per language (frontend key → lang code → €/day)."""
    n_langs = max(len(languages), 1)
    result: dict[str, dict[str, float]] = {}
    for backend_key, pct in split.items():
        fe_key = _FRONTEND_KEYS[backend_key]
        monthly_type = total_monthly * pct
        daily_per_lang = monthly_type / n_langs / 30.44
        result[fe_key] = {lang.upper(): round(daily_per_lang, 2) for lang in languages}
    return result


@router.post("/budget-strategy")
async def suggest_budget_strategy(
    payload: BudgetStrategyRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
) -> BudgetStrategyResponse:
    """
    Recommend which campaign types to activate and how to distribute the budget,
    based on hotel context and total monthly spend.
    Returns recommended_types, budget_split (%), daily_by_type_lang (€/day), and AI-generated rationale.
    """
    settings = get_settings()

    recommended, warning = _select_campaign_types(payload.total_monthly_budget_eur)
    split = _compute_split(recommended)
    daily = _compute_daily(split, payload.total_monthly_budget_eur, payload.languages)

    # Build rationale via Claude if API key is available; otherwise use static fallback
    rationale: dict[str, str] = {}
    overall_strategy = ""

    _STATIC_RATIONALE: dict[str, str] = {
        "search_brand": "Protegge il traffico branded dalle OTA e intercetta utenti ad altissima intenzione d'acquisto con CPC contenuto e ROAS elevato.",
        "search_acquisition": "Intercetta utenti che cercano attivamente hotel nella tua destinazione. È il motore principale per acquisire nuovi clienti diretti.",
        "performance_max": "Campagna omnicanale (Search, Display, YouTube, Maps) che scala automaticamente su tutti i touchpoint Google. Fondamentale dopo brand e acquisition.",
        "retargeting": "Re-ingaggia i visitatori che hanno esplorato il sito senza prenotare. Alta probabilità di conversione a basso CPA.",
        "demand_gen": "Campagna awareness su YouTube, Discover e Gmail per raggiungere viaggiatori nella fase di ispirazione. Efficace con budget superiori a €3.000/mese.",
    }

    if settings.anthropic_api_key:
        type_labels = {
            "search_brand": "Brand Search",
            "search_acquisition": "Acquisition Search",
            "performance_max": "Performance Max",
            "retargeting": "Retargeting Display",
            "demand_gen": "Demand Gen",
        }
        langs_str = ", ".join(payload.languages)
        types_str = "\n".join(
            f"- {type_labels[t]}: {split[t]*100:.1f}% (€{payload.total_monthly_budget_eur * split[t]:.0f}/mese)"
            for t in recommended
        )
        prompt = f"""Sei uno stratega Google Ads specializzato in hotel e hospitality.
Genera un piano strategico conciso per questo hotel.

HOTEL: {payload.brand_name} — {payload.hotel_category} {payload.stars} stelle
PAESE: {payload.country}
LINGUE: {langs_str}
BUDGET MENSILE TOTALE: €{payload.total_monthly_budget_eur:.0f}

CAMPAGNE CONSIGLIATE:
{types_str}

Per ciascuna campagna scrivi UN PARAGRAFO di 2-3 frasi che spieghi:
1. Perché questa campagna è strategica per questo hotel
2. Quale obiettivo primario persegue
3. Un tip pratico specifico per il settore alberghiero

Scrivi anche un paragrafo "overall" di 2-3 frasi che riassuma la strategia complessiva e il razionale del budget.

Rispondi ESCLUSIVAMENTE con JSON valido, zero testo aggiuntivo:
{{
  "overall": "...",
  {', '.join(f'"{t}": "..."' for t in recommended)}
}}"""

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
            raw = json_match.group(1) if json_match else raw[raw.find('{'):raw.rfind('}') + 1]
            parsed = json.loads(raw)
            overall_strategy = parsed.get("overall", "")
            for t in recommended:
                rationale[t] = parsed.get(t, _STATIC_RATIONALE.get(t, ""))
        except Exception as exc:
            logger.warning(f"BudgetStrategy AI rationale failed: {exc}. Using static fallback.")
            for t in recommended:
                rationale[t] = _STATIC_RATIONALE.get(t, "")
            overall_strategy = (
                f"Strategia full-funnel con {len(recommended)} campagne per un budget di "
                f"€{payload.total_monthly_budget_eur:.0f}/mese. "
                "Le campagne sono ordinate per priorità di intento: brand protection → acquisizione → scalabilità."
            )
    else:
        for t in recommended:
            rationale[t] = _STATIC_RATIONALE.get(t, "")
        overall_strategy = (
            f"Strategia full-funnel con {len(recommended)} campagne per un budget di "
            f"€{payload.total_monthly_budget_eur:.0f}/mese. "
            "Le campagne sono ordinate per priorità di intento: brand protection → acquisizione → scalabilità."
        )

    return BudgetStrategyResponse(
        recommended_types=recommended,
        budget_split={k: round(v * 100, 1) for k, v in split.items()},  # percentages
        daily_by_type_lang=daily,
        rationale=rationale,
        overall_strategy=overall_strategy,
        min_budget_warning=warning,
    )


# ─── Type Copy ────────────────────────────────────────────────────────────────

@router.post("/type-copy")
async def suggest_type_copy(
    payload: TypeCopyRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """
    Generate per-type RSA headlines and descriptions for a hotel using Claude.
    campaign_type: "brand" | "acquisition" | "retargeting"
    Returns { headlines: [...], descriptions: [...] } ready to populate the brief form.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")

    camp_type = payload.campaign_type.lower()
    if camp_type not in _TYPE_COPY_PROMPTS:
        raise HTTPException(status_code=422, detail=f"campaign_type deve essere: brand, acquisition, retargeting")

    meta = _TYPE_COPY_PROMPTS[camp_type]
    lang_code = payload.language_code.upper()
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    services_txt = ", ".join(payload.services or []) or "non specificati"
    strengths_txt = ", ".join(payload.strengths or []) or "non specificati"
    usp_txt = payload.usp_main or "non specificata"

    prompt = f"""Sei un copywriter Google Ads specializzato in hotel e hospitality.
Genera RSA copy ad alto impatto per campagne {meta['label']} in lingua {lang_name}.

═══ CONTESTO CAMPAGNA ═══
{meta['context']}

═══ DATI HOTEL ═══
Hotel: {payload.brand_name}
Categoria: {payload.hotel_category} — {payload.stars} stelle
Dominio: {payload.domain or 'non specificato'}
USP principale: {usp_txt}
Servizi: {services_txt}
Punti di forza: {strengths_txt}
Lingua output: {lang_name} ({lang_code})

═══ REGOLE HEADLINE (≤ 30 caratteri — VERIFICA OGNI STRINGA) ═══
{meta['headline_rules']}

Come verificare: conta ogni carattere inclusi spazi e apostrofi.
"Miglior Tariffa Garantita" = 25 chars ✓ | "Prenota sul Sito Ufficiale" = 26 chars ✓
NON troncare le parole: se una parola non entra per intero, eliminala.

═══ REGOLE DESCRIZIONI (≤ 90 caratteri — VERIFICA OGNI STRINGA) ═══
{meta['description_rules']}

═══ OUTPUT ═══
Genera ESATTAMENTE questo JSON, zero testo aggiuntivo:
{{
  "headlines": [
    "headline specifica per questo hotel",
    "beneficio diretto e verificabile",
    "USP concreta non generica",
    "posizione o servizio reale",
    "vantaggio prenotazione diretta",
    "elemento esclusivo o urgency",
    "headline variante sul tema 2",
    "headline variante sul tema 3"
  ],
  "descriptions": [
    "Prima descrizione ≤90 chars: beneficio principale + CTA chiara e specifica per questo hotel.",
    "Seconda descrizione ≤90 chars: USP diversa + rassicurazione o incentivo concreto al soggiorno."
  ]
}}"""

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        logger.error(f"TypeCopy suggestion failed ({camp_type}): {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")

    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        else:
            start, end = raw.find('{'), raw.rfind('}')
            if start != -1 and end != -1:
                raw = raw[start:end + 1]
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"TypeCopy JSON parse error: {exc}\nRaw: {raw[:500]}")
        raise HTTPException(status_code=500, detail="Risposta AI non parsabile. Riprova.")

    headlines = [_trim_to_word(h, 30) for h in data.get("headlines", []) if isinstance(h, str) and h.strip()]
    descriptions = [_trim_to_word(d, 90) for d in data.get("descriptions", []) if isinstance(d, str) and d.strip()]

    return {"headlines": headlines, "descriptions": descriptions}
