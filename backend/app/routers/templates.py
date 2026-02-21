"""Templates and presets API."""
from fastapi import APIRouter, Depends

from app.auth import get_current_user, TokenData
from app.templates.presets import list_presets, get_preset
from app.templates.vertical_templates import VerticalTemplates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("/presets")
async def list_presets_endpoint(current_user: TokenData = Depends(get_current_user)):
    return list_presets()


@router.get("/presets/{preset_name}")
async def get_preset_endpoint(
    preset_name: str,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        preset = get_preset(preset_name)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "name": preset.name,
        "slug": preset.slug,
        "description": preset.description,
        "naming_separator": preset.naming_separator,
        "naming_components": preset.naming_components,
        "utm_source": preset.utm_source,
        "utm_medium": preset.utm_medium,
        "utm_campaign": preset.utm_campaign,
        "utm_content": preset.utm_content,
        "utm_term": preset.utm_term,
        "utm_custom_params": preset.utm_custom_params,
        "utm_preset_tag": preset.utm_preset_tag,
        "base_labels": preset.base_labels,
        "tracking_template": preset.build_tracking_template(),
        "pmax_final_url_expansion": preset.pmax_final_url_expansion,
    }


@router.get("/verticals")
async def list_verticals(current_user: TokenData = Depends(get_current_user)):
    return {
        "verticals": VerticalTemplates.get_all_verticals(),
        "languages": VerticalTemplates.get_all_languages(),
    }


@router.get("/verticals/{vertical}/keywords")
async def get_vertical_keywords(
    vertical: str,
    lang: str = "IT",
    current_user: TokenData = Depends(get_current_user),
):
    from app.domain.schemas.brief import HotelVertical
    try:
        v = HotelVertical(vertical)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Verticale '{vertical}' non trovato")

    themes = VerticalTemplates.get_acquisition_themes(v, lang.upper())
    return {"vertical": vertical, "language": lang, "themes": themes}
