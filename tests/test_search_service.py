from src.google_features.translation import TranslationResult
from src.models import AutoCompleteData
from src.search_service import SearchService


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
