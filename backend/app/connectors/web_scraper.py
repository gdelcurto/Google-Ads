"""
HTML scraping + sitemap parsing for hotel websites.

Public interface:
    scrape_hotel_site(url, languages) -> ScrapedSite
"""
from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_ROME = ZoneInfo("Europe/Rome")
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ── Language / sitemap constants ──────────────────────────────────────────────

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

# Language-code patterns found in URL paths or query strings.
_LANG_URL_PATTERNS: list[tuple[str, str]] = [
    (r'(?:^|/)([a-z]{2}-[a-z]{2})(?:/|$)', 'path_region'),
    (r'(?:^|/)([a-z]{2})(?:/|$)',           'path_lang'),
    (r'[?&](?:lang|language|hl|locale)=([a-z]{2}(?:-[a-z]{2})?)', 'query'),
]

# Keywords that signal a page is relevant for hotel content analysis.
_RELEVANCE_KW: list[tuple[str, int]] = [
    ('camer',        4), ('room',         4), ('stanz',        4),
    ('suite',        4), ('zimmer',       4), ('chambre',      4),
    ('alloggi',      3), ('accommod',     3), ('schlafzimmer', 3),
    ('servizi',      3), ('service',      3), ('facilit',      3),
    ('ameniti',      3), ('dotazioni',    3),
    ('wellness',     3), ('spa',          3), ('piscin',       3),
    ('pool',         3), ('ristoran',     3), ('restauran',    3),
    ('colazion',     2), ('breakfast',    2), ('bar',          1),
    ('offert',       2), ('offer',        2), ('pacchett',     2),
    ('package',      2), ('promo',        2), ('deal',         2),
    ('about',        2), ('chi-siamo',    2), ('chi_siamo',    2),
    ('struttura',    2), ('storia',       2), ('about-us',     2),
    ('esperien',     2), ('attivit',      2), ('activit',      2),
    ('experi',       2),
    ('privacy',     -5), ('cookie',      -5), ('legal',       -5),
    ('gdpr',        -5), ('booking',     -3), ('reserv',      -3),
    ('prenot',      -3), ('login',       -5), ('admin',       -5),
    ('sitemap',     -5), ('cart',        -5), ('checkout',    -5),
    ('feed',        -5), ('rss',         -5), ('wp-',         -5),
]


# ── Public result dataclass ───────────────────────────────────────────────────

@dataclass
class ScrapedSite:
    """Result of scraping a hotel website."""
    content: str                          # combined plain text (≤80 000 chars)
    lang_urls: Dict[str, List[str]]       # lang_code → list of page URLs from sitemap
    lang_landings: Dict[str, str]         # lang_code → best landing-page URL
    scan_log: List[dict] = field(default_factory=list)


# ── Scan-log helper ───────────────────────────────────────────────────────────

def scan_entry(level: str, msg: str) -> dict:
    """Create a structured scan-log entry."""
    return {"ts": datetime.now(_TZ_ROME).isoformat(), "level": level, "msg": msg}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _detect_lang_from_url(url: str) -> Optional[str]:
    """Return ISO-639-1 language code detected from URL path/query, or None."""
    parsed = urllib.parse.urlparse(url)
    target = parsed.path.lower() + '?' + parsed.query.lower()
    for pattern, _ in _LANG_URL_PATTERNS:
        m = re.search(pattern, target)
        if m:
            code = m.group(1).split('-')[0].upper()
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
        text = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', text)
        text = re.sub(r'<(/?)\w+:(\w)', r'<\1\2', text)
        return ET.fromstring(text)
    except Exception as exc:
        logger.warning(f"_fetch_xml {url}: {type(exc).__name__}: {exc}")
    return None


def _strip_html(html: str) -> str:
    """Remove HTML tags, scripts, styles. Return plain text max 10 000 chars."""
    html = re.sub(r'<(script|style|noscript)[^>]*>.*?</(script|style|noscript)>', ' ', html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&[a-z]+;', '', html)
    html = re.sub(r'\s+', ' ', html).strip()
    return html[:10000]


def _score_link(path: str, anchor: str) -> int:
    """Score a URL path + anchor text by relevance to hotel content."""
    combined = path.lower() + ' ' + anchor.lower()
    return sum(w for kw, w in _RELEVANCE_KW if kw in combined)


def _score_sitemap_url(url: str) -> int:
    """Score a sitemap URL for relevance to hotel content."""
    path = urllib.parse.urlparse(url).path.lower()
    return sum(w for kw, w in _RELEVANCE_KW if kw in path)


def _pick_lang_landing(lang_urls: Dict[str, List[str]], lang: str, base_url: str) -> Optional[str]:
    """
    From the sitemap's language → URL map, find the best landing page for a given language.
    Prefers root/homepage paths (shortest path length).
    """
    candidates = lang_urls.get(lang, [])
    if not candidates:
        return None

    def _path_depth(url: str) -> int:
        return len([p for p in urllib.parse.urlparse(url).path.split('/') if p])

    return min(candidates, key=_path_depth)


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
        if re.match(r'^(javascript|mailto|tel|data|#)', href, re.I):
            continue
        if re.search(r'\.(pdf|jpe?g|png|gif|svg|webp|css|js|xml|zip|mp4)(\?|$)', href, re.I):
            continue
        full_url = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(full_url)
        if parsed.scheme not in ('http', 'https') or parsed.netloc != base_domain:
            continue
        clean = urllib.parse.urlunparse(parsed._replace(query='', fragment=''))
        if clean in seen:
            continue
        seen.add(clean)
        anchor_text = re.sub(r'<[^>]+>', ' ', anchor_html).strip()
        score = _score_link(parsed.path, anchor_text)
        if score > 0:
            scored.append((score, clean))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [url for _, url in scored[:max_links]]


async def _probe_lang_url(
    client: httpx.AsyncClient,
    base_url: str,
    lang_code: str,
    slog: List[dict],
) -> Optional[str]:
    """
    Try common language-specific URL patterns when the sitemap has no data.
    Returns the final URL (after redirects) if HTTP 200 HTML, else None.
    """
    parsed = urllib.parse.urlparse(base_url)
    root   = f"{parsed.scheme}://{parsed.netloc}"
    slug   = lang_code.lower()

    for candidate in [f"{root}/{slug}/", f"{root}/{slug}"]:
        try:
            resp = await client.get(candidate)
            ct = resp.headers.get('content-type', '')
            if resp.status_code == 200 and 'text/html' in ct:
                final = str(resp.url)
                slog.append(scan_entry("info", f"    ✓ Trovata per sondaggio HTTP: {final}"))
                return final
        except Exception:
            pass

    slog.append(scan_entry("warn", f"    · Sondaggio {root}/{slug}[/] → nessuna risposta valida"))
    return None


async def _discover_sitemaps(
    base_url: str,
    client: httpx.AsyncClient,
    slog: List[dict],
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Discover all sitemaps and return:
      - lang_urls: dict mapping language code → list of page URLs
      - all_urls:  flat list of all page URLs
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
        count_before = len(all_urls)
        hreflang_count = 0
        for url_el in root.findall('.//url'):
            loc_el = url_el.find('loc')
            if loc_el is None or not loc_el.text:
                continue
            loc = loc_el.text.strip()
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
        note  = f", {hreflang_count} con hreflang" if hreflang_count else ""
        slog.append(scan_entry("info", f"  → {added} URL estratti{note}"))

    async def _process_sitemapindex(root: ET.Element) -> None:
        tasks = []
        for sm_el in root.findall('.//sitemap'):
            loc_el = sm_el.find('loc')
            if loc_el is None or not loc_el.text:
                continue
            sm_url = loc_el.text.strip()
            if sm_url in visited_sitemaps:
                continue
            visited_sitemaps.add(sm_url)
            if any(k in sm_url.lower() for k in ('image', 'video', 'news', '.kml')):
                slog.append(scan_entry("info", f"  ⊘ Ignorata (immagini/video/news): {sm_url}"))
                continue
            slog.append(scan_entry("info", f"  📄 Sub-sitemap: {sm_url}"))
            tasks.append(_fetch_and_process(sm_url))
        await asyncio.gather(*tasks)

    async def _fetch_and_process(sm_url: str) -> None:
        root = await _fetch_xml(client, sm_url)
        if root is None:
            slog.append(scan_entry("warn", f"  ✗ Impossibile leggere: {sm_url}"))
            return
        tag = root.tag.lower()
        if 'sitemapindex' in tag:
            slog.append(scan_entry("info", f"  🗂 Indice sitemap: {sm_url}"))
            await _process_sitemapindex(root)
        elif 'urlset' in tag:
            await _process_urlset(root, sm_url)

    sitemap_candidates = [
        f"{root_domain}/sitemap.xml",
        f"{root_domain}/sitemap_index.xml",
        f"{root_domain}/sitemap/sitemap.xml",
        f"{root_domain}/wp-sitemap.xml",
        f"{root_domain}/sitemap.xml.gz",
    ]

    slog.append(scan_entry("info", f"🔍 Controllo robots.txt: {root_domain}/robots.txt"))
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
                slog.append(scan_entry("info", f"  ✓ Trovate {len(extra)} direttive Sitemap in robots.txt"))
            else:
                slog.append(scan_entry("info", "  · Nessuna direttiva Sitemap in robots.txt"))
        else:
            slog.append(scan_entry("info", f"  · robots.txt non disponibile (HTTP {resp.status_code})"))
    except Exception:
        slog.append(scan_entry("info", "  · robots.txt non raggiungibile"))

    for candidate in sitemap_candidates:
        if candidate in visited_sitemaps:
            continue
        visited_sitemaps.add(candidate)
        slog.append(scan_entry("info", f"🗺 Tentativo sitemap: {candidate}"))
        root = await _fetch_xml(client, candidate)
        if root is None:
            slog.append(scan_entry("info", "  · Non trovata o non leggibile"))
            continue
        tag = root.tag.lower()
        if 'sitemapindex' in tag:
            slog.append(scan_entry("info", "  ✓ Indice sitemap trovato — elaborazione sub-sitemap..."))
            await _process_sitemapindex(root)
        elif 'urlset' in tag:
            slog.append(scan_entry("info", "  ✓ Sitemap trovata — estrazione URL..."))
            await _process_urlset(root, candidate)
        if all_urls:
            break

    if all_urls:
        lang_summary = ", ".join(f"{k}: {len(v)} URL" for k, v in lang_urls.items()) or "nessuna lingua rilevata"
        slog.append(scan_entry("info",
            f"✅ Sitemap completata — {len(all_urls)} URL totali | Lingue: {lang_summary}"))
    else:
        slog.append(scan_entry("warn", "⚠ Nessuna sitemap trovata — uso crawl homepage"))

    logger.info(f"Sitemap discovery: {len(all_urls)} total URLs, languages found: {list(lang_urls.keys())}")
    return lang_urls, all_urls


# ── Public interface ──────────────────────────────────────────────────────────

async def scrape_hotel_site(
    base_url: str,
    langs: Optional[List[str]] = None,
) -> ScrapedSite:
    """
    Fetch hotel website content using a sitemap-first strategy.

    Returns a ScrapedSite with:
      - content:       Combined plain text from fetched pages (≤ 80 000 chars)
      - lang_urls:     Dict lang_code → list of URLs found in sitemap
      - lang_landings: Dict lang_code → best landing page URL
      - scan_log:      Human-readable scan process log
    """
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url

    slog: List[dict] = []
    slog.append(scan_entry("info", f"🚀 Avvio scansione: {base_url}"))
    if langs:
        slog.append(scan_entry("info", f"🌐 Lingue richieste: {', '.join(langs)}"))

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8,de;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    collected:     list[str]              = []
    errors:        list[str]              = []
    homepage_html: str                    = ''
    lang_urls:     Dict[str, List[str]]   = {}
    lang_landings: Dict[str, str]         = {}

    async with httpx.AsyncClient(
        timeout=20.0, follow_redirects=True, verify=False, headers=headers,
    ) as client:

        # Step 1: homepage
        slog.append(scan_entry("info", f"🏠 Homepage: {base_url}"))
        try:
            resp = await client.get(base_url)
            ct = resp.headers.get('content-type', '')
            if resp.status_code == 200 and 'text/html' in ct:
                homepage_html = resp.text
                base_url = str(resp.url)
                text = _strip_html(homepage_html)
                if len(text) > 200:
                    collected.append(f"[{base_url}]\n{text}")
                    slog.append(scan_entry("info", f"  ✓ Homepage scaricata ({len(text):,} caratteri)"))
                    if str(resp.url) != base_url:
                        slog.append(scan_entry("info", f"  ↳ Redirect → {resp.url}"))
            else:
                errors.append(f"{base_url} → HTTP {resp.status_code}")
                slog.append(scan_entry("error", f"  ✗ Errore HTTP {resp.status_code}"))
        except Exception as exc:
            errors.append(f"{base_url} → {type(exc).__name__}: {exc}")
            slog.append(scan_entry("error", f"  ✗ Errore connessione: {exc}"))

        # Step 2: sitemap discovery
        slog.append(scan_entry("info", ""))
        slog.append(scan_entry("info", "━━ SCANSIONE SITEMAP ━━"))
        try:
            lang_urls, sitemap_all_urls = await _discover_sitemaps(base_url, client, slog)
        except Exception as exc:
            logger.warning(f"Sitemap discovery failed: {exc}")
            slog.append(scan_entry("warn", f"⚠ Sitemap discovery fallita: {exc}"))
            lang_urls, sitemap_all_urls = {}, []

        # Step 3: determine best landing page per language
        if langs:
            slog.append(scan_entry("info", ""))
            slog.append(scan_entry("info", "━━ LANDING PAGE PER LINGUA ━━"))
            for lang in langs:
                lang_name = LANG_NAMES.get(lang, lang)
                landing = _pick_lang_landing(lang_urls, lang, base_url)
                if landing:
                    lang_landings[lang] = landing
                    slog.append(scan_entry("info", f"  ✓ {lang} ({lang_name}): {landing}  [sitemap]"))
                    continue
                slog.append(scan_entry("info",
                    f"  · {lang} ({lang_name}): non trovata in sitemap — sondaggio /{lang.lower()}[/] ..."))
                probed = await _probe_lang_url(client, base_url, lang, slog)
                if probed:
                    lang_landings[lang] = probed
                else:
                    slog.append(scan_entry("warn",
                        f"  · {lang} ({lang_name}): nessuna landing specifica — verrà usata la homepage"))

        # Step 4: pick pages to fetch
        urls_to_fetch: list[str] = []
        if sitemap_all_urls:
            scored_sitemap = sorted(
                [(url, _score_sitemap_url(url)) for url in sitemap_all_urls],
                key=lambda x: x[1], reverse=True,
            )
            seen_fetch: set[str] = {base_url}
            for url, score in scored_sitemap:
                if score <= 0:
                    break
                if url not in seen_fetch:
                    seen_fetch.add(url)
                    urls_to_fetch.append(url)
                if len(urls_to_fetch) >= 15:
                    break
            for lang_landing in lang_landings.values():
                if lang_landing not in seen_fetch:
                    seen_fetch.add(lang_landing)
                    urls_to_fetch.append(lang_landing)

        if not urls_to_fetch and homepage_html:
            urls_to_fetch = _extract_relevant_links(homepage_html, base_url, max_links=10)
            if urls_to_fetch:
                slog.append(scan_entry("info", "  · Nessuna sitemap — link estratti dalla homepage"))

        # Step 5: fetch selected pages
        if urls_to_fetch:
            slog.append(scan_entry("info", ""))
            slog.append(scan_entry("info", f"━━ PAGINE SCARICATE ({len(urls_to_fetch)}) ━━"))
        for url in urls_to_fetch:
            if len('\n\n'.join(collected)) >= 80000:
                break
            try:
                resp = await client.get(url)
                ct = resp.headers.get('content-type', '')
                if resp.status_code == 200 and 'text/html' in ct:
                    text = _strip_html(resp.text)
                    if len(text) > 200:
                        collected.append(f"[{url}]\n{text}")
                        slog.append(scan_entry("info", f"  ✓ {url} ({len(text):,} car.)"))
                    else:
                        slog.append(scan_entry("info", f"  · {url} (contenuto troppo breve)"))
                else:
                    errors.append(f"{url} → HTTP {resp.status_code}")
                    slog.append(scan_entry("warn", f"  ✗ {url} → HTTP {resp.status_code}"))
            except Exception as exc:
                errors.append(f"{url} → {type(exc).__name__}: {exc}")
                slog.append(scan_entry("warn", f"  ✗ {url} → {exc}"))

    if not collected:
        detail = "Impossibile recuperare il sito web dal server. "
        if errors:
            detail += "Dettagli: " + " | ".join(errors)
        detail += " Usa la modalità manuale: incolla il testo del sito nell'apposita area."
        logger.warning(f"scrape_hotel_site failed for {base_url}: {errors}")
        slog.append(scan_entry("error", "✗ Scansione fallita — nessun contenuto recuperato"))
        raise HTTPException(status_code=422, detail=detail)

    result = '\n\n'.join(collected)[:80000]
    total_chars = len(result)
    slog.append(scan_entry("info", ""))
    slog.append(scan_entry("info",
        f"✅ Scansione completata — {len(collected)} pagine, {total_chars:,} caratteri totali"))
    logger.info(f"scrape_hotel_site: {len(collected)} pages, {total_chars} chars total")

    return ScrapedSite(
        content=result,
        lang_urls=lang_urls,
        lang_landings=lang_landings,
        scan_log=slog,
    )
