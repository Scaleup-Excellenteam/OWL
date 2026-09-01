import pytest

from src.google_features.translation import TranslationResult
from src.models import AutoCompleteData
from src.search_service import SearchService, requires_translation


class FakeTranslator:
    def __init__(self):
        self.received = []

    def translate_to_english(self, text: str) -> TranslationResult:
        self.received.append(text)
        return TranslationResult(
            original_text=text,
            translated_text="how to install python",
            detected_language="he",
        )


def _completion(sentence: str) -> AutoCompleteData:
    return AutoCompleteData(sentence, "example.txt", 0, 10)


def test_regular_search_bypasses_translator():
    translator = FakeTranslator()
    searched = []

    def completion_search(query: str):
        searched.append(query)
        return [_completion("Regular result")]

    service = SearchService(translator, completion_search=completion_search)
    response = service.search("python install")

    assert translator.received == []
    assert searched == ["python install"]
    assert response.searched_query == "python install"
    assert response.translated is False
    assert response.completions[0].completed_sentence == "Regular result"


def test_regular_search_bypasses_translator_for_hebrew_too():
    translator = FakeTranslator()
    searched = []
    service = SearchService(
        translator,
        completion_search=lambda query: searched.append(query) or [],
    )

    response = service.search("איך להתקין פייתון", multilingual=False)

    assert translator.received == []
    assert searched == ["איך להתקין פייתון"]
    assert response.searched_query == "איך להתקין פייתון"
    assert response.translated is False


def test_multilingual_mode_bypasses_translator_for_english_query():
    translator = FakeTranslator()
    searched = []
    service = SearchService(
        translator,
        completion_search=lambda query: searched.append(query) or [],
    )

    response = service.search("ternet 3.12?", multilingual=True)

    assert translator.received == []
    assert searched == ["ternet 3.12?"]
    assert response.searched_query == "ternet 3.12?"
    assert response.detected_language is None
    assert response.translated is False


def test_multilingual_english_query_does_not_require_translator_configuration():
    searched = []
    service = SearchService(
        completion_search=lambda query: searched.append(query) or [],
    )

    response = service.search("python tutorial", multilingual=True)

    assert searched == ["python tutorial"]
    assert response.searched_query == "python tutorial"
    assert response.translated is False


def test_multilingual_search_translates_complete_query_before_searching():
    translator = FakeTranslator()
    searched = []

    def completion_search(query: str):
        searched.append(query)
        return [_completion("How to install Python")]

    service = SearchService(translator, completion_search=completion_search)
    response = service.search("איך להתקין פייתון", multilingual=True)

    assert translator.received == ["איך להתקין פייתון"]
    assert searched == ["how to install python"]
    assert response.original_query == "איך להתקין פייתון"
    assert response.searched_query == "how to install python"
    assert response.detected_language == "he"
    assert response.translated is True


def test_multilingual_search_translates_mixed_hebrew_and_english_query():
    translator = FakeTranslator()
    searched = []
    service = SearchService(
        translator,
        completion_search=lambda query: searched.append(query) or [],
    )

    response = service.search("איך להתקין Python", multilingual=True)

    assert translator.received == ["איך להתקין Python"]
    assert searched == ["how to install python"]
    assert response.translated is True


def test_empty_query_does_not_call_external_or_search_services():
    translator = FakeTranslator()
    searched = []
    service = SearchService(
        translator,
        completion_search=lambda query: searched.append(query),
    )

    response = service.search("   ", multilingual=True)

    assert translator.received == []
    assert searched == []
    assert response.completions == []


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("ternet", False),
        ("Python 3.12?", False),
        ("1234?!", False),
        ("איך להתקין", True),
        ("install פייתון", True),
        ("café", True),
    ],
)
def test_requires_translation(query, expected):
    assert requires_translation(query) is expected
