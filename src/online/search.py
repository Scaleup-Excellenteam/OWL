"""Resumable fuzzy DFS traversal between trie search and scoring."""

from collections.abc import Sequence

from src.models import Correction, CorrectionType, SearchCursor, TrieNode
from src.online.models.correction import SearchMatch


def _dfs(
    node: TrieNode,
    prefix: str,
    input_idx: int,
    budget: int,
    current_correction: Correction | None,
    consumed_length: int,
    ends_with_space: bool,
    results: list[SearchMatch],
    cursors: list[SearchCursor],
) -> None:
    """Traverse trie paths at most one correction from the current chunk.

    Args:
        node: The current trie node being explored.
        prefix: The normalized input chunk being consumed.
        input_idx: The index of the next chunk character to match.
        budget: The number of corrections still available.
        current_correction: The correction used on the current path, if any.
        consumed_length: Number of normalized characters consumed before this
            chunk.
        ends_with_space: Whether the accumulated normalized input ends in a
            space after this chunk.
        results: The list that collects successful search matches.
        cursors: The list that collects resumable stopping points.
    """
    if input_idx == len(prefix):
        results.append(
            SearchMatch(
                sentence_refs=set(node.sentence_refs),
                correction=current_correction,
            )
        )
        cursors.append(
            SearchCursor(
                node=node,
                budget=budget,
                correction=current_correction,
                consumed_length=consumed_length + len(prefix),
                ends_with_space=ends_with_space,
            )
        )
        return

    current_char = prefix[input_idx]
    correction_position = consumed_length + input_idx + 1

    if budget == 1:
        deletion = Correction(CorrectionType.DELETION, correction_position)
        _dfs(
            node,
            prefix,
            input_idx + 1,
            0,
            deletion,
            consumed_length,
            ends_with_space,
            results,
            cursors,
        )

    for child_char, child_node in node.children.items():
        if child_char == current_char:
            _dfs(
                child_node,
                prefix,
                input_idx + 1,
                budget,
                current_correction,
                consumed_length,
                ends_with_space,
                results,
                cursors,
            )
        elif budget == 1:
            replacement = Correction(
                CorrectionType.REPLACEMENT,
                correction_position,
            )
            _dfs(
                child_node,
                prefix,
                input_idx + 1,
                0,
                replacement,
                consumed_length,
                ends_with_space,
                results,
                cursors,
            )

            insertion = Correction(
                CorrectionType.INSERTION,
                correction_position,
            )
            _dfs(
                child_node,
                prefix,
                input_idx,
                0,
                insertion,
                consumed_length,
                ends_with_space,
                results,
                cursors,
            )


def search(
    trie_root: TrieNode,
    chunk: str,
    cursors: Sequence[SearchCursor] | None = None,
    ends_with_space: bool | None = None,
) -> tuple[list[SearchMatch], list[SearchCursor]]:
    """Consume a normalized chunk along fuzzy trie paths.

    Args:
        trie_root: The root node of the suffix trie.
        chunk: The normalized input chunk to consume.
        cursors: Previous stopping points to resume. When omitted, traversal
            starts at the trie root with one available correction.
        ends_with_space: Whether the full raw input ends in a separator. When
            omitted, this is inferred from the normalized chunk.

    Returns:
        Search matches and their corresponding resumable stopping cursors.
        The two returned lists have matching indexes.
    """
    results: list[SearchMatch] = []
    next_cursors: list[SearchCursor] = []
    if cursors is None:
        if not chunk:
            return results, next_cursors
        starting_cursors = (
            SearchCursor(
                node=trie_root,
                budget=1,
                correction=None,
                consumed_length=0,
                ends_with_space=False,
            ),
        )
    else:
        starting_cursors = cursors

    for cursor in starting_cursors:
        cursor_ends_with_space = ends_with_space
        if cursor_ends_with_space is None:
            cursor_ends_with_space = (
                chunk.endswith(" ") if chunk else cursor.ends_with_space
            )
        _dfs(
            cursor.node,
            chunk,
            0,
            cursor.budget,
            cursor.correction,
            cursor.consumed_length,
            cursor_ends_with_space,
            results,
            next_cursors,
        )
    return results, next_cursors
