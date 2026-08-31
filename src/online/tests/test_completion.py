"""Integration tests for completion using real search and scoring modules."""

from pathlib import Path

import pytest

import src.online.completion as completion_module
from src.online.completion import configure_completion, get_best_k_completions
from src.online.tests.mock_data import build_mock_system


def _configure_mock(tmp_path: Path, sentences: list[str]) -> None:
    """Configure completion with a temporary mock corpus.

    Args:
        tmp_path: Temporary directory supplied by pytest.
        sentences: Original source lines to index.
    """
    trie_root, registry = build_mock_system(tmp_path, sentences)
    configure_completion(trie_root, registry)


def test_completion_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject completion calls made before system initialization."""
    monkeypatch.setattr(completion_module, "_trie_root", None)
    monkeypatch.setattr(completion_module, "_file_registry", None)

    with pytest.raises(RuntimeError, match="configure_completion"):
        get_best_k_completions("hello")


def test_completion_uses_real_search_scoring_and_original_text(
    tmp_path: Path,
) -> None:
    """Search, score, rank, and hydrate matches from their source file."""
    _configure_mock(
        tmp_path,
        [
            "To become a better programmer.",
            "To be or not to be, that is the question.",
            "Nothing relevant here.",
        ],
    )

    results, cursors = get_best_k_completions("  TO,   BE ")

    assert [result.completed_sentence for result in results] == [
        "To be or not to be, that is the question.",
        "To become a better programmer.",
    ]
    assert [result.score for result in results] == [10, 10]
    assert [result.offset for result in results] == [1, 0]
    assert all(result.source_text.endswith("mock_source.txt") for result in results)
    assert cursors
    assert all(cursor.ends_with_space for cursor in cursors)


def test_completion_deduplicates_paths_and_keeps_best_score(
    tmp_path: Path,
) -> None:
    """Return one sentence when repeated letters allow two correction paths."""
    _configure_mock(tmp_path, ["Hello world."])

    results, _ = get_best_k_completions("heello")

    assert len(results) == 1
    assert results[0].completed_sentence == "Hello world."
    assert results[0].score == 4


def test_completion_returns_at_most_five_results(tmp_path: Path) -> None:
    """Apply the public result limit after score and alphabetical ordering."""
    sentences = [f"Alpha completion {letter}." for letter in "gfedcba"]
    _configure_mock(tmp_path, sentences)

    results, _ = get_best_k_completions("alpha")

    assert [result.completed_sentence for result in results] == sorted(sentences)[:5]


def test_completion_returns_no_results_for_empty_normalized_input(
    tmp_path: Path,
) -> None:
    """Avoid searching when the input contains only ignored characters."""
    _configure_mock(tmp_path, ["Hello world."])

    assert get_best_k_completions(" !!!  ") == ([], [])


@pytest.mark.parametrize(
    ("query", "expected_score"),
    [
        ("To be", 10),
        ("or Not", 12),
        ("be, that", 14),
        ("2o be", 3),
        ("to pe", 6),
        ("or knot", 8),
        ("or nt", 8),
    ],
)
def test_completion_matches_project_definition_examples(
    tmp_path: Path,
    query: str,
    expected_score: int,
) -> None:
    """Match and score every successful example from the specification."""
    sentence = "To be or not to be, that is the question."
    _configure_mock(tmp_path, [sentence])

    results, _ = get_best_k_completions(query)

    assert [(result.completed_sentence, result.score) for result in results] == [
        (sentence, expected_score)
    ]


def test_completion_rejects_project_definition_non_match(tmp_path: Path) -> None:
    """Reject the specification's query that requires more than one edit."""
    _configure_mock(tmp_path, ["To be or not to be, that is the question."])

    results, cursors = get_best_k_completions("not be")

    assert results == []
    assert cursors == []


def test_completion_resumes_with_cumulative_score(tmp_path: Path) -> None:
    """Score resumed matches using the complete accumulated query length."""
    sentence = "To be or not to be, that is the question."
    _configure_mock(tmp_path, [sentence])

    _, cursors = get_best_k_completions("to be")
    results, next_cursors = get_best_k_completions(" or", cursors)

    assert [(result.completed_sentence, result.score) for result in results] == [
        (sentence, 16)
    ]
    assert any(cursor.consumed_length == 8 for cursor in next_cursors)


def test_completion_scores_correction_in_later_chunk_globally(
    tmp_path: Path,
) -> None:
    """Keep global correction positions when the mistake is in a later chunk."""
    sentence = "To be or not to be, that is the question."
    _configure_mock(tmp_path, [sentence])

    _, cursors = get_best_k_completions("to ")
    results, _ = get_best_k_completions("pe", cursors)

    assert [(result.completed_sentence, result.score) for result in results] == [
        (sentence, 6)
    ]


def test_completion_carries_earlier_correction_into_later_chunk(
    tmp_path: Path,
) -> None:
    """Preserve an earlier correction and its budget while search continues."""
    sentence = "To be or not to be, that is the question."
    _configure_mock(tmp_path, [sentence])

    _, cursors = get_best_k_completions("2o")
    results, next_cursors = get_best_k_completions(" be", cursors)

    assert [(result.completed_sentence, result.score) for result in results] == [
        (sentence, 3)
    ]
    assert all(cursor.budget == 0 for cursor in next_cursors)


def test_completion_collapses_whitespace_across_chunk_boundaries(
    tmp_path: Path,
) -> None:
    """Treat repeated separators split across calls as one normalized space."""
    sentence = "Hello world."
    _configure_mock(tmp_path, [sentence])

    initial_results, cursors = get_best_k_completions("hello ")
    separator_results, cursors = get_best_k_completions("   ", cursors)
    final_results, final_cursors = get_best_k_completions("WORLD", cursors)

    assert initial_results[0].score == 10
    assert separator_results[0].score == 10
    assert final_results[0].score == 22
    assert any(cursor.consumed_length == 11 for cursor in final_cursors)
    assert all(not cursor.ends_with_space for cursor in final_cursors)


def test_completion_preserves_punctuation_boundary_between_chunks(
    tmp_path: Path,
) -> None:
    """Convert punctuation at one chunk's end into one later separator."""
    sentence = "Hello world."
    _configure_mock(tmp_path, [sentence])

    _, cursors = get_best_k_completions("hello,")
    results, _ = get_best_k_completions("world", cursors)

    assert [(result.completed_sentence, result.score) for result in results] == [
        (sentence, 22)
    ]
