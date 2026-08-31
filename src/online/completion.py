"""Coordinate normalization, fuzzy search, scoring, and result assembly."""

from collections.abc import Sequence
from pathlib import Path
import string

from src.models import AutoCompleteData, SearchCursor, SentenceMetadata, TrieNode
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
    normalized_chunk: str,
    cursors: Sequence[SearchCursor] | None,
    ends_with_space: bool,
) -> tuple[
    dict[tuple[int, int], tuple[SentenceMetadata, int]],
    list[SearchCursor],
]:
    """Retain the highest-scoring search path for each sentence occurrence.

    Args:
        trie_root: Root of the suffix trie to search.
        normalized_chunk: Normalized input chunk to consume.
        cursors: Previous search stopping points, or ``None`` for a new search.
        ends_with_space: Whether the complete raw input ends in a separator.

    Returns:
        Best sentence scores keyed by source position, and new search cursors.
    """
    best_results: dict[tuple[int, int], tuple[SentenceMetadata, int]] = {}

    matches, next_cursors = search(
        trie_root,
        normalized_chunk,
        cursors,
        ends_with_space,
    )
    for match, cursor in zip(matches, next_cursors, strict=True):
        score = calculate_score(cursor.consumed_length, match.correction)
        for sentence_ref in match.sentence_refs:
            key = (sentence_ref.file_id, sentence_ref.line_number)
            previous = best_results.get(key)
            if previous is None or score > previous[1]:
                best_results[key] = (sentence_ref, score)

    return best_results, next_cursors


def _is_normalized_separator(character: str) -> bool:
    """Return whether normalization maps a character to a word separator.

    Args:
        character: A single raw input character.

    Returns:
        ``True`` for whitespace and standard punctuation.
    """
    return character.isspace() or character in string.punctuation


def _normalize_chunk(
    chunk: str,
    cursors: Sequence[SearchCursor] | None,
) -> tuple[str, bool]:
    """Normalize a raw chunk while preserving continuous-search boundaries.

    Args:
        chunk: Newly appended raw input.
        cursors: Previous search stopping points, or ``None`` for an initial
            input.

    Returns:
        A normalized chunk whose boundary spaces compose correctly with the
        previous input, plus whether the raw input ends in a separator.

    Raises:
        ValueError: If cursors from incompatible input states are combined.
    """
    previous_ends_with_space = False
    if cursors:
        ending_states = {cursor.ends_with_space for cursor in cursors}
        if len(ending_states) != 1:
            raise ValueError("all cursors must represent the same normalized input")
        previous_ends_with_space = ending_states.pop()

    normalized = normalize_text(chunk)
    if not chunk:
        return normalized, previous_ends_with_space

    begins_with_separator = _is_normalized_separator(chunk[0])
    ends_with_separator = _is_normalized_separator(chunk[-1])

    if normalized and cursors is not None:
        if previous_ends_with_space or begins_with_separator:
            normalized = f" {normalized}"

    return normalized, ends_with_separator


def get_best_k_completions(
    chunk: str,
    cursors: Sequence[SearchCursor] | None = None,
) -> tuple[list[AutoCompleteData], list[SearchCursor]]:
    """Return completions and resumable cursors after consuming a raw chunk.

    Args:
        chunk: Newly appended raw input. For a new search, this is the complete
            initial input.
        cursors: Search cursors returned for the previous input, or ``None`` to
            begin a new search.

    Returns:
        Up to five ranked completions and the new search stopping cursors.

    Raises:
        RuntimeError: If completion data has not been configured.
    """
    if _trie_root is None or _file_registry is None:
        raise RuntimeError(
            "completion is not configured; call configure_completion() first"
        )

    normalized_chunk, ends_with_space = _normalize_chunk(chunk, cursors)
    if not normalized_chunk and cursors is None:
        return [], []

    completions = []
    best_scores, next_cursors = _best_scores_by_sentence(
        _trie_root,
        normalized_chunk,
        cursors,
        ends_with_space,
    )
    for metadata, score in best_scores.values():
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
    return completions[:5], next_cursors
