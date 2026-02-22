"""
AI-powered RSA copy generator using Claude.

For each ad group, calls Claude with the agent's GUIDELINES + SKILL_FILES
as system prompt and generates fresh, hotel-specific headlines and descriptions.

All generation is parallelized via asyncio.gather so an entire AccountPlan
can be enhanced in a single latency-bound call batch.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Optional

import anthropic

from app.agents.base import CampaignAgent
from app.domain.schemas.campaign_plan import CampaignPlan, CampaignType, PinnedHeadline
from app.skills import combined_skills

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief, LanguagePlan
    from app.domain.schemas.campaign_plan import AdGroupPlan, PMaxAssetGroup

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _json_object(raw: str) -> str:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        return m.group(1)
    s, e = raw.find("{"), raw.rfind("}")
    return raw[s : e + 1] if s != -1 and e != -1 else raw


def _trim(text: str, max_chars: int) -> str:
    """Trim to max_chars without breaking words."""
    text = text.rstrip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    space = cut.rfind(" ")
    return cut[:space] if space > 0 else cut


def _type_key(c: CampaignPlan) -> str:
    tv = c.campaign_type.value
    if tv == CampaignType.performance_max.value:
        return "performance_max"
    if tv == CampaignType.demand_gen.value:
        return "demand_gen"
    if tv == CampaignType.display.value:
        return "retargeting"
    if tv == CampaignType.search.value:
        return "search_brand" if c.campaign_subtype == "Brand" else "search_acquisition"
    return ""


def _extract_theme(ag_name: str) -> str:
    """'IT | Acquisition | Posizione' → 'Posizione' (skip match-type tokens)."""
    parts = [p.strip() for p in ag_name.split("|")]
    if len(parts) >= 3:
        last = parts[-1]
        if last.lower() not in ("exact", "phrase", "broad"):
            return last
    return ""


def _build_system(agent: CampaignAgent) -> str:
    parts = []
    if agent.SKILL_FILES:
        skills = combined_skills(*agent.SKILL_FILES)
        if skills:
            parts.append(f"═══ EXPERTISE ═══\n\n{skills}")
    parts.append(f"═══ GUIDELINES CAMPAGNA ═══\n\n{agent.GUIDELINES}")
    return "\n\n".join(parts)


def _hotel_ctx(brief: "Brief", lang: "LanguagePlan") -> str:
    h = brief.hotel_specifics
    lines = [
        f"Hotel: {brief.client.brand_name}",
        f"Categoria: {h.category.value} — {h.stars} stelle",
        f"Indirizzo: {h.location.address}",
        f"USP: {lang.usp.main}",
    ]
    if h.services:
        lines.append(f"Servizi: {', '.join(h.services[:8])}")
    if h.strengths:
        lines.append(f"Punti di forza: {', '.join(h.strengths[:5])}")
    if lang.brand_terms:
        lines.append(f"Brand terms: {', '.join(lang.brand_terms[:3])}")
    return "\n".join(lines)


# ── Main class ─────────────────────────────────────────────────────────────────

class AICopyGenerator:
    """
    Generates RSA / PMax / Display / DemandGen copy for every ad group via Claude.

    Usage:
        gen = AICopyGenerator(api_key)
        await gen.enhance_campaigns(campaigns, brief, agents_dict)
    """

    def __init__(self, api_key: str, model: str = _MODEL) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    # ── Core generation ────────────────────────────────────────────────────────

    async def generate_rsa(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        theme: str = "",
        pinned_text: Optional[str] = None,
        n_headlines: int = 10,
    ) -> tuple[list[str], list[str]]:
        """
        Generate n_headlines RSA headlines + 2-4 descriptions via Claude.
        Returns ([], []) on error so callers fall back to existing static copy.
        """
        system = _build_system(agent)
        ctx = _hotel_ctx(brief, lang)
        theme_line = f"\nTema ad group: {theme}" if theme else ""
        pin_line = (
            f"\nHEADLINE PINNATA obbligatoria in posizione 1: \"{pinned_text}\""
            if pinned_text else ""
        )

        prompt = (
            f"Genera RSA copy Google Ads ottimizzato per questo hotel.\n\n"
            f"═══ HOTEL ═══\n{ctx}\n"
            f"Lingua: {lang.name} ({lang.code}){theme_line}{pin_line}\n\n"
            f"═══ REGOLE ═══\n"
            f"- {n_headlines} headline SPECIFICHE e DIVERSE (≤30 caratteri — conta ogni carattere)\n"
            f"- 2-4 descrizioni (≤90 caratteri ciascuna)\n"
            f"- Ogni headline = UN argomento di vendita INDIPENDENTE\n"
            f"- Dati REALI dell'hotel, non inventare servizi o caratteristiche\n"
            f"- Scrivi in {lang.name}\n"
            f"- Rispetta le guidelines del tipo campagna\n\n"
            f"Rispondi SOLO con JSON valido:\n"
            f'{{\"headlines\": [\"h1\", ..., \"h{n_headlines}\"], \"descriptions\": [\"d1\", \"d2\"]}}'
        )

        try:
            msg = await self._client.messages.create(
                model=self._model,
                max_tokens=1000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = json.loads(_json_object(msg.content[0].text.strip()))
            headlines = [
                _trim(str(h), 30)
                for h in parsed.get("headlines", [])
                if isinstance(h, str) and h.strip()
            ]
            descriptions = [
                _trim(str(d), 90)
                for d in parsed.get("descriptions", [])
                if isinstance(d, str) and d.strip()
            ]
            return headlines, descriptions
        except Exception as exc:
            logger.warning(
                "AICopyGenerator.generate_rsa failed "
                f"[{agent.TYPE_KEY}/{lang.code}/theme={theme!r}]: {exc}"
            )
            return [], []

    # ── Per ad-group enhancers ─────────────────────────────────────────────────

    async def _enhance_rsa(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        ag: "AdGroupPlan",
    ) -> None:
        """Replace RSAd copy in-place with AI-generated copy."""
        theme = _extract_theme(ag.name)
        pinned = (
            lang.brand_terms[0]
            if agent.TYPE_KEY == "search_brand" and lang.brand_terms
            else None
        )
        headlines, descriptions = await self.generate_rsa(
            agent=agent, lang=lang, brief=brief, theme=theme, pinned_text=pinned
        )
        if not headlines:
            return
        for rsa in ag.ads:
            pinned_items = (
                [PinnedHeadline(text=pinned, pin_position=1)] if pinned else []
            )
            extra = [
                PinnedHeadline(text=h)
                for h in headlines
                if not pinned or h.lower() != pinned.lower()
            ]
            rsa.headlines = (pinned_items + extra)[:15]
            if descriptions:
                rsa.descriptions = descriptions[:4]

    async def _enhance_display(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        ag: "AdGroupPlan",
    ) -> None:
        """Replace Display ad copy in-place."""
        headlines, descriptions = await self.generate_rsa(
            agent=agent, lang=lang, brief=brief, n_headlines=5
        )
        if not headlines:
            return
        for display in ag.display_ads:
            display.headlines = headlines[:5]
            if descriptions:
                display.descriptions = descriptions[:5]

    async def _enhance_demand_gen(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        ag: "AdGroupPlan",
    ) -> None:
        """Replace Demand Gen ad copy in-place."""
        headlines, descriptions = await self.generate_rsa(
            agent=agent, lang=lang, brief=brief, n_headlines=5
        )
        if not headlines:
            return
        for dg in ag.demand_gen_ads:
            dg.headlines = headlines[:5]
            if descriptions:
                dg.descriptions = descriptions[:5]

    async def _enhance_pmax(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        ag: "PMaxAssetGroup",
    ) -> None:
        """Replace PMax asset group copy in-place."""
        headlines, descriptions = await self.generate_rsa(
            agent=agent, lang=lang, brief=brief, n_headlines=10
        )
        if not headlines:
            return
        ag.headlines = headlines[:15]
        if descriptions:
            ag.descriptions = descriptions[:5]

    # ── Top-level enhancer ─────────────────────────────────────────────────────

    async def enhance_campaigns(
        self,
        campaigns: list[CampaignPlan],
        brief: "Brief",
        agents: dict[str, CampaignAgent],
    ) -> None:
        """
        Enhance ALL campaigns with AI copy (mutates in-place).
        All ad groups across all campaigns are processed in parallel.
        """
        tasks = []
        for campaign in campaigns:
            tk = _type_key(campaign)
            if not tk or tk not in agents:
                continue
            agent = agents[tk]
            lang = brief.get_language(campaign.language_code)
            if not lang:
                continue

            for ag in campaign.ad_groups:
                if ag.ads:
                    tasks.append(self._enhance_rsa(agent, lang, brief, ag))
                if ag.display_ads:
                    tasks.append(self._enhance_display(agent, lang, brief, ag))
                if ag.demand_gen_ads:
                    tasks.append(self._enhance_demand_gen(agent, lang, brief, ag))

            for ag in campaign.pmax_asset_groups:
                tasks.append(self._enhance_pmax(agent, lang, brief, ag))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                logger.warning(
                    f"AICopyGenerator: {len(errors)}/{len(tasks)} tasks failed. "
                    "Affected ad groups kept static copy from brief."
                )
