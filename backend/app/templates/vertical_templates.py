"""
Vertical templates for hotel types × markets.
Used as fallback keyword/asset suggestions when brief is incomplete,
and as starting point for new briefs (template wizard).
"""
from __future__ import annotations

from typing import Dict, List

from app.domain.schemas.brief import HotelVertical


class VerticalTemplates:
    """
    Keyword themes organized by:
    - Hotel vertical (city_hotel, resort, boutique, business, agriturismo)
    - Language (IT, EN, FR, DE, ES)
    """

    _THEMES: Dict[str, Dict[str, Dict[str, List[str]]]] = {
        HotelVertical.city_hotel: {
            "IT": {
                "location": [
                    "hotel centro città",
                    "hotel centro storico",
                    "hotel vicino stazione",
                    "albergo centro",
                ],
                "category": [
                    "hotel 4 stelle centro",
                    "hotel 5 stelle centro",
                    "hotel lusso centro",
                ],
                "intent": [
                    "prenota hotel centro",
                    "offerta hotel centro città",
                    "hotel economico centro",
                ],
                "occasion": [
                    "hotel weekend città",
                    "hotel business viaggio lavoro",
                    "hotel romantico centro",
                ],
            },
            "EN": {
                "location": [
                    "city centre hotel",
                    "downtown hotel",
                    "hotel near train station",
                    "central hotel",
                ],
                "category": [
                    "4 star city hotel",
                    "luxury city hotel",
                    "boutique city hotel",
                ],
                "intent": [
                    "book city hotel",
                    "city hotel deals",
                    "cheap city centre hotel",
                ],
                "occasion": [
                    "weekend break city hotel",
                    "business hotel city centre",
                    "romantic hotel city",
                ],
            },
            "DE": {
                "location": [
                    "hotel stadtzentrum",
                    "hotel innenstadt",
                    "hotel nahe bahnhof",
                    "zentral hotel",
                ],
                "category": [
                    "4 sterne stadthotel",
                    "luxushotel stadtmitte",
                    "designhotel innenstadt",
                ],
                "intent": [
                    "stadthotel buchen",
                    "hotel stadtzentrum angebot",
                    "günstiges hotel innenstadt",
                ],
                "occasion": [
                    "wochenendhotel stadt",
                    "businesshotel zentrum",
                    "romantikhotel innenstadt",
                ],
            },
            "FR": {
                "location": [
                    "hôtel centre-ville",
                    "hôtel centre historique",
                    "hôtel près gare",
                    "hotel central",
                ],
                "category": [
                    "hôtel 4 étoiles centre",
                    "hôtel luxe centre-ville",
                    "boutique hôtel centre",
                ],
                "intent": [
                    "réserver hôtel centre",
                    "offre hôtel centre-ville",
                    "hôtel pas cher centre",
                ],
                "occasion": [
                    "week-end hôtel centre-ville",
                    "hôtel affaires centre",
                    "hôtel romantique centre",
                ],
            },
        },
        HotelVertical.resort: {
            "IT": {
                "location": [
                    "resort mare",
                    "resort montagna",
                    "resort lago",
                    "resort campagna",
                ],
                "category": [
                    "resort 5 stelle",
                    "resort lusso",
                    "resort all inclusive",
                    "resort spa",
                ],
                "intent": [
                    "prenota resort",
                    "offerta resort estate",
                    "resort vacanze famiglia",
                ],
                "occasion": [
                    "resort luna di miele",
                    "resort benessere",
                    "resort bambini",
                    "resort adulti",
                ],
            },
            "EN": {
                "location": [
                    "beach resort",
                    "mountain resort",
                    "lakeside resort",
                    "countryside resort",
                ],
                "category": [
                    "5 star resort",
                    "luxury resort",
                    "all inclusive resort",
                    "spa resort",
                ],
                "intent": [
                    "book resort",
                    "resort summer deals",
                    "family resort vacation",
                ],
                "occasion": [
                    "honeymoon resort",
                    "wellness resort",
                    "kids friendly resort",
                    "adults only resort",
                ],
            },
            "DE": {
                "location": [
                    "strandresort",
                    "bergresort",
                    "seeresort",
                    "landresort",
                ],
                "category": [
                    "5 sterne resort",
                    "luxusresort",
                    "all inclusive resort",
                    "wellnessresort",
                ],
                "intent": [
                    "resort buchen",
                    "resort sommerangebot",
                    "familienresort urlaub",
                ],
                "occasion": [
                    "flitterwochen resort",
                    "wellnessresort",
                    "resort mit kindern",
                ],
            },
        },
        HotelVertical.boutique: {
            "IT": {
                "location": [
                    "boutique hotel centro storico",
                    "hotel charme",
                    "hotel design",
                    "hotel storico",
                ],
                "category": [
                    "boutique hotel lusso",
                    "albergo diffuso",
                    "hotel stile",
                    "hotel unico",
                ],
                "intent": [
                    "soggiorno esclusivo",
                    "hotel esperienza",
                    "prenota boutique hotel",
                ],
                "occasion": [
                    "hotel anniversario",
                    "hotel sorpresa romantica",
                    "regalo soggiorno",
                ],
            },
            "EN": {
                "location": [
                    "boutique hotel historic centre",
                    "charming hotel",
                    "design hotel",
                    "heritage hotel",
                ],
                "category": [
                    "luxury boutique hotel",
                    "unique hotel",
                    "stylish hotel",
                    "intimate hotel",
                ],
                "intent": [
                    "exclusive stay",
                    "book boutique hotel",
                    "special hotel experience",
                ],
                "occasion": [
                    "anniversary hotel",
                    "romantic surprise hotel",
                    "special occasion hotel",
                ],
            },
            "DE": {
                "location": [
                    "boutique hotel altstadt",
                    "charme hotel",
                    "design hotel",
                    "historisches hotel",
                ],
                "category": [
                    "luxus boutique hotel",
                    "einzigartiges hotel",
                    "stilvolles hotel",
                ],
                "intent": [
                    "exklusiver aufenthalt",
                    "boutique hotel buchen",
                    "besonderes hotel erlebnis",
                ],
                "occasion": [
                    "jubiläums hotel",
                    "romantisches überraschungs hotel",
                ],
            },
        },
        HotelVertical.business: {
            "IT": {
                "location": ["hotel business district", "hotel fiera", "hotel congressi"],
                "category": ["hotel business", "hotel meetings", "hotel sala riunioni"],
                "intent": ["hotel viaggio lavoro", "prenota hotel business", "hotel trasferta"],
                "occasion": ["hotel corporate", "hotel evento aziendale"],
            },
            "EN": {
                "location": ["business district hotel", "conference hotel", "trade fair hotel"],
                "category": ["business hotel", "meeting hotel", "corporate hotel"],
                "intent": ["hotel for business travel", "book business hotel", "work trip hotel"],
                "occasion": ["corporate events hotel", "company retreat hotel"],
            },
            "DE": {
                "location": ["business hotel", "messehotel", "tagungshotel"],
                "category": ["businesshotel", "tagungshotel", "konferenzhotel"],
                "intent": ["hotel geschäftsreise", "businesshotel buchen"],
                "occasion": ["firmenhotel", "teamretreat hotel"],
            },
        },
        HotelVertical.agriturismo: {
            "IT": {
                "location": ["agriturismo", "agriturismo campagna", "fattoria vacanze"],
                "category": ["agriturismo lusso", "agriturismo piscina", "agriturismo biologico"],
                "intent": ["prenota agriturismo", "offerta agriturismo", "vacanza in campagna"],
                "occasion": ["agriturismo famiglia", "agriturismo romantico", "agriturismo bambini"],
            },
            "EN": {
                "location": ["farmhouse hotel", "countryside retreat", "rural hotel"],
                "category": ["luxury farmhouse", "agriturismo italy", "farm stay"],
                "intent": ["book farmhouse hotel", "countryside holiday", "rural escape"],
                "occasion": ["family farm stay", "romantic countryside hotel"],
            },
            "DE": {
                "location": ["landhotel", "bauernhof urlaub", "agriturismo"],
                "category": ["landhotel luxus", "agriturismo italien", "bauernhofhotel"],
                "intent": ["landhotel buchen", "urlaub auf dem land"],
                "occasion": ["familienurlaub landhotel", "romantikurlaub landhotel"],
            },
        },
    }

    @classmethod
    def get_acquisition_themes(
        cls, vertical: HotelVertical, lang_code: str
    ) -> Dict[str, List[str]]:
        """
        Get keyword themes for a vertical + language combination.
        Falls back to EN if the requested language is not available.
        """
        vertical_themes = cls._THEMES.get(vertical, cls._THEMES[HotelVertical.city_hotel])
        lang_themes = vertical_themes.get(lang_code, vertical_themes.get("EN", {}))
        return lang_themes

    @classmethod
    def get_all_verticals(cls) -> List[str]:
        return [v.value for v in HotelVertical]

    @classmethod
    def get_all_languages(cls) -> List[str]:
        """Return all supported language codes across all templates."""
        langs = set()
        for vertical_data in cls._THEMES.values():
            langs.update(vertical_data.keys())
        return sorted(langs)
