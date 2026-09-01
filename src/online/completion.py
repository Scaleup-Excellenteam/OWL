"""Coordinate normalization, fuzzy search, scoring, and result assembly."""

from pathlib import Path

from src.models import AutoCompleteData, SentenceMetadata, TrieNode, get_file_id, get_line_number
from src.online.query_cache import (
    DEFAULT_QUERY_CACHE_CAPACITY,
    QueryCacheInfo,
    QueryResultCache,
)
from src.online.scoring import calculate_score
from src.online.search import search
from src.utils import get_original_sentence, normalize_text

_trie_root: TrieNode | None = None
_file_registry: list[Path] | None = None
_query_cache = QueryResultCache()


def configure_completion(
    trie_root: TrieNode,
    registry: list[Path],
    *,
    query_cache_capacity: int = DEFAULT_QUERY_CACHE_CAPACITY,
) -> None:
    """Configure the initialized data used by completion requests.

    Args:
        trie_root: Root of the suffix trie to search.
        registry: File paths indexed by ``SentenceMetadata.file_id``.
        query_cache_capacity: Maximum number of query results to retain.
    """
    global _trie_root, _file_registry, _query_cache
    _trie_root = trie_root
    _file_registry = list(registry)
    _query_cache = QueryResultCache(query_cache_capacity)


def get_query_cache_info() -> QueryCacheInfo:
    """Return current autocomplete query-cache statistics.

    Returns:
        A read-only snapshot of capacity, occupancy, hits, and misses.
    """
    return _query_cache.info()


def _best_scores_by_sentence(
    trie_root: TrieNode,
    normalized_prefix: str,
    max_results: int | None = None
) -> dict[SentenceMetadata, tuple[SentenceMetadata, int]]:
    """Retain the highest-scoring search path for each sentence occurrence.

    Args:
        trie_root: Root of the suffix trie to search.
        normalized_prefix: Normalized, non-empty user input.

    Returns:
        Sentence metadata and its best score, keyed by file and line indexes.
    """
    best_results: dict[SentenceMetadata, tuple[SentenceMetadata, int]] = {}

    for match in search(trie_root, normalized_prefix, max_results):
        score = calculate_score(len(normalized_prefix), match.correction)
        for sentence_ref in match.sentence_refs:
            key = sentence_ref
            previous = best_results.get(key)
            if previous is None or score > previous[1]:
                best_results[key] = (sentence_ref, score)

    return best_results


from src.models import Correction, CorrectionType

def get_valid_match_correction(query: str, text: str, q_idx: int = 0, t_idx: int = 0, current_corr: Correction | None = None) -> tuple[bool, Correction | None]:
    """Check if query is a valid fuzzy prefix of text with at most 1 error, returning the best correction."""
    while q_idx < len(query) and t_idx < len(text):
        if query[q_idx] == text[t_idx]:
            q_idx += 1
            t_idx += 1
        else:
            if current_corr is not None:
                return False, None
                
            # Deletion: query has extra char, we skip it to match text
            del_corr = Correction(CorrectionType.DELETION, q_idx + 1)
            is_match, final_corr = get_valid_match_correction(query, text, q_idx + 1, t_idx, del_corr)
            if is_match: return True, final_corr
            
            # Insertion: query is missing a char, text advances
            ins_corr = Correction(CorrectionType.INSERTION, q_idx + 1)
            is_match, final_corr = get_valid_match_correction(query, text, q_idx, t_idx + 1, ins_corr)
            if is_match: return True, final_corr
            
            # Replacement: query char replaced to match text char
            rep_corr = Correction(CorrectionType.REPLACEMENT, q_idx + 1)
            is_match, final_corr = get_valid_match_correction(query, text, q_idx + 1, t_idx + 1, rep_corr)
            if is_match: return True, final_corr
            
            return False, None
            
    if q_idx == len(query):
        return True, current_corr
        
    remaining = len(query) - q_idx
    if current_corr is None and remaining == 1:
        # One extra char at the very end of query
        return True, Correction(CorrectionType.DELETION, q_idx + 1)
        
    return False, None


def get_fuzzy_substring_correction(query: str, text: str) -> tuple[bool, Correction | None]:
    """Check if query fuzzy matches ANY word-boundary suffix, returning the correction."""
    is_match, corr = get_valid_match_correction(query, text)
    if is_match:
        return True, corr
        
    for i in range(1, len(text)):
        if text[i-1] == " ":
            is_match, corr = get_valid_match_correction(query, text[i:])
            if is_match:
                return True, corr
    return False, None


def get_best_k_completions(
    prefix: str,
    max_results: int | None = None
) -> list[AutoCompleteData]:
    """Return the five best sentence completions for a user prefix.

    Args:
        prefix: Raw text typed by the user.
        max_results: Optional limit on the number of trie nodes to explore.

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

    cached_completions = _query_cache.get(normalized_prefix)
    if cached_completions is not None:
        return cached_completions

    # 1. Group candidates by score to avoid processing lower scores if we have enough
    from collections import defaultdict
    best_scores = _best_scores_by_sentence(_trie_root, normalized_prefix, max_results)
    score_buckets = defaultdict(list)
    for metadata, score in best_scores.values():
        score_buckets[score].append(metadata)

    completions = []
    from src.utils import get_original_sentences_batched

    # 2. Batch fetch ALL required sentences from disk at once
    # This prevents opening and scanning the same file multiple times for different score buckets
    all_metadata = []
    for bucket in score_buckets.values():
        all_metadata.extend(bucket)
    
    fetched_sentences = get_original_sentences_batched(all_metadata, _file_registry)

    # 3. Iterate from highest score to lowest
    for score in sorted(score_buckets.keys(), reverse=True):
        bucket_metadata = score_buckets[score]
        
        bucket_completions = []
        for metadata in bucket_metadata:
            sentence = fetched_sentences.get(metadata)
            if sentence is None:
                continue
                
            final_score = score
            # Fine Filter: If query exceeded trie depth, verify the match manually
            if len(normalized_prefix) > 15:
                normalized_sentence = normalize_text(sentence)
                is_match, real_corr = get_fuzzy_substring_correction(normalized_prefix, normalized_sentence)
                if not is_match:
                    continue
                final_score = calculate_score(len(normalized_prefix), real_corr)
                    
            bucket_completions.append(
                AutoCompleteData(
                    completed_sentence=sentence,
                    source_text=str(_file_registry[get_file_id(metadata)]),
                    offset=get_line_number(metadata),
                    score=final_score,
                )
            )
            
        # Sort this bucket alphabetically to break score ties
        bucket_completions.sort(
            key=lambda c: (c.completed_sentence, c.source_text, c.offset)
        )
        
        completions.extend(bucket_completions)
        
        # If we have collected enough highly-scored completions, we can stop processing lower buckets!
        # We check for >= 15 instead of 5 to ensure that even if the Fine Filter lowers
        # some scores, we still safely capture the true top 5 after sorting.
        if len(completions) >= 15:
            break

    # Re-sort everything because Fine Filter might have lowered some scores
    completions.sort(
        key=lambda c: (
            -c.score,
            c.completed_sentence,
            c.source_text,
            c.offset,
        )
    )

    results = completions[:5]
    _query_cache.put(normalized_prefix, results)
    return results
