"""Fixtures for deterministic autocomplete system tests."""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path

import pytest

from src.models import AutoCompleteData, TrieNode
from src.online.completion import configure_completion
from tests.system.oracle import CorpusLine, OracleResult, read_bounded_corpus


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MANIFEST_PATH = DATA_DIR / "sample_manifest.json"
CACHE_PATH = DATA_DIR / "sample_trie_cache.pkl"
METADATA_PATH = DATA_DIR / "sample_cache_metadata.json"


def _sha256(path: Path) -> str:
    """Calculate a file SHA-256 digest.

    Args:
        path: File to fingerprint.

    Returns:
        Lowercase hexadecimal digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.fixture(scope="session")
def sample_manifest() -> dict[str, object]:
    """Load the committed sample selection manifest.

    Returns:
        Parsed manifest dictionary.
    """
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


@pytest.fixture(scope="session")
def bounded_corpus(sample_manifest: dict[str, object]) -> list[CorpusLine]:
    """Load only the bounded source lines represented by the sample cache.

    Args:
        sample_manifest: Parsed sample selection manifest.

    Returns:
        Independent-oracle corpus lines.
    """
    return read_bounded_corpus(
        CORPUS_DIR,
        list(sample_manifest["files"]),
        int(sample_manifest["max_non_empty_lines_per_file"]),
    )


@pytest.fixture(scope="session")
def saved_sample_system() -> tuple[TrieNode, list[Path]]:
    """Load and verify the committed sample cache without rebuilding it.

    Returns:
        Saved trie root and resolved copied-source registry.

    Raises:
        AssertionError: If the cache or a copied source differs from metadata.
    """
    with METADATA_PATH.open(encoding="utf-8") as stream:
        metadata = json.load(stream)
    assert _sha256(CACHE_PATH) == metadata["cache_sha256"], (
        "saved sample cache changed; explicitly run "
        "`.venv/bin/python -m tests.system.build_sample_cache`"
    )

    for relative_file, expected_hash in metadata["source_sha256"].items():
        assert _sha256(CORPUS_DIR / relative_file) == expected_hash, (
            f"copied sample source changed: {relative_file}"
        )

    with CACHE_PATH.open("rb") as stream:
        trie_root, portable_registry = pickle.load(stream)
    registry = [PROJECT_ROOT / path for path in portable_registry]
    return trie_root, registry


@pytest.fixture()
def configured_sample_system(
    saved_sample_system: tuple[TrieNode, list[Path]],
) -> tuple[TrieNode, list[Path]]:
    """Configure the public completion API with the saved sample cache.

    Args:
        saved_sample_system: Verified saved sample trie and registry.

    Returns:
        The configured trie and registry.
    """
    trie_root, registry = saved_sample_system
    configure_completion(trie_root, registry)
    return trie_root, registry


def canonicalize_sample_results(
    results: list[AutoCompleteData],
) -> list[OracleResult]:
    """Map public results from copied paths back to Archive-relative paths.

    Args:
        results: Values returned by the public completion API.

    Returns:
        Results in the same representation used by the independent oracle.
    """
    canonical = []
    for result in results:
        relative_path = Path(result.source_text).resolve().relative_to(CORPUS_DIR)
        canonical.append(
            OracleResult(
                completed_sentence=result.completed_sentence,
                source_text=f"Archive/{relative_path.as_posix()}",
                offset=result.offset,
                score=result.score,
            )
        )
    return canonical
