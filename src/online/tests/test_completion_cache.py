"""Integration tests for caching normalized English completion queries."""

from pathlib import Path

import pytest

import src.online.completion as completion_module
from src.google_features.translation import TranslationResult
from src.models import TrieNode, create_metadata
from src.online.completion import (
    configure_completion,
    get_best_k_completions,
    get_query_cache_info,
)
from src.search_service import SearchService


class _FakeTranslator:
    """Translate a test query into the English cache key."""

    def translate_to_english(self, text: str) -> TranslationResult:
        """Return a deterministic English translation.

        Args:
            text: Original multilingual query.

        Returns:
            A translation that normalizes to ``hello``.
        """
        return TranslationResult(text, "HELLO!!!", "he")


def _install_fake_candidate_search(
    monkeypatch: pytest.MonkeyPatch,
    trie_root: TrieNode,
) -> list[str]:
    """Replace Trie candidate lookup with a call-recording fake.

    Args:
        monkeypatch: Pytest helper used to replace candidate lookup.
        trie_root: Expected configured Trie root.

    Returns:
        Mutable list receiving each normalized underlying query.
    """
    search_calls: list[str] = []

    def fake_best_scores(
        configured_root: TrieNode,
        normalized_prefix: str,
    ) -> dict[int, tuple[int, int]]:
        """Return one candidate while recording the underlying search.

        Args:
            configured_root: Trie supplied by completion configuration.
            normalized_prefix: Normalized query sent to the Trie layer.

        Returns:
            One deterministic candidate and score.
        """
        assert configured_root is trie_root
        search_calls.append(normalized_prefix)
        metadata = create_metadata(0, 0)
        return {metadata: (metadata, 10)}

    monkeypatch.setattr(
        completion_module,
        "_best_scores_by_sentence",
        fake_best_scores,
    )
    return search_calls


def test_completion_cache_uses_translated_normalized_english_query(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Share one entry between translated and equivalent English queries.

    Args:
        monkeypatch: Pytest helper used to count underlying searches.
        tmp_path: Temporary directory supplied by pytest.
    """
    source_path = tmp_path / "source.txt"
    source_path.write_text("Hello world.\n", encoding="utf-8")
    trie_root = TrieNode()
    configure_completion(trie_root, [source_path], query_cache_capacity=2)
    search_calls = _install_fake_candidate_search(monkeypatch, trie_root)
    service = SearchService(
        _FakeTranslator(),
        completion_search=get_best_k_completions,
    )

    translated = service.search("שלום", multilingual=True)
    english = service.search(" hello ")

    assert translated.completions == english.completions
    assert search_calls == ["hello"]
    info = get_query_cache_info()
    assert info.capacity == 2
    assert info.size == 1
    assert info.hits == 1
    assert info.misses == 1


def test_configuring_new_completion_data_clears_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Do not serve results produced from a previously configured Trie.

    Args:
        monkeypatch: Pytest helper used to count underlying searches.
        tmp_path: Temporary directory supplied by pytest.
    """
    source_path = tmp_path / "source.txt"
    source_path.write_text("Hello world.\n", encoding="utf-8")
    first_root = TrieNode()
    configure_completion(first_root, [source_path])
    first_calls = _install_fake_candidate_search(monkeypatch, first_root)

    get_best_k_completions("hello")
    get_best_k_completions("hello")
    assert first_calls == ["hello"]

    second_root = TrieNode()
    configure_completion(second_root, [source_path])
    second_calls = _install_fake_candidate_search(monkeypatch, second_root)
    get_best_k_completions("hello")

    assert second_calls == ["hello"]
    assert get_query_cache_info().misses == 1
