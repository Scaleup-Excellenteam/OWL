"""Orchestrate optional translation and the existing autocomplete search."""

from dataclasses import dataclass
from typing import Callable, Protocol

from src.google_features.translation import TranslationResult
from src.models import AutoCompleteData
from src.online.completion import get_best_k_completions


class Translator(Protocol):
    def translate_to_english(self, text: str) -> TranslationResult: ...


CompletionSearch = Callable[[str], list[AutoCompleteData]]


@dataclass(frozen=True, slots=True)
class SearchResponse:
    original_query: str
    searched_query: str
    detected_language: str | None
    translated: bool
    completions: list[AutoCompleteData]


class SearchService:
    """Keep Google integration separate from the core online search engine."""

    def __init__(
        self,
        translator: Translator | None = None,
        *,
        completion_search: CompletionSearch = get_best_k_completions,
    ) -> None:
        self._translator = translator
        self._completion_search = completion_search

    def search(self, query: str, *, multilingual: bool = False) -> SearchResponse:
        """Search normally or translate the complete query before searching."""
        if not query.strip():
            return SearchResponse(query, query, None, False, [])

        if multilingual:
            if self._translator is None:
                raise RuntimeError("multilingual search requires a translator")
            translation = self._translator.translate_to_english(query)
            searched_query = translation.translated_text
            detected_language = translation.detected_language
            translated = searched_query != query
        else:
            searched_query = query
            detected_language = None
            translated = False

        return SearchResponse(
            original_query=query,
            searched_query=searched_query,
            detected_language=detected_language,
            translated=translated,
            completions=self._completion_search(searched_query),
        )
