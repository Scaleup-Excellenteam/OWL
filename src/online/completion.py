"""Coordinate normalization, fuzzy search, scoring, and result assembly."""

from pathlib import Path

from src.models import AutoCompleteData, SentenceMetadata, TrieNode
from src.online.scoring import calculate_score
from src.online.search import search
from src.utils import get_original_sentence, normalize_text

_trie_root: TrieNode | None = None
_file_registry: list[Path] | None = None


def configure_completion(
    trie_root: TrieNode,
    registry: list[Path],
) -> None:
    """Configure the initialized data used by completion requests.

    Args:
        trie_root: Root of the suffix trie to search.
        registry: File paths indexed by ``SentenceMetadata.file_id``.
    """
    global _trie_root, _file_registry
    _trie_root = trie_root
    _file_registry = list(registry)


def _best_scores_by_sentence(
    trie_root: TrieNode,
    normalized_prefix: str,
) -> dict[tuple[int, int], tuple[SentenceMetadata, int]]:
    """Retain the highest-scoring search path for each sentence occurrence.

    Args:
        trie_root: Root of the suffix trie to search.
        normalized_prefix: Normalized, non-empty user input.

    Returns:
        Sentence metadata and its best score, keyed by file and line indexes.
    """
    best_results: dict[tuple[int, int], tuple[SentenceMetadata, int]] = {}

    for match in search(trie_root, normalized_prefix):
        score = calculate_score(len(normalized_prefix), match.correction)
        for sentence_ref in match.sentence_refs:
            key = (sentence_ref.file_id, sentence_ref.line_number)
            previous = best_results.get(key)
            if previous is None or score > previous[1]:
                best_results[key] = (sentence_ref, score)

    return best_results


def get_best_k_completions(prefix: str) -> list[AutoCompleteData]:
    """Return the five best sentence completions for a user prefix.

    Args:
        prefix: Raw text typed by the user.

    Returns:
        Up to five completions ordered by descending score and then
        alphabetically by their original sentence text.

    Raises:
        RuntimeError: If completion data has not been configured.
    """
    if _trie_root is None or _file_registry is None:
        raise RuntimeError(
            "completion is not configured; call configure_completion() first"
        )

    normalized_prefix = normalize_text(prefix)
    if not normalized_prefix:
        return []

    completions = []
    for metadata, score in _best_scores_by_sentence(
        _trie_root,
        normalized_prefix,
    ).values():
        sentence = get_original_sentence(metadata, _file_registry)
        completions.append(
            AutoCompleteData(
                completed_sentence=sentence,
                source_text=str(_file_registry[metadata.file_id]),
                offset=metadata.line_number,
                score=score,
            )
        )

    completions.sort(
        key=lambda completion: (
            -completion.score,
            completion.completed_sentence,
            completion.source_text,
            completion.offset,
        )
    )
    return completions[:5]
