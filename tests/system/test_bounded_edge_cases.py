"""Focused online-contract coverage over the saved bounded corpus."""

from __future__ import annotations

import pytest

from src.online.completion import get_best_k_completions
from tests.system.conftest import canonicalize_sample_results
from tests.system.oracle import CorpusLine, best_score, top_five


EDIT_SENTENCE = "qvwxabcdef"

PENALTY_CASES = [
    pytest.param("zvwxabcdef", 13, id="replacement-position-1"),
    pytest.param("qzwxabcdef", 14, id="replacement-position-2"),
    pytest.param("qvzxabcdef", 15, id="replacement-position-3"),
    pytest.param("qvwzabcdef", 16, id="replacement-position-4"),
    pytest.param("qvwxzbcdef", 17, id="replacement-position-5"),
    pytest.param("qvwxabcdez", 17, id="replacement-last-position"),
    pytest.param("zqvwxabcdef", 10, id="extra-position-1"),
    pytest.param("qzvwxabcdef", 12, id="extra-position-2"),
    pytest.param("qvzwxabcdef", 14, id="extra-position-3"),
    pytest.param("qvwzxabcdef", 16, id="extra-position-4"),
    pytest.param("qvwxzabcdef", 18, id="extra-position-5"),
    pytest.param("qvwxabcdefz", 18, id="extra-after-last-position"),
    pytest.param("qvxabcdef", 12, id="missing-position-3"),
    pytest.param("qvwabcdef", 14, id="missing-position-4"),
    pytest.param("qvwxbcdef", 16, id="missing-position-5"),
]

BOUNDARY_QUERIES = [
    pytest.param("wholelineuniquetoken", id="whole-source-line"),
    pytest.param("endboundaryuniquetoken", id="sentence-end"),
    pytest.param("mnrstuv", id="inside-word-exact"),
    pytest.param("mnrxtuv", id="inside-word-replacement"),
    pytest.param("qvwxabcde", id="shorter-query-is-exact-prefix"),
    pytest.param("wholelineuniquetokenzz", id="query-two-characters-too-long"),
    pytest.param("q", id="one-character-query"),
    pytest.param("qv", id="two-character-query"),
]

SPEC_SCORE_CASES = [
    pytest.param("To be", 10, id="exact"),
    pytest.param("or Not", 12, id="case-insensitive"),
    pytest.param("be, that", 14, id="punctuation-normalized"),
    pytest.param("2o be", 3, id="replacement-position-1"),
    pytest.param("to pe", 6, id="replacement-position-4"),
    pytest.param("or knot", 8, id="extra-position-4"),
    pytest.param("or nt", 8, id="missing-position-5"),
    pytest.param("not be", None, id="more-than-one-edit"),
]


@pytest.mark.parametrize(("query", "expected_score"), SPEC_SCORE_CASES)
def test_independent_oracle_reproduces_specification_examples(
    query: str,
    expected_score: int | None,
) -> None:
    """Lock the independent oracle to the Part A appendix examples.

    Args:
        query: Query copied from the specification appendix.
        expected_score: Score stated by the specification, if it is a match.
    """
    sentence = "To be or not to be, that is the question."
    assert best_score(query, sentence) == expected_score


@pytest.mark.parametrize(("query", "expected_target_score"), PENALTY_CASES)
def test_every_edit_penalty_band_matches_oracle_and_explicit_score(
    query: str,
    expected_target_score: int,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check every reachable penalty band, including extra-character boundaries.

    Args:
        query: A query with exactly one controlled edit.
        expected_target_score: Score required for the controlled sentence.
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == top_five(query, bounded_corpus)

    target = next(
        (result for result in actual if result.completed_sentence == EDIT_SENTENCE),
        None,
    )
    assert target is not None, "controlled penalty result was omitted from the top five"
    assert target.score == expected_target_score


@pytest.mark.parametrize("query", BOUNDARY_QUERIES)
def test_boundary_and_short_queries_match_independent_oracle(
    query: str,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check sentence, word, query-length, and short-query boundaries.

    Args:
        query: Controlled boundary query.
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == top_five(query, bounded_corpus)


def test_normalization_variants_have_identical_complete_top_five(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check case, punctuation, surrounding space, and whitespace collapsing.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    variants = (
        "normalization marker to be or not to be",
        "NORMALIZATION MARKER TO BE OR NOT TO BE",
        "  normalization   marker: to be, or not to be!!!  ",
        "normalization\tmarker to\tbe or   not to be",
    )
    expected = top_five(variants[0], bounded_corpus)
    for query in variants:
        assert top_five(query, bounded_corpus) == expected
        assert canonicalize_sample_results(get_best_k_completions(query)) == expected


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace-only"),
        pytest.param("!!! @#$ ...", id="punctuation-only"),
    ],
)
def test_normalized_empty_queries_return_no_results(
    query: str,
    configured_sample_system: object,
) -> None:
    """Require empty queries after normalization to return an empty list.

    Args:
        query: Raw empty-equivalent input.
        configured_sample_system: Fixture configuring the saved trie.
    """
    del configured_sample_system
    assert get_best_k_completions(query) == []


def test_fewer_than_five_results_are_returned_without_padding(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Require a unique query to return its sole completion only.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    query = "uniquelysingleresulttoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert len(expected) == 1
    assert actual == expected


def test_no_match_returns_an_empty_list(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Require a controlled query with two errors to return no completions.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    query = "uniquelysingleresulttokzz"
    assert top_five(query, bounded_corpus) == []
    assert get_best_k_completions(query) == []


def test_duplicate_occurrences_are_preserved_with_distinct_offsets(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Require identical source lines at different offsets to remain distinct.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    query = "universaltwinduplicatetoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert len(expected) == 2
    assert len({(result.source_text, result.offset) for result in expected}) == 2
    assert actual == expected


def test_best_occurrence_within_one_sentence_determines_its_score(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Prefer a later exact occurrence over an earlier corrected occurrence.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    query = "competitionuniquetoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected
    assert actual[0].score == 2 * len(query)


def test_repeated_characters_choose_the_highest_scoring_alignment(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Choose the least-penalized correction when repeated characters align twice.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
        bounded_corpus: Independently loaded bounded records.
    """
    del configured_sample_system
    query = "bookkeeperuniquetoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected
    assert actual[0].score == 2 * len(query) - 4


def test_result_objects_expose_the_required_online_contract(
    configured_sample_system: object,
) -> None:
    """Check the four required output fields and their basic value types.

    Args:
        configured_sample_system: Fixture configuring the saved trie.
    """
    del configured_sample_system
    results = get_best_k_completions("uniquelysingleresulttoken")
    assert results
    for result in results:
        assert isinstance(result.completed_sentence, str)
        assert isinstance(result.source_text, str)
        assert isinstance(result.offset, int)
        assert isinstance(result.score, int)
