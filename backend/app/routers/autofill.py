"""Auto-fill brief from hotel website using AI (Claude)."""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

import asyncio
from datetime import datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, require_strategist_or_admin
from app.config import get_settings
from app.database import AsyncSessionLocal, get_db

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

# ── Sitemap & multilingual URL detection ────────────────────────────────────

# Language-code patterns found in URL paths or query strings.
# Order matters: more specific patterns first.
_LANG_URL_PATTERNS: list[tuple[str, str]] = [
    # Path segments: /it/, /en-gb/, /de-ch/, etc.
    (r'(?:^|/)([a-z]{2}-[a-z]{2})(?:/|$)',   'path_region'),
    (r'(?:^|/)([a-z]{2})(?:/|$)',             'path_lang'),
    # Query string: ?lang=it, ?language=en, ?hl=de
    (r'[?&](?:lang|language|hl|locale)=([a-z]{2}(?:-[a-z]{2})?)', 'query'),
]

# Sitemap XML namespaces
_NS_SITEMAP  = 'http://www.sitemaps.org/schemas/sitemap/0.9'
_NS_XHTML    = 'http://www.w3.org/1999/xhtml'
_NS_IMAGE    = 'http://www.google.com/schemas/sitemap-image/1.1'


def _detect_lang_from_url(url: str) -> Optional[str]:
    """Return ISO-639-1 language code detected from URL path/query, or None."""
    parsed = urllib.parse.urlparse(url)
    target = parsed.path.lower() + '?' + parsed.query.lower()
    for pattern, _ in _LANG_URL_PATTERNS:
        m = re.search(pattern, target)
        if m:
            code = m.group(1).split('-')[0].upper()   # "en-gb" → "EN"
            if code in LANG_IDS:
                return code
    return None


async def _fetch_xml(client: httpx.AsyncClient, url: str) -> Optional[ET.Element]:
    """Fetch an XML document and return its parsed root, or None on error."""
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            logger.debug(f"_fetch_xml {url}: HTTP {resp.status_code}")
            return None
        text = resp.text.strip()
        if not text.startswith('<'):
            return None
        # 1. Strip namespace declarations (xmlns:foo="...") from opening tags
        text = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', text)
        # 2. Strip namespace prefixes from element names: <xhtml:link> → <link>, </xhtml:link> → </link>
        #    This must happen AFTER declaration removal so the prefix→URI mapping is already gone.
        text = re.sub(r'<(/?)\w+:(\w)', r'<\1\2', text)
        return ET.fromstring(text)
    except Exception as exc:
        logger.warning(f"_fetch_xml {url}: {type(exc).__name__}: {exc}")
    return None


def _scan_entry(level: str, msg: str) -> dict:
    """Create a structured scan log entry."""
    return {"ts": datetime.utcnow().isoformat(), "level": level, "msg": msg}


async def _discover_sitemaps(
    base_url: str,
    client: httpx.AsyncClient,
    scan_log: List[dict],
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Discover all sitemaps for a website and return:
      - lang_urls: dict mapping language code → list of page URLs found in sitemap
      - all_urls:  flat list of all page URLs (for relevance scoring)

    Strategy:
      1. Try /sitemap.xml (follows redirects to sitemap_index.xml automatically)
      2. Parse sitemap index → fetch each sub-sitemap
      3. For each <url><loc>, detect language from:
         a. <xhtml:link rel="alternate" hreflang=".."> inside the sitemap entry
         b. Language pattern in the URL path/query (/it/, /en/, ?lang=de, …)
      4. Also try robots.txt to find Sitemap: directives
    """
    parsed_base = urllib.parse.urlparse(base_url)
    root_domain  = f"{parsed_base.scheme}://{parsed_base.netloc}"

    lang_urls: Dict[str, List[str]] = {}
    all_urls:  List[str] = []
    visited_sitemaps: set[str] = set()

    def _add_url(url: str, lang: Optional[str]) -> None:
        all_urls.append(url)
        if lang:
            lang_urls.setdefault(lang, []).append(url)

    async def _process_urlset(root: ET.Element, source_url: str) -> None:
        """Extract <url> entries from a urlset element."""
        count_before = len(all_urls)
        hreflang_count = 0
        for url_el in root.findall('.//url'):
            loc_el = url_el.find('loc')
            if loc_el is None or not loc_el.text:
                continue
            loc = loc_el.text.strip()

            # Check xhtml:link alternates inside this <url> block
            alternates = url_el.findall('.//{http://www.w3.org/1999/xhtml}link') or \
                         url_el.findall('.//link')
            hreflang_found = False
            for link in alternates:
                hreflang = link.get('hreflang') or link.get('{http://www.w3.org/1999/xhtml}hreflang')
                href     = link.get('href')     or link.get('{http://www.w3.org/1999/xhtml}href')
                if hreflang and href and hreflang.lower() != 'x-default':
                    code = hreflang.split('-')[0].upper()
                    if code in LANG_IDS:
                        _add_url(href.strip(), code)
                        hreflang_found = True
                        hreflang_count += 1

            if not hreflang_found:
                lang = _detect_lang_from_url(loc)
                _add_url(loc, lang)

        added = len(all_urls) - count_before
        hreflang_note = f", {hreflang_count} con hreflang" if hreflang_count else ""
        scan_log.append(_scan_entry("info", f"  → {added} URL estratti{hreflang_note}"))

    async def _process_sitemapindex(root: ET.Element) -> None:
        """Fetch and process each <sitemap><loc> listed in a sitemapindex."""
        tasks = []
        for sm_el in root.findall('.//sitemap'):
            loc_el = sm_el.find('loc')
            if loc_el is None or not loc_el.text:
                continue
            sm_url = loc_el.text.strip()
            if sm_url in visited_sitemaps:
                continue
            visited_sitemaps.add(sm_url)

            # Skip image/video/news sitemaps — not useful for page content
            if any(k in sm_url.lower() for k in ('image', 'video', 'news', '.kml')):
                scan_log.append(_scan_entry("info", f"  ⊘ Ignorata (immagini/video/news): {sm_url}"))
                continue
            scan_log.append(_scan_entry("info", f"  📄 Sub-sitemap: {sm_url}"))
            tasks.append(_fetch_and_process(sm_url))
        await asyncio.gather(*tasks)

    async def _fetch_and_process(sm_url: str) -> None:
        root = await _fetch_xml(client, sm_url)
        if root is None:
            scan_log.append(_scan_entry("warn", f"  ✗ Impossibile leggere: {sm_url}"))
            return
        tag = root.tag.lower()
        if 'sitemapindex' in tag:
            scan_log.append(_scan_entry("info", f"  🗂 Indice sitemap: {sm_url}"))
            await _process_sitemapindex(root)
        elif 'urlset' in tag:
            await _process_urlset(root, sm_url)

    # 1. Try standard sitemap locations
    sitemap_candidates = [
        f"{root_domain}/sitemap.xml",
        f"{root_domain}/sitemap_index.xml",
        f"{root_domain}/sitemap/sitemap.xml",
        f"{root_domain}/wp-sitemap.xml",         # WordPress
        f"{root_domain}/sitemap.xml.gz",
    ]

    # 2. Also check robots.txt for Sitemap: directives
    scan_log.append(_scan_entry("info", f"🔍 Controllo robots.txt: {root_domain}/robots.txt"))
    try:
        resp = await client.get(f"{root_domain}/robots.txt")
        if resp.status_code == 200:
            extra = []
            for line in resp.text.splitlines():
                if line.lower().startswith('sitemap:'):
                    sm_url = line.split(':', 1)[1].strip()
                    if sm_url not in sitemap_candidates:
                        sitemap_candidates.insert(0, sm_url)
                        extra.append(sm_url)
            if extra:
                scan_log.append(_scan_entry("info", f"  ✓ Trovate {len(extra)} direttive Sitemap in robots.txt"))
            else:
                scan_log.append(_scan_entry("info", "  · Nessuna direttiva Sitemap in robots.txt"))
        else:
            scan_log.append(_scan_entry("info", f"  · robots.txt non disponibile (HTTP {resp.status_code})"))
    except Exception:
        scan_log.append(_scan_entry("info", "  · robots.txt non raggiungibile"))

    # 3. Fetch sitemaps (stop after first successful one that yields URLs)
    for candidate in sitemap_candidates:
        if candidate in visited_sitemaps:
            continue
        visited_sitemaps.add(candidate)
        scan_log.append(_scan_entry("info", f"🗺 Tentativo sitemap: {candidate}"))
        root = await _fetch_xml(client, candidate)
        if root is None:
            scan_log.append(_scan_entry("info", "  · Non trovata o non leggibile"))
            continue
        tag = root.tag.lower()
        if 'sitemapindex' in tag:
            scan_log.append(_scan_entry("info", f"  ✓ Indice sitemap trovato — elaborazione sub-sitemap..."))
            await _process_sitemapindex(root)
        elif 'urlset' in tag:
            scan_log.append(_scan_entry("info", f"  ✓ Sitemap trovata — estrazione URL..."))
            await _process_urlset(root, candidate)
        if all_urls:
            break  # found a working sitemap — no need to try fallbacks

    # Summary
    if all_urls:
        lang_summary = ", ".join(f"{k}: {len(v)} URL" for k, v in lang_urls.items()) or "nessuna lingua rilevata"
        scan_log.append(_scan_entry("info",
            f"✅ Sitemap completata — {len(all_urls)} URL totali | Lingue: {lang_summary}"))
    else:
        scan_log.append(_scan_entry("warn", "⚠ Nessuna sitemap trovata — uso crawl homepage"))

    logger.info(
        f"Sitemap discovery: {len(all_urls)} total URLs, "
        f"languages found: {list(lang_urls.keys())}"
    )
    return lang_urls, all_urls


def _pick_lang_landing(lang_urls: Dict[str, List[str]], lang: str, base_url: str) -> Optional[str]:
    """
    From the sitemap's language → URL map, find the best landing page for a given language.
    Prefers root/homepage paths (shortest path length) that belong to that language.
    """
    candidates = lang_urls.get(lang, [])
    if not candidates:
        return None

    def _path_depth(url: str) -> int:
        return len([p for p in urllib.parse.urlparse(url).path.split('/') if p])

    # Prefer shallowest path (most likely the language homepage)
    return min(candidates, key=_path_depth)


def _score_sitemap_url(url: str) -> int:
    """Score a sitemap URL for relevance to hotel content (same keywords as _score_link)."""
    path = urllib.parse.urlparse(url).path.lower()
    return sum(w for kw, w in _RELEVANCE_KW if kw in path)


def _build_lang_url_section(
    lang_landings: Dict[str, str],
    lang_urls: Dict[str, List[str]],
    langs: List[str],
) -> str:
    """
    Build a text block for the AI prompt describing discovered URLs per language.
    Returns empty string if no sitemap data was found.
    """
    if not lang_landings and not lang_urls:
        return ""

    lines = ["--- URL PER LINGUA (rilevati dalla sitemap del sito) ---"]
    for lang in langs:
        landing = lang_landings.get(lang)
        lang_name = LANG_NAMES.get(lang, lang)
        if landing:
            lines.append(f"{lang} ({lang_name}) — homepage: {landing}")
        # Add up to 5 relevant subpage URLs for this language
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

{lang_url_section}\
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

LANDING PAGE PER LINGUA (CRITICO):
- Usa ESATTAMENTE gli URL forniti nella sezione "URL per lingua" qui sopra.
- Se per una lingua è fornito un URL specifico, usalo come landing_page — NON inventare path.
- Se non è disponibile un URL specifico per quella lingua, usa la homepage principale.

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


# Keywords that signal a page is relevant for hotel content analysis.
# Each tuple: (substring_to_match, score_weight)
_RELEVANCE_KW: list[tuple[str, int]] = [
    # Rooms / accommodation — highest priority
    ('camer',        4), ('room',         4), ('stanz',        4),
    ('suite',        4), ('zimmer',       4), ('chambre',      4),
    ('alloggi',      3), ('accommod',     3), ('schlafzimmer', 3),
    # Services / facilities
    ('servizi',      3), ('service',      3), ('facilit',      3),
    ('ameniti',      3), ('dotazioni',    3),
    # Wellness / food
    ('wellness',     3), ('spa',          3), ('piscin',       3),
    ('pool',         3), ('ristoran',     3), ('restauran',    3),
    ('colazion',     2), ('breakfast',    2), ('bar',          1),
    # Offers / packages
    ('offert',       2), ('offer',        2), ('pacchett',     2),
    ('package',      2), ('promo',        2), ('deal',         2),
    # About / story
    ('about',        2), ('chi-siamo',    2), ('chi_siamo',    2),
    ('struttura',    2), ('storia',       2), ('about-us',     2),
    # Experience / activities
    ('esperien',     2), ('attivit',      2), ('activit',      2),
    ('experi',       2),
    # Low-value pages to de-rank (negative scores)
    ('privacy',     -5), ('cookie',      -5), ('legal',       -5),
    ('gdpr',        -5), ('booking',     -3), ('reserv',      -3),
    ('prenot',      -3), ('login',       -5), ('admin',       -5),
    ('sitemap',     -5), ('cart',        -5), ('checkout',    -5),
    ('feed',        -5), ('rss',         -5), ('wp-',         -5),
]


def _score_link(path: str, anchor: str) -> int:
    """Score a URL path + anchor text by relevance to hotel content."""
    combined = path.lower() + ' ' + anchor.lower()
    return sum(w for kw, w in _RELEVANCE_KW if kw in combined)


def _extract_relevant_links(html: str, base_url: str, max_links: int = 4) -> list[str]:
    """
    Parse <a href> tags from homepage HTML, keep only same-domain HTML links,
    score each by content relevance, return the top `max_links` URLs.
    """
    parsed_base = urllib.parse.urlparse(base_url)
    base_domain = parsed_base.netloc

    link_re = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    seen: set[str] = {base_url}
    scored: list[tuple[int, str]] = []

    for href, anchor_html in link_re.findall(html):
        href = href.strip()

        # Skip non-navigational schemes
        if re.match(r'^(javascript|mailto|tel|data|#)', href, re.I):
            continue
        # Skip non-HTML assets
        if re.search(r'\.(pdf|jpe?g|png|gif|svg|webp|css|js|xml|zip|mp4)(\?|$)', href, re.I):
            continue

        full_url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(full_url)

        # Internal links only (same domain, http/https)
        if parsed.scheme not in ('http', 'https') or parsed.netloc != base_domain:
            continue

        # Normalize: strip query string and fragment
        clean = urllib.parse.urlunparse(parsed._replace(query='', fragment=''))
        if clean in seen:
            continue
        seen.add(clean)

        anchor_text = re.sub(r'<[^>]+>', ' ', anchor_html).strip()
        score = _score_link(parsed.path, anchor_text)
        if score > 0:
            scored.append((score, clean))

    # Return top URLs by descending score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [url for _, url in scored[:max_links]]


async def _probe_lang_url(
    client: httpx.AsyncClient,
    base_url: str,
    lang_code: str,
    scan_log: List[dict],
) -> Optional[str]:
    """
    Try common language-specific URL patterns when the sitemap has no data for that language.
    Patterns tried (in order): /{lang}/, /{lang}
    Returns the final URL (after redirects) if HTTP 200 HTML, else None.
    """
    parsed = urllib.parse.urlparse(base_url)
    root   = f"{parsed.scheme}://{parsed.netloc}"
    slug   = lang_code.lower()   # EN → en, DE → de, IT → it

    for candidate in [f"{root}/{slug}/", f"{root}/{slug}"]:
        try:
            resp = await client.get(candidate)
            ct = resp.headers.get('content-type', '')
            if resp.status_code == 200 and 'text/html' in ct:
                final = str(resp.url)
                scan_log.append(_scan_entry("info", f"    ✓ Trovata per sondaggio HTTP: {final}"))
                return final
        except Exception:
            pass

    scan_log.append(_scan_entry("warn", f"    · Sondaggio {root}/{slug}[/] → nessuna risposta valida"))
    return None


async def _fetch_pages(
    base_url: str,
    langs: Optional[List[str]] = None,
) -> Tuple[str, Dict[str, List[str]], Dict[str, str], List[dict]]:
    """
    Fetch hotel website content using sitemap-first strategy.

    Returns:
      - content:       Combined plain text from fetched pages (≤ 14 000 chars)
      - lang_urls:     Dict lang_code → list of URLs found in sitemap for that language
      - lang_landings: Dict lang_code → best landing page URL for that language
      - scan_log:      Human-readable log of the scan process
    """
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url

    scan_log: List[dict] = []
    scan_log.append(_scan_entry("info", f"🚀 Avvio scansione: {base_url}"))
    if langs:
        scan_log.append(_scan_entry("info", f"🌐 Lingue richieste: {', '.join(langs)}"))

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8,de;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    collected: list[str] = []
    errors:    list[str] = []
    homepage_html = ''
    lang_urls:     Dict[str, List[str]] = {}
    lang_landings: Dict[str, str]       = {}

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        verify=False,
        headers=headers,
    ) as client:

        # ── Step 1: homepage ─────────────────────────────────────────────────
        scan_log.append(_scan_entry("info", f"🏠 Homepage: {base_url}"))
        try:
            resp = await client.get(base_url)
            ct = resp.headers.get('content-type', '')
            if resp.status_code == 200 and 'text/html' in ct:
                homepage_html = resp.text
                base_url = str(resp.url)  # final URL after redirects
                text = _strip_html(homepage_html)
                if len(text) > 200:
                    collected.append(f"[{base_url}]\n{text}")
                    scan_log.append(_scan_entry("info", f"  ✓ Homepage scaricata ({len(text):,} caratteri)"))
                    if str(resp.url) != base_url:
                        scan_log.append(_scan_entry("info", f"  ↳ Redirect → {resp.url}"))
            else:
                errors.append(f"{base_url} → HTTP {resp.status_code}")
                scan_log.append(_scan_entry("error", f"  ✗ Errore HTTP {resp.status_code}"))
        except Exception as exc:
            errors.append(f"{base_url} → {type(exc).__name__}: {exc}")
            scan_log.append(_scan_entry("error", f"  ✗ Errore connessione: {exc}"))

        # ── Step 2: sitemap discovery ─────────────────────────────────────────
        scan_log.append(_scan_entry("info", ""))
        scan_log.append(_scan_entry("info", "━━ SCANSIONE SITEMAP ━━"))
        try:
            lang_urls, sitemap_all_urls = await _discover_sitemaps(base_url, client, scan_log)
        except Exception as exc:
            logger.warning(f"Sitemap discovery failed: {exc}")
            scan_log.append(_scan_entry("warn", f"⚠ Sitemap discovery fallita: {exc}"))
            lang_urls, sitemap_all_urls = {}, []

        # ── Step 3: determine best landing page per language ──────────────────
        if langs:
            scan_log.append(_scan_entry("info", ""))
            scan_log.append(_scan_entry("info", "━━ LANDING PAGE PER LINGUA ━━"))
            for lang in langs:
                lang_name = LANG_NAMES.get(lang, lang)

                # a) Try sitemap data first
                landing = _pick_lang_landing(lang_urls, lang, base_url)
                if landing:
                    lang_landings[lang] = landing
                    scan_log.append(_scan_entry("info", f"  ✓ {lang} ({lang_name}): {landing}  [sitemap]"))
                    continue

                # b) Sitemap had no data for this lang → probe common path patterns
                scan_log.append(_scan_entry("info",
                    f"  · {lang} ({lang_name}): non trovata in sitemap — sondaggio /{lang.lower()}[/] ..."))
                probed = await _probe_lang_url(client, base_url, lang, scan_log)
                if probed:
                    lang_landings[lang] = probed
                else:
                    scan_log.append(_scan_entry("warn",
                        f"  · {lang} ({lang_name}): nessuna landing specifica — verrà usata la homepage"))

        # ── Step 4: pick pages to fetch ──────────────────────────────────────
        urls_to_fetch: list[str] = []

        if sitemap_all_urls:
            scored_sitemap = sorted(
                [(url, _score_sitemap_url(url)) for url in sitemap_all_urls],
                key=lambda x: x[1],
                reverse=True,
            )
            seen_fetch: set[str] = {base_url}
            for url, score in scored_sitemap:
                if score <= 0:
                    break
                if url not in seen_fetch:
                    seen_fetch.add(url)
                    urls_to_fetch.append(url)
                if len(urls_to_fetch) >= 6:
                    break

            for lang_landing in lang_landings.values():
                if lang_landing not in seen_fetch:
                    seen_fetch.add(lang_landing)
                    urls_to_fetch.append(lang_landing)

        if not urls_to_fetch and homepage_html:
            urls_to_fetch = _extract_relevant_links(homepage_html, base_url, max_links=5)
            if urls_to_fetch:
                scan_log.append(_scan_entry("info", "  · Nessuna sitemap — link estratti dalla homepage"))

        # ── Step 5: fetch selected pages ─────────────────────────────────────
        if urls_to_fetch:
            scan_log.append(_scan_entry("info", ""))
            scan_log.append(_scan_entry("info", f"━━ PAGINE SCARICATE ({len(urls_to_fetch)}) ━━"))
        for url in urls_to_fetch:
            if len('\n\n'.join(collected)) >= 14000:
                break
            try:
                resp = await client.get(url)
                ct = resp.headers.get('content-type', '')
                if resp.status_code == 200 and 'text/html' in ct:
                    text = _strip_html(resp.text)
                    if len(text) > 200:
                        collected.append(f"[{url}]\n{text}")
                        scan_log.append(_scan_entry("info", f"  ✓ {url} ({len(text):,} car.)"))
                    else:
                        scan_log.append(_scan_entry("info", f"  · {url} (contenuto troppo breve)"))
                else:
                    errors.append(f"{url} → HTTP {resp.status_code}")
                    scan_log.append(_scan_entry("warn", f"  ✗ {url} → HTTP {resp.status_code}"))
            except Exception as exc:
                errors.append(f"{url} → {type(exc).__name__}: {exc}")
                scan_log.append(_scan_entry("warn", f"  ✗ {url} → {exc}"))

    if not collected:
        detail = "Impossibile recuperare il sito web dal server. "
        if errors:
            detail += "Dettagli: " + " | ".join(errors)
        detail += " Usa la modalità manuale: incolla il testo del sito nell'apposita area."
        logger.warning(f"_fetch_pages failed for {base_url}: {errors}")
        scan_log.append(_scan_entry("error", "✗ Scansione fallita — nessun contenuto recuperato"))
        raise HTTPException(status_code=422, detail=detail)

    result = '\n\n'.join(collected)[:14000]
    total_chars = len(result)
    scan_log.append(_scan_entry("info", ""))
    scan_log.append(_scan_entry("info",
        f"✅ Scansione completata — {len(collected)} pagine, {total_chars:,} caratteri totali"))
    logger.info(f"_fetch_pages: {len(collected)} pages, {total_chars} chars total")
    return result, lang_urls, lang_landings, scan_log


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
            model="claude-haiku-4-5-20251001",
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
    lang_urls:     Dict[str, List[str]] = {}
    lang_landings: Dict[str, str]       = {}
    scan_log:      List[dict]           = []

    if payload.content and payload.content.strip():
        logger.info(f"Autofill: using manual content for {payload.url}, langs={langs}")
        content = payload.content.strip()[:14000]
        scan_log.append(_scan_entry("info", "📋 Contenuto manuale fornito — scansione sito saltata"))
    else:
        logger.info(f"Autofill: fetching {payload.url} for languages {langs}")
        content, lang_urls, lang_landings, scan_log = await _fetch_pages(payload.url, langs)

    # 2. Call Claude
    lang_url_section = _build_lang_url_section(lang_landings, lang_urls, langs)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        url=payload.url,
        languages=", ".join(langs),
        content=content,
        n_langs=len(langs),
        lang_url_section=lang_url_section,
    )

    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-6",
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

    # Override landing_page with sitemap-discovered URLs (deterministic — not AI-dependent)
    if lang_landings:
        scan_log.append(_scan_entry("info", ""))
        scan_log.append(_scan_entry("info", "━━ ASSEGNAZIONE LANDING PAGE ━━"))
        for lang in data.get('languages', []):
            code = lang.get('code', '')
            if code in lang_landings:
                old = lang.get('landing_page', '')
                lang['landing_page'] = lang_landings[code]
                if old != lang_landings[code]:
                    scan_log.append(_scan_entry("info",
                        f"  ✓ {code}: {lang_landings[code]} (AI suggeriva: {old or 'n/a'})"))
            else:
                scan_log.append(_scan_entry("warn",
                    f"  · {code}: nessuna landing specifica — mantenuto: {lang.get('landing_page', 'n/a')}"))

    data['_scan_log'] = scan_log
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
    languages: List[str]
    vertical: str = "hotel"
    country: str = "IT"
    # Optional: if provided, used as-is; if omitted, the agent suggests one
    total_monthly_budget_eur: float = 0.0


class BudgetStrategyResponse(BaseModel):
    recommended_types: List[str]
    budget_split: dict
    daily_by_type_lang: dict
    rationale: dict
    overall_strategy: str
    suggested_total_monthly_eur: float
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


def _suggest_budget(stars: int, hotel_category: str) -> float:
    """Heuristic monthly Google Ads budget based on hotel profile."""
    base: dict[int, float] = {1: 300, 2: 500, 3: 800, 4: 1500, 5: 3000}
    amount = base.get(min(max(stars, 1), 5), 800)
    cat = hotel_category.lower()
    if any(k in cat for k in ("resort", "luxury", "palazzo")):
        amount *= 1.4
    elif any(k in cat for k in ("boutique", "charme", "design")):
        amount *= 1.15
    return round(amount / 100) * 100  # round to nearest 100


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
    Suggest campaign types, budget allocation and rationale based on hotel profile.
    If total_monthly_budget_eur is 0 / omitted, the agent calculates a recommended budget
    from the hotel's stars and category. Returns recommended_types, budget_split (%),
    daily_by_type_lang (€/day), AI-generated rationale, and suggested_total_monthly_eur.
    """
    settings = get_settings()

    # Determine the working budget: use provided value or suggest one from profile
    total_monthly = (
        payload.total_monthly_budget_eur
        if payload.total_monthly_budget_eur > 0
        else _suggest_budget(payload.stars, payload.hotel_category)
    )

    recommended, warning = _select_campaign_types(total_monthly)
    split = _compute_split(recommended)
    daily = _compute_daily(split, total_monthly, payload.languages)

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
        budget_source = "suggerito in base al profilo hotel" if payload.total_monthly_budget_eur == 0 else "fornito dal cliente"
        types_str = "\n".join(
            f"- {type_labels[t]}: {split[t]*100:.1f}% (€{total_monthly * split[t]:.0f}/mese)"
            for t in recommended
        )
        prompt = f"""Sei uno stratega Google Ads specializzato in hotel e hospitality.
Genera un piano strategico per questo hotel basandoti sul suo profilo.

HOTEL: {payload.brand_name} — {payload.hotel_category} {payload.stars} stelle
PAESE: {payload.country}
LINGUE: {langs_str}
BUDGET MENSILE TOTALE: €{total_monthly:.0f} ({budget_source})

CAMPAGNE CONSIGLIATE (già calcolate in base al profilo):
{types_str}

Per ciascuna campagna scrivi UN PARAGRAFO di 2-3 frasi che spieghi:
1. Perché questa campagna è strategica specificamente per questo tipo di hotel
2. Quale obiettivo primario persegue nel funnel alberghiero
3. Un consiglio pratico concreto per il settore hospitality

Scrivi anche un paragrafo "overall" di 2-3 frasi che:
- Spieghi il razionale del budget consigliato (€{total_monthly:.0f}/mese) per questo profilo hotel
- Riassuma la strategia full-funnel scelta
- Indichi la priorità di attivazione delle campagne

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
                f"€{total_monthly:.0f}/mese, adeguato a un {payload.hotel_category} {payload.stars} stelle. "
                "Le campagne sono ordinate per priorità di intento: brand protection → acquisizione → scalabilità."
            )
    else:
        for t in recommended:
            rationale[t] = _STATIC_RATIONALE.get(t, "")
        overall_strategy = (
            f"Strategia full-funnel con {len(recommended)} campagne per un budget di "
            f"€{total_monthly:.0f}/mese, adeguato a un {payload.hotel_category} {payload.stars} stelle. "
            "Le campagne sono ordinate per priorità di intento: brand protection → acquisizione → scalabilità."
        )

    return BudgetStrategyResponse(
        recommended_types=recommended,
        budget_split={k: round(v * 100, 1) for k, v in split.items()},  # percentages
        daily_by_type_lang=daily,
        rationale=rationale,
        overall_strategy=overall_strategy,
        suggested_total_monthly_eur=total_monthly,
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
            model="claude-haiku-4-5-20251001",
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


# ─── Background Auto-fill Jobs ────────────────────────────────────────────────

class StartJobRequest(BaseModel):
    url: str
    languages: List[str] = ["IT", "EN"]
    project_id: str
    content: Optional[str] = None  # manual fallback: paste website text directly


@router.post("/jobs")
async def start_autofill_job(
    payload: StartJobRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a background auto-fill job and return the job ID immediately.
    The job fetches the hotel website, calls Claude Sonnet, and enriches each language
    with sitelinks and per-type RSA copies — all without blocking the HTTP response.
    Poll GET /api/autofill/jobs/{job_id} to check progress.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chiave API Anthropic non configurata. Imposta ANTHROPIC_API_KEY nel file .env",
        )
    langs = [lang.upper() for lang in payload.languages if lang.strip()]
    if not langs:
        raise HTTPException(status_code=422, detail="Almeno una lingua richiesta")

    from app.domain.models import AutofillJob

    job = AutofillJob(
        project_id=payload.project_id,
        url=payload.url,
        languages_json=json.dumps(langs),
        status="pending",
    )
    db.add(job)
    await db.flush()
    job_id = job.id

    background_tasks.add_task(
        _run_autofill_job,
        job_id=job_id,
        url=payload.url,
        langs=langs,
        content=payload.content,
        api_key=settings.anthropic_api_key,
    )

    logger.info(f"AutofillJob {job_id} queued for project {payload.project_id}")
    return {"job_id": job_id, "status": "pending"}


@router.get("/jobs/{job_id}")
async def get_autofill_job(
    job_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Poll the status and result of a background auto-fill job."""
    from sqlalchemy import select
    from app.domain.models import AutofillJob

    result = await db.execute(select(AutofillJob).where(AutofillJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    resp: dict = {
        "id": job.id,
        "project_id": job.project_id,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "result": None,
    }
    if job.status == "completed" and job.result_json:
        resp["result"] = json.loads(job.result_json)
    return resp


# ─── Background task helpers ──────────────────────────────────────────────────

async def _update_job_status(
    job_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    """Update an AutofillJob in a fresh DB session (safe to call from background tasks)."""
    from sqlalchemy import select
    from app.domain.models import AutofillJob

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(AutofillJob).where(AutofillJob.id == job_id))
        job = res.scalar_one_or_none()
        if not job:
            return
        job.status = status
        if result is not None:
            job.result_json = json.dumps(result)
        if error is not None:
            job.error_message = str(error)[:2000]
        if status in ("completed", "failed"):
            job.completed_at = datetime.utcnow()
        await db.commit()


async def _bg_sitelinks(
    client,
    common: dict,
    lang_code: str,
    landing_page: str,
    booking_url: str,
    sitemap_urls: Optional[List[str]] = None,
) -> list:
    """Generate sitelinks for one language inside the background task.

    sitemap_urls: real page URLs for this language discovered from the sitemap.
    When provided, the AI is instructed to use them as final_url values instead of guessing.
    """
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    services_txt = ", ".join(common.get("services") or []) or "non specificati"
    strengths_txt = ", ".join(common.get("strengths") or []) or "non specificati"
    bk = booking_url or landing_page

    # Build sitemap URL hint for the prompt
    sitemap_hint = ""
    if sitemap_urls:
        # Score and pick the most relevant real URLs to suggest for sitelinks
        scored = sorted(
            [(url, _score_sitemap_url(url)) for url in sitemap_urls if url != landing_page],
            key=lambda x: x[1],
            reverse=True,
        )
        top_urls = [url for url, _ in scored[:8]]
        if top_urls:
            sitemap_hint = (
                "\nURL REALI DEL SITO (usa questi come final_url dove pertinenti):\n"
                + "\n".join(f"  {u}" for u in top_urls)
                + "\n"
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
        "NON troncare le parole: se non entra, elimina l'ultima parola.\n\n"
        "REGOLE CONTENUTO:\n"
        "- final_url: usa gli URL reali forniti sopra quando disponibili; "
        "altrimenti adatta il path della landing page\n"
        f"- Scrivi in {lang_name}\n"
        "- 5 temi diversi: prenotazione diretta, offerte, camere, servizi, location\n\n"
        "Restituisci SOLO array JSON di 5 oggetti, zero testo aggiuntivo:\n"
        '[{"text":"...","description_1":"...","description_2":"...","final_url":"..."}]'
    )

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    m = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', raw, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        s, e = raw.find('['), raw.rfind(']')
        if s != -1 and e != -1:
            raw = raw[s:e + 1]
    sitelinks = json.loads(raw)
    return [
        {
            "text": _trim_to_word(str(sl.get("text", "")), 25),
            "description_1": _trim_to_word(str(sl.get("description_1", "")), 35),
            "description_2": _trim_to_word(str(sl.get("description_2", "")), 35),
            "final_url": str(sl.get("final_url", landing_page)),
        }
        for sl in sitelinks if isinstance(sl, dict) and sl.get("text")
    ]


async def _bg_type_copy(
    client, common: dict, lang_code: str, usp: str | None, campaign_type: str
) -> dict:
    """Generate RSA headlines/descriptions for one language + campaign type in the background task."""
    if campaign_type not in _TYPE_COPY_PROMPTS:
        return {"headlines": [], "descriptions": []}
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
        f"═══ REGOLE HEADLINE (≤ 30 caratteri) ═══\n{meta['headline_rules']}\n\n"
        f"═══ REGOLE DESCRIZIONI (≤ 90 caratteri) ═══\n{meta['description_rules']}\n\n"
        'Genera ESATTAMENTE questo JSON, zero testo aggiuntivo:\n'
        '{"headlines":["h1","h2","h3","h4","h5","h6","h7","h8"],"descriptions":["d1","d2"]}'
    )

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        s, e = raw.find('{'), raw.rfind('}')
        if s != -1 and e != -1:
            raw = raw[s:e + 1]
    parsed = json.loads(raw)
    return {
        "headlines": [_trim_to_word(h, 30) for h in parsed.get("headlines", []) if isinstance(h, str) and h.strip()],
        "descriptions": [_trim_to_word(d, 90) for d in parsed.get("descriptions", []) if isinstance(d, str) and d.strip()],
    }


async def _run_autofill_job(
    job_id: str, url: str, langs: List[str], content: Optional[str], api_key: str
) -> None:
    """
    Background task: orchestrate the complete auto-fill pipeline.
    1. Fetch hotel website (or use manual content).
    2. Call Claude Sonnet for the main brief JSON.
    3. For each language in parallel: sitelinks + brand/acquisition/retargeting RSA copies.
    4. Persist the enriched result in AutofillJob.result_json with status=completed|failed.
    """
    await _update_job_status(job_id, "running")
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)

        # 1. Fetch website content + sitemap data
        lang_urls:     Dict[str, List[str]] = {}
        lang_landings: Dict[str, str]       = {}
        scan_log:      List[dict]           = []

        if content and content.strip():
            page_content = content.strip()[:14000]
            scan_log.append(_scan_entry("info", "📋 Contenuto manuale fornito — scansione sito saltata"))
        else:
            page_content, lang_urls, lang_landings, scan_log = await _fetch_pages(url, langs)

        # 2. Main brief generation
        lang_url_section = _build_lang_url_section(lang_landings, lang_urls, langs)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            url=url,
            languages=", ".join(langs),
            content=page_content,
            n_langs=len(langs),
            lang_url_section=lang_url_section,
        )
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if m:
            raw = m.group(1)
        else:
            s, e = raw.find('{'), raw.rfind('}')
            if s != -1 and e != -1:
                raw = raw[s:e + 1]
        data = json.loads(raw)

        # Enrich language metadata
        for lang in data.get('languages', []):
            code = str(lang.get('code', '')).upper()
            lang['code'] = code
            if not lang.get('google_language_id'):
                lang['google_language_id'] = LANG_IDS.get(code, 0)
            if not lang.get('name'):
                lang['name'] = LANG_NAMES.get(code, code)
        data = _truncate_assets(data)

        # Override landing_page with sitemap-discovered URLs (deterministic — not AI-dependent)
        if lang_landings:
            scan_log.append(_scan_entry("info", ""))
            scan_log.append(_scan_entry("info", "━━ ASSEGNAZIONE LANDING PAGE ━━"))
            for lang in data.get('languages', []):
                code = lang.get('code', '')
                if code in lang_landings:
                    old = lang.get('landing_page', '')
                    lang['landing_page'] = lang_landings[code]
                    if old != lang_landings[code]:
                        scan_log.append(_scan_entry("info",
                            f"  ✓ {code}: {lang_landings[code]} (AI suggeriva: {old or 'n/a'})"))
                else:
                    scan_log.append(_scan_entry("warn",
                        f"  · {code}: nessuna landing specifica — mantenuto: {lang.get('landing_page', 'n/a')}"))

        data['_scan_log'] = scan_log

        # 3. Enrich each language with sitelinks + type copies (all in parallel)
        common = {
            "brand_name": data.get("brand_name", ""),
            "hotel_category": data.get("hotel_category", "city_hotel"),
            "stars": data.get("stars", 3),
            "services": data.get("services", []),
            "strengths": data.get("strengths", []),
        }
        booking_url = data.get("booking_engine_url") or f"https://{data.get('domain', '')}"

        async def _enrich_language(lang: dict) -> dict:
            code = lang.get("code", "IT")
            landing = lang.get("landing_page") or f"https://{data.get('domain', '')}"
            usp = lang.get("usp_main")
            # Real sitemap URLs for this language (used to build accurate sitelink final_urls)
            sitemap_lang_urls = lang_urls.get(code, [])

            async def _safe_sitelinks():
                try:
                    return await _bg_sitelinks(
                        client, common, code, landing, booking_url, sitemap_lang_urls
                    )
                except Exception as exc:
                    logger.warning(f"Job {job_id}: sitelinks failed for {code}: {exc}")
                    return []

            async def _safe_copy(ctype):
                try:
                    return await _bg_type_copy(client, common, code, usp, ctype)
                except Exception as exc:
                    logger.warning(f"Job {job_id}: type-copy {ctype} failed for {code}: {exc}")
                    return {"headlines": [], "descriptions": []}

            sl, brand, acq, ret = await asyncio.gather(
                _safe_sitelinks(),
                _safe_copy("brand"),
                _safe_copy("acquisition"),
                _safe_copy("retargeting"),
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
            }

        enriched = await asyncio.gather(*[_enrich_language(lang) for lang in data.get("languages", [])])
        data["languages"] = list(enriched)

        await _update_job_status(job_id, "completed", result=data)
        logger.info(f"AutofillJob {job_id} completed — brand: {data.get('brand_name')}")

    except Exception as exc:
        logger.error(f"AutofillJob {job_id} failed: {exc}", exc_info=True)
        await _update_job_status(job_id, "failed", error=str(exc))
