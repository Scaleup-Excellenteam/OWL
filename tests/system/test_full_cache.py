"""Read-only integrity, determinism, golden, and latency tests at full scale."""

from __future__ import annotations

import json

from tests.system.full_cache_support import (
    CACHE_PATH,
    GOLDEN_PATH,
    exercise_full_cache,
    load_full_cache_read_only,
)


def test_existing_full_cache_matches_reviewed_golden_and_reports_latency() -> None:
    """Validate the existing cache without rebuilding or timing assertions."""
    cache_before = (CACHE_PATH.stat().st_size, CACHE_PATH.stat().st_mtime_ns)
    load_full_cache_read_only()
    actual_golden, summary = exercise_full_cache()
    cache_after = (CACHE_PATH.stat().st_size, CACHE_PATH.stat().st_mtime_ns)

    with GOLDEN_PATH.open(encoding="utf-8") as stream:
        expected_golden = json.load(stream)
    snapshot_matches = actual_golden == expected_golden
    summary["exact_snapshot_agreement"] = snapshot_matches
    print("\nFULL_CACHE_REPORT=" + json.dumps(summary, sort_keys=True))

    assert cache_after == cache_before, "full-cache test modified trie_cache.pkl"
    assert summary["invalid_results"] == 0
    assert summary["score_errors"] == 0
    assert summary["path_offset_errors"] == 0
    assert summary["non_deterministic_queries"] == 0
    assert snapshot_matches
