"""Export and publish routes (CSV + Google Ads API)."""
import json
import logging
import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_ROME = ZoneInfo("Europe/Rome")
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, require_strategist_or_admin
from app.connectors.csv_exporter import export_plan_to_csv
from app.connectors.google_ads_api import GoogleAdsApiConnector, GoogleAdsApiNotConfiguredError
from app.database import get_db
from app.domain.models import AuditLog, ExportRecord, Project
from app.domain.schemas.brief import Brief
from app.domain.schemas.campaign_plan import AccountPlan
from app.generators.orchestrator import CampaignOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["export"])

EXPORTS_DIR = Path("data/exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

orchestrator = CampaignOrchestrator()
api_connector = GoogleAdsApiConnector()


@router.get("/{project_id}/export/csv")
async def export_csv(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export the project campaign plan as a Google Ads Editor CSV file.
    Download is triggered immediately.
    """
    plan = await _get_or_generate_plan(project_id, db)

    csv_content = export_plan_to_csv(plan)
    filename = f"{plan.client_slug}_{datetime.now(_TZ_ROME).strftime('%Y%m%d_%H%M%S')}_ads_editor.csv"

    # Persist export record
    export_record = ExportRecord(
        id=str(uuid.uuid4()),
        project_id=project_id,
        export_type="csv",
        file_path=str(EXPORTS_DIR / filename),
        is_dry_run=True,
        status="completed",
        created_by=current_user.user_id,
    )
    db.add(export_record)

    log = AuditLog(
        project_id=project_id,
        user_id=current_user.user_id,
        action="export_csv",
        entity_type="export",
        entity_id=export_record.id,
        details=json.dumps({"filename": filename, "campaigns": plan.total_campaigns}),
    )
    db.add(log)

    # Save file to disk
    (EXPORTS_DIR / filename).write_text(csv_content, encoding="utf-8")

    # Stream response
    def csv_generator():
        yield csv_content.encode("utf-8")

    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{project_id}/publish")
async def publish_to_google_ads(
    project_id: str,
    dry_run: bool = True,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish campaigns to Google Ads via API.
    - dry_run=True (default): simulate only, return diff
    - dry_run=False: actually publish (requires Google Ads credentials)
    """
    project = await _get_project_or_404(project_id, db)
    plan = await _get_or_generate_plan(project_id, db)

    if not plan.is_valid and not dry_run:
        raise HTTPException(
            status_code=400,
            detail=f"Piano non valido — risolvi prima gli errori: {plan.validation_errors}",
        )

    customer_id = _extract_customer_id(plan, project)
    if not customer_id and not dry_run:
        raise HTTPException(
            status_code=400,
            detail="Google Ads Customer ID non trovato nel brief. Impossibile pubblicare.",
        )

    try:
        result = api_connector.publish(
            plan=plan,
            customer_id=customer_id or "000-000-0000",
            dry_run=dry_run,
        )
    except GoogleAdsApiNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Publish failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore pubblicazione: {exc}")

    export_record = ExportRecord(
        id=str(uuid.uuid4()),
        project_id=project_id,
        export_type="api",
        is_dry_run=dry_run,
        status="completed" if not result.get("errors") else "partial",
        created_by=current_user.user_id,
    )
    db.add(export_record)

    if not dry_run:
        project.status = "published"

    log = AuditLog(
        project_id=project_id,
        user_id=current_user.user_id,
        action="publish_api",
        entity_type="export",
        entity_id=export_record.id,
        details=json.dumps({"dry_run": dry_run, "result_summary": result.get("summary", {})}),
    )
    db.add(log)

    return result


@router.get("/{project_id}/exports")
async def list_exports(
    project_id: str,
    current_user: TokenData = Depends(require_strategist_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExportRecord)
        .where(ExportRecord.project_id == project_id)
        .order_by(ExportRecord.created_at.desc())
    )
    exports = result.scalars().all()
    return [
        {
            "id": e.id,
            "export_type": e.export_type,
            "is_dry_run": e.is_dry_run,
            "status": e.status,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]


async def _get_or_generate_plan(project_id: str, db: AsyncSession) -> AccountPlan:
    """Get existing plan or generate fresh."""
    project = await _get_project_or_404(project_id, db)

    if project.plan_json:
        return AccountPlan(**json.loads(project.plan_json))

    if not project.brief_json:
        raise HTTPException(
            status_code=400,
            detail="Né brief né piano trovati. Carica il brief e genera il piano prima.",
        )

    brief = Brief(**json.loads(project.brief_json))
    plan = orchestrator.generate_plan(brief, project_id, dry_run=True)
    project.plan_json = plan.model_dump_json()
    return plan


def _extract_customer_id(plan: AccountPlan, project: Project) -> str:
    """Try to get the Customer ID from the brief JSON."""
    try:
        brief_data = json.loads(project.brief_json or "{}")
        return brief_data.get("client", {}).get("google_ads_customer_id", "")
    except Exception:
        return ""


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return project
