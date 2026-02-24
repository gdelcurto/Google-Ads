"""Campaign generation and preview routes."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, require_strategist_or_admin
from app.config import Settings, get_settings
from app.database import get_db
from app.domain.models import AuditLog, CampaignRecord, Project
from app.domain.schemas.brief import Brief
from app.domain.schemas.campaign_plan import AccountPlan
from app.generators.orchestrator import CampaignOrchestrator, _campaign_type_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["campaigns"])
orchestrator = CampaignOrchestrator()


@router.post("/{project_id}/generate")
async def generate_campaign_plan(
    project_id: str,
    dry_run: bool = True,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Generate the full campaign plan from the project's brief.
    Returns a preview of all campaigns, ad groups, and assets.
    """
    project = await _get_project_or_404(project_id, db)

    if not project.brief_json:
        raise HTTPException(status_code=400, detail="Brief non caricato. Carica prima il brief.")

    try:
        brief = Brief(**json.loads(project.brief_json))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Brief non valido: {exc}")

    # Get existing campaigns for idempotency
    result = await db.execute(
        select(CampaignRecord).where(CampaignRecord.project_id == project_id)
    )
    existing = [
        {
            "external_key": c.external_key,
            "google_ads_campaign_id": c.google_ads_campaign_id,
        }
        for c in result.scalars().all()
    ]

    try:
        if settings.anthropic_api_key:
            plan = await orchestrator.generate_plan_ai(
                brief=brief,
                project_id=project_id,
                api_key=settings.anthropic_api_key,
                dry_run=dry_run,
                existing_campaigns=existing,
            )
        else:
            plan = orchestrator.generate_plan(
                brief=brief,
                project_id=project_id,
                dry_run=dry_run,
                existing_campaigns=existing,
            )
    except Exception as exc:
        logger.error(f"Generation failed for project {project_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore generazione: {exc}")

    # Persist plan to project
    project.plan_json = plan.model_dump_json()
    project.status = "preview"

    # Upsert campaign records
    existing_keys = {c["external_key"] for c in existing}
    for campaign in plan.campaigns:
        if campaign.external_key not in existing_keys:
            record = CampaignRecord(
                project_id=project_id,
                external_key=campaign.external_key,
                campaign_name=campaign.campaign_name,
                campaign_type=campaign.campaign_type.value,
                language_code=campaign.language_code,
                budget_daily=campaign.settings.budget_daily_eur,
                can_publish=campaign.can_publish,
                plan_json=campaign.model_dump_json(),
            )
            db.add(record)
        else:
            # Update existing record
            result2 = await db.execute(
                select(CampaignRecord).where(
                    CampaignRecord.project_id == project_id,
                    CampaignRecord.external_key == campaign.external_key,
                )
            )
            record = result2.scalar_one_or_none()
            if record:
                record.budget_daily = campaign.settings.budget_daily_eur
                record.can_publish = campaign.can_publish
                record.plan_json = campaign.model_dump_json()

    log = AuditLog(
        project_id=project_id,
        user_id=current_user.user_id,
        action="generate_plan",
        entity_type="project",
        entity_id=project_id,
        details=json.dumps({
            "dry_run": dry_run,
            "campaigns_count": len(plan.campaigns),
            "is_valid": plan.is_valid,
            "publish_ready": plan.publish_ready,
        }),
    )
    db.add(log)

    return _plan_to_preview(plan)


@router.put("/{project_id}/plan")
async def save_plan_json(
    project_id: str,
    plan_data: dict,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Save a manually edited plan JSON back to the project."""
    project = await _get_project_or_404(project_id, db)
    try:
        plan = AccountPlan(**plan_data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Piano JSON non valido: {exc}")

    project.plan_json = plan.model_dump_json()

    log = AuditLog(
        project_id=project_id,
        user_id=current_user.user_id,
        action="save_plan_manual",
        entity_type="project",
        entity_id=project_id,
        details=json.dumps({"campaigns_count": len(plan.campaigns)}),
    )
    db.add(log)

    return {"status": "ok", "campaigns": len(plan.campaigns)}


@router.get("/{project_id}/plan")
async def get_plan(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get the previously generated plan for a project."""
    project = await _get_project_or_404(project_id, db)
    if not project.plan_json:
        raise HTTPException(status_code=404, detail="Piano non ancora generato. Esegui /generate prima.")
    try:
        plan = AccountPlan(**json.loads(project.plan_json))
    except Exception as exc:
        logger.error(f"Plan deserialization failed for project {project_id}: {exc}")
        raise HTTPException(
            status_code=422,
            detail=f"Piano salvato non valido. Rigenera il piano. Dettaglio: {exc}",
        )
    return _plan_to_preview(plan)


def _plan_to_preview(plan: AccountPlan) -> dict:
    """Serialize plan to a UI-friendly preview structure."""
    return {
        "project_id": plan.project_id,
        "client_name": plan.client_name,
        "generated_at": plan.generated_at.isoformat(),
        "is_valid": plan.is_valid,
        "publish_ready": plan.publish_ready,
        "total_campaigns": plan.total_campaigns,
        "validation_errors": plan.validation_errors,
        "validation_warnings": plan.validation_warnings,
        # Structured warnings carry optional suggested_fix for frontend CTAs.
        # Each item: {message, code, level, agent, suggested_fix?}
        "validation_warnings_structured": plan.validation_warnings_structured,
        "campaigns": [
            {
                "external_key": c.external_key,
                "campaign_name": c.campaign_name,
                "campaign_type": _campaign_type_key(c),
                "language_code": c.language_code,
                "status": c.status.value,
                "budget_daily_eur": c.settings.budget_daily_eur,
                "bid_strategy": c.settings.bid_strategy.value,
                "can_publish": c.can_publish,
                "publish_blockers": c.publish_blockers,
                "ad_groups_count": len(c.ad_groups),
                "pmax_asset_groups_count": len(c.pmax_asset_groups),
                "dry_run_diff": c.dry_run_diff,
                "ad_groups": [
                    {
                        "name": ag.name,
                        "keywords_count": len(ag.keywords),
                        "ads_count": len(ag.ads),
                        "display_ads_count": len(ag.display_ads),
                        "demand_gen_ads_count": len(ag.demand_gen_ads),
                        "audience_targeting": ag.audience_targeting,
                        # RSA copy: actual headlines/descriptions from the generated plan.
                        # Falls back to display_ads or demand_gen_ads text when no RSA.
                        "rsa_headlines": (
                            [ph.text for ph in ag.ads[0].headlines] if ag.ads
                            else ag.display_ads[0].headlines if ag.display_ads
                            else ag.demand_gen_ads[0].headlines if ag.demand_gen_ads
                            else []
                        ),
                        "rsa_descriptions": (
                            list(ag.ads[0].descriptions) if ag.ads
                            else list(ag.display_ads[0].descriptions) if ag.display_ads
                            else list(ag.demand_gen_ads[0].descriptions) if ag.demand_gen_ads
                            else []
                        ),
                    }
                    for ag in c.ad_groups
                ],
                "pmax_asset_groups": [
                    {
                        "name": ag.name,
                        "headlines": ag.headlines,
                        "long_headlines": ag.long_headlines,
                        "descriptions": ag.descriptions,
                        "headlines_count": len(ag.headlines),
                        "images": ag.images,
                        "logo_url": ag.logo_url,
                        "youtube_video_url": ag.youtube_video_url,
                        "final_url": ag.final_url,
                        "has_missing_assets": ag.has_missing_assets,
                        "missing_asset_notes": ag.missing_asset_notes,
                        "audience_signals": ag.audience_signals,
                    }
                    for ag in c.pmax_asset_groups
                ],
            }
            for c in plan.campaigns
        ],
    }


@router.post("/{project_id}/apply-brief-fix")
async def apply_brief_fix(
    project_id: str,
    fix: dict,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a structured suggested_fix to the project's brief.

    Request body:
      {
        "brief_path": "objectives.kpi.target_cpa_eur",  // dot-notation
        "value": 60.0,
        "action": "set"                                  // "set" | "append_list"
      }

    On success saves the updated brief and returns the new value.
    The caller should then re-generate the plan to see the effect.
    """
    project = await _get_project_or_404(project_id, db)
    if not project.brief_json:
        raise HTTPException(status_code=400, detail="Brief non trovato per questo progetto.")

    brief_path: str = fix.get("brief_path", "")
    value = fix.get("value")
    action: str = fix.get("action", "set")

    if not brief_path:
        raise HTTPException(status_code=422, detail="brief_path è obbligatorio.")
    if value is None:
        raise HTTPException(status_code=422, detail="value è obbligatorio.")

    brief_dict: dict = json.loads(project.brief_json)

    # Navigate to parent node using dot-notation
    keys = brief_path.split(".")
    node = brief_dict
    try:
        for key in keys[:-1]:
            if key not in node:
                node[key] = {}
            node = node[key]
        final_key = keys[-1]
    except (TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Path non valido '{brief_path}': {exc}")

    if action == "append_list":
        existing = node.get(final_key, [])
        if not isinstance(existing, list):
            raise HTTPException(status_code=422, detail=f"Il campo '{brief_path}' non è una lista.")
        if not isinstance(value, list):
            raise HTTPException(status_code=422, detail="Per 'append_list' value deve essere un array.")
        # Deduplicate while preserving order
        seen = set(existing)
        for item in value:
            if item not in seen:
                existing.append(item)
                seen.add(item)
        node[final_key] = existing
    else:  # "set"
        node[final_key] = value

    # Re-validate the patched brief
    try:
        Brief(**brief_dict)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Brief non valido dopo il fix: {exc}")

    project.brief_json = json.dumps(brief_dict)

    log = AuditLog(
        project_id=project_id,
        user_id=current_user.user_id,
        action="apply_brief_fix",
        entity_type="project",
        entity_id=project_id,
        details=json.dumps({"brief_path": brief_path, "action": action}),
    )
    db.add(log)
    await db.commit()

    return {"status": "ok", "brief_path": brief_path, "value": value}


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return project
