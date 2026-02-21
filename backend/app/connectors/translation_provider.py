"""
Translation provider abstraction.
Supports: NoOp (pass-through), Google Translate, DeepL.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranslationProvider(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        pass

    def translate_batch(
        self, texts: List[str], source_lang: str, target_lang: str
    ) -> List[str]:
        return [self.translate(t, source_lang, target_lang) for t in texts]


class NoOpTranslationProvider(TranslationProvider):
    """
    Pass-through: returns source text unchanged.
    Use when translations are provided directly in the brief.
    """

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        logger.debug(f"NoOp translation: [{source_lang}→{target_lang}] {text[:40]}...")
        return text


class GoogleTranslateProvider(TranslationProvider):
    """
    Google Cloud Translation API v2.
    Requires GOOGLE_TRANSLATE_API_KEY in environment.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._base_url = "https://translation.googleapis.com/language/translate/v2"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        import httpx

        if source_lang == target_lang:
            return text

        try:
            response = httpx.post(
                self._base_url,
                params={"key": self.api_key},
                json={
                    "q": text,
                    "source": source_lang.lower(),
                    "target": target_lang.lower(),
                    "format": "text",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]["translations"][0]["translatedText"]
        except Exception as exc:
            logger.error(f"Google Translate error: {exc}")
            return f"[TRANSLATION ERROR] {text}"


class DeepLProvider(TranslationProvider):
    """
    DeepL API.
    Requires DEEPL_API_KEY in environment.
    """

    LANG_MAP = {
        "IT": "IT",
        "EN": "EN-GB",
        "DE": "DE",
        "FR": "FR",
        "ES": "ES",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._base_url = (
            "https://api-free.deepl.com/v2/translate"
            if api_key.endswith(":fx")
            else "https://api.deepl.com/v2/translate"
        )

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        import httpx

        if source_lang == target_lang:
            return text

        target = self.LANG_MAP.get(target_lang.upper(), target_lang.upper())
        source = self.LANG_MAP.get(source_lang.upper(), source_lang.upper())

        # DeepL EN source must be plain "EN"
        if source.startswith("EN"):
            source = "EN"

        try:
            response = httpx.post(
                self._base_url,
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={
                    "text": text,
                    "source_lang": source,
                    "target_lang": target,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["translations"][0]["text"]
        except Exception as exc:
            logger.error(f"DeepL error: {exc}")
            return f"[TRANSLATION ERROR] {text}"


def get_translation_provider() -> TranslationProvider:
    """Factory: returns the configured translation provider."""
    provider_name = settings.translation_provider.lower()

    if provider_name == "google":
        if not settings.google_translate_api_key:
            logger.warning("Google Translate API key not set; falling back to NoOp")
            return NoOpTranslationProvider()
        return GoogleTranslateProvider(settings.google_translate_api_key)

    if provider_name == "deepl":
        if not settings.deepl_api_key:
            logger.warning("DeepL API key not set; falling back to NoOp")
            return NoOpTranslationProvider()
        return DeepLProvider(settings.deepl_api_key)

    return NoOpTranslationProvider()
