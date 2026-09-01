"""Explicitly rebuild the committed bounded-corpus trie cache."""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

from src.offline.trie_builder import build_suffix_trie


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MANIFEST_PATH = DATA_DIR / "sample_manifest.json"
CACHE_PATH = DATA_DIR / "sample_trie_cache.pkl"
METADATA_PATH = DATA_DIR / "sample_cache_metadata.json"


def _load_manifest() -> dict[str, object]:
    """Load the committed sample selection manifest.

    Returns:
        Parsed sample manifest.
    """
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def _file_sha256(path: Path) -> str:
    """Calculate a source file fingerprint.

    Args:
        path: File to fingerprint.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_saved_sample_cache() -> None:
    """Build and save the bounded trie plus reproducibility metadata.

    Raises:
        FileNotFoundError: If a selected copied source file is absent.
    """
    manifest = _load_manifest()
    relative_files = [Path(value) for value in manifest["files"]]
    max_lines = int(manifest["max_non_empty_lines_per_file"])
    registry = [CORPUS_DIR / relative_path for relative_path in relative_files]

    records: list[tuple[int, int, str]] = []
    fingerprints: dict[str, str] = {}
    selected_counts: dict[str, int] = {}
    for file_id, (relative_path, source_path) in enumerate(
        zip(relative_files, registry, strict=True)
    ):
        if not source_path.is_file():
            raise FileNotFoundError(f"sample source is missing: {source_path}")

        fingerprints[relative_path.as_posix()] = _file_sha256(source_path)
        selected_count = 0
        with source_path.open(encoding="utf-8", errors="replace") as stream:
            for line_number, raw_line in enumerate(stream):
                if not raw_line.strip():
                    continue
                records.append((file_id, line_number, raw_line))
                selected_count += 1
                if selected_count == max_lines:
                    break
        selected_counts[relative_path.as_posix()] = selected_count

    trie_root = build_suffix_trie(records)
    portable_registry = [path.relative_to(PROJECT_ROOT) for path in registry]
    with CACHE_PATH.open("wb") as stream:
        pickle.dump(
            (trie_root, portable_registry),
            stream,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    metadata = {
        "schema_version": 1,
        "record_count": len(records),
        "max_non_empty_lines_per_file": max_lines,
        "selected_non_empty_line_counts": selected_counts,
        "source_sha256": fingerprints,
        "cache_sha256": _file_sha256(CACHE_PATH),
    }
    with METADATA_PATH.open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> None:
    """Rebuild the saved sample cache when invoked explicitly."""
    build_saved_sample_cache()
    print(f"Saved sample cache: {CACHE_PATH}")


if __name__ == "__main__":
    main()
