"""Auto-fill brief from hotel website using AI (Claude)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, require_strategist_or_admin
from app.config import get_settings
from app.connectors.claude_enricher import ClaudeEnricher, run_autofill_job
from app.connectors.web_scraper import scrape_hotel_site, ScrapedSite, scan_entry
from app.database import AsyncSessionLocal, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autofill", tags=["autofill"])


# ── Request / Response models ─────────────────────────────────────────────────

class AutofillRequest(BaseModel):
    url: str
    languages: List[str] = ["IT", "EN"]
    content: Optional[str] = None


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
    campaign_type: str   # "brand" | "acquisition" | "retargeting"
    brand_name: str
    hotel_category: str
    stars: int
    language_code: str
    domain: Optional[str] = None
    usp_main: Optional[str] = None
    services: Optional[List[str]] = None
    strengths: Optional[List[str]] = None


class BudgetStrategyRequest(BaseModel):
    brand_name: str
    hotel_category: str
    stars: int
    languages: List[str]
    vertical: str = "hotel"
    country: str = "IT"
    total_monthly_budget_eur: float = 0.0


class BudgetStrategyResponse(BaseModel):
    recommended_types: List[str]
    budget_split: dict
    daily_by_type_lang: dict
    rationale: dict
    overall_strategy: str
    api_call_log: Optional[dict] = None
    suggested_total_monthly_eur: float
    min_budget_warning: Optional[str] = None
    ai_raw_response: Optional[str] = None
    ai_prompt_used: Optional[str] = None
    reasoning_steps: Optional[List[dict]] = None


class StartJobRequest(BaseModel):
    url: str
    languages: List[str] = ["IT", "EN"]
    project_id: str
    content: Optional[str] = None


class RegenerateRequest(BaseModel):
    languages: Optional[List[str]] = None


# ── DB helper (background tasks open their own session) ───────────────────────

async def _update_job_status(
    job_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    scraped: dict | None = None,
) -> None:
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
        if scraped is not None:
            job.scraped_json = json.dumps(scraped)
        if error is not None:
            job.error_message = str(error)[:2000]
        if status in ("completed", "failed"):
            job.completed_at = datetime.utcnow()
        await db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("")
async def autofill_from_url(
    payload: AutofillRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """Fetch a hotel website and generate a complete brief draft using Claude."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")

    langs = [l.upper() for l in payload.languages if l.strip()]
    if not langs:
        raise HTTPException(status_code=422, detail="Almeno una lingua richiesta")

    if payload.content and payload.content.strip():
        logger.info(f"Autofill: using manual content for {payload.url}")
        scraped = ScrapedSite(
            content=payload.content.strip()[:14000],
            lang_urls={},
            lang_landings={},
            scan_log=[scan_entry("info", "📋 Contenuto manuale fornito — scansione sito saltata")],
        )
    else:
        logger.info(f"Autofill: fetching {payload.url} for languages {langs}")
        scraped = await scrape_hotel_site(payload.url, langs)

    try:
        enricher = ClaudeEnricher(settings.anthropic_api_key)
        data, _ = await enricher.enrich_brief(scraped, langs, url=payload.url)
    except Exception as exc:
        logger.error(f"Anthropic call failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore chiamata AI: {exc}")

    logger.info(f"Autofill OK: {data.get('brand_name')} — {len(data.get('languages', []))} langs")
    return data


@router.post("/keywords")
async def suggest_keywords(
    payload: KeywordsRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """Generate acquisition keyword themes for a hotel using AI."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")
    try:
        enricher = ClaudeEnricher(settings.anthropic_api_key)
        result, log = await enricher.suggest_keywords(payload.model_dump())
    except Exception as exc:
        logger.error(f"Keywords suggestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")
    return {**result, "api_call_log": log}


@router.post("/sitelinks")
async def suggest_sitelinks(
    payload: SitelinksRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """Generate 4–6 Google Ads sitelinks for a hotel using AI."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")
    common = {
        "brand_name": payload.brand_name,
        "hotel_category": payload.hotel_category,
        "stars": payload.stars,
        "services": payload.services,
        "strengths": payload.strengths,
    }
    booking_url = payload.booking_engine_url or payload.landing_page
    try:
        enricher = ClaudeEnricher(settings.anthropic_api_key)
        sitelinks, log = await enricher.suggest_sitelinks(
            common, payload.language_code, payload.landing_page, booking_url
        )
    except Exception as exc:
        logger.error(f"Sitelinks suggestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")
    return {"sitelinks": sitelinks, "api_call_log": log}


@router.post("/type-copy")
async def suggest_type_copy(
    payload: TypeCopyRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
):
    """Generate per-type RSA headlines and descriptions using Claude."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")
    if payload.campaign_type.lower() not in ("brand", "acquisition", "retargeting"):
        raise HTTPException(status_code=422, detail="campaign_type deve essere: brand, acquisition, retargeting")
    common = {
        "brand_name": payload.brand_name,
        "hotel_category": payload.hotel_category,
        "stars": payload.stars,
        "domain": payload.domain,
        "services": payload.services,
        "strengths": payload.strengths,
    }
    try:
        enricher = ClaudeEnricher(settings.anthropic_api_key)
        copy, log = await enricher.suggest_type_copy(
            common, payload.language_code, payload.usp_main, payload.campaign_type.lower()
        )
    except Exception as exc:
        logger.error(f"TypeCopy suggestion failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore AI: {exc}")
    return {**copy, "api_call_log": log}


@router.post("/budget-strategy")
async def suggest_budget_strategy(
    payload: BudgetStrategyRequest,
    current_user: TokenData = Depends(require_strategist_or_admin),
) -> BudgetStrategyResponse:
    """Suggest campaign types, budget allocation and rationale based on hotel profile."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chiave API Anthropic non configurata. La strategia budget richiede l'AI.",
        )
    enricher = ClaudeEnricher(settings.anthropic_api_key)
    result = await enricher.suggest_budget_strategy(payload.model_dump())
    return BudgetStrategyResponse(**result)


@router.post("/jobs")
async def start_autofill_job(
    payload: StartJobRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Start a background auto-fill job and return the job ID immediately."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")

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
        run_autofill_job,
        job_id=job_id,
        url=payload.url,
        langs=langs,
        content=payload.content,
        api_key=settings.anthropic_api_key,
        update_status=_update_job_status,
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
    resp["has_scraped_data"] = bool(job.scraped_json)
    return resp


@router.post("/jobs/{job_id}/regenerate")
async def regenerate_from_cache(
    job_id: str,
    payload: RegenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the brief using cached scraped data — no re-scraping, no AI.

    Uses the website data persisted from the original scan to rebuild the
    enriched result.  If new languages are provided, the enrichment pipeline
    runs only for those languages (calling AI only for new per-type copies).
    If no languages are provided, the original result is returned as-is.
    """
    from sqlalchemy import select
    from app.domain.models import AutofillJob

    settings = get_settings()

    res = await db.execute(select(AutofillJob).where(AutofillJob.id == job_id))
    original_job = res.scalar_one_or_none()
    if not original_job:
        raise HTTPException(status_code=404, detail="Job non trovato")
    if not original_job.scraped_json:
        raise HTTPException(
            status_code=409,
            detail="Nessun dato scansionato disponibile per questo job. "
                   "Esegui una nuova scansione completa.",
        )

    original_langs = json.loads(original_job.languages_json)
    new_langs = (
        [l.upper() for l in payload.languages if l.strip()]
        if payload.languages
        else original_langs
    )

    # If the same languages are requested and we already have a result,
    # return the cached result immediately without any API call.
    if set(new_langs) == set(original_langs) and original_job.result_json:
        return {
            "job_id": original_job.id,
            "status": "completed",
            "result": json.loads(original_job.result_json),
            "from_cache": True,
        }

    # Different languages requested — need AI enrichment with cached scrape data
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chiave API Anthropic non configurata.")

    # Create a new job that reuses the scraped data
    new_job = AutofillJob(
        project_id=original_job.project_id,
        url=original_job.url,
        languages_json=json.dumps(new_langs),
        status="pending",
        scraped_json=original_job.scraped_json,
    )
    db.add(new_job)
    await db.flush()
    new_job_id = new_job.id

    # Run enrichment using cached scraped content (no HTTP scraping)
    scraped_data = json.loads(original_job.scraped_json)
    background_tasks.add_task(
        run_autofill_job,
        job_id=new_job_id,
        url=original_job.url,
        langs=new_langs,
        content=scraped_data["content"],
        api_key=settings.anthropic_api_key,
        update_status=_update_job_status,
    )

    logger.info(
        f"AutofillJob {new_job_id} (regenerate from {job_id}) "
        f"queued for project {original_job.project_id}"
    )
    return {"job_id": new_job_id, "status": "pending", "from_cache": False}
