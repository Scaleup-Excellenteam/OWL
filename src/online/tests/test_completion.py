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

    results = get_best_k_completions("  TO,   BE ")

    assert [result.completed_sentence for result in results] == [
        "To be or not to be, that is the question.",
        "To become a better programmer.",
    ]
    assert [result.score for result in results] == [10, 10]
    assert [result.offset for result in results] == [1, 0]
    assert all(result.source_text.endswith("mock_source.txt") for result in results)


def test_completion_deduplicates_paths_and_keeps_best_score(
    tmp_path: Path,
) -> None:
    """Return one sentence when repeated letters allow two correction paths."""
    _configure_mock(tmp_path, ["Hello world."])

    results = get_best_k_completions("heello")

    assert len(results) == 1
    assert results[0].completed_sentence == "Hello world."
    assert results[0].score == 4


def test_completion_returns_at_most_five_results(tmp_path: Path) -> None:
    """Apply the public result limit after score and alphabetical ordering."""
    sentences = [f"Alpha completion {letter}." for letter in "gfedcba"]
    _configure_mock(tmp_path, sentences)

    results = get_best_k_completions("alpha")

    assert [result.completed_sentence for result in results] == sorted(sentences)[:5]


def test_completion_returns_no_results_for_empty_normalized_input(
    tmp_path: Path,
) -> None:
    """Avoid searching when the input contains only ignored characters."""
    _configure_mock(tmp_path, ["Hello world."])

    assert get_best_k_completions(" !!!  ") == []
