"""Tests for fuzzy DFS trie search."""

from src.models import TrieNode
from src.online.models.correction import Correction, CorrectionType, SearchMatch
from src.online.search import search


def _add_path(root: TrieNode, text: str, sentence_ref: str) -> None:
    """Add a searchable path and its reference to a test trie.

    Args:
        root: The trie root to extend.
        text: The text represented by the new trie path.
        sentence_ref: A hashable stand-in for sentence metadata.
    """
    node = root
    for char in text:
        node = node.children.setdefault(char, TrieNode(char))
        node.sentence_refs.add(sentence_ref)


def _matches_with(
    results: list[SearchMatch], correction: Correction | None
) -> set[str]:
    """Collect references belonging to results with a given correction.

    Args:
        results: Search matches to inspect.
        correction: The correction used to select matches.

    Returns:
        All sentence references associated with the selected matches.
    """
    return {
        sentence_ref
        for match in results
        if match.correction == correction
        for sentence_ref in match.sentence_refs
    }


def test_search_finds_exact_substring_path() -> None:
    """Return sentence references for an exact normalized prefix."""
    root = TrieNode()
    _add_path(root, "to be or not to be", "question")

    results = search(root, "to be")

    assert _matches_with(results, None) == {"question"}


def test_search_finds_replacement_from_project_example() -> None:
    """Record a replacement for an incorrect query character."""
    root = TrieNode()
    _add_path(root, "to be", "question")

    results = search(root, "2o be")

    correction = Correction(CorrectionType.REPLACEMENT, position=1)
    assert _matches_with(results, correction) == {"question"}


def test_search_inserts_character_missing_from_query() -> None:
    """Record an insertion when the query omits a trie character."""
    root = TrieNode()
    _add_path(root, "or not", "question")

    results = search(root, "or nt")

    correction = Correction(CorrectionType.INSERTION, position=5)
    assert _matches_with(results, correction) == {"question"}


def test_search_deletes_extra_character_from_query() -> None:
    """Record a deletion when the query contains an extra character."""
    root = TrieNode()
    _add_path(root, "or not", "question")

    results = search(root, "or knot")

    correction = Correction(CorrectionType.DELETION, position=4)
    assert _matches_with(results, correction) == {"question"}


def test_search_reports_repeated_character_deletion_paths() -> None:
    """Return both valid deletion positions for adjacent repeated letters."""
    root = TrieNode()
    _add_path(root, "hello", "greeting")

    results = search(root, "heello")

    deletion_positions = {
        match.correction.position
        for match in results
        if match.correction is not None
        and match.correction.correction_type == CorrectionType.DELETION
        and "greeting" in match.sentence_refs
    }
    assert deletion_positions == {2, 3}


def test_search_rejects_more_than_one_correction() -> None:
    """Do not return a path requiring two character corrections."""
    root = TrieNode()
    _add_path(root, "hello", "greeting")

    assert search(root, "hxllo!") == []


def test_search_returns_empty_list_for_empty_prefix() -> None:
    """Handle an empty prefix without traversing the trie."""
    root = TrieNode()
    _add_path(root, "hello", "greeting")

    assert search(root, "") == []


def test_search_copies_sentence_reference_sets() -> None:
    """Do not expose a trie node's mutable reference set to callers."""
    root = TrieNode()
    _add_path(root, "hello", "greeting")

    result = next(match for match in search(root, "hello") if match.correction is None)
    result.sentence_refs.clear()

    node = root
    for char in "hello":
        node = node.children[char]
    assert node.sentence_refs == {"greeting"}
