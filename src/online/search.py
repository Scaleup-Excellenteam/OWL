"""Fuzzy DFS traversal at the boundary between trie search and scoring."""

from src.models import Correction, CorrectionType, TrieNode
from src.online.models.correction import SearchMatch


def _gather_refs(node: TrieNode, max_refs: int = 25) -> set[int]:
    collected = set()
    if node.sentence_refs is not None:
        collected.update(node.sentence_refs)
    
    if len(collected) >= max_refs:
        return set(list(collected)[:max_refs])
        
    if node.children is not None:
        for child in node.children.values():
            collected.update(_gather_refs(child, max_refs - len(collected)))
            if len(collected) >= max_refs:
                break
                
    return collected


def _dfs(
    node: TrieNode,
    prefix: str,
    input_idx: int,
    budget: int,
    current_correction: Correction | None,
    results: list[SearchMatch],
    trie_depth: int = 0,
    max_results: int | None = None,
) -> None:
    """Traverse trie paths that are at most one correction from the prefix."""
    if max_results is not None and len(results) >= max_results:
        return

    if input_idx >= len(prefix):
        refs = _gather_refs(node, 25)
        if refs:
            results.append(
                SearchMatch(
                    sentence_refs=refs,
                    correction=current_correction,
                )
            )
        return

    # Only accept truncated leaves if they actually reached the depth limit!
    if node.children is None:
        if trie_depth >= 15:
            refs = _gather_refs(node, 25)
            if refs:
                results.append(
                    SearchMatch(
                        sentence_refs=refs,
                        correction=current_correction,
                    )
                )
        return

    current_char = prefix[input_idx]

    if budget == 1:
        deletion = Correction(CorrectionType.DELETION, input_idx + 1)
        _dfs(node, prefix, input_idx + 1, 0, deletion, results, trie_depth, max_results)

    if node.children is not None:
        for child_char, child_node in node.children.items():
            if child_char == current_char:
                _dfs(
                    child_node,
                    prefix,
                    input_idx + 1,
                    budget,
                    current_correction,
                    results,
                    trie_depth + 1,
                    max_results
                )
            elif budget == 1:
                replacement = Correction(CorrectionType.REPLACEMENT, input_idx + 1)
                _dfs(child_node, prefix, input_idx + 1, 0, replacement, results, trie_depth + 1, max_results)

                insertion = Correction(CorrectionType.INSERTION, input_idx + 1)
                _dfs(child_node, prefix, input_idx, 0, insertion, results, trie_depth + 1, max_results)


def search(trie_root: TrieNode, prefix: str, max_results: int | None = None) -> list[SearchMatch]:
    results: list[SearchMatch] = []
    if not prefix:
        return results

    _dfs(trie_root, prefix, 0, 1, None, results, 0, max_results)
    return results
