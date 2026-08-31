"""Tests for fuzzy DFS trie search."""

from src.models import Correction, CorrectionType, SentenceMetadata, TrieNode
from src.online.models.correction import SearchMatch
from src.online.search import search


_QUESTION = SentenceMetadata(file_id=0, line_number=0)
_GREETING = SentenceMetadata(file_id=0, line_number=1)


def _add_path(
    root: TrieNode,
    text: str,
    sentence_ref: SentenceMetadata,
) -> None:
    """Add a searchable path and its reference to a test trie.

    Args:
        root: The trie root to extend.
        text: The text represented by the new trie path.
        sentence_ref: Metadata associated with the searchable path.
    """
    node = root
    for char in text:
        node = node.children.setdefault(char, TrieNode(char))
        node.sentence_refs.add(sentence_ref)


def _matches_with(
    results: list[SearchMatch], correction: Correction | None
) -> set[SentenceMetadata]:
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
    _add_path(root, "to be or not to be", _QUESTION)

    results, _ = search(root, "to be")

    assert _matches_with(results, None) == {_QUESTION}


def test_search_finds_replacement_from_project_example() -> None:
    """Record a replacement for an incorrect query character."""
    root = TrieNode()
    _add_path(root, "to be", _QUESTION)

    results, _ = search(root, "2o be")

    correction = Correction(CorrectionType.REPLACEMENT, position=1)
    assert _matches_with(results, correction) == {_QUESTION}


def test_search_inserts_character_missing_from_query() -> None:
    """Record an insertion when the query omits a trie character."""
    root = TrieNode()
    _add_path(root, "or not", _QUESTION)

    results, _ = search(root, "or nt")

    correction = Correction(CorrectionType.INSERTION, position=5)
    assert _matches_with(results, correction) == {_QUESTION}


def test_search_deletes_extra_character_from_query() -> None:
    """Record a deletion when the query contains an extra character."""
    root = TrieNode()
    _add_path(root, "or not", _QUESTION)

    results, _ = search(root, "or knot")

    correction = Correction(CorrectionType.DELETION, position=4)
    assert _matches_with(results, correction) == {_QUESTION}


def test_search_reports_repeated_character_deletion_paths() -> None:
    """Return both valid deletion positions for adjacent repeated letters."""
    root = TrieNode()
    _add_path(root, "hello", _GREETING)

    results, _ = search(root, "heello")

    deletion_positions = {
        match.correction.position
        for match in results
        if match.correction is not None
        and match.correction.correction_type == CorrectionType.DELETION
        and _GREETING in match.sentence_refs
    }
    assert deletion_positions == {2, 3}


def test_search_rejects_more_than_one_correction() -> None:
    """Do not return a path requiring two character corrections."""
    root = TrieNode()
    _add_path(root, "hello", _GREETING)

    assert search(root, "hxllo!") == ([], [])


def test_search_returns_empty_list_for_empty_prefix() -> None:
    """Handle an empty prefix without traversing the trie."""
    root = TrieNode()
    _add_path(root, "hello", _GREETING)

    assert search(root, "") == ([], [])


def test_search_copies_sentence_reference_sets() -> None:
    """Do not expose a trie node's mutable reference set to callers."""
    root = TrieNode()
    _add_path(root, "hello", _GREETING)

    results, _ = search(root, "hello")
    result = next(match for match in results if match.correction is None)
    result.sentence_refs.clear()

    node = root
    for char in "hello":
        node = node.children[char]
    assert node.sentence_refs == {_GREETING}


def test_search_resumes_exact_path_and_tracks_consumed_length() -> None:
    """Continue from prior nodes without traversing from the trie root."""
    root = TrieNode()
    _add_path(root, "to be or not to be", _QUESTION)

    _, cursors = search(root, "to be")
    results, next_cursors = search(root, " or", cursors)

    assert _matches_with(results, None) == {_QUESTION}
    exact_cursor = next(
        cursor for cursor in next_cursors if cursor.correction is None
    )
    assert exact_cursor.consumed_length == len("to be or")
    assert exact_cursor.budget == 1


def test_search_offsets_correction_position_in_resumed_chunk() -> None:
    """Report correction positions relative to the complete normalized input."""
    root = TrieNode()
    _add_path(root, "to be", _QUESTION)

    _, cursors = search(root, "to ")
    results, next_cursors = search(root, "pe", cursors)

    correction = Correction(CorrectionType.REPLACEMENT, position=4)
    assert _matches_with(results, correction) == {_QUESTION}
    matching_cursor = next(
        cursor for cursor in next_cursors if cursor.correction == correction
    )
    assert matching_cursor.consumed_length == len("to pe")
    assert matching_cursor.budget == 0


def test_search_preserves_spent_budget_across_chunks() -> None:
    """Reject a second correction after an earlier chunk spent the budget."""
    root = TrieNode()
    _add_path(root, "hello", _GREETING)

    _, cursors = search(root, "hx")
    results, next_cursors = search(root, "llo!", cursors)

    assert results == []
    assert next_cursors == []


def test_search_updates_boundary_state_without_consuming_a_character() -> None:
    """Retain trie positions while recording a pending normalized separator."""
    root = TrieNode()
    _add_path(root, "hello world", _GREETING)

    results, cursors = search(root, "hello")
    repeated_results, pending_cursors = search(
        root,
        "",
        cursors,
        ends_with_space=True,
    )

    assert repeated_results == results
    assert all(cursor.consumed_length == 5 for cursor in pending_cursors)
    assert all(cursor.ends_with_space for cursor in pending_cursors)
