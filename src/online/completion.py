"""Coordinate normalization, fuzzy search, scoring, and result assembly."""

from pathlib import Path

from src.models import AutoCompleteData, SentenceMetadata, TrieNode, get_file_id, get_line_number
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
) -> dict[SentenceMetadata, tuple[SentenceMetadata, int]]:
    """Retain the highest-scoring search path for each sentence occurrence.

    Args:
        trie_root: Root of the suffix trie to search.
        normalized_prefix: Normalized, non-empty user input.

    Returns:
        Sentence metadata and its best score, keyed by file and line indexes.
    """
    best_results: dict[SentenceMetadata, tuple[SentenceMetadata, int]] = {}

    for match in search(trie_root, normalized_prefix):
        score = calculate_score(len(normalized_prefix), match.correction)
        for sentence_ref in match.sentence_refs:
            key = sentence_ref
            previous = best_results.get(key)
            if previous is None or score > previous[1]:
                best_results[key] = (sentence_ref, score)

    return best_results


def is_valid_match(query: str, text: str, errors: int = 0) -> bool:
    """Check if query is a valid fuzzy prefix of text with at most 1 error."""
    if errors > 1: return False
    i, j = 0, 0
    while i < len(query) and j < len(text):
        if query[i] == text[j]:
            i += 1
            j += 1
        else:
            if errors == 1: return False
            # Try deletion (query missing a char)
            if is_valid_match(query[i:], text[j+1:], 1): return True
            # Try insertion (query has extra char)
            if is_valid_match(query[i+1:], text[j:], 1): return True
            # Try replacement
            if is_valid_match(query[i+1:], text[j+1:], 1): return True
            return False
            
    # If query is longer than text, remaining chars count as insertions
    return errors + (len(query) - i) <= 1


def is_fuzzy_substring(query: str, text: str) -> bool:
    """Check if query fuzzy matches ANY word-boundary suffix of the text."""
    if is_valid_match(query, text):
        return True
        
    for i in range(1, len(text)):
        if text[i-1] == " ":
            if is_valid_match(query, text[i:]):
                return True
    return False


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

    # 1. Group candidates by score to avoid processing lower scores if we have enough
    from collections import defaultdict
    best_scores = _best_scores_by_sentence(_trie_root, normalized_prefix)
    score_buckets = defaultdict(list)
    for metadata, score in best_scores.values():
        score_buckets[score].append(metadata)

    completions = []
    from src.utils import get_original_sentences_batched

    # 2. Iterate from highest score to lowest
    for score in sorted(score_buckets.keys(), reverse=True):
        bucket_metadata = score_buckets[score]
        
        # Batch fetch all required sentences from disk for this score group
        fetched_sentences = get_original_sentences_batched(bucket_metadata, _file_registry)
        
        bucket_completions = []
        for metadata in bucket_metadata:
            sentence = fetched_sentences.get(metadata)
            if sentence is None:
                continue
                
            # Fine Filter: If query exceeded trie depth, verify the match manually
            if len(normalized_prefix) > 15:
                normalized_sentence = normalize_text(sentence)
                if not is_fuzzy_substring(normalized_prefix, normalized_sentence):
                    continue
                    
            bucket_completions.append(
                AutoCompleteData(
                    completed_sentence=sentence,
                    source_text=str(_file_registry[get_file_id(metadata)]),
                    offset=get_line_number(metadata),
                    score=score,
                )
            )
            
        # Sort this bucket alphabetically to break score ties
        bucket_completions.sort(
            key=lambda c: (c.completed_sentence, c.source_text, c.offset)
        )
        
        completions.extend(bucket_completions)
        
        # If we have collected at least 5 completions across the highest buckets, we are done!
        if len(completions) >= 5:
            break

    return completions[:5]
