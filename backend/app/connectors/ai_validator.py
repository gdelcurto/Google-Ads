"""
AI-powered copy validator using Claude.

After AI copy generation, validates the enhanced RSA/PMax copy for each
(campaign_type, language) pair using the relevant agent's GUIDELINES +
SKILL_FILES as system prompt.

All validation is parallelized via asyncio.gather.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING

import anthropic

from app.agents.base import CampaignAgent, ValidationIssue
from app.connectors.ai_copy_generator import _build_system, _hotel_ctx, _type_key
from app.domain.schemas.campaign_plan import CampaignPlan

if TYPE_CHECKING:
    from app.domain.schemas.brief import Brief, LanguagePlan

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"


class AIValidator:
    """
    Validates AI-generated RSA / PMax / Display / DemandGen copy via Claude.

    Usage:
        validator = AIValidator(api_key)
        issues = await validator.validate_all(campaigns, brief, agents_dict)
    """

    def __init__(self, api_key: str, model: str = _MODEL) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def validate_copy(
        self,
        agent: CampaignAgent,
        lang: "LanguagePlan",
        brief: "Brief",
        headlines: list[str],
        descriptions: list[str],
        campaign_type_key: str,
    ) -> list[ValidationIssue]:
        """
        Ask Claude to review the generated copy for one (campaign_type, language).
        Returns [] on error so the pipeline is never blocked.
        """
        system = _build_system(agent)
        ctx = _hotel_ctx(brief, lang)

        hl_block = "\n".join(f"  {i + 1}. {h}" for i, h in enumerate(headlines))
        desc_block = "\n".join(f"  {i + 1}. {d}" for i, d in enumerate(descriptions))

        prompt = (
            f"Valida questa copy Google Ads generata per il seguente hotel.\n\n"
            f"═══ HOTEL ═══\n{ctx}\n\n"
            f"═══ COPY GENERATA ═══\n"
            f"Headlines ({len(headlines)}):\n{hl_block}\n\n"
            f"Descriptions ({len(descriptions)}):\n{desc_block}\n\n"
            f"═══ CRITERI DI VALUTAZIONE ═══\n"
            f"1. Headline specifiche per QUESTO hotel (non generiche per 'qualsiasi hotel')\n"
            f"2. Diversità reale (nessuna headline ripetitiva o quasi-identica)\n"
            f"3. Rispetto delle regole per campagna {campaign_type_key}\n"
            f"4. Dati fedeli all'hotel (nessuna caratteristica inventata)\n"
            f"5. Lunghezza: headline ≤30 caratteri, descrizioni ≤90 caratteri\n\n"
            f"Rispondi SOLO con un array JSON. Lista vuota se tutto è corretto.\n"
            f"Formato: "
            f'[{{"code": "CODICE", "message": "descrizione problema concreta", '
            f'"level": "warning", "blocks_publish": false}}]'
        )

        try:
            msg = await self._client.messages.create(
                model=self._model,
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            arr_match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not arr_match:
                return []
            parsed = json.loads(arr_match.group(0))
            issues: list[ValidationIssue] = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                message = str(item.get("message", "")).strip()
                if not message:
                    continue
                issues.append(ValidationIssue(
                    code=str(item.get("code", "AI_COPY_ISSUE")),
                    message=f"[AI/{lang.code}/{campaign_type_key}] {message}",
                    level="warning",
                    blocks_publish=False,
                    agent="AIValidator",
                    language=lang.code,
                ))
            return issues
        except Exception as exc:
            logger.warning(
                f"AIValidator.validate_copy failed [{campaign_type_key}/{lang.code}]: {exc}"
            )
            return []

    async def validate_all(
        self,
        campaigns: list[CampaignPlan],
        brief: "Brief",
        agents: dict[str, CampaignAgent],
    ) -> list[ValidationIssue]:
        """
        Validate copy for all (campaign_type, language) pairs in parallel.
        Returns merged list of all ValidationIssue objects found.
        """
        tasks: list = []
        seen: set[tuple[str, str]] = set()

        for campaign in campaigns:
            tk = _type_key(campaign)
            if not tk or tk not in agents:
                continue
            lang = brief.get_language(campaign.language_code)
            if not lang:
                continue

            pair = (tk, lang.code)
            if pair in seen:
                continue
            seen.add(pair)

            # Collect all unique headlines/descriptions for this campaign type + language
            all_headlines: list[str] = []
            all_descriptions: list[str] = []

            for ag in campaign.ad_groups:
                for rsa in ag.ads:
                    all_headlines.extend(ph.text for ph in rsa.headlines)
                    all_descriptions.extend(rsa.descriptions)
                for display in ag.display_ads:
                    all_headlines.extend(display.headlines)
                    all_descriptions.extend(display.descriptions)
                for dg in ag.demand_gen_ads:
                    all_headlines.extend(dg.headlines)
                    all_descriptions.extend(dg.descriptions)

            for ag in campaign.pmax_asset_groups:
                all_headlines.extend(ag.headlines)
                all_descriptions.extend(ag.descriptions)

            if not all_headlines:
                continue

            unique_headlines = list(dict.fromkeys(all_headlines))[:15]
            unique_descriptions = list(dict.fromkeys(all_descriptions))[:4]

            tasks.append(self.validate_copy(
                agent=agents[tk],
                lang=lang,
                brief=brief,
                headlines=unique_headlines,
                descriptions=unique_descriptions,
                campaign_type_key=tk,
            ))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_issues: list[ValidationIssue] = []
        errors = 0
        for r in results:
            if isinstance(r, list):
                all_issues.extend(r)
            elif isinstance(r, Exception):
                errors += 1
                logger.warning(f"AIValidator task failed: {r}")

        if errors:
            logger.warning(
                f"AIValidator: {errors}/{len(tasks)} validation tasks failed. "
                "Affected campaigns kept rule-based validation only."
            )

        return all_issues
