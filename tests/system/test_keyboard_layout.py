"""Integration checks for keyboard-layout correction against the saved Trie."""

from src.google_features.translation import TranslationResult
from src.search_service import SearchService


class _FakeTranslator:
    def translate_to_english(self, text: str) -> TranslationResult:
        return TranslationResult(
            original_text=text,
            translated_text="unrelated translation",
            detected_language="he",
        )


def test_hebrew_layout_python_is_confirmed_by_saved_trie(
    configured_sample_system: object,
) -> None:
    del configured_sample_system

    response = SearchService(_FakeTranslator()).search(
        "פטאיםמ",
        multilingual=True,
    )

    assert response.searched_query == "python"
    assert response.keyboard_corrected is True
    assert response.translated is False
    assert response.completions
