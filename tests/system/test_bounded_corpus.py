"""Deterministic top-five correctness tests over the saved bounded corpus."""

from __future__ import annotations

import pytest

from src.online.completion import get_best_k_completions
from tests.system.conftest import canonicalize_sample_results
from tests.system.oracle import CorpusLine, rank_all, top_five


QUERY_MATRIX = {
    "exact_short": "base64",
    "exact_long": "the python profilers",
    "sentence_middle": "deterministic profiling",
    "inside_word": "ternet engineering",
    "replacement": "baze64",
    "missing_character": "bse64",
    "extra_character": "basex64",
    "two_errors": "baze6x",
    "case_punctuation_whitespace": "  THIS,   DOCUMENT!!! ",
    "alphabetical_and_more_than_five": "this document is",
    "more_than_25": "internet",
    "long_edit_after_trie_depth": "this document provydes a terminology",
}


@pytest.mark.parametrize("query", QUERY_MATRIX.values(), ids=QUERY_MATRIX.keys())
def test_saved_sample_exact_top_five_matches_independent_oracle(
    query: str,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Require the public API to equal the oracle's complete top five.

    Args:
        query: Fixed matrix query.
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected


@pytest.mark.parametrize("query", QUERY_MATRIX.values(), ids=QUERY_MATRIX.keys())
def test_saved_sample_calls_are_deterministic(
    query: str,
    configured_sample_system: object,
) -> None:
    """Require repeated public calls to return identical ordered results.

    Args:
        query: Fixed matrix query.
        configured_sample_system: Fixture configuring the saved trie.
    """
    del configured_sample_system
    first = canonicalize_sample_results(get_best_k_completions(query))
    for _ in range(4):
        assert canonicalize_sample_results(get_best_k_completions(query)) == first


def test_high_fanout_query_really_exceeds_25_candidates(
    bounded_corpus: list[CorpusLine],
) -> None:
    """Guard the candidate-cap regression case against fixture drift.

    Args:
        bounded_corpus: Independently loaded bounded records.
    """
    assert len(rank_all(QUERY_MATRIX["more_than_25"], bounded_corpus)) > 25


def test_duplicate_sentence_occurrences_are_in_sample(
    bounded_corpus: list[CorpusLine],
) -> None:
    """Guard duplicate-source coverage against fixture drift.

    Args:
        bounded_corpus: Independently loaded bounded records.
    """
    ranked = rank_all(QUERY_MATRIX["alphabetical_and_more_than_five"], bounded_corpus)
    sentences = [result.completed_sentence for result in ranked]
    assert len(sentences) > len(set(sentences))
