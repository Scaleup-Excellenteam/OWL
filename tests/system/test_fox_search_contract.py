"""FOX-derived alignment contracts exercised through OWL's public API."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.offline.trie_builder import build_suffix_trie
from src.online.completion import configure_completion, get_best_k_completions


@pytest.fixture()
def configure_fox_search(tmp_path: Path) -> None:
    """Build a real OWL trie from FOX's compact alignment corpus."""
    sentences = [
        "xbcde and abcdx",
        "abcdef and xabcde",
        "abxcde and abcdxe",
        "before abcdef after",
        "To be or not to be, that is the question.",
    ]
    source_path = tmp_path / "fox_contract_corpus.txt"
    source_path.write_text("\n".join(sentences) + "\n", encoding="utf-8")
    trie_root = build_suffix_trie(
        [(0, offset, sentence) for offset, sentence in enumerate(sentences)]
    )
    configure_completion(trie_root, [source_path])


@pytest.mark.parametrize(
    ("query", "sentence", "score"),
    [
        pytest.param(
            "abcde", "xbcde and abcdx", 7, id="best-substitution-alignment"
        ),
        pytest.param(
            "xabcdef", "abcdef and xabcde", 10, id="best-extra-character-alignment"
        ),
        pytest.param(
            "abcde", "abxcde and abcdxe", 8, id="best-missing-character-alignment"
        ),
        pytest.param(
            "abxdef", "before abcdef after", 7, id="substitution-inside-context"
        ),
        pytest.param(
            "be, that", "To be or not to be, that is the question.", 14,
            id="normalized-official-example",
        ),
    ],
)
def test_fox_derived_search_chooses_best_legal_alignment(
    query: str,
    sentence: str,
    score: int,
    configure_fox_search: None,
) -> None:
    """Return the highest-scoring legal alignment, not the first one found."""
    del configure_fox_search

    result = next(
        (
            candidate
            for candidate in get_best_k_completions(query)
            if candidate.completed_sentence == sentence
        ),
        None,
    )

    assert result is not None
    assert result.score == score


def test_fox_derived_search_rejects_two_edits(configure_fox_search: None) -> None:
    """A completion that needs two corrections must not be returned."""
    del configure_fox_search

    assert get_best_k_completions("abxxef") == []
