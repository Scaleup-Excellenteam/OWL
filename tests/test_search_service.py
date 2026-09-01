import pytest

from src.google_features.translation import TranslationResult
from src.models import AutoCompleteData
from src.google_features.keyboard_layout import convert_hebrew_keyboard_layout
from src.search_service import (
    SearchService,
    has_exact_whole_query_match,
    keyboard_layout_candidate,
    requires_translation,
)


class FakeTranslator:
    def __init__(self, translated_text="how to install python"):
        self.received = []
        self.translated_text = translated_text

    def translate_to_english(self, text: str) -> TranslationResult:
        self.received.append(text)
        return TranslationResult(
            original_text=text,
            translated_text=self.translated_text,
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
    ("hebrew", "english"),
    [
        ("פטאיםמ", "python"),
        ("יקךךם", "hello"),
        ("עןא", "git"),
        ("בםגק", "code"),
        ("'ןמגם'", "window"),
        ("/וקרט", "query"),
        ("שלום", "akuo"),
    ],
)
def test_converts_hebrew_layout_to_english_keys(hebrew, english):
    assert convert_hebrew_keyboard_layout(hebrew) == english


def test_keyboard_candidate_requires_english_words_after_conversion():
    assert keyboard_layout_candidate("פטאיםמ") == "python"
    assert keyboard_layout_candidate("'ןמגם'") == "window"
    assert keyboard_layout_candidate("/וקרט") == "query"
    assert keyboard_layout_candidate("python") is None
    assert keyboard_layout_candidate("שלום!") is None


def test_english_punctuation_is_not_converted_without_hebrew():
    assert convert_hebrew_keyboard_layout("what's / this") == "what's / this"


def test_whole_query_match_rejects_text_inside_another_word():
    assert has_exact_whole_query_match(
        "akuo",
        [_completion("A pakuo example")],
    ) is False
    assert has_exact_whole_query_match(
        "python",
        [_completion("Install Python today")],
    ) is True


def test_keyboard_correction_is_used_for_an_exact_word_match():
    translator = FakeTranslator(translated_text="unrelated translation")

    def completion_search(query: str):
        if query == "python":
            return [_completion("Install Python today")]
        return []

    response = SearchService(
        translator,
        completion_search=completion_search,
    ).search("פטאיםמ", multilingual=True)

    assert translator.received == ["פטאיםמ"]
    assert response.searched_query == "python"
    assert response.keyboard_corrected is True
    assert response.translated is False
    assert response.alternatives == ()


def test_inside_word_match_falls_back_to_google_translation():
    translator = FakeTranslator(translated_text="hello")

    def completion_search(query: str):
        if query == "akuo":
            return [_completion("A pakuo example")]
        if query == "hello":
            return [_completion("Hello world")]
        return []

    response = SearchService(
        translator,
        completion_search=completion_search,
    ).search("שלום", multilingual=True)

    assert response.searched_query == "hello"
    assert response.translated is True
    assert response.keyboard_corrected is False


def test_both_valid_interpretations_are_returned_for_the_cli_to_choose():
    translator = FakeTranslator(translated_text="serpent")

    def completion_search(query: str):
        matches = {
            "python": [_completion("Python tutorial")],
            "serpent": [_completion("Serpent documentation")],
        }
        return matches.get(query, [])

    response = SearchService(
        translator,
        completion_search=completion_search,
    ).search("פטאיםמ", multilingual=True)

    assert [option.searched_query for option in response.alternatives] == [
        "python",
        "serpent",
    ]
    assert response.alternatives[0].keyboard_corrected is True
    assert response.alternatives[1].translated is True


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
