"""Google Cloud Translation adapter used by multilingual search."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
import os
from typing import Callable, ContextManager, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.logging_config import get_logger


TRANSLATE_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
API_KEY_ENV_VAR = "GOOGLE_TRANSLATE_API_KEY"
logger = get_logger("google_features.translation")


class TranslationConfigurationError(RuntimeError):
    """Raised when multilingual search has not been configured."""


class TranslationServiceError(RuntimeError):
    """Raised when Google Translation cannot return a usable translation."""


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """A translated query and the language detected by Google."""

    original_text: str
    translated_text: str
    detected_language: str | None


class _ReadableResponse(Protocol):
    def read(self) -> bytes: ...


OpenUrl = Callable[..., ContextManager[_ReadableResponse]]


class GoogleTranslator:
    """Translate short user queries to English with Cloud Translation Basic v2."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 5.0,
        open_url: OpenUrl = urlopen,
    ) -> None:
        if not api_key.strip():
            raise TranslationConfigurationError("Google Translation API key is missing")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._open_url = open_url

    @classmethod
    def from_environment(cls, *, timeout_seconds: float = 5.0) -> GoogleTranslator:
        """Create a translator using ``GOOGLE_TRANSLATE_API_KEY``."""
        api_key = os.environ.get(API_KEY_ENV_VAR, "")
        if not api_key.strip():
            raise TranslationConfigurationError(
                f"Set {API_KEY_ENV_VAR} to enable multilingual search"
            )
        return cls(api_key, timeout_seconds=timeout_seconds)

    def translate_to_english(self, text: str) -> TranslationResult:
        """Translate non-empty text to English and return detected language data."""
        if not text.strip():
            raise ValueError("text must not be empty")

        request_body = json.dumps(
            {"q": text, "target": "en", "format": "text"}
        ).encode("utf-8")
        url = f"{TRANSLATE_ENDPOINT}?{urlencode({'key': self._api_key})}"
        request = Request(
            url,
            data=request_body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with self._open_url(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            logger.warning("Translation request failed status=%d", exc.code)
            raise TranslationServiceError(
                f"Google Translation returned HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            logger.warning("Translation request unavailable reason=%s", type(exc).__name__)
            raise TranslationServiceError("Google Translation is unavailable") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Translation response invalid reason=%s", type(exc).__name__)
            raise TranslationServiceError(
                "Google Translation returned an invalid response"
            ) from exc

        try:
            translation = payload["data"]["translations"][0]
            translated_text = html.unescape(translation["translatedText"]).strip()
            detected_language = translation.get("detectedSourceLanguage")
        except (KeyError, IndexError, TypeError) as exc:
            raise TranslationServiceError(
                "Google Translation response is missing translation data"
            ) from exc

        if not translated_text:
            logger.warning("Translation response contained empty text")
            raise TranslationServiceError("Google Translation returned empty text")

        logger.debug(
            "Translation completed source_length=%d result_length=%d "
            "detected_language=%s",
            len(text),
            len(translated_text),
            detected_language or "unknown",
        )

        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            detected_language=detected_language,
        )
