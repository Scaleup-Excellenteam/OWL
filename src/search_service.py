"""Orchestrate keyboard correction, translation, and autocomplete search."""

from dataclasses import dataclass
import re
from typing import Callable, Protocol

from src.google_features.keyboard_layout import (
    contains_hebrew,
    convert_hebrew_keyboard_layout,
)
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
    keyboard_corrected: bool = False
    alternatives: tuple["SearchAlternative", ...] = ()


@dataclass(frozen=True, slots=True)
class SearchAlternative:
    """One plausible interpretation of an ambiguous multilingual query."""

    searched_query: str
    description: str
    detected_language: str | None
    translated: bool
    keyboard_corrected: bool
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
        """Search normally, correct a Hebrew layout error, or translate."""
        if not query.strip():
            return SearchResponse(query, query, None, False, [])

        should_translate = multilingual and requires_translation(query)

        if should_translate:
            if self._translator is None:
                raise RuntimeError("multilingual search requires a translator")

            keyboard_query = keyboard_layout_candidate(query)
            keyboard_completions: list[AutoCompleteData] = []
            keyboard_match = False
            if keyboard_query is not None:
                keyboard_completions = self._completion_search(keyboard_query)
                keyboard_match = has_exact_whole_query_match(
                    keyboard_query,
                    keyboard_completions,
                )

            translation = self._translator.translate_to_english(query)
            searched_query = translation.translated_text
            detected_language = translation.detected_language
            translated = True
            translated_completions = self._completion_search(searched_query)

            if keyboard_match:
                keyboard_option = SearchAlternative(
                    searched_query=keyboard_query,
                    description="keyboard correction",
                    detected_language=None,
                    translated=False,
                    keyboard_corrected=True,
                    completions=keyboard_completions,
                )

                if (
                    translated_completions
                    and keyboard_query.casefold() != searched_query.casefold()
                ):
                    translation_option = SearchAlternative(
                        searched_query=searched_query,
                        description="Google translation",
                        detected_language=detected_language,
                        translated=True,
                        keyboard_corrected=False,
                        completions=translated_completions,
                    )
                    return SearchResponse(
                        original_query=query,
                        searched_query=searched_query,
                        detected_language=detected_language,
                        translated=True,
                        completions=translated_completions,
                        alternatives=(keyboard_option, translation_option),
                    )

                return SearchResponse(
                    original_query=query,
                    searched_query=keyboard_query,
                    detected_language=None,
                    translated=False,
                    completions=keyboard_completions,
                    keyboard_corrected=True,
                )
        else:
            searched_query = query
            detected_language = None
            translated = False
            translated_completions = self._completion_search(searched_query)

        return SearchResponse(
            original_query=query,
            searched_query=searched_query,
            detected_language=detected_language,
            translated=translated,
            completions=translated_completions,
        )


def keyboard_layout_candidate(query: str) -> str | None:
    """Return an English-looking keyboard correction for Hebrew input."""
    if not contains_hebrew(query):
        return None

    candidate = convert_hebrew_keyboard_layout(query).strip()
    if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", candidate):
        return None
    return candidate


def has_exact_whole_query_match(
    query: str,
    completions: list[AutoCompleteData],
) -> bool:
    """Check that query occurs exactly on word boundaries in a completion."""
    words = re.split(r"\s+", query.strip())
    phrase = r"\s+".join(re.escape(word) for word in words)
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){phrase}(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    return any(pattern.search(item.completed_sentence) for item in completions)


def requires_translation(query: str) -> bool:
    """Return whether a query contains alphabetic characters outside English."""
    return any(
        char.isalpha() and not ("a" <= char.lower() <= "z")
        for char in query
    )
