"""Fuzzy DFS traversal at the boundary between trie search and scoring."""

from src.models import TrieNode
from src.online.models.correction import Correction, CorrectionType, SearchMatch


def _dfs(
    node: TrieNode,
    prefix: str,
    input_idx: int,
    budget: int,
    current_correction: Correction | None,
    results: list[SearchMatch],
) -> None:
    """Traverse trie paths that are at most one correction from the prefix.

    Args:
        node: The current trie node being explored.
        prefix: The user's typed search string.
        input_idx: The index of the next prefix character to match.
        budget: The number of corrections still available.
        current_correction: The correction used on the current path, if any.
        results: The list that collects successful search matches.
    """
    if input_idx == len(prefix):
        results.append(
            SearchMatch(
                sentence_refs=set(node.sentence_refs),
                correction=current_correction,
            )
        )
        return

    current_char = prefix[input_idx]

    if budget == 1:
        deletion = Correction(CorrectionType.DELETION, input_idx + 1)
        _dfs(node, prefix, input_idx + 1, 0, deletion, results)

    for child_char, child_node in node.children.items():
        if child_char == current_char:
            _dfs(
                child_node,
                prefix,
                input_idx + 1,
                budget,
                current_correction,
                results,
            )
        elif budget == 1:
            replacement = Correction(CorrectionType.REPLACEMENT, input_idx + 1)
            _dfs(child_node, prefix, input_idx + 1, 0, replacement, results)

            insertion = Correction(CorrectionType.INSERTION, input_idx + 1)
            _dfs(child_node, prefix, input_idx, 0, insertion, results)


def search(trie_root: TrieNode, prefix: str) -> list[SearchMatch]:
    """Find trie paths matching a prefix with at most one correction.

    Args:
        trie_root: The root node of the suffix trie.
        prefix: The user's typed search string.

    Returns:
        Search matches containing sentence references and the correction used
        by each successful path.
    """
    results: list[SearchMatch] = []
    if not prefix:
        return results

    _dfs(trie_root, prefix, 0, 1, None, results)
    return results
