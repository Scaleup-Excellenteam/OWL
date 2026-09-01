"""Read-only helpers for full-cache validation and measurement."""

from __future__ import annotations

import json
import pickle
import statistics
import time
from pathlib import Path
from typing import Any

from src.models import AutoCompleteData, TrieNode
from src.online.completion import configure_completion, get_best_k_completions
from tests.system.oracle import best_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = PROJECT_ROOT / "Archive"
CACHE_PATH = PROJECT_ROOT / "trie_cache.pkl"
DATA_DIR = Path(__file__).resolve().parent / "data"
QUERIES_PATH = DATA_DIR / "full_cache_queries.json"
GOLDEN_PATH = DATA_DIR / "full_cache_golden.json"
CANDIDATE_PATH = DATA_DIR / "full_cache_golden.candidate.json"


def load_queries() -> list[dict[str, str]]:
    """Load the fixed full-cache query definitions.

    Returns:
        Query identifiers and raw query strings.
    """
    with QUERIES_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    return payload["queries"]


def load_full_cache_read_only() -> tuple[TrieNode, list[Path]]:
    """Load and configure the existing project cache without modifying it.

    Returns:
        Full trie root and source registry.

    Raises:
        FileNotFoundError: If the required existing cache is absent.
    """
    if not CACHE_PATH.is_file():
        raise FileNotFoundError(
            f"required full cache is missing: {CACHE_PATH}; refusing to rebuild it"
        )
    with CACHE_PATH.open("rb") as stream:
        trie_root, registry = pickle.load(stream)
    configure_completion(trie_root, registry)
    return trie_root, registry


def _resolved_source(source_text: str) -> Path:
    """Resolve a cache result source and require it to remain in Archive.

    Args:
        source_text: Source path returned by the public API.

    Returns:
        Resolved source path.
    """
    source = Path(source_text)
    resolved = source.resolve() if source.is_absolute() else (PROJECT_ROOT / source).resolve()
    if not resolved.is_relative_to(ARCHIVE_DIR.resolve()):
        raise AssertionError(f"result source escapes Archive: {source_text}")
    return resolved


def _original_line(path: Path, offset: int) -> str:
    """Read one physical zero-based source line.

    Args:
        path: Existing Archive source path.
        offset: Physical zero-based line number.

    Returns:
        Original line without its newline terminator.

    Raises:
        AssertionError: If the offset does not exist.
    """
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line_number, raw_line in enumerate(stream):
            if line_number == offset:
                return raw_line.rstrip("\r\n")
    raise AssertionError(f"offset {offset} does not exist in {path}")


def canonical_result(result: AutoCompleteData) -> dict[str, object]:
    """Serialize a public result with an Archive-relative source path.

    Args:
        result: Public API result.

    Returns:
        Deterministic JSON-ready result mapping.
    """
    source = _resolved_source(result.source_text)
    return {
        "completed_sentence": result.completed_sentence,
        "source_text": f"Archive/{source.relative_to(ARCHIVE_DIR).as_posix()}",
        "offset": result.offset,
        "score": result.score,
    }


def validate_results(query: str, results: list[AutoCompleteData]) -> dict[str, int]:
    """Independently validate returned locations, matches, scores, and order.

    Args:
        query: Raw fixed query.
        results: Results returned by the public API.

    Returns:
        Validation error counts by category.
    """
    errors = {"invalid_results": 0, "score_errors": 0, "path_offset_errors": 0}
    if len(results) > 5:
        errors["invalid_results"] += len(results) - 5

    for result in results:
        try:
            source = _resolved_source(result.source_text)
            if not source.is_file():
                raise AssertionError(f"source does not exist: {source}")
            original = _original_line(source, result.offset)
            if original != result.completed_sentence:
                raise AssertionError("returned sentence differs from source line")
        except (AssertionError, OSError):
            errors["path_offset_errors"] += 1
            continue

        expected_score = best_score(query, original)
        if expected_score is None:
            errors["invalid_results"] += 1
        elif expected_score != result.score:
            errors["score_errors"] += 1

    serialized = [canonical_result(result) for result in results]
    expected_order = sorted(
        serialized,
        key=lambda result: (
            -int(result["score"]),
            str(result["completed_sentence"]),
            str(result["source_text"]),
            int(result["offset"]),
        ),
    )
    if serialized != expected_order:
        errors["invalid_results"] += 1
    return errors


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    """Calculate a deterministic nearest-rank percentile.

    Args:
        values: Non-empty measurement values.
        percentile: Fraction from zero through one.

    Returns:
        Selected percentile value.
    """
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * percentile + 0.999999999))
    return ordered[rank - 1]


def exercise_full_cache(rounds: int = 5) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate, repeat, and time every fixed full-cache query.

    Args:
        rounds: Number of measured rounds after warm-up.

    Returns:
        Golden-ready responses and measurement summary.
    """
    queries = load_queries()
    responses: dict[str, list[dict[str, object]]] = {}
    validation_totals = {
        "invalid_results": 0,
        "score_errors": 0,
        "path_offset_errors": 0,
    }
    nondeterministic_queries: set[str] = set()
    timings: list[tuple[str, float]] = []

    for query_spec in queries:
        query_id = query_spec["id"]
        query = query_spec["query"]
        warm_results = get_best_k_completions(query)
        responses[query_id] = [canonical_result(result) for result in warm_results]
        validation = validate_results(query, warm_results)
        for name, count in validation.items():
            validation_totals[name] += count

    for _ in range(rounds):
        for query_spec in queries:
            query_id = query_spec["id"]
            query = query_spec["query"]
            started = time.perf_counter_ns()
            results = get_best_k_completions(query)
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
            timings.append((query_id, elapsed_ms))
            if [canonical_result(result) for result in results] != responses[query_id]:
                nondeterministic_queries.add(query_id)

    latency_values = [elapsed for _, elapsed in timings]
    slowest_id, maximum_ms = max(timings, key=lambda item: item[1])
    golden = {
        "schema_version": 1,
        "archive_file_count": sum(1 for path in ARCHIVE_DIR.rglob("*.txt") if path.is_file()),
        "cache_file": CACHE_PATH.name,
        "queries": [
            {
                "id": query_spec["id"],
                "query": query_spec["query"],
                "results": responses[query_spec["id"]],
            }
            for query_spec in queries
        ],
    }
    summary = {
        "number_of_queries": len(queries),
        "valid_results": sum(len(results) for results in responses.values())
        - validation_totals["invalid_results"],
        **validation_totals,
        "non_deterministic_queries": len(nondeterministic_queries),
        "p50_latency_ms": round(statistics.median(latency_values), 3),
        "p95_latency_ms": round(percentile_nearest_rank(latency_values, 0.95), 3),
        "maximum_latency_ms": round(maximum_ms, 3),
        "slowest_query": slowest_id,
    }
    return golden, summary
