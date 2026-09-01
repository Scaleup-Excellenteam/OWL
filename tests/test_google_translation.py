import json
from urllib.error import URLError

import pytest

from src.google_features.translation import (
    API_KEY_ENV_VAR,
    GoogleTranslator,
    TranslationConfigurationError,
    TranslationServiceError,
)


class FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self._body


def test_translate_to_english_sends_unicode_and_parses_response():
    captured = {}

    def fake_open(request, *, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "data": {
                    "translations": [
                        {
                            "translatedText": "how to install Python",
                            "detectedSourceLanguage": "he",
                        }
                    ]
                }
            }
        )

    translator = GoogleTranslator(
        "test-api-key",
        timeout_seconds=3.5,
        open_url=fake_open,
    )

    result = translator.translate_to_english("איך להתקין פייתון")

    assert result.original_text == "איך להתקין פייתון"
    assert result.translated_text == "how to install Python"
    assert result.detected_language == "he"
    assert captured["body"] == {
        "q": "איך להתקין פייתון",
        "target": "en",
        "format": "text",
    }
    assert "test-api-key" in captured["url"]
    assert captured["timeout"] == 3.5


def test_translate_to_english_decodes_html_entities():
    def fake_open(request, *, timeout):
        return FakeResponse(
            {
                "data": {
                    "translations": [
                        {"translatedText": "Python &amp; Google"}
                    ]
                }
            }
        )

    result = GoogleTranslator("key", open_url=fake_open).translate_to_english(
        "Python וגוגל"
    )

    assert result.translated_text == "Python & Google"
    assert result.detected_language is None


def test_translate_to_english_rejects_empty_input():
    translator = GoogleTranslator("key", open_url=lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="must not be empty"):
        translator.translate_to_english("   ")


def test_translate_to_english_wraps_network_errors():
    def unavailable(request, *, timeout):
        raise URLError("offline")

    translator = GoogleTranslator("key", open_url=unavailable)

    with pytest.raises(TranslationServiceError, match="unavailable"):
        translator.translate_to_english("שלום")


def test_from_environment_requires_api_key(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)

    with pytest.raises(TranslationConfigurationError, match=API_KEY_ENV_VAR):
        GoogleTranslator.from_environment()
