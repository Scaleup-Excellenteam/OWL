"""Generate reviewable full-cache golden candidates and measurements."""

from __future__ import annotations

import json

from tests.system.full_cache_support import (
    CANDIDATE_PATH,
    exercise_full_cache,
    load_full_cache_read_only,
)


def main() -> None:
    """Load the existing cache and write a validated candidate snapshot."""
    load_full_cache_read_only()
    golden, summary = exercise_full_cache()
    with CANDIDATE_PATH.open("w", encoding="utf-8") as stream:
        json.dump(golden, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps(summary, indent=2))
    print(f"Review candidate: {CANDIDATE_PATH}")


if __name__ == "__main__":
    main()
