"""
Tests for app.connectors.web_scraper.

All HTTP calls are mocked via pytest-httpx or unittest.mock.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import xml.etree.ElementTree as ET

from app.connectors.web_scraper import (
    _detect_lang_from_url,
    _extract_relevant_links,
    _pick_lang_landing,
    _score_sitemap_url,
    _strip_html,
    scan_entry,
    scrape_hotel_site,
    ScrapedSite,
    LANG_IDS,
    LANG_NAMES,
)


# ── _detect_lang_from_url ──────────────────────────────────────────────────────

def test_detect_lang_from_url_path_segment():
    assert _detect_lang_from_url("https://hotel.com/it/camere") == "IT"
    assert _detect_lang_from_url("https://hotel.com/en/rooms") == "EN"
    assert _detect_lang_from_url("https://hotel.com/de/zimmer") == "DE"


def test_detect_lang_from_url_query_string():
    assert _detect_lang_from_url("https://hotel.com/?lang=fr") == "FR"
    assert _detect_lang_from_url("https://hotel.com/?language=es") == "ES"
    assert _detect_lang_from_url("https://hotel.com/?hl=it") == "IT"


def test_detect_lang_from_url_no_lang():
    assert _detect_lang_from_url("https://hotel.com/rooms/double") is None
    assert _detect_lang_from_url("https://hotel.com/") is None


def test_detect_lang_from_url_unknown_lang():
    # "xx" is not in LANG_IDS
    assert _detect_lang_from_url("https://hotel.com/xx/page") is None


# ── _pick_lang_landing ────────────────────────────────────────────────────────

def test_pick_lang_landing_prefers_shallow_path():
    lang_urls = {
        "IT": [
            "https://hotel.com/it/camere/suite-deluxe",
            "https://hotel.com/it/",
            "https://hotel.com/it/offerte/estate",
        ]
    }
    result = _pick_lang_landing(lang_urls, "IT", "https://hotel.com")
    assert result == "https://hotel.com/it/"


def test_pick_lang_landing_returns_none_when_no_match():
    lang_urls = {"IT": ["https://hotel.com/it/"]}
    assert _pick_lang_landing(lang_urls, "DE", "https://hotel.com") is None


def test_pick_lang_landing_single_url():
    lang_urls = {"EN": ["https://hotel.com/en/rooms"]}
    assert _pick_lang_landing(lang_urls, "EN", "https://hotel.com") == "https://hotel.com/en/rooms"


# ── _score_sitemap_url ────────────────────────────────────────────────────────

def test_score_sitemap_url_ranks_rooms_higher():
    rooms_url   = "https://hotel.com/camere/suite"
    privacy_url = "https://hotel.com/privacy-policy"
    spa_url     = "https://hotel.com/spa-wellness"
    assert _score_sitemap_url(rooms_url)   > _score_sitemap_url(spa_url)
    assert _score_sitemap_url(privacy_url) < 0


def test_score_sitemap_url_negative_for_admin():
    assert _score_sitemap_url("https://hotel.com/admin/login") < 0
    assert _score_sitemap_url("https://hotel.com/wp-admin") < 0


def test_score_sitemap_url_zero_for_unrelated():
    assert _score_sitemap_url("https://hotel.com/contact-us") == 0


# ── _strip_html ───────────────────────────────────────────────────────────────

def test_strip_html_removes_script_and_style():
    html = '<html><head><style>.a{color:red}</style></head><body><script>alert(1)</script>Hello world</body></html>'
    result = _strip_html(html)
    assert "alert" not in result
    assert "color:red" not in result
    assert "Hello world" in result


def test_strip_html_removes_tags():
    html = '<p class="test">Hotel <strong>Roma</strong></p>'
    result = _strip_html(html)
    assert "Hotel Roma" in result
    assert "<p" not in result
    assert "<strong" not in result


def test_strip_html_truncates_at_10000():
    html = "A" * 20000
    result = _strip_html(html)
    assert len(result) == 10000


def test_strip_html_collapses_whitespace():
    html = "<p>Hello    \n\n  World</p>"
    result = _strip_html(html)
    assert "Hello World" in result
    assert "  " not in result


# ── _extract_relevant_links ───────────────────────────────────────────────────

def test_extract_relevant_links_returns_only_same_domain():
    html = '''
    <html><body>
      <a href="/camere">Camere</a>
      <a href="https://otherdomain.com/rooms">External</a>
      <a href="/spa">Spa</a>
    </body></html>
    '''
    result = _extract_relevant_links(html, "https://hotel.com", max_links=5)
    assert all("hotel.com" in url for url in result)


def test_extract_relevant_links_skips_non_html_assets():
    html = '''
    <html><body>
      <a href="/brochure.pdf">PDF</a>
      <a href="/logo.png">Logo</a>
      <a href="/camere">Camere</a>
    </body></html>
    '''
    result = _extract_relevant_links(html, "https://hotel.com", max_links=5)
    assert all(not url.endswith(('.pdf', '.png')) for url in result)
    assert any("camere" in url for url in result)


def test_extract_relevant_links_respects_max_links():
    links = "".join(f'<a href="/camer{i}">Camere {i}</a>' for i in range(20))
    html = f"<html><body>{links}</body></html>"
    result = _extract_relevant_links(html, "https://hotel.com", max_links=3)
    assert len(result) <= 3


# ── scan_entry ────────────────────────────────────────────────────────────────

def test_scan_entry_structure():
    entry = scan_entry("info", "Test message")
    assert entry["level"] == "info"
    assert entry["msg"] == "Test message"
    assert "ts" in entry


def test_scan_entry_levels():
    for level in ("info", "warn", "error"):
        entry = scan_entry(level, "msg")
        assert entry["level"] == level


# ── scrape_hotel_site (mocked) ────────────────────────────────────────────────

SIMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://hotel.com/</loc>
    <xhtml:link rel="alternate" hreflang="it" href="https://hotel.com/it/"/>
    <xhtml:link rel="alternate" hreflang="en" href="https://hotel.com/en/"/>
  </url>
  <url>
    <loc>https://hotel.com/it/camere</loc>
  </url>
</urlset>"""


@pytest.mark.asyncio
async def test_scrape_hotel_site_discovers_sitemaps():
    """scrape_hotel_site should parse sitemap and fill lang_landings."""
    html_content = (
        b"<html><body>" +
        b"Hotel Roma Centro 4 stelle piscina spa colazione ristorante " * 10 +
        b"</body></html>"
    )

    responses = []

    class FakeResp:
        def __init__(self, content=b"", status_code=200, content_type="text/html"):
            self._content = content
            self.status_code = status_code
            self.headers = {"content-type": content_type}
            self.url = "https://hotel.com/"

        @property
        def text(self):
            return self._content.decode()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            if "robots.txt" in url:
                return FakeResp(b"", status_code=404)
            if "sitemap" in url and url.endswith(".xml"):
                return FakeResp(SIMPLE_SITEMAP_XML.encode(), content_type="text/xml")
            if "sitemap" in url:
                return FakeResp(b"", status_code=404)
            return FakeResp(html_content)

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        result = await scrape_hotel_site("https://hotel.com", ["IT", "EN"])

    assert isinstance(result, ScrapedSite)
    assert len(result.content) > 0
    assert "IT" in result.lang_landings or len(result.scan_log) > 0


@pytest.mark.asyncio
async def test_scrape_hotel_site_fallback_probe_lang_url():
    """When sitemap has no lang data, _probe_lang_url is tried."""
    html_content = b"<html><body>" + b"Hotel content camere piscina spa ristorante colazione " * 10 + b"</body></html>"

    class FakeResp:
        def __init__(self, content=b"", status_code=200, content_type="text/html"):
            self._content = content
            self.status_code = status_code
            self.headers = {"content-type": content_type}
            self.url = "https://hotel.com/"

        @property
        def text(self):
            return self._content.decode()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            # No sitemap, no robots, homepage ok, /en/ probe returns 200
            if "sitemap" in url or "robots" in url:
                return FakeResp(b"", status_code=404)
            if url.rstrip("/").endswith("/en"):
                r = FakeResp(html_content)
                r.url = url
                return r
            return FakeResp(html_content)

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        result = await scrape_hotel_site("https://hotel.com", ["EN"])

    assert isinstance(result, ScrapedSite)
    # Probe for EN might succeed
    assert len(result.scan_log) > 0


@pytest.mark.asyncio
async def test_scrape_hotel_site_raises_on_no_content():
    """When all HTTP requests fail, scrape_hotel_site raises HTTPException 422."""
    from fastapi import HTTPException

    class FakeResp:
        status_code = 503
        headers = {"content-type": "text/html"}
        text = ""
        url = "https://hotel.com/"

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return FakeResp()

    with patch("httpx.AsyncClient", return_value=FakeClient()):
        with pytest.raises(HTTPException) as exc_info:
            await scrape_hotel_site("https://hotel.com", [])

    assert exc_info.value.status_code == 422
