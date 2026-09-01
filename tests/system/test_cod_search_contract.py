"""COD-derived search-mechanism contracts using OWL's real trie setup."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.offline.trie_builder import build_suffix_trie
from src.online.completion import configure_completion, get_best_k_completions


SENTENCES = [
    "To be or not to be, that is the question.",
    "Something useful happens here.",
]


@pytest.fixture()
def configured_cod_search(tmp_path: Path) -> None:
    """Configure production completion with COD's compact search corpus."""
    source_path = tmp_path / "cod_contract_corpus.txt"
    source_path.write_text("\n".join(SENTENCES) + "\n", encoding="utf-8")
    trie_root = build_suffix_trie(
        [(0, offset, sentence) for offset, sentence in enumerate(SENTENCES)]
    )
    configure_completion(trie_root, [source_path])


@pytest.mark.parametrize(
    ("query", "sentence", "score"),
    [
        pytest.param("2o be", SENTENCES[0], 3, id="replacement"),
        pytest.param("to pe", SENTENCES[0], 6, id="replacement-later-position"),
        pytest.param("or knot", SENTENCES[0], 8, id="extra-character"),
        pytest.param("or nt", SENTENCES[0], 8, id="missing-character"),
        pytest.param("xomething useful", SENTENCES[1], 25, id="early-anchor-error"),
        pytest.param("something usefyl", SENTENCES[1], 29, id="late-anchor-error"),
    ],
)
def test_cod_derived_one_edit_search_contracts(
    query: str,
    sentence: str,
    score: int,
    configured_cod_search: None,
) -> None:
    """Find and score a legal one-edit completion through OWL's public API."""
    del configured_cod_search

    results = get_best_k_completions(query)

    target = next(
        (result for result in results if result.completed_sentence == sentence), None
    )
    assert target is not None
    assert target.score == score
