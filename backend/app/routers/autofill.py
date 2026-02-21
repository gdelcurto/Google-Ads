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
Sei un esperto certificato Google Ads per hotel e turismo.
Analizzi il contenuto di siti web di hotel e generi dati strutturati per campagne Google Ads.

REGOLE ASSOLUTE (non derogabili):
1. HEADLINE: massimo 30 caratteri ciascuna, spazi inclusi. Conta ogni carattere.
   Esempi OK: "Prenota Diretto Online" (22), "Hotel 4 Stelle Roma" (20)
   Esempi ERRATI: "Prenota sul Sito Ufficiale e Risparmia" (troppo lungo)
2. DESCRIZIONI: massimo 90 caratteri ciascuna, spazi inclusi.
3. CALLOUT: massimo 25 caratteri ciascuno, spazi inclusi.
4. Genera solo contenuti REALI trovati nel sito. Non inventare servizi non menzionati.
5. Le headline devono avere un beneficio o CTA chiaro, specifico per quell'hotel.
6. Rispondi ESCLUSIVAMENTE con JSON valido, zero testo aggiuntivo.
"""

USER_PROMPT_TEMPLATE = """\
Analizza il seguente sito web di un hotel e genera un brief strutturato per Google Ads.

URL: {url}
Lingue richieste: {languages}

--- CONTENUTO DEL SITO ---
{content}
--- FINE CONTENUTO ---

Genera il JSON con questa struttura esatta:
{{
  "brand_name": "Nome commerciale dell'hotel",
  "brand_slug": "nome-in-slug",
  "domain": "www.dominio.it",
  "country": "IT",
  "hotel_category": "city_hotel|resort|boutique|business|agriturismo",
  "stars": 4,
  "rooms": null,
  "address": "Via Esempio 1, 00100 Roma",
  "services": ["Piscina", "Spa", "Ristorante"],
  "strengths": ["Posizione centrale", "Vista panoramica"],
  "booking_engine_url": "https://www.dominio.it/prenota",
  "target_countries": ["IT", "DE", "GB"],
  "languages": [
    {{
      "code": "IT",
      "name": "Italiano",
      "google_language_id": 1004,
      "landing_page": "https://www.dominio.it/",
      "brand_terms": ["nome hotel", "variante 1", "variante 2"],
      "usp_main": "Proposta di valore unica max 90 caratteri",
      "headlines": [
        "Max 30 Caratteri Ciascuna",
        "Prenota Diretto Online",
        "Miglior Tariffa Garantita",
        "Posizione Centrale",
        "Colazione Inclusa",
        "Cancellazione Gratuita",
        "Wi-Fi Gratuito",
        "Navetta Aeroporto"
      ],
      "descriptions": [
        "Descrizione di max 90 caratteri con beneficio principale e call to action chiaro.",
        "Seconda descrizione con altri vantaggi e differenziatori reali dell'hotel. Max 90."
      ],
      "callouts": [
        "Miglior Prezzo",
        "Cancellazione Gratis",
        "Wi-Fi Gratuito",
        "Check-in Flessibile"
      ]
    }}
  ]
}}

Genera {n_langs} oggetti nella lista "languages", uno per ciascuna lingua: {languages}.
Per ogni lingua, scrivi headline, descrizioni e callout nella lingua corretta.
Brand terms: come gli utenti cercano l'hotel su Google in quella lingua.
Callouts: sintetici, fatti concreti dell'hotel.
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


def _truncate_assets(data: dict) -> dict:
    """Post-process: hard-truncate headlines/descriptions/callouts to Google Ads limits."""
    for lang in data.get('languages', []):
        lang['headlines'] = [h[:30] for h in lang.get('headlines', [])]
        lang['descriptions'] = [d[:90] for d in lang.get('descriptions', [])]
        lang['callouts'] = [c[:25] for c in lang.get('callouts', [])]
        if lang.get('usp_main'):
            lang['usp_main'] = lang['usp_main'][:90]
    return data


class AutofillRequest(BaseModel):
    url: str
    languages: List[str] = ["IT", "EN"]
    content: Optional[str] = None  # manual fallback: paste website text directly


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
